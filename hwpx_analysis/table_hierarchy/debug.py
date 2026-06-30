from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
from typing import Any

from .common import (
    get_body_cells,
    get_cell_position,
    get_cell_text,
    get_cells,
    get_child_tables,
    get_grid,
    get_header_cols,
    get_header_rows,
    get_layout,
    get_nested,
    get_nested_table_refs,
    get_table_id,
    get_table_type,
    iter_child_tables,
    load_tables,
)


def _prefix(indent: int) -> str:
    return " " * indent


def _preview(text: str, limit: int) -> str:
    normalized = " ".join(str(text).replace("\r", " ").replace("\n", " ").split())
    return normalized[:limit]


def _print(line: str = "") -> None:
    encoding = sys.stdout.encoding or "utf-8"
    safe_line = line.encode(encoding, errors="replace").decode(encoding)
    print(safe_line)


def _plain_text_preview(table: dict[str, Any]) -> str:
    text = get_nested(
        table,
        "preprocess",
        "text",
        "plain_text_without_nested_tables",
    )
    if text is None:
        text = get_nested(table, "preprocess", "text", "plain_text")
    if text is None:
        text = " ".join(get_cell_text(cell) for cell in get_cells(table))

    return _preview(str(text), 100)


def _iter_tables_recursive(tables: list[dict[str, Any]]):
    for table in tables:
        yield table
        yield from _iter_tables_recursive(get_child_tables(table))


def _iter_child_tables_recursive(table: dict[str, Any]):
    for _parent_cell_id, child_table in iter_child_tables(table):
        yield child_table
        yield from _iter_child_tables_recursive(child_table)


def print_table_debug_summary(table: dict[str, Any], indent: int = 0) -> None:
    prefix = _prefix(indent)
    child_prefix = _prefix(indent + 2)
    layout = get_layout(table)
    grid = get_grid(table)
    cells = get_cells(table)
    non_empty_cells = sum(1 for cell in cells if get_cell_text(cell))
    grid_issues = grid.get("issues", [])

    _print(f"{prefix}[table] {get_table_id(table)}")
    _print(f"{child_prefix}type: {get_table_type(table)}")
    _print(
        f"{child_prefix}layout: "
        f"{layout['row_count']} x {layout['col_count']}"
    )
    _print(f"{child_prefix}header_rows: {get_header_rows(table)}")
    _print(f"{child_prefix}header_cols: {get_header_cols(table)}")
    _print(f"{child_prefix}body_cells: {len(get_body_cells(table))}")
    _print(f"{child_prefix}cells: {len(cells)} non_empty={non_empty_cells}")
    _print(
        f"{child_prefix}grid: "
        f"{grid['row_count']} x {grid['col_count']} issues={len(grid_issues)}"
    )
    _print(f"{child_prefix}preview: {_plain_text_preview(table)}")


def print_table_cells_debug(
    table: dict[str, Any],
    indent: int = 0,
    max_cells: int = 5,
) -> None:
    prefix = _prefix(indent)
    cell_prefix = _prefix(indent + 2)

    _print(f"{prefix}cells preview:")
    for cell in get_cells(table)[:max_cells]:
        if not isinstance(cell, dict):
            continue

        position = get_cell_position(cell)
        cell_id = cell.get("cell_id", "")
        text = _preview(get_cell_text(cell), 80)

        _print(
            f"{cell_prefix}- "
            f"r{position['row_addr']} "
            f"c{position['col_addr']} "
            f"span={position['row_span']}x{position['col_span']} "
            f"id={cell_id} "
            f"text={text}"
        )


def debug_one_table(
    table: dict[str, Any],
    include_cells: bool = True,
    include_nested: bool = True,
    indent: int = 0,
) -> None:
    print_table_debug_summary(table, indent=indent)

    if include_cells:
        print_table_cells_debug(table, indent=indent + 2)

    if include_nested:
        for parent_cell_id, nested_table in iter_child_tables(table):
            _print(f"{_prefix(indent + 2)}[nested] parent_cell={parent_cell_id}")
            debug_one_table(
                nested_table,
                include_cells=include_cells,
                include_nested=include_nested,
                indent=indent + 4,
            )


def debug_table_hierarchy_input(
    input_path: str | Path = "tables_hierarchical.json",
    limit: int | None = 10,
    table_type: str | None = None,
    table_id: str | None = None,
    include_cells: bool = True,
    include_nested: bool = True,
) -> None:
    tables = load_tables(input_path)
    all_tables = list(_iter_tables_recursive(tables))
    top_level_type_counts = Counter(get_table_type(table) for table in tables)
    recursive_type_counts = Counter(get_table_type(table) for table in all_tables)
    nested_count = sum(
        1
        for table in tables
        for _child_table in _iter_child_tables_recursive(table)
    )
    nested_ref_count = sum(
        len(get_nested_table_refs(table))
        for table in all_tables
    )
    tables_with_grid_issues = sum(
        1
        for table in tables
        if get_grid(table).get("issues")
    )

    printed = 0
    for table in tables:
        if table_id is not None and get_table_id(table) != table_id:
            continue
        if table_type is not None and get_table_type(table) != table_type:
            continue
        if limit is not None and printed >= limit:
            break

        if printed:
            _print("")
        debug_one_table(
            table,
            include_cells=include_cells,
            include_nested=include_nested,
        )
        printed += 1

    _print("")
    _print("[summary]")
    _print(f"  total top-level tables loaded: {len(tables)}")
    _print(f"  total tables including nested: {len(all_tables)}")
    _print(f"  printed top-level tables: {printed}")
    _print(f"  top-level type counts: {dict(top_level_type_counts)}")
    _print(f"  recursive type counts: {dict(recursive_type_counts)}")
    _print(f"  nested tables found in children: {nested_count}")
    _print(f"  nested table refs found: {nested_ref_count}")
    _print(f"  tables with grid issues: {tables_with_grid_issues}")
