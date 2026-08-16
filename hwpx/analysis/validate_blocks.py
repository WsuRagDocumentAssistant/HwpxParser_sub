#================================================
# validate_blocks.py
# Stage 9-A: Validator 분리
# Stage 9-B: Validator 경량 보강
#   - caption/footnote orphan 검사를 source_xml_path 문자열 매칭으로 실동작화
#   - style cluster-depth consistency 통계 (blocks.json만으로 독립 재계산)
#   - native numbering/bullet 통계 + numbering level jump 검사
#
# blocks.json을 읽기 전용 단일 진실 소스로 사용해
# warnings.json / quality_report.json을 생성한다.
#
# blocks.json은 절대 수정하지 않는다.
# 신규 warning은 여기서만 생성되며 blocks.json에는 반영되지 않는다.
#================================================

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .pipeline_models import (
    BlocksDocument,
    TableInternalBlocks,
    ValidationReport,
)

import logging

# 라이브러리는 조용한 것이 기본이다. 단계 보고를 보려면 쓰는 쪽에서
# logging 을 켠다. tools 는 그렇게 하고 있다.
log = logging.getLogger(__name__)


_SEVERITY_MAP = {
    "missing_table_hierarchy": "error",
    "table_id_mismatch": "error",

    "low_record_confidence": "warning",
    "missing_header_rows": "warning",
    "raw_only_table": "warning",
    "floating_anchor_unresolved": "warning",
    "depth_jump_without_constraint_decision": "warning",

    "unchanged_depth_jump": "info",
    "nested_table_present": "info",
    "irregular_grid": "info",
    "orphan_caption_uncertain": "info",
    "orphan_footnote_uncertain": "info",
    "linebreak_depth_candidate_unused": "info",

    # Stage 9-B
    "orphan_caption_unresolved": "warning",
    "orphan_footnote_unresolved": "warning",
    "cluster_depth_inconsistent": "warning",
    "native_numbering_level_jump": "warning",
}

# preferred_depth로 인정할 클러스터 내 점유율 (기준 7)
_PREFERRED_DEPTH_RATIO = 0.8

# numbering level jump 경고 임계 (기준 9)
_NUMBERING_LEVEL_JUMP_THRESHOLD = 2

# table_hierarchy_ref.quality_warnings -> warning_code 변환 (기준 7)
_TABLE_WARNING_CODE_MAP = {
    "low_record_confidence": "low_record_confidence",
    "missing_header_rows": "missing_header_rows",
    "raw_only_table": "raw_only_table",
    "nested_table_present": "nested_table_present",
    "irregular_grid": "irregular_grid",
}


def _text_preview(block: dict[str, Any]) -> str | None:
    text = block.get("normalized_text") or block.get("text_content")
    return text[:40] if text else None


def _make_warning(
    warning_code: str,
    block: dict[str, Any],
    source_stage: str,
    message: str,
    evidence: list[str],
) -> dict[str, Any]:
    return {
        "warning_code": warning_code,
        "severity": _SEVERITY_MAP.get(warning_code, "warning"),
        "block_id": block.get("block_id"),
        "source_stage": source_stage,
        "message": message,
        "evidence": evidence,
        "text_preview": _text_preview(block),
    }


#------------------------------------------------
# 기준 5, 6: depth_jump -> unchanged_depth_jump / depth_jump_without_constraint_decision
#------------------------------------------------

def _check_depth_jump(block: dict[str, Any], warnings: list[dict[str, Any]]) -> None:
    has_depth_jump = any(
        w.startswith("depth_jump") and not w.startswith("depth_jump_without")
        for w in (block.get("warnings") or [])
    )
    if not has_depth_jump:
        return

    decision = block.get("depth_constraint_decision")
    if decision is not None:
        warnings.append(_make_warning(
            "unchanged_depth_jump",
            block,
            source_stage="stage8b",
            message=(
                f"depth jump retained by constraint decision "
                f"(action={decision.get('action')}, "
                f"old_depth={decision.get('old_depth')}, "
                f"relaxation_candidate_depth={decision.get('relaxation_candidate_depth')})"
            ),
            evidence=list(decision.get("reasons") or []),
        ))
    else:
        warnings.append(_make_warning(
            "depth_jump_without_constraint_decision",
            block,
            source_stage="stage8a_or_before",
            message="depth_jump warning present but no Stage 8-B constraint decision found",
            evidence=list(block.get("warnings") or []),
        ))


