from __future__ import annotations

from typing import Any


def to_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_machine_grid(table: dict[str, Any]) -> dict[str, Any]:
    row_count, col_count = get_table_size(table)
    issues: list[dict[str, Any]] = []

    grid = {
        "row_count": row_count,
        "col_count": col_count,
        "slots": [],
        "issues": issues,
    }

    if row_count is None or col_count is None or row_count <= 0 or col_count <= 0:
        issues.append(
            {
                "type": "invalid_table_size",
                "row_count": row_count,
                "col_count": col_count,
            }
        )
        return grid

    grid_cells: list[list[dict[str, Any] | None]] = [
        [None for _ in range(col_count)]
        for _ in range(row_count)
    ]

    for cell in _iter_direct_cells(table):
        cell_id = cell.get("cell_id")

        if not isinstance(cell_id, str) or not cell_id:
            issues.append(
                {
                    "type": "missing_cell_id",
                    "cell": _cell_issue_ref(cell),
                }
            )
            continue

        row_addr = get_cell_int(cell, "row_addr")
        col_addr = get_cell_int(cell, "col_addr")

        if row_addr is None or col_addr is None:
            issues.append(
                {
                    "type": "invalid_position",
                    "cell_id": cell_id,
                    "row_addr": cell.get("row_addr"),
                    "col_addr": cell.get("col_addr"),
                }
            )
            continue

        row_span = get_cell_int(cell, "row_span", default=1)
        col_span = get_cell_int(cell, "col_span", default=1)

        if row_span is None or row_span <= 0:
            issues.append(
                {
                    "type": "invalid_span",
                    "cell_id": cell_id,
                    "field": "row_span",
                    "value": cell.get("row_span"),
                    "fallback": 1,
                }
            )
            row_span = 1

        if col_span is None or col_span <= 0:
            issues.append(
                {
                    "type": "invalid_span",
                    "cell_id": cell_id,
                    "field": "col_span",
                    "value": cell.get("col_span"),
                    "fallback": 1,
                }
            )
            col_span = 1

        for row_index in range(row_addr, row_addr + row_span):
            for col_index in range(col_addr, col_addr + col_span):
                if (
                    row_index < 0
                    or col_index < 0
                    or row_index >= row_count
                    or col_index >= col_count
                ):
                    issues.append(
                        {
                            "type": "out_of_bounds",
                            "cell_id": cell_id,
                            "row_index": row_index,
                            "col_index": col_index,
                            "row_count": row_count,
                            "col_count": col_count,
                            "origin_row": row_addr,
                            "origin_col": col_addr,
                        }
                    )
                    continue

                if grid_cells[row_index][col_index] is not None:
                    issues.append(
                        {
                            "type": "overlap",
                            "cell_id": cell_id,
                            "row_index": row_index,
                            "col_index": col_index,
                            "existing": grid_cells[row_index][col_index],
                            "origin_row": row_addr,
                            "origin_col": col_addr,
                        }
                    )
                    continue

                if row_index == row_addr and col_index == col_addr:
                    grid_cells[row_index][col_index] = {
                        "kind": "origin",
                        "cell_id": cell_id,
                    }
                else:
                    grid_cells[row_index][col_index] = {
                        "kind": "covered",
                        "cell_id": cell_id,
                        "origin_row": row_addr,
                        "origin_col": col_addr,
                    }

    for row_index in range(row_count):
        for col_index in range(col_count):
            if grid_cells[row_index][col_index] is None:
                grid_cells[row_index][col_index] = {"kind": "empty"}
                issues.append(
                    {
                        "type": "missing_grid_cell",
                        "row_index": row_index,
                        "col_index": col_index,
                    }
                )

    grid["slots"] = grid_cells

    return grid


