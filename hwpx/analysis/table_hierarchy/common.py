from __future__ import annotations

from typing import Any


def get_nested(data: Any, *keys: str, default: Any = None) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        if key not in current:
            return default
        current = current[key]
    return current


def get_cells(table: dict[str, Any]) -> list[dict[str, Any]]:
    preprocess_cells = get_nested(table, "preprocess", "cells")
    if isinstance(preprocess_cells, list):
        return preprocess_cells

    cells = table.get("cells")
    if isinstance(cells, list):
        return cells

    return []


def get_cell_text(cell: dict[str, Any]) -> str:
    text_data = cell.get("text")

    if isinstance(text_data, dict):
        text = text_data.get("text", "")
    elif isinstance(text_data, str):
        text = text_data
    else:
        text = ""

    return str(text).strip()