#------------------------------------------------
# 기준 7, 8, 9: table_hierarchy_ref 관련 warning
#------------------------------------------------

def _check_table_hierarchy_ref(block: dict[str, Any], warnings: list[dict[str, Any]]) -> None:
    ref = block.get("table_hierarchy_ref")
    if ref is None:
        return

    # 기준 8: match_status == missing -> error
    if ref.get("match_status") == "missing":
        warnings.append(_make_warning(
            "missing_table_hierarchy",
            block,
            source_stage="stage7_5a",
            message=f"table block source_table_id={ref.get('table_id')} not found in tables_hierarchical.json",
            evidence=["match_status=missing"],
        ))
        return

    # 기준 9: 보조 검증 불일치 -> table_id_mismatch (error)
    ref_warnings = ref.get("quality_warnings") or []
    if "table_id_mismatch" in ref_warnings:
        warnings.append(_make_warning(
            "table_id_mismatch",
            block,
            source_stage="stage7_5a",
            message=f"table_id={ref.get('table_id')} matched but section/table/xml id auxiliary check failed",
            evidence=["table_id_mismatch in table_hierarchy_ref.quality_warnings"],
        ))

    # 기준 7: 나머지 quality_warnings -> table 관련 warning 변환
    for code in ref_warnings:
        if code == "table_id_mismatch":
            continue
        mapped = _TABLE_WARNING_CODE_MAP.get(code)
        if mapped is None:
            continue
        warnings.append(_make_warning(
            mapped,
            block,
            source_stage="stage7_5a",
            message=(
                f"table_id={ref.get('table_id')} table_type={ref.get('table_type')} "
                f"record_status={ref.get('record_status')}: {code}"
            ),
            evidence=[f"table_hierarchy_ref.quality_warnings contains {code}"],
        ))


#------------------------------------------------
# 기준 10: floating anchor 미해결
#------------------------------------------------

def _check_floating_anchor(block: dict[str, Any], warnings: list[dict[str, Any]]) -> None:
    layout = block.get("layout_position") or {}
    if layout.get("anchor_type") != "floating":
        return

    resolution = block.get("anchor_resolution")

    # Stage 4-B가 anchor를 확정(resolved)한 경우에는 경고를 생성하지 않는다
    if resolution is not None and resolution.get("status") == "resolved":
        return

    if resolution is not None:
        # unresolved / ambiguous: Stage 4-B가 실행됐지만 anchor를 확정하지 못함
        warnings.append(_make_warning(
            "floating_anchor_unresolved",
            block,
            source_stage="stage4b",
            message=(
                f"floating object anchor resolution status="
                f"{resolution.get('status')} (reason={resolution.get('reason')})"
            ),
            evidence=[
                f"anchor_section_index={resolution.get('anchor_section_index')}",
                f"anchor_paragraph_index={resolution.get('anchor_paragraph_index')}",
            ],
        ))
    else:
        # Stage 4-B가 아직 실행되지 않은 경우 (하위 호환)
        warnings.append(_make_warning(
            "floating_anchor_unresolved",
            block,
            source_stage="stage4_pending",
            message=(
                "floating object detected but reading-order re-anchoring "
                "(Stage 4-B) has not been run; xml order is used as-is"
            ),
            evidence=[f"anchor_type=floating, treat_as_char={layout.get('treat_as_char')}"],
        ))


