#================================================
# generate_depth_text_preview.py
# Stage 10-C: Depth Text Preview
#
# 최종 산출물의 계층(depth)이 어떻게 잡혔는지 사람이 눈으로
# 바로 확인할 수 있는 계층 시각화 텍스트를 생성한다.
#
# 핵심 원칙:
# - 순수 텍스트. JSON 객체/필드 목록을 출력하지 않는다.
# - BlocksDocument의 depth/reading_order_index를 그대로 사용한다 (재계산 금지).
# - TableInternalBlocks는 title_box 텍스트 fallback 용도로만 읽는다.
#   global stream에 병합하지 않는다.
# - 입력 데이터는 읽기 전용이며 이 단계는 아무것도 수정하지 않는다.
#================================================

from __future__ import annotations

from typing import Any

from hwpx_analysis.add_toc_depth0_anchors import iter_toc_entry_levels
from hwpx_analysis.pipeline_models import (
    BlocksDocument,
    DepthTextPreview,
    TableInternalBlocks,
)

# True일 때만 각 table 아래에 내부 cell text를 추가 출력한다 (기본 False)
INCLUDE_TABLE_INTERNAL_PREVIEW = False

_MAX_TEXT_LENGTH = 120

_TABLE_TYPE_PREFIXES = {
    "title_box": "[title_box] ",
    "data_table": "[table:data_table] ",
    "key_value_table": "[table:key_value_table] ",
    "caption_or_note_table": "[table:caption_or_note_table] ",
}

_EMPTY_PLACEHOLDER_BY_TYPE = {
    "table": "[table]",
    "image": "[image]",
    "shape": "[shape]",
    "document_control": "[document_control]",
}


def _clean_text(text: str) -> str:
    """줄바꿈을 공백으로 치환하고 연속 공백을 정규화한 뒤 120자로 자른다."""
    cleaned = " ".join(text.split())
    if len(cleaned) > _MAX_TEXT_LENGTH:
        cleaned = cleaned[:_MAX_TEXT_LENGTH] + "…"
    return cleaned


_FALLBACK_CELL_TEXT_LIMIT = 5


def _build_first_cell_text_by_root(internal_blocks: list[dict[str, Any]]) -> dict[str, str]:
    """root_table_id별로 비어 있지 않은 앞쪽 cell text를 이어 붙인다 (table text fallback용).
    title_box는 첫 셀이 번호뿐인 경우가 많아 여러 셀을 합쳐야 제목이 보인다."""
    texts_by_root: dict[str, list[str]] = {}
    for b in internal_blocks:
        if b.get("internal_block_type") != "table_cell_text":
            continue
        root_id = b.get("root_table_id")
        collected = texts_by_root.setdefault(root_id, [])
        if len(collected) >= _FALLBACK_CELL_TEXT_LIMIT:
            continue
        text = (b.get("text_content") or "").strip()
        if text:
            collected.append(text)
    return {root_id: " ".join(texts) for root_id, texts in texts_by_root.items() if texts}


def _select_block_text(
    block: dict[str, Any],
    first_cell_text_by_root: dict[str, str],
) -> str:
    """block 표시 텍스트를 우선순위에 따라 선택한다."""
    ref = block.get("table_hierarchy_ref") or {}
    for candidate in (
        block.get("normalized_text"),
        block.get("text_content"),
        ref.get("title_text"),
        ref.get("text_preview"),
    ):
        if candidate and str(candidate).strip():
            return str(candidate)

    # table은 table_internal_blocks의 첫 cell text를 fallback으로 사용한다
    table_id = ref.get("table_id")
    if table_id and table_id in first_cell_text_by_root:
        return first_cell_text_by_root[table_id]
    return ""


