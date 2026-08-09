from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def load_tables(
    source: str | Path | list[dict[str, Any]] | dict[str, Any] = "tables_hierarchical.json",
) -> list[dict[str, Any]]:
    """
    역할: 표 리스트 소스를 정규화한다.
    입력 데이터: 인메모리 표 리스트/dict 또는 (하위 호환) JSON 파일 경로.
    출력 데이터: 표 dict 리스트.
    """
    if isinstance(source, (str, Path)):
        with Path(source).open("r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = source

    if isinstance(data, list):
        return data

    if isinstance(data, dict) and isinstance(data.get("tables"), list):
        return data["tables"]

    raise ValueError(
        "tables source must be a list or a dict with a 'tables' list."
    )


def get_nested(data: Any, *keys: str, default: Any = None) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        if key not in current:
            return default
        current = current[key]
    return current


def get_table_id(table: dict[str, Any]) -> str:
    table_id = table.get("table_id")
    if table_id:
        return str(table_id)

    preprocess_table_id = get_nested(table, "preprocess", "identity", "table_id")
    if preprocess_table_id:
        return str(preprocess_table_id)

    return "unknown_table"


def get_table_type(table: dict[str, Any]) -> str:
    table_type = get_nested(table, "hierarchy", "table_type")
    if table_type:
        return str(table_type)
    return "unknown"


def get_layout(table: dict[str, Any]) -> dict[str, Any]:
    row_count = get_nested(table, "preprocess", "layout", "row_count")
    col_count = get_nested(table, "preprocess", "layout", "col_count")
    repeat_header = get_nested(
        table,
        "preprocess",
        "layout",
        "repeat_header",
        default=False,
    )

    if row_count is None:
        row_count = get_nested(table, "grid", "row_count", default=0)
    if col_count is None:
        col_count = get_nested(table, "grid", "col_count", default=0)

    return {
        "row_count": row_count or 0,
        "col_count": col_count or 0,
        "repeat_header": bool(repeat_header),
    }


def get_grid(table: dict[str, Any]) -> dict[str, Any]:
    grid = table.get("grid")
    if not isinstance(grid, dict):
        grid = {}

    return {
        "row_count": grid.get("row_count", 0) or 0,
        "col_count": grid.get("col_count", 0) or 0,
        "slots": grid.get("slots", []) or [],
        "issues": grid.get("issues", []) or [],
    }


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


def get_cell_position(cell: dict[str, Any]) -> dict[str, int]:
    position = cell.get("position")
    if not isinstance(position, dict):
        position = {}

    return {
        "row_addr": position.get("row_addr", cell.get("row_addr", 0)) or 0,
        "col_addr": position.get("col_addr", cell.get("col_addr", 0)) or 0,
        "row_span": position.get("row_span", cell.get("row_span", 1)) or 1,
        "col_span": position.get("col_span", cell.get("col_span", 1)) or 1,
    }


def get_header_rows(table: dict[str, Any]) -> list[Any]:
    header_rows = get_nested(table, "hierarchy", "header_rows")
    if isinstance(header_rows, list):
        return header_rows
    return []


def get_header_cols(table: dict[str, Any]) -> list[Any]:
    header_cols = get_nested(table, "hierarchy", "header_cols")
    if isinstance(header_cols, list):
        return header_cols
    return []


def get_body_cells(table: dict[str, Any]) -> list[Any]:
    body_cells = get_nested(table, "hierarchy", "body_cells")
    if isinstance(body_cells, list):
        return body_cells
    return []


def get_child_tables(table: dict[str, Any]) -> list[dict[str, Any]]:
    children = table.get("children")
    if not isinstance(children, list):
        return []

    return [
        child_table
        for child_table in children
        if isinstance(child_table, dict)
    ]


def get_nested_table_refs(table: dict[str, Any]) -> list[dict[str, Any]]:
    nested_table_refs = get_nested(table, "hierarchy", "nested_table_refs")
    if isinstance(nested_table_refs, list):
        return nested_table_refs
    return []


def build_nested_ref_map(table: dict[str, Any]) -> dict[str, str]:
    ref_map: dict[str, str] = {}

    for ref in get_nested_table_refs(table):
        if not isinstance(ref, dict):
            continue

        nested_table_id = ref.get("nested_table_id")
        parent_cell_id = ref.get("parent_cell_id")
        if nested_table_id and parent_cell_id:
            ref_map[str(nested_table_id)] = str(parent_cell_id)

    return ref_map


def iter_child_tables(
    table: dict[str, Any],
) -> Iterator[tuple[str | None, dict[str, Any]]]:
    ref_map = build_nested_ref_map(table)

    for child_table in get_child_tables(table):
        child_table_id = get_table_id(child_table)
        parent_cell_id = ref_map.get(child_table_id)
        if parent_cell_id is None:
            fallback_parent_cell_id = child_table.get("parent_cell_id")
            if fallback_parent_cell_id:
                parent_cell_id = str(fallback_parent_cell_id)

        yield parent_cell_id, child_table

