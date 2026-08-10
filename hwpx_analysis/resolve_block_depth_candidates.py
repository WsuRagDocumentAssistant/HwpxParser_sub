#================================================
# resolve_block_depth_candidates.py
# Stage 8-A: DepthResolver 후보 구조 개선
#
# 기존 depth 최종값은 유지한 채,
# - depth_candidates를 top-k 후보 배열로 재생성하고
# - section_heading의 depth jump에 완화 후보를 기록하고
# - body/table/figure 계열에 직전 heading stack 기준 후보를 추가하고
# - table block에는 table_hierarchy_ref 신호를 반영한다.
#
# 이 단계에서 하지 않는 것:
# - depth 최종값 변경 (후보/근거/디버그 기록만)
# - role 재분류
# - band 변경
#================================================

from __future__ import annotations

from typing import Any

from hwpx_analysis.pipeline_models import BlocksDocument


# heading depth jump 완화 후보를 만들 점프 임계 (이전 heading 대비 +2 이상)
_HEADING_JUMP_THRESHOLD = 2

# low_record_confidence table 후보의 confidence 감산량
_LOW_RECORD_CONFIDENCE_PENALTY = 0.15

_OBJECT_ROLES = frozenset({
    "table", "figure", "decorative_shape_candidate",
})
_FLOW_TEXT_ROLES = frozenset({
    "body_text", "list_item", "empty_paragraph",
})


#------------------------------------------------
# 후보 목록 유틸
#------------------------------------------------

def _add_candidate(
    candidates: list[dict[str, Any]],
    depth: int,
    score: float,
    signals: list[str],
) -> None:
    """같은 depth 후보는 병합(신호 합침, 점수는 최대값)한다."""
    for candidate in candidates:
        if candidate["depth"] == depth:
            candidate["score"] = max(candidate["score"], round(score, 2))
            for signal in signals:
                if signal not in candidate["signals"]:
                    candidate["signals"].append(signal)
            return
    candidates.append({
        "depth": depth,
        "score": round(score, 2),
        "signals": list(signals),
    })


