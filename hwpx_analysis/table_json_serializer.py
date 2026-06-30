#================================================
# document/table/table_json_serializer.py
#================================================

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def to_jsonable(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, list):
        return [to_jsonable(item) for item in value]

    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): to_jsonable(val)
            for key, val in value.items()
        }

    if is_dataclass(value):
        return {
            key: to_jsonable(val)
            for key, val in asdict(value).items()
        }

    if hasattr(value, "__dict__"):
        return {
            key: to_jsonable(val)
            for key, val in value.__dict__.items()
            if not key.startswith("_")
        }

    return str(value)


def table_to_dict(table: Any) -> dict[str, Any]:
    return {
        "table_id": table.table_id,
        "section_index": table.section_index,
        "table_index": table.table_index,
        "xml_table_id": table.xml_table_id,

        "row_count": table.row_count,
        "col_count": table.col_count,
        "cell_spacing": table.cell_spacing,

        "border_fill_id_ref": table.border_fill_id_ref,
        "border_fill": to_jsonable(getattr(table, "border_fill", None)),

        "repeat_header": table.repeat_header,
        "page_break": table.page_break,
        "text_wrap": table.text_wrap,
        "text_flow": table.text_flow,

        "width": table.width,
        "height": table.height,
        "pos_x": table.pos_x,
        "pos_y": table.pos_y,
        "treat_as_char": table.treat_as_char,
        "flow_with_text": table.flow_with_text,

        "in_margin_left": table.in_margin_left,
        "in_margin_right": table.in_margin_right,
        "in_margin_top": table.in_margin_top,
        "in_margin_bottom": table.in_margin_bottom,

        "out_margin_left": table.out_margin_left,
        "out_margin_right": table.out_margin_right,
        "out_margin_top": table.out_margin_top,
        "out_margin_bottom": table.out_margin_bottom,

        "caption_candidate": table.caption_candidate,
        "note_candidate": table.note_candidate,
        "source_candidate": table.source_candidate,

        "validation": to_jsonable(table.validation),
        "semantic": to_jsonable(table.semantic),
        "raw_attrs": to_jsonable(table.raw_attrs),
        "is_nested": getattr(table, "is_nested", False),
        "parent_table_id": getattr(table, "parent_table_id", None),
        "parent_cell_id": getattr(table, "parent_cell_id", None),

        "rows": [
            row_to_dict(row)
            for row in table.rows
        ],
    }


def row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "row_id": row.row_id,
        "table_id": row.table_id,
        "row_index": row.row_index,
        "raw_attrs": to_jsonable(getattr(row, "raw_attrs", {})),

        "cells": [
            cell_to_dict(cell)
            for cell in row.cells
        ],
    }


def cell_to_dict(cell: Any) -> dict[str, Any]:
    return {
        "cell_id": cell.cell_id,
        "table_id": cell.table_id,
        "row_id": cell.row_id,
        "cell_index": cell.cell_index,

        "name": cell.name,
        "header": cell.header,
        "has_margin": cell.has_margin,
        "protect": cell.protect,
        "editable": cell.editable,
        "dirty": cell.dirty,

        "border_fill_id_ref": cell.border_fill_id_ref,
        "border_fill": to_jsonable(getattr(cell, "border_fill", None)),

        "row_addr": cell.row_addr,
        "col_addr": cell.col_addr,
        "row_span": cell.row_span,
        "col_span": cell.col_span,
        "end_row": cell.end_row,
        "end_col": cell.end_col,

        "width": cell.width,
        "height": cell.height,

        "margin_left": cell.margin_left,
        "margin_right": cell.margin_right,
        "margin_top": cell.margin_top,
        "margin_bottom": cell.margin_bottom,

        "sublist_raw_attrs": to_jsonable(cell.sublist_raw_attrs),
        "sublist_id": cell.sublist_id,
        "sublist_text_direction": cell.sublist_text_direction,
        "sublist_line_wrap": cell.sublist_line_wrap,
        "sublist_vert_align": cell.sublist_vert_align,
        "sublist_link_list_id_ref": cell.sublist_link_list_id_ref,
        "sublist_link_list_next_id_ref": cell.sublist_link_list_next_id_ref,
        "sublist_text_width": cell.sublist_text_width,
        "sublist_text_height": cell.sublist_text_height,
        "sublist_has_text_ref": cell.sublist_has_text_ref,
        "sublist_has_num_ref": cell.sublist_has_num_ref,

        "images": to_jsonable(getattr(cell, "images", [])),

        "nested_tables": [
            table_to_dict(nested_table)
            for nested_table in getattr(cell, "nested_tables", [])
        ],

        "paragraphs": [
            paragraph_to_dict(paragraph)
            for paragraph in cell.paragraphs
        ],

        "text": cell.text,
        "is_empty": cell.is_empty,
        "has_image": cell.has_image,
        "has_field": cell.has_field,
        "has_shape": cell.has_shape,

        "is_column_header": cell.is_column_header,
        "is_row_header": cell.is_row_header,
        "is_group_header": cell.is_group_header,
        "is_data_cell": cell.is_data_cell,

        "raw_attrs": to_jsonable(cell.raw_attrs),
    }


