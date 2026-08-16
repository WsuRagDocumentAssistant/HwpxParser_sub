#================================================
# assign_block_visibility.py
# v3.1 보완 2차: block visibility 부여
#
# 모든 block에 visibility 필드를 추가한다.
# block을 삭제하지 않고, preview / LLM context 노출 여부만 결정한다.
# depth 정합성(트리 구조)은 visibility와 무관하게 유지된다.
#
# include_in_preview = false 대상:
# - semantic_role == "empty_paragraph"
# - block_type in {"control", "section_control"}
# - depth_band == "peripheral"
#================================================

from __future__ import annotations

from typing import Any

from .pipeline_models import BlocksDocument

import logging

# 라이브러리는 조용한 것이 기본이다. 단계 보고를 보려면 쓰는 쪽에서
# logging 을 켠다. tools 는 그렇게 하고 있다.
log = logging.getLogger(__name__)

_HIDDEN_BLOCK_TYPES = {"control", "section_control"}


def _visibility_for_block(block: dict[str, Any]) -> dict[str, Any]:
    reason = None
    if block.get("semantic_role") == "empty_paragraph":
        reason = "empty_paragraph"
    elif block.get("block_type") in _HIDDEN_BLOCK_TYPES:
        reason = "document_control"
    elif block.get("depth_band") == "peripheral":
        reason = "peripheral"

    visible = reason is None
    return {
        "include_in_raw_blocks": True,
        "include_in_preview": visible,
        "include_in_llm_context": visible,
        "reason": reason,
    }


def assign_block_visibility(blocks_doc: BlocksDocument) -> dict[str, Any]:
    """
    역할: BlocksDocument의 모든 block에 visibility 필드를 부여한다.
          depth / reading_order_index / block 수는 변경하지 않는다.
    입력 데이터: blocks_doc (Stage 8-B까지 반영된 BlocksDocument).
    출력 데이터: {"hidden_count": int, "hidden_reason_distribution": {...}} dict.
    """
    blocks = blocks_doc.blocks
    reason_counts: dict[str, int] = {}
    for block in blocks:
        visibility = _visibility_for_block(block)
        block["visibility"] = visibility
        if visibility["reason"]:
            reason_counts[visibility["reason"]] = reason_counts.get(visibility["reason"], 0) + 1

    hidden_count = sum(reason_counts.values())
    log.info("=== visibility 부여 결과 ===")
    log.info(f"block_count: {len(blocks)}")
    log.info(f"hidden_in_preview_count: {hidden_count}")
    log.info(f"hidden_reason_distribution: {reason_counts}")

    return {
        "hidden_count": hidden_count,
        "hidden_reason_distribution": reason_counts,
    }