#------------------------------------------------
# Stage 9-B 기준 5: orphan 검사 (caption/footnote만, page_footer 제외)
#
# anchor_paragraph_path가 있으면 별도 파싱 없이 paragraph block의
# source_xml_path와 문자열 그대로 비교한다 (기준 2).
#------------------------------------------------

def _check_orphan(
    block: dict[str, Any],
    warnings: list[dict[str, Any]],
    paragraph_paths: set[str],
) -> str | None:
    """
    orphan 판정 결과를 반환한다: "anchored" | "uncertain" | "unresolved" | None(대상 아님).
    """
    block_type = block.get("block_type")
    if block_type not in ("caption", "footnote"):
        return None

    anchor_path = block.get("anchor_paragraph_path")
    kind = "caption" if block_type == "caption" else "footnote"

    if not anchor_path:
        warnings.append(_make_warning(
            f"orphan_{kind}_uncertain",
            block,
            source_stage="stage9b",
            message=(
                f"{block_type} block has no anchor_paragraph_path; "
                "orphan status is uncertain, not confirmed"
            ),
            evidence=["anchor_paragraph_path is missing"],
        ))
        return "uncertain"

    if anchor_path in paragraph_paths:
        return "anchored"

    warnings.append(_make_warning(
        f"orphan_{kind}_unresolved",
        block,
        source_stage="stage9b",
        message=(
            f"{block_type} block has anchor_paragraph_path={anchor_path} "
            "but no matching paragraph block was found"
        ),
        evidence=[f"anchor_paragraph_path={anchor_path} not in any paragraph.source_xml_path"],
    ))
    return "unresolved"


#------------------------------------------------
# Stage 9-B 기준 7: style cluster-depth consistency (독립 재계산)
#
# Stage 8-B 내부 함수를 import하지 않고 blocks.json만으로 계산한다.
#------------------------------------------------

