#================================================
# apply_depth_constraints.py
# Stage 8-B: DepthResolver 제약 전파
#
# Stage 8-A가 생성한 depth_candidates(top-k)를 입력으로,
# 복수 후보가 있는 heading block의 최종 depth를 재판정한다.
#
# 기본 정책: 완화 후보는 기각한다.
# 채택 조건 (전부 만족해야 함):
#   1. heading의 style cluster 멤버 수 >= 2 (싱글턴 = 표지형 디스플레이 스타일)
#   2. cluster preferred_depth(80% 이상 점유)와 충돌하지 않음
#   3. old_depth보다 얕거나 같은 다음 heading 전까지 하위 heading이 없음
#      (하위 heading이 있으면 완화 시 새 점프가 생기므로 기각)
#
# 채택 시: 다음 section_heading 전까지의 flow block depth를
#          selected heading depth + 1로 연쇄 재계산한다.
#
# 입력/출력: BlocksDocument를 제자리에서 갱신한다.
#            최종 소비 기준 depth는 blocks[].depth이며,
#            depth 보정의 마지막 단계는 correct_title_box_depths다.
#================================================

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from hwpx_analysis.pipeline_models import BlocksDocument


# preferred_depth로 인정할 클러스터 내 점유율
_PREFERRED_DEPTH_RATIO = 0.8

# 전파 대상 flow role
_PROPAGATION_ROLES = frozenset({
    "body_text", "list_item", "empty_paragraph",
    "table", "figure", "decorative_shape_candidate",
})


#------------------------------------------------
# 클러스터 depth 통계
#------------------------------------------------

