from __future__ import annotations

from typing import Any

from . import common


TABLE_TYPE_TITLE_BOX = "title_box"
TABLE_TYPE_CAPTION_OR_NOTE = "caption_or_note_table"
TABLE_TYPE_DATA_TABLE = "data_table"
TABLE_TYPE_KEY_VALUE_TABLE = "key_value_table"
SUPPORTED_TABLE_TYPES = {
    TABLE_TYPE_TITLE_BOX,
    TABLE_TYPE_CAPTION_OR_NOTE,
    TABLE_TYPE_DATA_TABLE,
    TABLE_TYPE_KEY_VALUE_TABLE,
}


def _clean_text(text: Any) -> str:
    return str(text).replace("\r", " ").replace("\n", " ").strip()


def _format_bool(value: bool) -> str:
    return str(value).lower()


def _truncate_text(text: str, max_length: int = 200) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length]


def build_common_structure(table: dict[str, Any]) -> dict[str, Any]:
    layout = common.get_layout(table)
    cells = common.get_cells(table)

    non_empty_cell_count = 0
    has_merged_cell = False

    for cell in cells:
        if common.get_cell_text(cell):
            non_empty_cell_count += 1

        position = common.get_cell_position(cell)
        if position["row_span"] > 1 or position["col_span"] > 1:
            has_merged_cell = True

    return {
        "row_count": layout["row_count"],
        "col_count": layout["col_count"],
        "header_row_indices": common.get_header_rows(table),
        "header_col_indices": common.get_header_cols(table),
        "body_cell_count": len(common.get_body_cells(table)),
        "cell_count": len(cells),
        "non_empty_cell_count": non_empty_cell_count,
        "has_merged_cell": has_merged_cell,
        "child_table_count": len(common.get_child_tables(table)),
        "nested_ref_count": len(common.get_nested_table_refs(table)),
    }


def get_plain_text(table: dict[str, Any]) -> str:
    plain_text = common.get_nested(
        table,
        "preprocess",
        "text",
        "plain_text_without_nested_tables",
    )
    if not plain_text:
        plain_text = " ".join(get_non_empty_cell_texts(table))

    return _clean_text(plain_text)


def get_non_empty_cell_texts(table: dict[str, Any]) -> list[str]:
    texts: list[str] = []

    for cell in common.get_cells(table):
        text = _clean_text(common.get_cell_text(cell))
        if text:
            texts.append(text)

    return texts


def _build_source(table: dict[str, Any]) -> dict[str, Any]:
    return {
        "is_nested": bool(table.get("is_nested", False)),
        "parent_table_id": table.get("parent_table_id"),
        "parent_cell_id": table.get("parent_cell_id"),
    }


def _build_quality() -> dict[str, Any]:
    return {
        "requires_review": False,
        "warnings": [],
    }


def build_title_box_object(table: dict[str, Any]) -> dict[str, Any]:
    table_type = common.get_table_type(table)
    if table_type != TABLE_TYPE_TITLE_BOX:
        raise ValueError(f"Expected title_box table, got {table_type}.")

    title_parts = get_non_empty_cell_texts(table)
    title_text = _clean_text(" ".join(title_parts))

    quality = _build_quality()
    if not title_text:
        quality["requires_review"] = True
        quality["warnings"].append("empty title_box text")

    return {
        "table_id": common.get_table_id(table),
        "table_type": TABLE_TYPE_TITLE_BOX,
        "source": _build_source(table),
        "structure": build_common_structure(table),
        "hierarchy": {
            "title_text": title_text,
            "title_parts": title_parts,
        },
        "records": [],
        "children": [],
        "quality": quality,
    }


def build_caption_or_note_object(table: dict[str, Any]) -> dict[str, Any]:
    table_type = common.get_table_type(table)
    if table_type != TABLE_TYPE_CAPTION_OR_NOTE:
        raise ValueError(f"Expected caption_or_note_table table, got {table_type}.")

    caption_text = None
    note_texts: list[str] = []
    source_texts: list[str] = []
    description_texts: list[str] = []

    for text in get_non_empty_cell_texts(table):
        is_caption = any(
            marker in text
            for marker in ("<표", "[표", "표 ", "Table")
        )
        is_note = any(marker in text for marker in ("주:", "※", "단위:"))
        is_source = any(marker in text for marker in ("자료:", "출처:"))

        if caption_text is None and is_caption:
            caption_text = text
        elif not is_note and not is_source:
            description_texts.append(text)

        if is_note:
            note_texts.append(text)

        if is_source:
            source_texts.append(text)

    quality = _build_quality()
    if (
        caption_text is None
        and not note_texts
        and not source_texts
        and not description_texts
    ):
        quality["requires_review"] = True
        quality["warnings"].append("empty caption_or_note_table text")

    return {
        "table_id": common.get_table_id(table),
        "table_type": TABLE_TYPE_CAPTION_OR_NOTE,
        "source": _build_source(table),
        "structure": build_common_structure(table),
        "hierarchy": {
            "caption_text": caption_text,
            "note_texts": note_texts,
            "source_texts": source_texts,
            "description_texts": description_texts,
        },
        "records": [],
        "children": [],
        "quality": quality,
    }


