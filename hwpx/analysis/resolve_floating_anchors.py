#================================================
# resolve_floating_anchors.py
# Stage 4-B: Floating Object Anchor Resolution
#
# layout_position.anchor_type == "floating"인 block에 대해
# paragraph_index 기준으로 anchor 문단을 구조적으로 확인하고 기록한다.
#
# 이 단계는 좌표 기반 재배치를 하지 않는다.
# reading_order_index와 depth는 변경하지 않고,
# resolved_order_index 등 보조 필드만 추가한다.
#================================================

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .pipeline_models import BlocksDocument

import logging

# 라이브러리는 조용한 것이 기본이다. 단계 보고를 보려면 쓰는 쪽에서
# logging 을 켠다. tools 는 그렇게 하고 있다.
log = logging.getLogger(__name__)


def _find_anchor_candidates(
    floating_block: dict[str, Any],
    paragraphs_by_key: dict[tuple, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    key = (
        floating_block.get("section_index"),
        (floating_block.get("layout_position") or {}).get("paragraph_index"),
    )
    return paragraphs_by_key.get(key, [])


def _build_anchor_resolution(
    floating_block: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    layout = floating_block.get("layout_position") or {}
    section_index = floating_block.get("section_index")
    paragraph_index = layout.get("paragraph_index")

    base = {
        "anchor_basis": "section_index+paragraph_index",
        "anchor_section_index": section_index,
        "anchor_paragraph_index": paragraph_index,
        "order_policy": "after_anchor_paragraph_preserve_xml_order",
    }

    if len(candidates) == 1:
        anchor = candidates[0]
        return {
            **base,
            "status": "resolved",
            "anchor_block_id": anchor["block_id"],
            "anchor_block_reading_order_index": anchor.get("reading_order_index"),
            "confidence": 0.9,
            "reason": None,
        }

    if len(candidates) == 0:
        return {
            **base,
            "status": "unresolved",
            "anchor_block_id": None,
            "anchor_block_reading_order_index": None,
            "confidence": 0.0,
            "reason": "anchor_paragraph_not_found",
        }

    # 2개 이상 후보 -> ambiguous
    return {
        **base,
        "status": "ambiguous",
        "anchor_block_id": None,
        "anchor_block_reading_order_index": None,
        "confidence": 0.0,
        "reason": "multiple_anchor_paragraph_candidates",
    }


def _resolve_order_within_anchor_groups(
    floating_blocks: list[dict[str, Any]],
) -> None:
    """
    동일 anchor 문단에 걸린 floating 객체들의 상대 순서는
    xml_order_index 오름차순을 보존한다.

    이미 reading_order_index 오름차순이 xml_order_index 오름차순과 일치하면
    (=이미 올바른 순서) resolved_order_index는 original과 동일하게 두고
    order_changed=False로 둔다. 이번 파서 설계상 개체는 XML 등장 순서 그대로
    방출되므로 이 경우가 정상 케이스다 (기준 11).

    두 순서가 어긋날 때만 anchor 문단 바로 뒤에 xml 순서대로 재배치하고
    실제로 순위가 바뀐 멤버만 order_changed=True로 표시한다.
    """
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for block in floating_blocks:
        resolution = block["anchor_resolution"]
        if resolution["status"] != "resolved":
            continue
        groups[resolution["anchor_block_id"]].append(block)

    for anchor_block_id, members in groups.items():
        by_xml_order = sorted(
            members,
            key=lambda b: (b.get("layout_position") or {}).get("xml_order_index", 0),
        )
        by_reading_order = sorted(members, key=lambda b: b["reading_order_index"])

        already_consistent = (
            [b["block_id"] for b in by_xml_order]
            == [b["block_id"] for b in by_reading_order]
        )

        anchor_reading_order = members[0]["anchor_resolution"]["anchor_block_reading_order_index"]

        for offset, block in enumerate(by_xml_order, start=1):
            original = block["reading_order_index"]

            if already_consistent or anchor_reading_order is None:
                resolved = original
            else:
                # 순서가 어긋난 경우에만 anchor 뒤 xml 순서로 재배치한다
                resolved = anchor_reading_order + offset * 0.001

            block["reading_order_resolution"] = {
                "original_reading_order_index": original,
                "resolved_order_index": resolved,
                "order_basis": "after_anchor_paragraph_preserve_xml_order",
                "order_confidence": block["anchor_resolution"]["confidence"],
                "order_changed": resolved != original,
            }


def _resolve_order_for_non_resolved(floating_blocks: list[dict[str, Any]]) -> None:
    """unresolved/ambiguous 블록은 순서를 바꿀 근거가 없으므로 원본을 유지한다."""
    for block in floating_blocks:
        if "reading_order_resolution" in block:
            continue
        original = block["reading_order_index"]
        block["reading_order_resolution"] = {
            "original_reading_order_index": original,
            "resolved_order_index": original,
            "order_basis": "unresolved_fallback_xml_order",
            "order_confidence": 0.0,
            "order_changed": False,
        }


#------------------------------------------------
# 진입점
#------------------------------------------------

def resolve_floating_anchors(
    blocks_doc: BlocksDocument,
) -> BlocksDocument:
    """
    역할: floating block의 anchor 문단을 paragraph_index 기준으로 구조적으로 확인한다.
    입력 데이터: blocks_doc(Stage 3~6까지 반영된 BlocksDocument).
    출력 데이터: anchor_resolution / reading_order_resolution이 추가된 BlocksDocument.
                 reading_order_index와 depth는 변경하지 않는다.
    """
    blocks = blocks_doc.blocks

    paragraphs_by_key: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for block in blocks:
        if block.get("block_type") == "paragraph":
            key = (
                block.get("section_index"),
                (block.get("layout_position") or {}).get("paragraph_index"),
            )
            paragraphs_by_key[key].append(block)

    floating_blocks = [
        block for block in blocks
        if (block.get("layout_position") or {}).get("anchor_type") == "floating"
    ]

    for block in floating_blocks:
        candidates = _find_anchor_candidates(block, paragraphs_by_key)
        block["anchor_resolution"] = _build_anchor_resolution(block, candidates)

    _resolve_order_within_anchor_groups(floating_blocks)
    _resolve_order_for_non_resolved(floating_blocks)

    resolved_count = sum(
        1 for b in floating_blocks if b["anchor_resolution"]["status"] == "resolved"
    )
    unresolved_count = sum(
        1 for b in floating_blocks if b["anchor_resolution"]["status"] == "unresolved"
    )
    ambiguous_count = sum(
        1 for b in floating_blocks if b["anchor_resolution"]["status"] == "ambiguous"
    )
    order_changed_count = sum(
        1 for b in floating_blocks if b["reading_order_resolution"]["order_changed"]
    )
    same_anchor_groups = sum(
        1 for members in _group_by_anchor(floating_blocks).values() if len(members) > 1
    )

    blocks_doc.quality["floating_anchor_resolution"] = {
        "floating_object_count": len(floating_blocks),
        "floating_anchor_resolved_count": resolved_count,
        "floating_anchor_unresolved_count": unresolved_count,
        "floating_anchor_ambiguous_count": ambiguous_count,
        "floating_order_changed_count": order_changed_count,
    }

    log.info("=== Stage 4-B: Floating Object Anchor Resolution 결과 ===")
    log.info(f"floating objects: {len(floating_blocks)}")
    log.info(f"resolved: {resolved_count}")
    log.info(f"unresolved: {unresolved_count}")
    log.info(f"ambiguous: {ambiguous_count}")
    log.info(f"order changed: {order_changed_count}")
    log.info(f"same-anchor groups: {same_anchor_groups}")

    return blocks_doc


def _group_by_anchor(floating_blocks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for block in floating_blocks:
        resolution = block["anchor_resolution"]
        if resolution["status"] == "resolved":
            groups[resolution["anchor_block_id"]].append(block)
    return groups
