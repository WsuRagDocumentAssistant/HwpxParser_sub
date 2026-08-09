#================================================
# add_document_blocks_to_json.py
# HWPX section XML 전체를 순회해서 본문/표/이미지/도형/캡션/컨트롤을
# 하나의 blocks.json(블록 레지스트리)으로 만든다.
#
# 처리 순서:
# 1. SectionStreamParser  : 모든 요소를 XML 순서대로 RawNode 수집
# 2. StyleFeatureExtractor: header.xml 참조(paraPr/charPr/style/heading)를
#                           블록 스타일 피처로 해석
# 3. StyleCluster         : 문서 내부 스타일 통계로 heading 후보 클러스터 산출
#                           (키워드/정규식을 쓰지 않는다)
# 4. RoleAssigner         : 구조/스타일 신호 기반 1차 semantic_role
# 5. DepthResolver(1차)   : heading/list/body/table/caption 수준의 coarse depth
# 6. Export               : blocks.json + blocks_outline_preview.md
#================================================

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from hwpx_analysis.pipeline_models import BlocksDocument
from hwpx_document.header_data import HeaderData
from hwpx_parser.section_stream_parser import SectionStreamParser


#------------------------------------------------
# 스타일 피처 해석
#------------------------------------------------

def _find_child_raw(raw: dict[str, Any] | None, tag: str) -> dict[str, Any] | None:
    """element raw dict(children 재귀 구조)에서 첫 tag 노드를 찾는다."""
    if not isinstance(raw, dict):
        return None
    for child in raw.get("children", []):
        if child.get("tag") == tag:
            return child
        found = _find_child_raw(child, tag)
        if found is not None:
            return found
    return None


def _to_int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_para_style(
    header: HeaderData,
    para_pr_id_ref: str | None,
    style_id_ref: str | None,
) -> dict[str, Any]:
    """
    paraPr(직접 참조 또는 style 경유)에서 depth 추론에 쓰는 문단 피처를 해석한다.

    heading 하위 요소의 type을 구분하는 것이 핵심이다:
    - OUTLINE          -> 저자가 선언한 개요 수준 (native heading)
    - NUMBER / BULLET  -> 목록 수준 (list item)
    """
    resolved_id = header.resolve_para_pr_id(
        para_pr_id=para_pr_id_ref,
        style_id=style_id_ref,
    )
    raw = header.get_para_pr_raw(resolved_id)

    features: dict[str, Any] = {
        "resolved_para_pr_id": resolved_id,
        "heading_type": None,
        "heading_level_native": None,
        "numbering_level": None,
        "alignment": None,
        "indent": None,
        "margin_left": None,
        # 문단 앞에 자동 렌더링되지만 hp:t에는 없는 마커(불릿/번호 형식).
        # 원문 무손실성을 위해 text_content에 접합하지 않고 별도 필드로 둔다.
        "auto_label": header.resolve_auto_label(
            para_pr_id=para_pr_id_ref,
            style_id=style_id_ref,
        ),
    }

    if raw is None:
        return features

    heading = _find_child_raw(raw, "heading")
    if heading is not None:
        h_attrs = heading.get("attrs", {})
        h_type = h_attrs.get("type")
        level = _to_int_or_none(h_attrs.get("level"))
        features["heading_type"] = h_type
        if h_type == "OUTLINE":
            features["heading_level_native"] = level
        elif h_type in ("NUMBER", "BULLET"):
            features["numbering_level"] = level

    align = _find_child_raw(raw, "align")
    if align is not None:
        features["alignment"] = align.get("attrs", {}).get("horizontal")

    margin = _find_child_raw(raw, "margin")
    if margin is not None:
        intent = _find_child_raw(margin, "intent")
        left = _find_child_raw(margin, "left")
        if intent is not None:
            features["indent"] = _to_int_or_none(intent.get("attrs", {}).get("value"))
        if left is not None:
            features["margin_left"] = _to_int_or_none(left.get("attrs", {}).get("value"))

    return features