def build_stub_table_object(table: dict[str, Any]) -> dict[str, Any]:
    table_type = common.get_table_type(table)
    if table_type not in {TABLE_TYPE_DATA_TABLE, TABLE_TYPE_KEY_VALUE_TABLE}:
        raise ValueError(f"Expected data_table or key_value_table, got {table_type}.")

    return {
        "table_id": common.get_table_id(table),
        "table_type": table_type,
        "source": _build_source(table),
        "structure": build_common_structure(table),
        "hierarchy": {
            "preview_text": _truncate_text(get_plain_text(table)),
        },
        "records": [],
        "children": [],
        "quality": {
            "requires_review": False,
            "warnings": ["stub object: records builder not implemented"],
        },
    }


def build_table_object(table: dict[str, Any]) -> dict[str, Any]:
    table_type = common.get_table_type(table)

    if table_type == TABLE_TYPE_TITLE_BOX:
        obj = build_title_box_object(table)
    elif table_type == TABLE_TYPE_CAPTION_OR_NOTE:
        obj = build_caption_or_note_object(table)
    elif table_type in {TABLE_TYPE_DATA_TABLE, TABLE_TYPE_KEY_VALUE_TABLE}:
        obj = build_stub_table_object(table)
    else:
        raise ValueError(f"Unsupported table_type: {table_type}.")

    for child_table in common.get_child_tables(table):
        obj["children"].append(build_table_object(child_table))

    return obj


def _iter_objects(obj: dict[str, Any]):
    yield obj

    for child_obj in obj.get("children", []):
        yield from _iter_objects(child_obj)


def _empty_type_counts() -> dict[str, int]:
    return {table_type: 0 for table_type in SUPPORTED_TABLE_TYPES}


def _count_types(objects: list[dict[str, Any]]) -> dict[str, int]:
    counts = _empty_type_counts()

    for obj in objects:
        table_type = obj["table_type"]
        counts[table_type] = counts.get(table_type, 0) + 1

    return counts


def print_simple_object(obj: dict[str, Any], indent: int = 0) -> None:
    prefix = " " * indent
    source = obj["source"]
    structure = obj["structure"]
    hierarchy = obj["hierarchy"]
    quality = obj["quality"]
    children = obj["children"]

    print(f"{prefix}[simple] {obj['table_id']}")
    print(f"{prefix}  type: {obj['table_type']}")
    print(
        f"{prefix}  nested: "
        f"{_format_bool(source['is_nested'])} "
        f"parent_table={source['parent_table_id']} "
        f"parent_cell={source['parent_cell_id']}"
    )
    print(
        f"{prefix}  structure: "
        f"{structure['row_count']} x {structure['col_count']} "
        f"cells={structure['cell_count']} "
        f"non_empty={structure['non_empty_cell_count']} "
        f"merged={_format_bool(structure['has_merged_cell'])} "
        f"children={len(children)}"
    )

    if obj["table_type"] == TABLE_TYPE_TITLE_BOX:
        print(f"{prefix}  title_text: {hierarchy['title_text']}")
    elif obj["table_type"] == TABLE_TYPE_CAPTION_OR_NOTE:
        print(f"{prefix}  caption_text: {hierarchy['caption_text']}")
        print(f"{prefix}  note_texts: {hierarchy['note_texts']}")
        print(f"{prefix}  source_texts: {hierarchy['source_texts']}")
        print(f"{prefix}  description_texts: {hierarchy['description_texts']}")
    else:
        print(f"{prefix}  preview_text: {hierarchy['preview_text']}")

    print(f"{prefix}  records: {len(obj['records'])}")
    print(f"{prefix}  children: {len(children)}")
    print(f"{prefix}  warnings: {quality['warnings']}")

    for child_obj in children:
        print_simple_object(child_obj, indent=indent + 2)


def debug_simple_tables(
    input_path: str = "tables_hierarchical.json",
    limit: int | None = 20,
    include_nested: bool = True,
) -> None:
    _ = include_nested
    tables = common.load_tables(input_path)
    top_level_objects: list[dict[str, Any]] = []

    for table in tables:
        obj = build_table_object(table)
        top_level_objects.append(obj)

    recursive_objects = [
        nested_obj
        for top_level_obj in top_level_objects
        for nested_obj in _iter_objects(top_level_obj)
    ]
    top_level_counts = _count_types(top_level_objects)
    recursive_counts = _count_types(recursive_objects)
    review_count = sum(
        1
        for obj in recursive_objects
        if obj["quality"]["requires_review"]
    )

    printed_count = 0
    for obj in top_level_objects:
        if limit is not None and printed_count >= limit:
            break

        print_simple_object(obj)
        printed_count += 1

    print("[simple summary]")
    print(f"  total objects found: {len(recursive_objects)}")
    print(f"  printed top-level objects: {printed_count}")
    print("  top-level type counts:")
    for table_type in sorted(SUPPORTED_TABLE_TYPES):
        print(f"    {table_type}: {top_level_counts.get(table_type, 0)}")
    print("  recursive type counts:")
    for table_type in sorted(SUPPORTED_TABLE_TYPES):
        print(f"    {table_type}: {recursive_counts.get(table_type, 0)}")
    print(f"  objects requiring review count: {review_count}")