def _build_heading_cluster_stats(blocks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """section_heading 블록의 클러스터별 depth 분포와 preferred_depth를 계산한다."""
    depth_counts: dict[str, Counter] = defaultdict(Counter)

    for block in blocks:
        if block.get("semantic_role") != "section_heading":
            continue
        cluster_id = (block.get("style_features") or {}).get("style_cluster_id")
        if cluster_id is None:
            continue
        depth_counts[cluster_id][block.get("depth")] += 1

    stats: dict[str, dict[str, Any]] = {}
    for cluster_id, counts in depth_counts.items():
        member_count = sum(counts.values())
        top_depth, top_count = counts.most_common(1)[0]
        ratio = top_count / member_count
        stats[cluster_id] = {
            "member_count": member_count,
            "depth_distribution": dict(counts),
            "preferred_depth": top_depth if ratio >= _PREFERRED_DEPTH_RATIO else None,
            "preferred_depth_ratio": round(ratio, 2),
        }
    return stats


def _cluster_consistency_score(blocks: list[dict[str, Any]]) -> float:
    """heading 클러스터별 최빈 depth 점유율의 멤버수 가중 평균 (변경 후 재계산)."""
    stats = _build_heading_cluster_stats(blocks)
    total = sum(s["member_count"] for s in stats.values())
    if total == 0:
        return 1.0
    weighted = sum(
        s["preferred_depth_ratio"] * s["member_count"] for s in stats.values()
    )
    return round(weighted / total, 3)


#------------------------------------------------
# 완화 후보 판정
#------------------------------------------------

def _find_relaxation_candidate(block: dict[str, Any]) -> dict[str, Any] | None:
    for candidate in block.get("depth_candidates") or []:
        if any(s.startswith("depth_jump_relaxation") for s in candidate.get("signals", [])):
            return candidate
    return None


def _has_descendant_headings(
    blocks: list[dict[str, Any]],
    start_index: int,
    old_depth: int,
) -> bool:
    """old_depth 이하의 다음 heading 전 구간에 하위 heading이 있는지 검사한다."""
    for block in blocks[start_index + 1:]:
        if block.get("depth_band") != "body":
            continue
        if block.get("semantic_role") != "section_heading":
            continue
        if block.get("depth") <= old_depth:
            return False
        return True  # 더 깊은 heading 발견
    return False


def _judge_relaxation(
    block: dict[str, Any],
    block_index: int,
    blocks: list[dict[str, Any]],
    cluster_stats: dict[str, dict[str, Any]],
    relaxation: dict[str, Any],
) -> tuple[bool, list[str]]:
    """완화 후보 채택 여부와 사유 목록을 반환한다. 기본은 기각."""
    reasons: list[str] = []
    cluster_id = (block.get("style_features") or {}).get("style_cluster_id")
    stats = cluster_stats.get(cluster_id)

    # 조건 1: 싱글턴 클러스터 금지
    if stats is None or stats["member_count"] < 2:
        reasons.append(
            f"rejected:singleton_cluster ({cluster_id} n={stats['member_count'] if stats else 0})"
        )
        return False, reasons

    # 조건 2: cluster preferred_depth와 충돌 금지
    preferred = stats["preferred_depth"]
    if preferred is not None and relaxation["depth"] != preferred:
        reasons.append(
            f"rejected:cluster_consistency (preferred_depth={preferred} "
            f"ratio={stats['preferred_depth_ratio']}, relaxed={relaxation['depth']})"
        )
        return False, reasons

    # 조건 3: 하위 heading 존재 시 금지 (완화하면 새 점프 발생)
    if _has_descendant_headings(blocks, block_index, block["depth"]):
        reasons.append("rejected:descendant_headings_present")
        return False, reasons

    reasons.append(
        f"adopted: non_singleton({stats['member_count']}) "
        f"cluster_consistent(preferred={preferred}) no_descendant_headings"
    )
    return True, reasons


#------------------------------------------------
# 채택 시 flow 전파
#------------------------------------------------

def _propagate_flow_depth(
    blocks: list[dict[str, Any]],
    heading_index: int,
    new_heading_depth: int,
    heading_block_id: str,
    update_log: list[dict[str, Any]],
) -> int:
    """다음 section_heading 전까지의 flow block depth를 new_depth+1로 재계산한다."""
    propagated = 0
    target_depth = new_heading_depth + 1

    for block in blocks[heading_index + 1:]:
        if block.get("depth_band") != "body":
            continue
        if block.get("semantic_role") == "section_heading":
            break
        if block.get("semantic_role") not in _PROPAGATION_ROLES:
            continue
        if (block.get("depth_source") or "").startswith("toc_depth"):
            continue  # 목차 기반 depth anchor는 flow 전파로 덮지 않는다
        if block.get("depth") == target_depth:
            continue

        update_log.append({
            "block_id": block["block_id"],
            "old_depth": block.get("depth"),
            "new_depth": target_depth,
            "reason": "flow_propagation_from_relaxed_heading",
            "affected_by_heading_block_id": heading_block_id,
        })
        block["depth"] = target_depth
        _sync_selected_candidate(block)
        propagated += 1

    return propagated


def _sync_selected_candidate(block: dict[str, Any]) -> None:
    """depth 변경 후 selected_depth_candidate_index를 재동기화한다."""
    candidates = block.get("depth_candidates") or []
    depth = block.get("depth")
    for index, candidate in enumerate(candidates):
        if candidate["depth"] == depth:
            block["selected_depth_candidate_index"] = index
            return
    candidates.append({
        "depth": depth,
        "score": 0.5,
        "signals": ["assigned_by_constraint_propagation"],
    })
    block["depth_candidates"] = candidates
    block["selected_depth_candidate_index"] = len(candidates) - 1


#------------------------------------------------
# 진입점
#------------------------------------------------

def apply_depth_constraints(
    blocks_doc: BlocksDocument,
) -> BlocksDocument:
    """
    역할: 복수 depth 후보를 가진 heading의 최종 depth를 보수적 제약으로 재판정한다.
    입력 데이터: blocks_doc(Stage 8-A까지 반영된 BlocksDocument — 단일 진실 소스).
    출력 데이터: 갱신된 BlocksDocument.
    """
    blocks = sorted(
        blocks_doc.blocks,
        key=lambda b: b.get("reading_order_index", 0),
    )

    # 변경 전 클러스터 통계 (판정 기준은 변경 전 분포로 고정)
    cluster_stats = _build_heading_cluster_stats(blocks)

    update_log: list[dict[str, Any]] = []
    relaxed_heading_count = 0
    unchanged_jump_count = 0
    propagated_flow_block_count = 0

    for index, block in enumerate(blocks):
        if block.get("semantic_role") != "section_heading":
            continue

        relaxation = _find_relaxation_candidate(block)
        if relaxation is None:
            continue

        adopted, reasons = _judge_relaxation(
            block, index, blocks, cluster_stats, relaxation,
        )

        old_depth = block["depth"]
        decision = {
            "action": "relaxed" if adopted else "kept",
            "old_depth": old_depth,
            "new_depth": relaxation["depth"] if adopted else old_depth,
            "relaxation_candidate_depth": relaxation["depth"],
            "reasons": reasons,
        }
        block["depth_constraint_decision"] = decision

        if adopted:
            relaxed_heading_count += 1
            update_log.append({
                "block_id": block["block_id"],
                "old_depth": old_depth,
                "new_depth": relaxation["depth"],
                "reason": "heading_jump_relaxation_adopted",
                "affected_by_heading_block_id": None,
            })
            block["depth"] = relaxation["depth"]
            _sync_selected_candidate(block)

            propagated_flow_block_count += _propagate_flow_depth(
                blocks, index, block["depth"], block["block_id"], update_log,
            )
        else:
            unchanged_jump_count += 1

    consistency = _cluster_consistency_score(blocks)

    quality = blocks_doc.quality
    quality["depth_constraints"] = {
        "depth_changed_count": len(update_log),
        "relaxed_heading_count": relaxed_heading_count,
        "unchanged_jump_count": unchanged_jump_count,
        "cluster_consistency_score": consistency,
        "propagated_flow_block_count": propagated_flow_block_count,
    }
    quality["depth_update_log"] = update_log

    print("=== Stage 8-B: depth 제약 전파 결과 ===")
    print(f"depth_changed_count: {len(update_log)}")
    print(f"relaxed_heading_count: {relaxed_heading_count}")
    print(f"unchanged_jump_count: {unchanged_jump_count}")
    print(f"propagated_flow_block_count: {propagated_flow_block_count}")
    print(f"cluster_consistency_score: {consistency}")

    return blocks_doc
