#================================================
# propagate_toc_anchor_depth.py
# Stage 8-C: 목차 anchor 하위 flow 전파 + 잔여 구간 clamp
#
# add_toc_depth0_anchors는 목차와 매칭된 블록의 depth만 절대값으로 확정하고
# 그 뒤 블록은 건드리지 않는다. 그런데 anchor는 대개 깊이 박혀 있던 블록을
# 크게 끌어올리므로(측정: delta -5 ~ -9), 뒤따르는 flow 블록은 옛 좌표에
# 남아 부모 없는 depth가 된다.
#
# Stage 8-B의 flow 전파는 section_heading만 기점으로 삼고,
# correct_title_box_depths의 shift는 paragraph heading을 기점으로 삼는다.
# 목차 anchor는 어느 전파의 기점도 되지 못해 그 구간이 통째로 미보정으로 남는다.
#
# 처리:
#   1. anchor 하위 flow 전파 - anchor 뒤 flow 블록을 anchor_depth + 1로.
#      다음 section_heading 또는 다음 anchor에서 멈춘다.
#   2. 잔여 구간 clamp - 어떤 보정도 받지 않은 블록이 직전 확정 depth + 1을
#      넘으면 끌어내린다.
#
# 실행 위치: correct_title_box_depths 이후, flatten_table_internal_blocks 이전.
#            flatten이 base_depth로 최종 depth를 쓰므로 그 앞이어야 한다.
#
# 하지 않는 것:
#   - anchor 자신의 depth 변경 (목차가 최우선 골격이라는 전제를 지킨다)
#   - reading_order_index / block 수 변경
#   - 주변부(peripheral) 블록 변경
#================================================

from __future__ import annotations

from typing import Any

from .pipeline_models import BlocksDocument

_PERIPHERAL_BANDS = {"peripheral"}


def _is_toc_anchor(block: dict[str, Any]) -> bool:
    """목차와 매칭되어 depth가 확정된 블록인지."""
    return (
        str(block.get("depth_source") or "").startswith("toc_depth")
        and (block.get("toc_match") or {}).get("matched") is True
    )


def _has_applied_correction(block: dict[str, Any]) -> bool:
    """앞선 보정 단계가 실제로 depth를 정한 블록인지."""
    correction = block.get("depth_correction")
    return isinstance(correction, dict) and bool(correction.get("applied"))


def _record(block: dict[str, Any], old: int, new: int, reason: str) -> None:
    """무엇이 왜 바뀌었는지 남긴다. 기존 depth_correction은 덮지 않는다."""
    block["toc_flow_correction"] = {
        "old_depth": old,
        "new_depth": new,
        "reason": reason,
    }


def _propagate_from_anchors(blocks: list[dict[str, Any]]) -> int:
    """
    역할: 목차 anchor 뒤의 flow 블록을 anchor_depth + 1로 재계산한다.
    입력 데이터: reading order로 정렬된 block 리스트.
    출력 데이터: 변경한 블록 수.
    """
    changed = 0

    for index, anchor in enumerate(blocks):
        if not _is_toc_anchor(anchor):
            continue

        anchor_depth = anchor.get("depth") or 0
        section_index = anchor.get("section_index")

        for block in blocks[index + 1:]:
            if block.get("section_index") != section_index:
                break
            if block.get("semantic_role") == "section_heading" or _is_toc_anchor(block):
                break
            if block.get("depth_band") in _PERIPHERAL_BANDS:
                continue

            old = block.get("depth") or 0
            new = anchor_depth + 1
            if old == new:
                continue

            block["depth"] = new
            _record(block, old, new, "toc_anchor_flow_propagation")
            changed += 1

    return changed


def _clamp_residual(blocks: list[dict[str, Any]]) -> int:
    """
    역할: 어떤 보정도 받지 않아 1차 부여값이 그대로 남은 블록을
          직전 확정 depth + 1로 끌어내린다.
    입력 데이터: reading order로 정렬된 block 리스트.
    출력 데이터: 변경한 블록 수.
    """
    changed = 0
    last_confirmed: int | None = None

    for block in blocks:
        if block.get("depth_band") in _PERIPHERAL_BANDS:
            continue

        confirmed = (
            block.get("semantic_role") == "section_heading"
            or _is_toc_anchor(block)
            or _has_applied_correction(block)
            or block.get("toc_flow_correction") is not None
        )
        if confirmed:
            last_confirmed = block.get("depth") or 0
            continue

        if last_confirmed is None:
            continue

        old = block.get("depth") or 0
        if old <= last_confirmed + 1:
            continue

        new = last_confirmed + 1
        block["depth"] = new
        _record(block, old, new, "residual_depth_clamp")
        changed += 1

    return changed


#------------------------------------------------
# 진입점
#------------------------------------------------

def propagate_toc_anchor_depth(blocks_doc: BlocksDocument) -> dict[str, Any]:
    """
    역할: 목차 anchor 하위 flow를 전파하고 잔여 구간을 clamp한다.
    입력 데이터: blocks_doc (correct_title_box_depths까지 반영된 상태).
    출력 데이터: 통계 dict. blocks_doc은 제자리에서 갱신된다.
    """
    blocks = sorted(
        blocks_doc.blocks,
        key=lambda b: (
            b.get("reading_order_index") is None,
            b.get("reading_order_index"),
        ),
    )

    anchor_count = sum(1 for b in blocks if _is_toc_anchor(b))
    propagated = _propagate_from_anchors(blocks)
    clamped = _clamp_residual(blocks)

    stats = {
        "toc_anchor_count": anchor_count,
        "flow_propagated_count": propagated,
        "residual_clamped_count": clamped,
    }
    blocks_doc.quality["toc_anchor_flow"] = stats

    print("=== Stage 8-C: 목차 anchor flow 전파 결과 ===")
    print(f"toc anchor           : {anchor_count}")
    print(f"flow 전파 블록        : {propagated}")
    print(f"잔여 clamp 블록       : {clamped}")

    return stats
