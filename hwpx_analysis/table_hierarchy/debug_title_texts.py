from __future__ import annotations

import sys
from typing import Any

from . import common


def _title_text(table: dict[str, Any]) -> str:
    return " ".join(
        text
        for cell in common.get_cells(table)
        if (text := common.get_cell_text(cell))
    )


def _iter_tables(tables: list[dict[str, Any]]):
    for table in tables:
        yield table
        yield from _iter_tables(common.get_child_tables(table))


def _safe_print(text: str) -> None:
    encoding = sys.stdout.encoding or "utf-8"
    print(text.encode(encoding, errors="replace").decode(encoding))


def _table_meta(table: dict[str, Any]) -> str:
    layout = table.get("preprocess", {}).get("layout", {})
    rows = layout.get("row_count", "?")
    cols = layout.get("col_count", "?")
    cells = common.get_cells(table)
    non_empty = sum(1 for c in cells if common.get_cell_text(c))
    nested = table.get("is_nested", False)
    tid = table.get("table_id", "")
    text = _title_text(table)
    return f"rows={rows} cols={cols} non_empty={non_empty} nested={nested} len={len(text)} id={tid}"


def debug_title_texts(input_path: str = "tables_hierarchical.json") -> None:
    for table in _iter_tables(common.load_tables(input_path)):
        table_type = common.get_table_type(table)
        if table_type == "title_box":
            _safe_print(f"[title_box] {_title_text(table)}")
        elif table_type == "caption_or_note_table":
            _safe_print(f"[caption_or_note] {_table_meta(table)}")
            _safe_print(f"  >> {_title_text(table)[:120]}")