def paragraph_to_dict(paragraph: Any) -> dict[str, Any]:
    return {
        "paragraph_id": paragraph.paragraph_id,
        "cell_id": paragraph.cell_id,
        "paragraph_index": paragraph.paragraph_index,
        "text": paragraph.text,
        "para_pr_id_ref": paragraph.para_pr_id_ref,
        "style_id_ref": paragraph.style_id_ref,
        "raw_attrs": to_jsonable(paragraph.raw_attrs),

        "runs": [
            run_to_dict(run)
            for run in paragraph.runs
        ],
    }


def run_to_dict(run: Any) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "paragraph_id": run.paragraph_id,
        "run_index": run.run_index,
        "text": run.text,
        "char_pr_id_ref": run.char_pr_id_ref,
        "has_line_break": run.has_line_break,
        "has_tab": run.has_tab,
        "has_fw_space": run.has_fw_space,
        "raw_attrs": to_jsonable(run.raw_attrs),
    }


def build_tables_json_struct_markdown() -> str:
    return """# tables.json 구조

```text
tables: list[Table]
```

## Table

```text
table_id
section_index
table_index
xml_table_id
row_count
col_count
cell_spacing
border_fill_id_ref
border_fill
repeat_header
page_break
text_wrap
text_flow
width
height
pos_x
pos_y
treat_as_char
flow_with_text
in_margin_left
in_margin_right
in_margin_top
in_margin_bottom
out_margin_left
out_margin_right
out_margin_top
out_margin_bottom
caption_candidate
note_candidate
source_candidate
validation
semantic
raw_attrs
is_nested
parent_table_id
parent_cell_id
rows: list[TableRow]
```

## TableRow

```text
row_id
table_id
row_index
raw_attrs
cells: list[TableCell]
```

## TableCell

```text
cell_id
table_id
row_id
cell_index
name
header
has_margin
protect
editable
dirty
border_fill_id_ref
border_fill
row_addr
col_addr
row_span
col_span
end_row
end_col
width
height
margin_left
margin_right
margin_top
margin_bottom
sublist_raw_attrs
sublist_id
sublist_text_direction
sublist_line_wrap
sublist_vert_align
sublist_link_list_id_ref
sublist_link_list_next_id_ref
sublist_text_width
sublist_text_height
sublist_has_text_ref
sublist_has_num_ref
images: list[ImageInfo]
nested_tables: list[Table]
paragraphs: list[TableParagraph]
text
is_empty
has_image
has_field
has_shape
is_column_header
is_row_header
is_group_header
is_data_cell
raw_attrs
```

## ImageInfo

```text
image_id
parent_table_id
parent_cell_id
binary_item_id_ref
href
ref_id
width
height
raw_attrs
```

## TableParagraph

```text
paragraph_id
cell_id
paragraph_index
text
para_pr_id_ref
style_id_ref
raw_attrs
runs: list[TableRun]
```

## TableRun

```text
run_id
paragraph_id
run_index
text
char_pr_id_ref
has_line_break
has_tab
has_fw_space
raw_attrs
```
"""


def save_tables_json_struct(path: str | Path) -> None:
    Path(path).write_text(
        build_tables_json_struct_markdown(),
        encoding="utf-8",
    )