def _finalize_candidates(
    block: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> None:
    """점수 내림차순 정렬 후 블록에 기록하고 선택 후보 index를 남긴다."""
    # 기존 depth와 일치하는 후보가 없으면(방어) 기존 depth를 후보로 보존한다
    depth = block.get("depth")
    if depth is not None and not any(c["depth"] == depth for c in candidates):
        _add_candidate(
            candidates, depth, block.get("confidence_score") or 0.5,
            ["existing_depth_preserved"],
        )

    candidates.sort(key=lambda c: (-c["score"], c["depth"]))
    block["depth_candidates"] = candidates

    selected = next(
        (i for i, c in enumerate(candidates) if c["depth"] == depth),
        None,
    )
    block["selected_depth_candidate_index"] = selected


#------------------------------------------------
# 역할별 후보 생성
#------------------------------------------------

def _heading_candidates(
    block: dict[str, Any],
    prev_heading_depth: int | None,
) -> list[dict[str, Any]]:
    sf = block.get("style_features") or {}
    candidates: list[dict[str, Any]] = []

    base_score = sf.get("cluster_confidence") or block.get("confidence_score") or 0.6
    base_signals = []
    if sf.get("heading_level_native") is not None:
        base_signals.append(f"native_outline_level={sf['heading_level_native']}")
    if sf.get("depth_rank_candidate") is not None:
        base_signals.append(
            f"cluster={sf.get('style_cluster_id')} "
            f"depth_rank_candidate={sf['depth_rank_candidate']}"
        )
    if not base_signals:
        base_signals.append("heading_without_cluster_rank")

    _add_candidate(candidates, block["depth"], base_score, base_signals)

    # depth jump 완화 후보: 이전 heading 대비 +2 이상 점프
    if (
        prev_heading_depth is not None
        and block["depth"] - prev_heading_depth >= _HEADING_JUMP_THRESHOLD
    ):
        relaxed = prev_heading_depth + 1
        _add_candidate(
            candidates,
            relaxed,
            max(0.3, base_score - 0.2),
            [f"depth_jump_relaxation: prev_heading={prev_heading_depth} "
             f"jump={block['depth'] - prev_heading_depth}"],
        )
        if not any(w.startswith("depth_jump") for w in block.get("warnings", [])):
            block.setdefault("warnings", []).append(
                f"depth_jump: {prev_heading_depth} -> {block['depth']}"
            )

    return candidates


def _flow_block_candidates(
    block: dict[str, Any],
    heading_stack_top: int,
) -> list[dict[str, Any]]:
    """body_text/list_item/figure/shape 계열: 직전 heading stack 기준 후보."""
    candidates: list[dict[str, Any]] = []
    base_score = block.get("confidence_score") or 0.6

    base_signals = [f"heading_stack_top={heading_stack_top}"]
    lf = block.get("line_features") or {}
    if lf.get("line_depth_candidate"):
        base_signals.append(
            f"line_depth_candidate variation={lf.get('line_style_variation')}"
        )

    _add_candidate(candidates, block["depth"], base_score, base_signals)

    stack_depth = heading_stack_top + 1
    if stack_depth != block["depth"]:
        _add_candidate(
            candidates,
            stack_depth,
            max(0.3, base_score - 0.2),
            [f"prev_heading_stack+1={stack_depth}"],
        )

    return candidates


def _table_candidates(
    block: dict[str, Any],
    heading_stack_top: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    ref = block.get("table_hierarchy_ref") or {}

    base_score = block.get("confidence_score") or 0.8
    base_signals = [f"heading_stack_top={heading_stack_top}"]

    table_type = ref.get("table_type")
    record_status = ref.get("record_status")
    quality_warnings = ref.get("quality_warnings") or []

    if table_type:
        base_signals.append(f"table_type={table_type}")
    if record_status:
        base_signals.append(f"record_status={record_status}")
    for code in quality_warnings:
        base_signals.append(f"table_warning={code}")

    if "low_record_confidence" in quality_warnings:
        base_score = max(0.3, base_score - _LOW_RECORD_CONFIDENCE_PENALTY)
        block["confidence_score"] = round(
            min(block.get("confidence_score") or base_score, base_score), 2
        )

    _add_candidate(candidates, block["depth"], base_score, base_signals)

    stack_depth = heading_stack_top + 1
    if stack_depth != block["depth"]:
        _add_candidate(
            candidates,
            stack_depth,
            max(0.3, base_score - 0.2),
            [f"prev_heading_stack+1={stack_depth}"],
        )

    # title_box는 표 형태의 제목일 수 있으므로 section_heading 후보를 병기한다
    if table_type == "title_box":
        _add_candidate(
            candidates,
            heading_stack_top + 1,
            max(0.35, base_score - 0.1),
            ["title_box_as_section_heading_candidate"],
        )
        block.setdefault("evidence", []).append(
            "title_box: section_heading candidate added by depth resolver"
        )

    return candidates


def _track_candidates(block: dict[str, Any]) -> list[dict[str, Any]]:
    """annotation/peripheral 계열: 기존 band 유지, 트랙/앵커 기준 후보만 기록."""
    candidates: list[dict[str, Any]] = []
    band = block.get("depth_band")
    score = block.get("confidence_score") or 0.7

    if band == "peripheral":
        signals = [f"peripheral_track role={block.get('semantic_role')}"]
    elif band == "annotation":
        signals = ["annotation_track: anchored_object_depth+1"]
    else:
        signals = [f"track={band}"]

    _add_candidate(candidates, block.get("depth") or 0, score, signals)
    return candidates


#------------------------------------------------
# 진입점
#------------------------------------------------

def resolve_block_depth_candidates(
    blocks_doc: BlocksDocument,
) -> BlocksDocument:
    """
    역할: BlocksDocument의 depth_candidates를 top-k 후보 구조로 재생성한다.
    입력 데이터: blocks_doc(Stage 7.5-A까지 반영된 BlocksDocument).
    출력 데이터: 갱신된 BlocksDocument. depth 최종값은 변경하지 않는다.
    """
    blocks = sorted(
        blocks_doc.blocks,
        key=lambda b: b.get("reading_order_index", 0),
    )

    prev_heading_depth: int | None = None
    heading_stack: list[int] = []
    multi_candidate_count = 0
    relaxation_count = 0

    for block in blocks:
        role = block.get("semantic_role")
        band = block.get("depth_band")

        if band in ("peripheral", "annotation"):
            candidates = _track_candidates(block)
        elif role == "section_heading":
            candidates = _heading_candidates(block, prev_heading_depth)
            # heading stack 갱신 (최종 depth 기준 — 이번 단계는 값 변경 없음)
            depth = block["depth"]
            heading_stack = [d for d in heading_stack if d < depth] + [depth]
            prev_heading_depth = depth
        elif role in _OBJECT_ROLES and block.get("block_type") == "table":
            candidates = _table_candidates(
                block, heading_stack[-1] if heading_stack else 0
            )
        elif role in _OBJECT_ROLES or role in _FLOW_TEXT_ROLES:
            candidates = _flow_block_candidates(
                block, heading_stack[-1] if heading_stack else 0
            )
        else:
            candidates = _track_candidates(block)

        _finalize_candidates(block, candidates)

        if len(block["depth_candidates"]) > 1:
            multi_candidate_count += 1
        if any(
            any(s.startswith("depth_jump_relaxation") for s in c["signals"])
            for c in block["depth_candidates"]
        ):
            relaxation_count += 1

    blocks_doc.quality["depth_candidates"] = {
        "blocks_with_multiple_candidates": multi_candidate_count,
        "heading_jump_relaxation_candidates": relaxation_count,
    }

    print("=== Stage 8-A: depth candidates 재생성 결과 ===")
    print(f"blocks: {len(blocks_doc.blocks)}")
    print(f"multiple candidates: {multi_candidate_count}")
    print(f"heading jump relaxation candidates: {relaxation_count}")

    return blocks_doc
