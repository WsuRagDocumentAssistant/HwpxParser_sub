#================================================
# generate_llm_context.py
# Stage 10-D: LLM Context Text
#
# depth_text_preview는 사람이 계층을 눈으로 확인하는 디버그 산출물이라
# 표 내부 텍스트를 통째로 빼고(INCLUDE_TABLE_INTERNAL_PREVIEW=False)
# 본문도 120자에서 자른다. 이 문서 기준으로 4,017개 텍스트 중 2,108개가
# 그 산출물에 존재하지 않는다.
#
# 이 모듈은 그 산출물과 목적을 분리해, 텍스트 손실이 없는 LLM 입력용
# 텍스트를 따로 만든다.
#
# 원칙:
# - 자르지 않는다. 텍스트를 요약하거나 생략하지 않는다.
# - 표 내부 cell text / caption을 계층 위치에 포함한다.
# - 텍스트가 있는 블록은 종류를 불문하고 모두 넣는다.
#   머리말/꼬리말처럼 주변부(peripheral)도 버리지 않고 표시만 붙인다.
#   (버릴지 말지는 소비하는 쪽이 정할 문제이고, 여기서 조용히 버리면 안 된다)
# - 제외한 것은 반드시 머리말 통계에 개수로 남긴다.
#================================================

from __future__ import annotations

from typing import Any

from .add_toc_depth0_anchors import iter_toc_entry_levels
from .pipeline_models import (
    BlocksDocument,
    LlmContextText,
    TableInternalBlocks,
)

import logging

# 라이브러리는 조용한 것이 기본이다. 단계 보고를 보려면 쓰는 쪽에서
# logging 을 켠다. tools 는 그렇게 하고 있다.
log = logging.getLogger(__name__)


# 텍스트가 없어도 구조 앵커로 남겨야 하는 블록
_STRUCTURAL_BLOCK_TYPES = frozenset({"table", "image"})

# 블록 종류별 표시 접두어 (텍스트가 없을 때 무엇이 있었는지 알려준다)
_EMPTY_PLACEHOLDER_BY_TYPE = {
    "table": "[table]",
    "image": "[image]",
    "shape": "[shape]",
    "shape_group": "[shape_group]",
}

_INTERNAL_PREFIX = {
    "table_cell_text": "cell",
    "table_caption": "caption",
    "table_control": "control",
}


def _band_tag(block: dict[str, Any]) -> str:
    """주변부/주석 블록임을 드러내는 태그. 본문 블록은 태그 없음."""
    band = block.get("depth_band")
    if band == "peripheral":
        return f"[{block.get('block_type')}] "
    if band == "annotation":
        return f"[{block.get('block_type')}] "
    return ""


def _block_text(block: dict[str, Any]) -> str:
    """블록의 표시 텍스트. 자르지 않는다."""
    text = block.get("text_content")
    if text and str(text).strip():
        return " ".join(str(text).split())

    ref = block.get("table_hierarchy_ref") or {}
    for candidate in (ref.get("title_text"), ref.get("text_preview")):
        if candidate and str(candidate).strip():
            return " ".join(str(candidate).split())

    return ""


