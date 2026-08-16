#================================================
# table_hierarchy/grid_normalizer.py
# grid 정규화 (재귀)
#================================================

from __future__ import annotations

from typing import Any

from .cell_utils import _as_list


def normalize_grid_location_recursive(table: dict[str, Any]) -> None:
    preprocess = table.get("preprocess")
    preprocess_grid = preprocess.get("grid") if isinstance(preprocess, dict) else None

    if isinstance(preprocess_grid, dict) and not is_valid_grid(table.get("grid")):
        table["grid"] = preprocess_grid

    grid = table.get("grid")
    if isinstance(grid, dict):
        grid.pop("cells", None)

    if isinstance(preprocess, dict):
        preprocess.pop("grid", None)

    recursed = False
    for row in _as_list(table.get("rows")):
        if not isinstance(row, dict):
            continue
        for cell in _as_list(row.get("cells")):
            if not isinstance(cell, dict):
                continue
            nested_tables = cell.get("nested_tables")
            if not isinstance(nested_tables, list):
                continue
            recursed = True
            for nested_table in nested_tables:
                if isinstance(nested_table, dict):
                    normalize_grid_location_recursive(nested_table)

    if recursed:
        return

    for cell in _as_list(table.get("cells")):
        if not isinstance(cell, dict):
            continue
        nested_tables = cell.get("nested_tables")
        if not isinstance(nested_tables, list):
            continue
        recursed = True
        for nested_table in nested_tables:
            if isinstance(nested_table, dict):
                normalize_grid_location_recursive(nested_table)

    if recursed:
        return

    for child in _as_list(table.get("children")):
        if isinstance(child, dict):
            normalize_grid_location_recursive(child)


def is_valid_grid(grid: Any) -> bool:
    if not isinstance(grid, dict):
        return False

    if grid.get("row_count") is None or grid.get("col_count") is None:
        return False

    slots = grid.get("slots")
    return isinstance(slots, list) and len(slots) > 0