def _check_cluster_depth_consistency(
    blocks: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    depth_counts: dict[str, Counter] = defaultdict(Counter)
    representative_block: dict[str, dict[str, Any]] = {}

    for block in blocks:
        if block.get("semantic_role") != "section_heading":
            continue
        cluster_id = (block.get("style_features") or {}).get("style_cluster_id")
        if cluster_id is None:
            continue
        depth_counts[cluster_id][block.get("depth")] += 1
        representative_block.setdefault(cluster_id, block)

    clusters_report: dict[str, Any] = {}
    total_weighted_ratio = 0.0
    total_members = 0

    for cluster_id, counts in depth_counts.items():
        member_count = sum(counts.values())
        preferred_depth, top_count = counts.most_common(1)[0]
        ratio = top_count / member_count

        clusters_report[cluster_id] = {
            "member_count": member_count,
            "depth_distribution": {str(k): v for k, v in counts.items()},
            "preferred_depth": preferred_depth,
            "preferred_depth_ratio": round(ratio, 3),
        }

        total_weighted_ratio += ratio * member_count
        total_members += member_count

        if member_count >= 2 and ratio < _PREFERRED_DEPTH_RATIO:
            warnings.append(_make_warning(
                "cluster_depth_inconsistent",
                representative_block[cluster_id],
                source_stage="stage9b",
                message=(
                    f"style cluster {cluster_id} has inconsistent heading depth: "
                    f"preferred_depth={preferred_depth} ratio={ratio:.2f} "
                    f"(member_count={member_count})"
                ),
                evidence=[f"depth_distribution={dict(counts)}"],
            ))

    consistency_score = (
        round(total_weighted_ratio / total_members, 3) if total_members else 1.0
    )

    return {
        "clusters": clusters_report,
        "cluster_consistency_score": consistency_score,
        "inconsistent_cluster_count": sum(
            1 for c in clusters_report.values()
            if c["member_count"] >= 2 and c["preferred_depth_ratio"] < _PREFERRED_DEPTH_RATIO
        ),
    }


#------------------------------------------------
# Stage 9-B 기준 8, 9: native numbering/bullet 통계 + level jump 검사
#
# 문자열/정규식 추론 없이 style_features의 native 필드만 사용한다.
#------------------------------------------------

def _check_native_numbering(
    blocks: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    numbering_block_count = 0
    bullet_block_count = 0
    level_dist: Counter = Counter()

    for block in blocks:
        sf = block.get("style_features") or {}
        heading_type = sf.get("heading_type")
        level = sf.get("numbering_level")

        if heading_type == "NUMBER":
            numbering_block_count += 1
        elif heading_type == "BULLET":
            bullet_block_count += 1

        if level is not None:
            level_dist[level] += 1

    # 기준 9: 같은 section 안에서 연속된 list_item 간 numbering_level 점프 검사
    jump_warning_count = 0
    prev_by_section: dict[int, int] = {}

    for block in blocks:
        role = block.get("semantic_role")
        block_type = block.get("block_type")
        if role != "list_item" and block_type != "list_item":
            continue

        section_index = block.get("section_index")
        level = (block.get("style_features") or {}).get("numbering_level")
        if not isinstance(level, int):
            continue

        prev_level = prev_by_section.get(section_index)
        if prev_level is not None and (level - prev_level) >= _NUMBERING_LEVEL_JUMP_THRESHOLD:
            warnings.append(_make_warning(
                "native_numbering_level_jump",
                block,
                source_stage="stage9b",
                message=(
                    f"numbering_level jumped from {prev_level} to {level} "
                    f"between consecutive list_item blocks in section {section_index}"
                ),
                evidence=[f"prev_numbering_level={prev_level}", f"numbering_level={level}"],
            ))
            jump_warning_count += 1

        prev_by_section[section_index] = level

    return {
        "numbering_block_count": numbering_block_count,
        "bullet_block_count": bullet_block_count,
        "numbering_level_distribution": {str(k): v for k, v in level_dist.items()},
        "native_numbering_sequence_warning_count": jump_warning_count,
    }


#------------------------------------------------
# 기준 12: lineBreak 기반 depth 후보 미사용
#------------------------------------------------

def _check_linebreak_unused(block: dict[str, Any], warnings: list[dict[str, Any]]) -> None:
    lf = block.get("line_features") or {}
    if not lf.get("line_depth_candidate"):
        return

    signals = [
        s
        for candidate in (block.get("depth_candidates") or [])
        for s in candidate.get("signals", [])
    ]
    has_line_signal = any("line" in s.lower() for s in signals)
    if has_line_signal:
        return

    warnings.append(_make_warning(
        "linebreak_depth_candidate_unused",
        block,
        source_stage="stage8_pending",
        message=(
            f"line_style_variation={lf.get('line_style_variation')} suggests "
            "possible sub-depth structure inside this paragraph, "
            "but no depth candidate reflects it yet"
        ),
        evidence=[f"line_features={lf}"],
    ))


#------------------------------------------------
# warnings.json 생성
#------------------------------------------------

def _collect_warnings(blocks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paragraph_paths = {
        b["source_xml_path"] for b in blocks if b.get("block_type") == "paragraph"
    }
    warnings: list[dict[str, Any]] = []

    orphan_stats = {
        "caption_block_count": 0,
        "footnote_block_count": 0,
        "anchored_caption_count": 0,
        "anchored_footnote_count": 0,
        "orphan_caption_uncertain_count": 0,
        "orphan_footnote_uncertain_count": 0,
        "orphan_caption_unresolved_count": 0,
        "orphan_footnote_unresolved_count": 0,
    }

    for block in blocks:
        _check_depth_jump(block, warnings)
        _check_table_hierarchy_ref(block, warnings)
        _check_floating_anchor(block, warnings)
        _check_linebreak_unused(block, warnings)

        block_type = block.get("block_type")
        result = _check_orphan(block, warnings, paragraph_paths)
        if block_type == "caption":
            orphan_stats["caption_block_count"] += 1
            if result == "anchored":
                orphan_stats["anchored_caption_count"] += 1
            elif result == "uncertain":
                orphan_stats["orphan_caption_uncertain_count"] += 1
            elif result == "unresolved":
                orphan_stats["orphan_caption_unresolved_count"] += 1
        elif block_type == "footnote":
            orphan_stats["footnote_block_count"] += 1
            if result == "anchored":
                orphan_stats["anchored_footnote_count"] += 1
            elif result == "uncertain":
                orphan_stats["orphan_footnote_uncertain_count"] += 1
            elif result == "unresolved":
                orphan_stats["orphan_footnote_unresolved_count"] += 1

    cluster_report = _check_cluster_depth_consistency(blocks, warnings)
    numbering_report = _check_native_numbering(blocks, warnings)

    return warnings, {
        "orphan_anchor_stats": orphan_stats,
        "cluster_depth_consistency": cluster_report,
        "native_numbering_stats": numbering_report,
    }


#------------------------------------------------
# quality_report.json 생성 (기준 13, 14)
#------------------------------------------------

def _build_quality_report(
    quality: dict[str, Any],
    blocks: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    stage9b_stats: dict[str, Any],
    table_internal_stats: dict[str, Any] | None,
) -> dict[str, Any]:

    block_type_dist = Counter(b.get("block_type") for b in blocks)
    role_dist = Counter(b.get("semantic_role") for b in blocks)
    band_dist = Counter(b.get("depth_band") for b in blocks)
    depth_dist = Counter(b.get("depth") for b in blocks)

    table_blocks = [b for b in blocks if b.get("block_type") == "table"]
    table_refs = [b.get("table_hierarchy_ref") for b in table_blocks if b.get("table_hierarchy_ref")]

    top_level_table_type_dist = Counter(r.get("table_type") for r in table_refs)
    top_level_record_status_dist = Counter(r.get("record_status") for r in table_refs)
    table_quality_warning_dist = Counter(
        code for r in table_refs for code in (r.get("quality_warnings") or [])
    )
    match_status_dist = Counter(r.get("match_status") for r in table_refs)

    # 기준 14: blocks.json quality에 이미 있는 전체 hierarchy 통계는 재배치, 없으면 생략
    all_table_hierarchy_stats = (
        (quality.get("table_hierarchy_link") or {}).get("all_table_hierarchy_stats")
    )

    depth_candidate_count_dist = Counter(
        len(b.get("depth_candidates") or []) for b in blocks
    )

    floating_blocks = [
        b for b in blocks
        if (b.get("layout_position") or {}).get("anchor_type") == "floating"
    ]
    floating_type_dist = Counter(b.get("block_type") for b in floating_blocks)

    warning_code_dist = Counter(w["warning_code"] for w in warnings)
    severity_dist = Counter(w["severity"] for w in warnings)

    page_footer_count = sum(1 for b in blocks if b.get("block_type") == "footer")

    return {
        "document": {
            "block_count": len(blocks),
        },
        "block_type_distribution": dict(block_type_dist),
        "semantic_role_distribution": dict(role_dist),
        "depth_band_distribution": dict(band_dist),
        "depth_distribution": {str(k): v for k, v in depth_dist.items()},

        "table_hierarchy_ref": {
            "top_level_block_stats": {
                "table_block_count": len(table_blocks),
                "match_status": dict(match_status_dist),
                "table_type_distribution": dict(top_level_table_type_dist),
                "record_status_distribution": dict(top_level_record_status_dist),
                "table_quality_warning_distribution": dict(table_quality_warning_dist),
            },
            "all_table_hierarchy_stats": all_table_hierarchy_stats,
        },

        "depth_candidates": {
            "candidate_count_distribution": {
                str(k): v for k, v in depth_candidate_count_dist.items()
            },
            **(quality.get("depth_candidates") or {}),
        },

        "depth_constraints": quality.get("depth_constraints") or {},

        "warning_code_distribution": dict(warning_code_dist),
        "severity_distribution": dict(severity_dist),

        "floating_object_stats": {
            "floating_block_count": len(floating_blocks),
            "floating_block_type_distribution": dict(floating_type_dist),
            "unresolved_count": sum(
                1 for w in warnings if w["warning_code"] == "floating_anchor_unresolved"
            ),
            **(quality.get("floating_anchor_resolution") or {}),
        },

        "peripheral_stats": {
            "page_footer_count": page_footer_count,
        },

        # Stage 9-B: blocks.json만으로 독립 재계산한 값 (Stage 8-B 내부 함수 미사용).
        # depth_constraints.cluster_consistency_score(Stage 8-B 산출)와 교차검증용으로 병기한다.
        "cluster_depth_consistency": stage9b_stats["cluster_depth_consistency"],
        "cluster_consistency_score": (
            stage9b_stats["cluster_depth_consistency"]["cluster_consistency_score"]
        ),

        "native_numbering_stats": stage9b_stats["native_numbering_stats"],
        "orphan_anchor_stats": stage9b_stats["orphan_anchor_stats"],

        # Stage 7.5-B 결과 통계 (table_internal_blocks.json이 있을 때만 채워짐)
        "table_internal_ref_stats": table_internal_stats,
    }


#------------------------------------------------
# Stage 7.5-B 결과 통계 (table_internal_blocks.json이 있으면 집계)
#------------------------------------------------

def _build_table_internal_stats(
    table_internal: TableInternalBlocks | None,
) -> dict[str, Any] | None:
    if table_internal is None:
        return None

    internal_blocks = table_internal.internal_blocks
    type_counts = Counter(b.get("internal_block_type") for b in internal_blocks)

    ids = [b.get("internal_block_id") for b in internal_blocks]
    duplicate_count = len(ids) - len(set(ids))

    id_set = set(ids)
    missing_parent_count = sum(
        1 for b in internal_blocks
        if b.get("parent_internal_block_id") is not None
        and b["parent_internal_block_id"] not in id_set
    )

    top_level_tables_with_nested_refs = len({
        b.get("root_table_id")
        for b in internal_blocks
        if b.get("internal_block_type") == "nested_table_ref"
    })

    return {
        "table_internal_block_count": len(internal_blocks),
        "row_group_count": type_counts.get("table_row_group", 0),
        "cell_group_count": type_counts.get("table_cell_group", 0),
        "text_block_count": type_counts.get("table_cell_text", 0),
        "nested_table_ref_count": type_counts.get("nested_table_ref", 0),
        "top_level_tables_with_nested_refs": top_level_tables_with_nested_refs,
        "max_local_depth": max((b.get("local_depth", 0) for b in internal_blocks), default=0),
        "max_absolute_depth": max((b.get("absolute_depth", 0) for b in internal_blocks), default=0),
        "duplicate_internal_block_id_count": duplicate_count,
        "missing_parent_ref_count": missing_parent_count,
    }


#------------------------------------------------
# 진입점
#------------------------------------------------

def validate_blocks(
    blocks_doc: BlocksDocument,
    table_internal: TableInternalBlocks | None = None,
) -> ValidationReport:
    """
    역할: BlocksDocument를 읽기 전용으로 검증해 ValidationReport를 생성한다.
    입력 데이터: blocks_doc(Stage 8-B까지 반영된 BlocksDocument). 이 함수는 blocks를 수정하지 않는다.
    출력 데이터: ValidationReport(warnings/quality_report).
    """
    blocks = blocks_doc.blocks

    # 기준 12: blocks가 읽기 전용임을 before/after 비교로 증명한다
    block_count_before = len(blocks)
    depth_snapshot_before = {
        b["block_id"]: b.get("depth") for b in blocks
    }
    reading_order_snapshot_before = {
        b["block_id"]: b.get("reading_order_index") for b in blocks
    }

    warnings, stage9b_stats = _collect_warnings(blocks)
    table_internal_stats = _build_table_internal_stats(table_internal)
    quality_report = _build_quality_report(
        blocks_doc.quality, blocks, warnings, stage9b_stats, table_internal_stats,
    )

    block_count_after = len(blocks)
    depth_changed_count = sum(
        1 for b in blocks if depth_snapshot_before.get(b["block_id"]) != b.get("depth")
    )
    reading_order_changed_count = sum(
        1 for b in blocks
        if reading_order_snapshot_before.get(b["block_id"]) != b.get("reading_order_index")
    )
    anchor_paragraph_path_copied_count = sum(
        1 for b in blocks if b.get("anchor_paragraph_path")
    )

    _print_summary_log(
        warnings, quality_report,
        block_count_before, block_count_after,
        depth_changed_count, reading_order_changed_count,
        anchor_paragraph_path_copied_count,
    )

    return ValidationReport(warnings=warnings, quality_report=quality_report)


def _print_summary_log(
    warnings: list[dict[str, Any]],
    quality_report: dict[str, Any],
    block_count_before: int,
    block_count_after: int,
    depth_changed_count: int,
    reading_order_changed_count: int,
    anchor_paragraph_path_copied_count: int,
) -> None:
    severity_dist = Counter(w["severity"] for w in warnings)
    code_dist = Counter(w["warning_code"] for w in warnings)

    orphan_stats = quality_report["orphan_anchor_stats"]
    numbering_stats = quality_report["native_numbering_stats"]
    orphan_warning_count = (
        orphan_stats["orphan_caption_uncertain_count"]
        + orphan_stats["orphan_footnote_uncertain_count"]
        + orphan_stats["orphan_caption_unresolved_count"]
        + orphan_stats["orphan_footnote_unresolved_count"]
    )

    log.info("=== Stage 9-A/9-B: Validator 분리 및 경량 보강 결과 ===")
    log.info(f"block_count before/after: {block_count_before} / {block_count_after}")
    log.info(f"depth_changed_count: {depth_changed_count}")
    log.info(f"reading_order_changed_count: {reading_order_changed_count}")
    log.info(f"anchor_paragraph_path copied count: {anchor_paragraph_path_copied_count}")
    log.info('')
    log.info(f"total warnings: {len(warnings)}")
    log.info(f"error: {severity_dist.get('error', 0)}")
    log.info(f"warning: {severity_dist.get('warning', 0)}")
    log.info(f"info: {severity_dist.get('info', 0)}")
    log.info(f"unchanged_depth_jump: {code_dist.get('unchanged_depth_jump', 0)}")
    log.info(f"floating_anchor_unresolved: {code_dist.get('floating_anchor_unresolved', 0)}")
    log.info("table warning distribution:")
    for code in (
        "low_record_confidence", "missing_header_rows",
        "raw_only_table", "nested_table_present", "irregular_grid",
    ):
        if code in code_dist:
            log.info(f"  - {code}: {code_dist[code]}")
    log.info('')
    log.info(f"caption/footnote orphan warning count: {orphan_warning_count}")
    log.info(f"cluster_consistency_score: {quality_report['cluster_consistency_score']}")
    log.info(f"cluster_depth_inconsistent count: {code_dist.get('cluster_depth_inconsistent', 0)}")
    log.info(f"numbering_block_count: {numbering_stats['numbering_block_count']}")
    log.info(f"bullet_block_count: {numbering_stats['bullet_block_count']}")
    log.info(
        "native_numbering_sequence_warning_count: "
        f"{numbering_stats['native_numbering_sequence_warning_count']}"
    )

    table_internal_stats = quality_report.get("table_internal_ref_stats")
    if table_internal_stats is not None:
        log.info('')
        log.info("table_internal_ref_stats:")
        for key in (
            "table_internal_block_count", "row_group_count", "cell_group_count",
            "text_block_count", "nested_table_ref_count",
            "top_level_tables_with_nested_refs",
            "duplicate_internal_block_id_count", "missing_parent_ref_count",
            "max_local_depth", "max_absolute_depth",
        ):
            log.info(f"  - {key}: {table_internal_stats[key]}")

    log.info("blocks.json modified: false")