def _resolve_char_style(
    header: HeaderData,
    run_char_infos: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    문단 내 run들의 charPr 참조를 합산해 font_size / bold_ratio를 계산한다.
    font_size는 텍스트 길이 가중 최대값(제목 신호)과 가중 평균을 함께 둔다.
    """
    total_chars = 0
    bold_chars = 0
    max_size: float | None = None
    weighted_sum = 0.0
    weighted_chars = 0
    char_pr_ids: list[str] = []

    for info in run_char_infos:
        char_pr_id = info.get("char_pr_id_ref")
        length = int(info.get("text_length") or 0)
        if char_pr_id is None:
            continue
        char_pr_ids.append(char_pr_id)

        raw = header.get_char_pr_raw(str(char_pr_id))
        if not isinstance(raw, dict):
            continue

        is_bold = any(c.get("tag") == "bold" for c in raw.get("children", []))
        height = _to_int_or_none(raw.get("attrs", {}).get("height"))
        size = (height / 100) if height is not None else None

        total_chars += length
        if is_bold:
            bold_chars += length

        if size is not None:
            if max_size is None or size > max_size:
                max_size = size
            if length > 0:
                weighted_sum += size * length
                weighted_chars += length

    return {
        "char_pr_id_refs": char_pr_ids,
        "font_size": max_size,
        "font_size_avg": (weighted_sum / weighted_chars) if weighted_chars else None,
        "bold_ratio": (bold_chars / total_chars) if total_chars else 0.0,
    }


#------------------------------------------------
# 스타일 클러스터 (문서 내부 통계 기반 heading 후보)
#------------------------------------------------

def _cluster_key_of(sf: dict[str, Any]) -> tuple:
    """paragraph 스타일 피처 -> 클러스터 시그니처 키."""
    size = sf.get("font_size")
    return (
        sf.get("style_id_ref"),
        sf.get("para_pr_id_ref"),
        round(size * 2) / 2 if size is not None else None,
        sf.get("bold_ratio", 0.0) >= 0.5,
    )


# depth_rank 병합 시 같은 계층으로 볼 글자 크기 허용 오차 (pt)
_DEPTH_RANK_SIZE_TOLERANCE = 0.9

# heading-like 판정 점수 임계
_HEADING_SCORE_THRESHOLD = 3.0


def _build_style_clusters(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """
    텍스트가 있는 paragraph 블록을 스타일 시그니처로 묶은 뒤,

    1) 본문 기준선(body baseline) 확정: 총 글자수 최대 클러스터
    2) heading-like 점수제: 글자 크기/굵기/짧은 텍스트/희소성/
       후행 블록 다양성/들여쓰기 차이를 가산, 고빈도·장문을 감산
    3) style_cluster_rank(세분 랭크)와 depth_rank_candidate(병합 랭크) 분리

    키워드·정규식 없이 문서 스스로의 스타일 일관성만 사용한다.
    """
    clusters: dict[tuple, dict[str, Any]] = {}
    member_indices: dict[tuple, list[int]] = {}

    # 후행 블록 신호용: 의미 있는 블록의 순서 목록
    meaningful: list[int] = []
    for idx, block in enumerate(blocks):
        bt = block["block_type"]
        if bt == "paragraph":
            if (block.get("text_content") or "").strip():
                meaningful.append(idx)
        elif bt in ("table", "image", "shape", "shape_group"):
            meaningful.append(idx)

    next_meaningful: dict[int, int | None] = {}
    for pos, idx in enumerate(meaningful):
        next_meaningful[idx] = meaningful[pos + 1] if pos + 1 < len(meaningful) else None

    for idx, block in enumerate(blocks):
        if block["block_type"] != "paragraph":
            continue
        text = (block.get("text_content") or "").strip()
        if not text:
            continue

        sf = block["style_features"]
        key = _cluster_key_of(sf)

        cluster = clusters.setdefault(key, {
            "count": 0,
            "total_chars": 0,
            "font_size": key[2],
            "bold": key[3],
            "alignment": sf.get("alignment"),
            "indent_values": [],
            "sample_texts": [],
        })
        cluster["count"] += 1
        cluster["total_chars"] += len(text)
        if sf.get("indent") is not None:
            cluster["indent_values"].append(sf["indent"])
        if len(cluster["sample_texts"]) < 5:
            cluster["sample_texts"].append(text[:60])
        member_indices.setdefault(key, []).append(idx)

    if not clusters:
        return {
            "cluster_records": {},
            "body_font_size": None,
            "body_cluster_id": None,
            "cluster_info_of": {},
            "cluster_key_of": _cluster_key_of,
            "report": [],
        }

    # ── 1) 본문 기준선 확정 ──
    body_key = max(clusters, key=lambda k: clusters[k]["total_chars"])
    body_cluster = clusters[body_key]
    body_size = body_cluster["font_size"]
    body_alignment = body_cluster["alignment"]
    body_indent_avg = (
        sum(body_cluster["indent_values"]) / len(body_cluster["indent_values"])
        if body_cluster["indent_values"] else 0
    )

    total_paragraphs = sum(c["count"] for c in clusters.values())

    # ── 2) heading-like 점수제 ──
    scores: dict[tuple, tuple[float, list[str]]] = {}
    for key, cluster in clusters.items():
        if key == body_key:
            continue

        size = cluster["font_size"]
        avg_len = cluster["total_chars"] / cluster["count"]
        freq_ratio = cluster["count"] / total_paragraphs

        score = 0.0
        signals: list[str] = []

        if size is not None and body_size is not None and size > body_size + 0.1:
            gain = min(2.0, 1.0 + (size - body_size) / 4.0)
            score += gain
            signals.append(f"font_size {size} > body {body_size} (+{gain:.1f})")

        if cluster["bold"]:
            score += 1.0
            signals.append("bold (+1.0)")

        if avg_len <= 40:
            score += 1.0
            signals.append(f"short avg_len {avg_len:.0f} (+1.0)")
        elif avg_len <= 80:
            score += 0.5
            signals.append(f"medium avg_len {avg_len:.0f} (+0.5)")

        if 2 <= cluster["count"] and freq_ratio <= 0.3:
            score += 0.5
            signals.append(f"repeated but rare count={cluster['count']} (+0.5)")

        # 후행 블록 다양성: heading은 같은 스타일이 연달아 오지 않는다
        members = member_indices.get(key, [])
        followed_by_other = 0
        followed_total = 0
        for m in members:
            nxt = next_meaningful.get(m)
            if nxt is None:
                continue
            followed_total += 1
            nxt_block = blocks[nxt]
            if nxt_block["block_type"] != "paragraph":
                followed_by_other += 1
            else:
                nxt_key = _cluster_key_of(nxt_block["style_features"])
                if nxt_key != key:
                    followed_by_other += 1
        if followed_total and followed_by_other / followed_total >= 0.7:
            score += 1.0
            signals.append(
                f"followed_by_other {followed_by_other}/{followed_total} (+1.0)"
            )

        indent_avg = (
            sum(cluster["indent_values"]) / len(cluster["indent_values"])
            if cluster["indent_values"] else 0
        )
        if cluster["alignment"] != body_alignment or abs(indent_avg - body_indent_avg) > 500:
            score += 0.5
            signals.append("alignment/indent differs from body (+0.5)")

        if freq_ratio > 0.3:
            score -= 2.0
            signals.append(f"too frequent {freq_ratio:.0%} (-2.0)")
        if avg_len > 100:
            score -= 2.0
            signals.append(f"too long avg_len {avg_len:.0f} (-2.0)")

        scores[key] = (score, signals)

    heading_keys = [
        key for key, (score, _) in scores.items()
        if score >= _HEADING_SCORE_THRESHOLD
    ]

    # ── 3) 랭크 산정: style_cluster_rank(세분) / depth_rank(병합) 분리 ──
    heading_sorted = sorted(
        heading_keys,
        key=lambda k: (
            -(clusters[k]["font_size"] or 0),
            not clusters[k]["bold"],
            clusters[k]["total_chars"] / clusters[k]["count"],
        ),
    )
    style_rank_of = {key: rank + 1 for rank, key in enumerate(heading_sorted)}

    # depth_rank: (글자 크기 밴드, bold 여부)로 병합.
    # 같은 크기라도 bold 제목(□)과 비굵음 소제목(○)은 다른 계층이다.
    depth_rank_of: dict[tuple, int] = {}
    current_rank = 0
    band_size: float | None = None
    band_bold: bool | None = None
    for key in heading_sorted:
        size = clusters[key]["font_size"] or 0
        bold = clusters[key]["bold"]
        if (
            band_size is None
            or band_size - size > _DEPTH_RANK_SIZE_TOLERANCE
            or bold != band_bold
        ):
            current_rank += 1
            band_size = size
            band_bold = bold
        depth_rank_of[key] = current_rank

    # ── 클러스터 ID 부여 (글자수 많은 순 C01..) 및 리포트 생성 ──
    ordered_keys = sorted(
        clusters,
        key=lambda k: (-clusters[k]["total_chars"], -clusters[k]["count"]),
    )
    cluster_id_of = {
        key: f"C{index + 1:02d}" for index, key in enumerate(ordered_keys)
    }

    cluster_info_of: dict[tuple, dict[str, Any]] = {}
    report: list[dict[str, Any]] = []
    for key in ordered_keys:
        cluster = clusters[key]
        score, signals = scores.get(key, (None, []))
        is_body = key == body_key
        is_heading = key in style_rank_of

        if is_body:
            role_candidate = "body_baseline"
            confidence = 0.9
        elif is_heading:
            role_candidate = "section_heading"
            confidence = min(0.9, 0.45 + 0.08 * (score or 0))
        else:
            role_candidate = "body"
            confidence = 0.7

        info = {
            "style_cluster_id": cluster_id_of[key],
            "cluster_role_candidate": role_candidate,
            "cluster_confidence": round(confidence, 2),
            "style_cluster_rank": style_rank_of.get(key),
            "depth_rank_candidate": depth_rank_of.get(key),
        }
        cluster_info_of[key] = info

        indent_avg = (
            sum(cluster["indent_values"]) / len(cluster["indent_values"])
            if cluster["indent_values"] else 0
        )
        report.append({
            "cluster_id": cluster_id_of[key],
            "role_candidate": role_candidate,
            "style_cluster_rank": style_rank_of.get(key),
            "depth_rank_candidate": depth_rank_of.get(key),
            "heading_score": round(score, 2) if score is not None else None,
            "heading_signals": signals,
            "block_count": cluster["count"],
            "total_chars": cluster["total_chars"],
            "avg_text_length": round(cluster["total_chars"] / cluster["count"], 1),
            "font_size": cluster["font_size"],
            "bold": cluster["bold"],
            "alignment": cluster["alignment"],
            "avg_indent_left": round(indent_avg, 1),
            "signature": {
                "style_id_ref": key[0],
                "para_pr_id_ref": key[1],
            },
            "sample_texts": cluster["sample_texts"],
        })

    return {
        "cluster_records": clusters,
        "body_font_size": body_size,
        "body_cluster_id": cluster_id_of[body_key],
        "cluster_info_of": cluster_info_of,
        "cluster_key_of": _cluster_key_of,
        "heading_cluster_count": len(heading_keys),
        "depth_rank_count": current_rank,
        "report": report,
    }


#------------------------------------------------
# 역할(semantic_role) 1차 부여
#------------------------------------------------

_PERIPHERAL_TYPES = frozenset({"header", "footer", "section_control", "control"})
_ANNOTATION_TYPES = frozenset({"caption", "footnote", "endnote"})


def _assign_roles(blocks: list[dict[str, Any]], style_stats: dict[str, Any]) -> None:
    """구조 신호(블록 타입/heading 참조) 우선, 스타일 클러스터 보조로 role을 부여한다."""
    cluster_info_of = style_stats.get("cluster_info_of", {})
    key_of = style_stats.get("cluster_key_of")

    for block in blocks:
        block_type = block["block_type"]
        sf = block["style_features"]
        evidence = block["evidence"]

        if block_type in ("header",):
            block["semantic_role"] = "page_header"
            block["confidence_score"] = 0.9
            evidence.append("hp:ctrl page header element")
        elif block_type in ("footer",):
            block["semantic_role"] = "page_footer"
            block["confidence_score"] = 0.9
            evidence.append("hp:ctrl page footer element")
        elif block_type == "footnote":
            block["semantic_role"] = "footnote"
            block["confidence_score"] = 0.9
        elif block_type == "endnote":
            block["semantic_role"] = "endnote"
            block["confidence_score"] = 0.9
        elif block_type == "caption":
            block["semantic_role"] = "caption"
            block["confidence_score"] = 0.85
            evidence.append("explicit hp:caption element")
        elif block_type == "table":
            block["semantic_role"] = "table"
            block["confidence_score"] = 0.95
        elif block_type == "image":
            block["semantic_role"] = "figure"
            block["confidence_score"] = 0.9
        elif block_type in ("shape", "shape_group"):
            has_text = bool((block.get("text_content") or "").strip())
            block["semantic_role"] = "figure" if has_text else "decorative_shape_candidate"
            block["confidence_score"] = 0.6
            evidence.append(f"shape text_present={has_text}")
        elif block_type in ("section_control", "control"):
            block["semantic_role"] = "document_control"
            block["confidence_score"] = 0.9
        elif block_type == "paragraph":
            _assign_paragraph_role(block, sf, cluster_info_of, key_of)
        else:
            block["semantic_role"] = "unknown"
            block["confidence_score"] = 0.3


def _assign_paragraph_role(block, sf, cluster_info_of, key_of) -> None:
    """문단 role: native heading > 목록 수준 > 스타일 클러스터 heading > 본문."""
    evidence = block["evidence"]
    text = (block.get("text_content") or "").strip()

    if not text:
        block["semantic_role"] = "empty_paragraph"
        block["confidence_score"] = 0.9
        return

    # 텍스트가 있는 문단은 소속 클러스터 정보를 항상 표기한다 (디버깅 필수)
    cluster_key = key_of(sf) if key_of else None
    info = cluster_info_of.get(cluster_key)
    if info is not None:
        sf["style_cluster_id"] = info["style_cluster_id"]
        sf["style_cluster_rank"] = info["style_cluster_rank"]
        sf["cluster_role_candidate"] = info["cluster_role_candidate"]
        sf["cluster_confidence"] = info["cluster_confidence"]
        sf["depth_rank_candidate"] = info["depth_rank_candidate"]

    if sf.get("heading_level_native") is not None:
        block["semantic_role"] = "section_heading"
        block["confidence_score"] = 0.9
        evidence.append(
            f"paraPr OUTLINE heading level={sf['heading_level_native']}"
        )
        return

    if sf.get("numbering_level") is not None:
        block["semantic_role"] = "list_item"
        block["confidence_score"] = 0.75
        evidence.append(
            f"paraPr {sf.get('heading_type')} level={sf['numbering_level']}"
        )
        return

    if info is not None and info["cluster_role_candidate"] == "section_heading":
        block["semantic_role"] = "section_heading"
        block["confidence_score"] = info["cluster_confidence"]
        evidence.append(
            f"style cluster {info['style_cluster_id']} "
            f"rank={info['style_cluster_rank']} "
            f"depth_rank={info['depth_rank_candidate']}"
        )
        return

    block["semantic_role"] = "body_text"
    block["confidence_score"] = 0.8


#------------------------------------------------
# 1차 depth 부여
#------------------------------------------------

def _resolve_depth_first_pass(blocks: list[dict[str, Any]]) -> None:
    """
    coarse depth 1차 부여.

    - peripheral(머리말/꼬리말/컨트롤): depth 0, band=peripheral
    - section_heading: native level 우선, 없으면 클러스터 랭크 -> depth 1..k
    - body/table/figure/shape: 직전 heading depth + 1
    - list_item: 본문 depth + numbering level
    - caption/footnote: 앵커 개체 depth + 1, band=annotation
    """
    current_heading_depth = 0
    last_object_depth = 1
    max_native_level_seen = 0

    for block in blocks:
        role = block["semantic_role"]
        block_type = block["block_type"]
        sf = block["style_features"]
        evidence = block["evidence"]

        if block_type in _PERIPHERAL_TYPES:
            block["depth_band"] = "peripheral"
            block["depth"] = 0
            continue

        if block_type in _ANNOTATION_TYPES:
            block["depth_band"] = "annotation"
            block["depth"] = last_object_depth + 1
            evidence.append(f"anchored object depth={last_object_depth}")
            continue

        block["depth_band"] = "body"

        if role == "section_heading":
            native = sf.get("heading_level_native")
            if native is not None:
                # HWPX outline level은 0부터 시작하는 경우가 많다
                depth = native + 1
                max_native_level_seen = max(max_native_level_seen, depth)
                evidence.append(f"depth from native outline level {native}")
            else:
                # 세분 랭크가 아닌 병합 depth_rank를 사용한다
                rank = sf.get("depth_rank_candidate") or sf.get("style_cluster_rank") or 1
                depth = max_native_level_seen + rank
                evidence.append(
                    f"depth from cluster {sf.get('style_cluster_id')} depth_rank {rank}"
                )

            if current_heading_depth and depth > current_heading_depth + 1:
                block["warnings"].append(
                    f"depth_jump: {current_heading_depth} -> {depth}"
                )
            current_heading_depth = depth
            block["depth"] = depth
            block["depth_candidates"] = [{
                "depth": depth,
                "score": block["confidence_score"],
                "signals": list(evidence),
            }]
            continue

        body_depth = current_heading_depth + 1

        if role == "list_item":
            level = sf.get("numbering_level") or 0
            block["depth"] = body_depth + max(level - 1, 0)
            evidence.append(f"list level={level} over body depth={body_depth}")
        elif role == "empty_paragraph":
            block["depth"] = body_depth
        else:
            block["depth"] = body_depth

        if block_type in ("table", "image", "shape", "shape_group"):
            last_object_depth = block["depth"]


#------------------------------------------------
# RawNode -> Block 변환
#------------------------------------------------

def _node_to_block(
    node: dict[str, Any],
    header: HeaderData,
    block_counter: int,
) -> dict[str, Any]:
    section_index = node["section_index"]
    block_type = node["node_type"]

    style_features: dict[str, Any] = {
        "style_id_ref": node.get("style_id_ref"),
        "para_pr_id_ref": node.get("para_pr_id_ref"),
    }

    if block_type == "paragraph":
        style_features.update(_resolve_para_style(
            header,
            para_pr_id_ref=node.get("para_pr_id_ref"),
            style_id_ref=node.get("style_id_ref"),
        ))
        style_features.update(_resolve_char_style(
            header,
            run_char_infos=node.get("run_char_infos", []),
        ))

    anchor_info = node.get("anchor_info") or {}
    text_content = node.get("text_content")

    structure_features: dict[str, Any] = {
        "is_table_related": block_type == "table",
        "table_id": None,
        "object_type": node.get("object_type"),
        "contained_object_count": node.get("contained_object_count"),
        "child_object_summary": node.get("child_object_summary"),
        "binary_item_id_ref": node.get("binary_item_id_ref"),
        "control_type": node.get("control_type"),
    }

    if block_type == "table":
        table_index = node.get("table_index")
        xml_table_id = node.get("xml_table_id")
        if table_index is not None:
            # TableParser._make_table_id와 동일 규칙으로 재구성해
            # tables_hierarchical.json과 연결한다.
            if xml_table_id:
                structure_features["table_id"] = (
                    f"section{section_index}_tbl{table_index}_{xml_table_id}"
                )
            else:
                structure_features["table_id"] = (
                    f"section{section_index}_tbl{table_index}"
                )
        structure_features["table_index"] = table_index
        structure_features["xml_table_id"] = xml_table_id

    anchor_paragraph_path = node.get("anchor_paragraph_path")
    anchor_reference = None
    if anchor_paragraph_path is not None:
        anchor_reference = {
            "anchor_paragraph_path": anchor_paragraph_path,
            "source": "raw_node",
            "confidence": 0.9,
        }

    return {
        "block_id": f"s{section_index}_b{block_counter:05d}",
        "block_type": block_type,
        "semantic_role": None,
        "section_index": section_index,
        "source_xml_path": node["source_xml_path"],
        "source_element": node["source_element"],
        "reading_order_index": node["xml_order_index"],
        "text_content": text_content,
        "normalized_text": " ".join(text_content.split()) if text_content else None,
        # Stage 9-B: RawNode의 anchor_paragraph_path를 block 최상위로 전달한다.
        # caption/footnote orphan 검사(validate_blocks.py)의 매칭 키로 쓰인다.
        "anchor_paragraph_path": anchor_paragraph_path,
        "anchor_reference": anchor_reference,
        "layout_position": {
            "xml_order_index": node["xml_order_index"],
            "paragraph_index": node.get("paragraph_index"),
            "anchor_type": anchor_info.get("anchor_type")
                or ("inline" if block_type == "paragraph" else None),
            "treat_as_char": anchor_info.get("treat_as_char"),
            "z_order": anchor_info.get("z_order"),
            "size": node.get("size"),
            "page_number_estimate": None,
            "bounding_box_estimate": None,
        },
        "style_features": style_features,
        "line_features": node.get("line_features"),
        "structure_features": structure_features,
        "depth": None,
        "depth_band": None,
        "depth_candidates": [],
        "confidence_score": None,
        "evidence": [],
        "warnings": [],
    }


#------------------------------------------------
# 진입점
#------------------------------------------------

def build_document_blocks(
    section_paths: list[str | Path],
    header: HeaderData,
) -> BlocksDocument:
    """
    역할: 섹션 XML 전체를 블록 레지스트리(BlocksDocument)로 변환한다.
    입력 데이터: section_paths(정렬된 section*.xml 경로), header(HeaderData).
    출력 데이터: BlocksDocument(document/blocks/quality).
    """
    nodes = SectionStreamParser.parse(section_paths)

    blocks = [
        _node_to_block(node, header, counter)
        for counter, node in enumerate(nodes)
    ]

    # 같은 source_xml_path가 반복될 때 개별 block을 구분하는 발생 순번.
    # 미래의 동일 문단 내 중복 control 보존을 위한 안정 키다.
    path_occurrence: Counter[str] = Counter()
    for block in blocks:
        path = block["source_xml_path"]
        block["source_occurrence_index"] = path_occurrence[path]
        path_occurrence[path] += 1

    # 중첩 개체(꼬리말/그리기개체 등) 내부라서 블록으로 방출하지 않은
    # control 통계. '조용한 유실'을 '기록된 정책'으로 남긴다.
    nested_control_skipped: Counter[str] = Counter()
    for node in nodes:
        for key, count in (node.get("nested_control_counts") or {}).items():
            nested_control_skipped[key] += count

    style_stats = _build_style_clusters(blocks)
    _assign_roles(blocks, style_stats)
    _resolve_depth_first_pass(blocks)

    type_counts = Counter(b["block_type"] for b in blocks)
    role_counts = Counter(b["semantic_role"] for b in blocks)
    depth_jump_count = sum(
        1 for b in blocks for w in b["warnings"] if w.startswith("depth_jump")
    )

    return BlocksDocument(
        document={
            "source_type": "hwpx",
            "section_count": len(section_paths),
            "block_count": len(blocks),
            "parser_version": "block-depth-v1",
            "style_summary": {
                "body_font_size": style_stats.get("body_font_size"),
                "body_cluster_id": style_stats.get("body_cluster_id"),
                "cluster_count": len(style_stats.get("report", [])),
                "heading_cluster_count": style_stats.get("heading_cluster_count", 0),
                "depth_rank_count": style_stats.get("depth_rank_count", 0),
            },
        },
        blocks=blocks,
        quality={
            "block_type_counts": dict(type_counts),
            "semantic_role_counts": dict(role_counts),
            "depth_jump_count": depth_jump_count,
            "nested_control_skipped": {
                "total": sum(nested_control_skipped.values()),
                "by_container": dict(nested_control_skipped),
            },
            "unresolved_blocks": [
                b["block_id"] for b in blocks if b["depth"] is None
            ],
        },
    )