def generate_depth_text_preview(
    blocks_doc: BlocksDocument,
    table_internal: TableInternalBlocks | None = None,
) -> DepthTextPreview:
    """
    역할: BlocksDocument를 reading_order_index 순으로 순회해 depth 들여쓰기 기반
          텍스트 계층 프리뷰를 raw/clean 두 벌 생성한다.
          raw = 전체 block, clean = visibility.include_in_preview == false 제외.
    입력 데이터: blocks_doc / table_internal (읽기 전용).
    출력 데이터: DepthTextPreview(raw_text/clean_text/line_counts/max_depth).
    """
    blocks = blocks_doc.blocks
    internal_blocks = (
        table_internal.internal_blocks if table_internal is not None else []
    )
    first_cell_text_by_root = _build_first_cell_text_by_root(internal_blocks)

    # 목차 표는 문서 골격이므로 fallback 미리보기(앞 5셀 + 120자)로 접지 않고
    # 항목을 선언 depth로 펼친다. 그 외 표는 기존 동작을 유지한다.
    toc_table_ids = set(
        (blocks_doc.quality.get("toc_depth0_anchor") or {}).get("toc_source_table_ids")
        or []
    )
    toc_entries = iter_toc_entry_levels(internal_blocks, toc_table_ids)

    internal_by_root: dict[str, list[dict[str, Any]]] = {}
    if INCLUDE_TABLE_INTERNAL_PREVIEW:
        for b in internal_blocks:
            internal_by_root.setdefault(b.get("root_table_id"), []).append(b)

    ordered_blocks = sorted(
        blocks, key=lambda b: (b.get("reading_order_index") is None, b.get("reading_order_index"))
    )

    def _render(include_hidden: bool) -> tuple[list[str], dict[str, int]]:
        lines: list[str] = []
        counts = {"global": 0, "title_box": 0, "table": 0, "section_heading": 0, "max_depth": 0}
        current_section: Any = object()  # 첫 block에서 반드시 구분선이 나오도록 sentinel

        for block in ordered_blocks:
            if not include_hidden:
                visibility = block.get("visibility") or {}
                if visibility.get("include_in_preview") is False:
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
            ref = block.get("table_hierarchy_ref") or {}
            table_type = ref.get("table_type")
            block_type = block.get("block_type")

            text = _clean_text(_select_block_text(block, first_cell_text_by_root))
            prefix = _TABLE_TYPE_PREFIXES.get(table_type, "")

            if not text and not prefix:
                text = _EMPTY_PLACEHOLDER_BY_TYPE.get(block_type, "[empty]")

            if ref.get("table_id") in toc_table_ids:
                # 미리보기 문자열 대신 목차 항목을 펼친다
                lines.append(f"{indent}(depth={depth}) {prefix}[목차]".rstrip())
                counts["global"] += 1
                for entry_text, entry_depth in toc_entries:
                    lines.append(f"{'  ' * entry_depth}(depth={entry_depth}) (toc) {entry_text}")
                    counts["global"] += 1
                    counts["toc_entry"] = counts.get("toc_entry", 0) + 1
                counts["table"] += 1
                continue

            lines.append(f"{indent}(depth={depth}) {prefix}{text}".rstrip())
            counts["global"] += 1
            counts["max_depth"] = max(counts["max_depth"], depth)
            if table_type == "title_box":
                counts["title_box"] += 1
            if block_type == "table":
                counts["table"] += 1
            if block.get("semantic_role") == "section_heading":
                counts["section_heading"] += 1

            if INCLUDE_TABLE_INTERNAL_PREVIEW and block_type == "table":
                for ib in internal_by_root.get(ref.get("table_id")) or []:
                    if ib.get("internal_block_type") != "table_cell_text":
                        continue
                    cell_text = _clean_text(ib.get("text_content") or "")
                    if not cell_text:
                        continue
                    local_depth = ib.get("local_depth") or 1
                    lines.append(f"{indent}{'  ' * local_depth}(cell) {cell_text}")

        return lines, counts

    raw_lines, raw_counts = _render(include_hidden=True)
    clean_lines, clean_counts = _render(include_hidden=False)

    global_line_count = raw_counts["global"]
    title_box_line_count = raw_counts["title_box"]
    table_line_count = raw_counts["table"]
    section_heading_line_count = raw_counts["section_heading"]
    max_depth = raw_counts["max_depth"]

    print("=== Stage 10-C: Depth Text Preview 결과 ===")
    print(f"raw global line count: {global_line_count}")
    print(f"clean global line count: {clean_counts['global']}")
    print(f"title_box line count: {title_box_line_count}")
    print(f"table line count: {table_line_count}")
    print(f"section_heading line count: {section_heading_line_count}")
    print(f"max_depth: {max_depth}")

    return DepthTextPreview(
        raw_text="\n".join(raw_lines) + "\n",
        clean_text="\n".join(clean_lines) + "\n",
        line_counts={
            "raw_global": global_line_count,
            "clean_global": clean_counts["global"],
            "title_box": title_box_line_count,
            "table": table_line_count,
            "section_heading": section_heading_line_count,
        },
        max_depth=max_depth,
    )