def _internal_by_root(
    internal_blocks: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    역할: table_internal_blocks를 root_table_id별로 원본 순서 그대로 묶는다.
          local_order_index는 중첩 표마다 0부터 다시 시작하므로 정렬 키로 쓰지 않고
          리스트 append 순서(= 문서 순서)를 그대로 보존한다.
    입력 데이터: internal_blocks(TableInternalBlocks.internal_blocks).
    출력 데이터: {root_table_id: [internal block, ...]}.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for block in internal_blocks:
        grouped.setdefault(block.get("root_table_id"), []).append(block)
    return grouped


def generate_llm_context(
    blocks_doc: BlocksDocument,
    table_internal: TableInternalBlocks | None = None,
) -> LlmContextText:
    """
    역할: 텍스트 손실 없는 LLM 입력용 계층 텍스트를 만든다.
    입력 데이터: blocks_doc / table_internal (읽기 전용, 아무것도 수정하지 않는다).
    출력 데이터: LlmContextText(text / stats).
    """
    blocks = blocks_doc.blocks
    internal_blocks = (
        table_internal.internal_blocks if table_internal is not None else []
    )
    grouped_internal = _internal_by_root(internal_blocks)

    # 목차 표는 셀을 뭉갠 미리보기 대신 항목을 선언 depth로 펼친다.
    # 문서 골격이므로 미리보기 한 줄로 접으면 계층 정보가 사라진다.
    toc_table_ids = set(
        (blocks_doc.quality.get("toc_depth0_anchor") or {}).get("toc_source_table_ids")
        or []
    )
    toc_entries = iter_toc_entry_levels(internal_blocks, toc_table_ids)

    ordered_blocks = sorted(
        blocks,
        key=lambda b: (
            b.get("reading_order_index") is None,
            b.get("reading_order_index"),
        ),
    )

    lines: list[str] = []
    stats = {
        "block_total": len(blocks),
        "block_emitted": 0,
        "block_skipped_no_text": 0,
        "peripheral_included": 0,
        "annotation_included": 0,
        "cell_text_emitted": 0,
        "caption_emitted": 0,
        "control_emitted": 0,
        "toc_entry_emitted": 0,
        "truncated": 0,
    }

    current_section: Any = object()

    for block in ordered_blocks:
        block_type = block.get("block_type")
        text = _block_text(block)

        if not text and block_type not in _STRUCTURAL_BLOCK_TYPES:
            # 텍스트도 없고 구조 앵커도 아니면 넣을 내용이 없다
            # (빈 문단, colPr/pageHiding 같은 컨트롤)
            stats["block_skipped_no_text"] += 1
            continue

        section_index = block.get("section_index")
        if section_index != current_section:
            if lines:
                lines.append("")
            lines.append(f"==================== section {section_index} ====================")
            lines.append("")
            current_section = section_index

        depth = block.get("depth") or 0
        indent = "  " * depth
        tag = _band_tag(block)

        if block.get("depth_band") == "peripheral":
            stats["peripheral_included"] += 1
        elif block.get("depth_band") == "annotation":
            stats["annotation_included"] += 1

        body = text or _EMPTY_PLACEHOLDER_BY_TYPE.get(block_type, "[empty]")
        lines.append(f"{indent}{tag}{body}")
        stats["block_emitted"] += 1

        if block_type != "table":
            continue

        table_id = (block.get("table_hierarchy_ref") or {}).get("table_id")

        #--- 목차 표: 항목을 선언 depth로 펼친다 (셀 나열 대신) ----------
        if table_id in toc_table_ids:
            for entry_text, entry_depth in toc_entries:
                lines.append(f"{'  ' * entry_depth}(toc) {entry_text}")
                stats["toc_entry_emitted"] += 1
            continue

        #--- 표 내부: cell text / caption을 계층 위치에 그대로 붙인다 -----

        for internal in grouped_internal.get(table_id) or []:
            internal_type = internal.get("internal_block_type")
            prefix = _INTERNAL_PREFIX.get(internal_type)

            if prefix is None:
                continue

            internal_text = internal.get("text_content")
            if not internal_text or not str(internal_text).strip():
                continue

            local_depth = internal.get("local_depth") or 1
            internal_indent = "  " * (depth + local_depth)
            flat_text = " ".join(str(internal_text).split())

            if internal_type == "table_caption":
                image_ref = internal.get("binary_item_id_ref")
                suffix = f"  <- {image_ref}" if image_ref else ""
                lines.append(f"{internal_indent}({prefix}) {flat_text}{suffix}")
                stats["caption_emitted"] += 1
            elif internal_type == "table_control":
                control_type = internal.get("object_type") or "control"
                lines.append(f"{internal_indent}({prefix}:{control_type}) {flat_text}")
                stats["control_emitted"] += 1
            else:
                lines.append(f"{internal_indent}({prefix}) {flat_text}")
                stats["cell_text_emitted"] += 1

    header = [
        "# HWPX LLM context",
        f"# blocks: total={stats['block_total']} emitted={stats['block_emitted']} "
        f"skipped_no_text={stats['block_skipped_no_text']}",
        f"# table internals: cell_text={stats['cell_text_emitted']} "
        f"caption={stats['caption_emitted']} control={stats['control_emitted']} "
        f"toc_entry={stats['toc_entry_emitted']}",
        f"# peripheral_included={stats['peripheral_included']} "
        f"annotation_included={stats['annotation_included']}",
        f"# truncated={stats['truncated']} (this artifact never truncates)",
        "",
    ]

    text_out = "\n".join(header + lines) + "\n"

    log.info("=== Stage 10-D: LLM Context 결과 ===")
    log.info(f"emitted blocks     : {stats['block_emitted']} / {stats['block_total']}")
    log.info(f"skipped (no text)  : {stats['block_skipped_no_text']}")
    log.info(f"cell text lines    : {stats['cell_text_emitted']}")
    log.info(f"caption lines      : {stats['caption_emitted']}")
    log.info(f"control lines      : {stats['control_emitted']}")
    log.info(f"toc entry lines    : {stats['toc_entry_emitted']}")

    return LlmContextText(text=text_out, stats=stats)