def add_grid_to_tables(tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for table in tables:
        preprocess_grid = get_valid_preprocess_grid(table)

        if preprocess_grid is not None and not has_top_level_cells(table):
            table["grid"] = preprocess_grid
        else:
            table["grid"] = build_machine_grid(table)

        found_nested = False
        for cell in get_direct_cells(table):
            nested_tables = cell.get("nested_tables")

            if isinstance(nested_tables, list):
                found_nested = True
                add_grid_to_tables(nested_tables)

        if not found_nested:
            children = table.get("children")
            if isinstance(children, list):
                add_grid_to_tables([
                    child for child in children
                    if isinstance(child, dict)
                ])

    return tables


def add_table_grid(tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    역할: preprocess가 반영된 표 리스트에 grid(slots) 정보를 추가한다.
    입력 데이터: tables(preprocess 표 dict 리스트). in-place로 grid 키를 추가한다.
    출력 데이터: grid가 추가된 동일 리스트.
    """
    if not isinstance(tables, list):
        raise ValueError("tables 최상위 구조는 list[table] 이어야 합니다.")

    return add_grid_to_tables(tables)


def get_direct_cells(table: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []

    for row in table.get("rows", []):
        if not isinstance(row, dict):
            continue

        for cell in row.get("cells", []):
            if isinstance(cell, dict):
                result.append(cell)

    if result:
        return result

    cells = table.get("cells")

    if isinstance(cells, list):
        return [
            cell for cell in cells
            if isinstance(cell, dict)
        ]

    preprocess_cells = get_preprocess_cells(table)
    if preprocess_cells:
        return preprocess_cells

    return []


def _iter_direct_cells(table: dict[str, Any]) -> list[dict[str, Any]]:
    return get_direct_cells(table)


def _cell_issue_ref(cell: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_addr": get_cell_int(cell, "row_addr"),
        "col_addr": get_cell_int(cell, "col_addr"),
        "row_span": get_cell_int(cell, "row_span"),
        "col_span": get_cell_int(cell, "col_span"),
    }


def get_table_size(table: dict[str, Any]) -> tuple[int | None, int | None]:
    row_count = to_int(table.get("row_count"))
    col_count = to_int(table.get("col_count"))

    if row_count is not None and col_count is not None:
        return row_count, col_count

    preprocess = table.get("preprocess")
    layout = preprocess.get("layout") if isinstance(preprocess, dict) else None
    if isinstance(layout, dict):
        row_count = row_count if row_count is not None else to_int(layout.get("row_count"))
        col_count = col_count if col_count is not None else to_int(layout.get("col_count"))

    return row_count, col_count


def get_preprocess_cells(table: dict[str, Any]) -> list[dict[str, Any]]:
    preprocess = table.get("preprocess")
    if not isinstance(preprocess, dict):
        return []

    cells = preprocess.get("cells")
    if not isinstance(cells, list):
        return []

    return [
        cell for cell in cells
        if isinstance(cell, dict)
    ]


def get_valid_preprocess_grid(table: dict[str, Any]) -> dict[str, Any] | None:
    preprocess = table.get("preprocess")
    if not isinstance(preprocess, dict):
        return None

    grid = preprocess.get("grid")
    if not isinstance(grid, dict):
        return None

    row_count = to_int(grid.get("row_count"))
    col_count = to_int(grid.get("col_count"))
    if row_count is None or col_count is None or row_count <= 0 or col_count <= 0:
        return None

    slots = grid.get("slots")
    cells = grid.get("cells")
    if not isinstance(slots, list) and not isinstance(cells, list):
        return None

    return grid


def has_top_level_cells(table: dict[str, Any]) -> bool:
    rows = table.get("rows")
    if isinstance(rows, list) and rows:
        return True

    cells = table.get("cells")
    return isinstance(cells, list) and bool(cells)


def get_cell_int(
    cell: dict[str, Any],
    field: str,
    default: int | None = None,
) -> int | None:
    value = to_int(cell.get(field))
    if value is not None:
        return value

    position = cell.get("position")
    if isinstance(position, dict):
        value = to_int(position.get(field))
        if value is not None:
            return value

    return default
