#================================================
# add_table_preprocess_to_json.py
#================================================

from __future__ import annotations

from typing import Any


#================================================
# 공통 유틸
#================================================

def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def unique_keep_order(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()

    for value in values:
        if value is None:
            continue

        key = str(value)
        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


def is_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def get_rows(table: dict[str, Any]) -> list[dict[str, Any]]:
    return as_list(table.get("rows"))


def get_cells(table: dict[str, Any]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []

    for row in get_rows(table):
        cells.extend(as_list(row.get("cells")))

    return cells


def get_nested_tables_from_cell(cell: dict[str, Any]) -> list[dict[str, Any]]:
    return as_list(cell.get("nested_tables"))


def get_nested_tables_from_table(table: dict[str, Any]) -> list[dict[str, Any]]:
    nested_tables: list[dict[str, Any]] = []

    for cell in get_cells(table):
        nested_tables.extend(get_nested_tables_from_cell(cell))

    return nested_tables


#================================================
# preprocess 생성
#================================================

def build_table_preprocess(
    table: dict[str, Any],
    depth: int = 0,
) -> dict[str, Any]:
    cells = get_cells(table)

    return {
        "identity": build_identity(table),
        "nesting": build_nesting(table, cells, depth),
        "layout": build_layout(table),
        "candidates": build_candidates(table),
        "validation": build_validation(table.get("validation")),
        "structure": build_structure(table, cells),
        "text": build_text(cells),
        "style": build_style(cells),
        "style_features": build_style_features(cells),
        "objects": build_objects(cells),
        "cells": [
            build_cell_preprocess(cell)
            for cell in cells
        ],
    }


def build_identity(table: dict[str, Any]) -> dict[str, Any]:
    return {
        "table_id": table.get("table_id"),
        "section_index": table.get("section_index"),
        "table_index": table.get("table_index"),
        "xml_table_id": table.get("xml_table_id"),
    }


def build_nesting(
    table: dict[str, Any],
    cells: list[dict[str, Any]],
    depth: int,
) -> dict[str, Any]:
    child_table_ids: list[Any] = []

    for cell in cells:
        for nested_table in get_nested_tables_from_cell(cell):
            child_table_ids.append(nested_table.get("table_id"))

    child_table_ids = unique_keep_order(child_table_ids)

    return {
        "is_nested": table.get("is_nested", False),
        # 머리말/꼬리말/각주 안의 표인지. None이면 일반 표다.
        "owner_control_type": table.get("owner_control_type"),
        "parent_table_id": table.get("parent_table_id"),
        "parent_cell_id": table.get("parent_cell_id"),
        "depth": depth,
        "has_child_table": len(child_table_ids) > 0,
        "child_table_count": len(child_table_ids),
        "child_table_ids": child_table_ids,
    }


def build_layout(table: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_count": table.get("row_count"),
        "col_count": table.get("col_count"),
        "cell_spacing": table.get("cell_spacing"),

        "repeat_header": table.get("repeat_header"),
        "page_break": table.get("page_break"),
        "text_wrap": table.get("text_wrap"),
        "text_flow": table.get("text_flow"),

        "width": table.get("width"),
        "height": table.get("height"),
        "pos_x": table.get("pos_x"),
        "pos_y": table.get("pos_y"),
        "treat_as_char": table.get("treat_as_char"),
        "flow_with_text": table.get("flow_with_text"),

        "in_margin_left": table.get("in_margin_left"),
        "in_margin_right": table.get("in_margin_right"),
        "in_margin_top": table.get("in_margin_top"),
        "in_margin_bottom": table.get("in_margin_bottom"),

        "out_margin_left": table.get("out_margin_left"),
        "out_margin_right": table.get("out_margin_right"),
        "out_margin_top": table.get("out_margin_top"),
        "out_margin_bottom": table.get("out_margin_bottom"),
    }


def build_candidates(table: dict[str, Any]) -> dict[str, Any]:
    return {
        "caption_candidate": table.get("caption_candidate"),
        "note_candidate": table.get("note_candidate"),
        "source_candidate": table.get("source_candidate"),
    }


def build_validation(validation: Any) -> dict[str, Any]:
    if not isinstance(validation, dict):
        validation = {}

    issues = as_list(validation.get("issues"))

    return {
        "is_valid": validation.get("is_valid"),

        "declared_row_count": validation.get("declared_row_count"),
        "declared_col_count": validation.get("declared_col_count"),
        "actual_tr_count": validation.get("actual_tr_count"),
        "actual_cell_count": validation.get("actual_cell_count"),
        "actual_max_row_count": validation.get("actual_max_row_count"),
        "actual_max_col_count": validation.get("actual_max_col_count"),

        "issues": issues,
        "issue_count": len(issues),

        "has_row_count_mismatch": validation.get("has_row_count_mismatch"),
        "has_col_count_mismatch": validation.get("has_col_count_mismatch"),
        "has_missing_cell_addr": validation.get("has_missing_cell_addr"),
        "has_invalid_cell_addr": validation.get("has_invalid_cell_addr"),
        "has_out_of_range_cell": validation.get("has_out_of_range_cell"),
        "has_row_order_mismatch": validation.get("has_row_order_mismatch"),
        "has_invalid_cell_span": validation.get("has_invalid_cell_span"),
        "has_duplicated_slot": validation.get("has_duplicated_slot"),
        "has_empty_slot": validation.get("has_empty_slot"),
        "has_missing_style_ref": validation.get("has_missing_style_ref"),
        "has_missing_para_pr_ref": validation.get("has_missing_para_pr_ref"),
        "has_missing_char_pr_ref": validation.get("has_missing_char_pr_ref"),
        "has_size_mismatch": validation.get("has_size_mismatch"),
        "has_margin_difference": validation.get("has_margin_difference"),
        "has_empty_cell": validation.get("has_empty_cell"),
        "has_nested_object": validation.get("has_nested_object"),
        "is_irregular": validation.get("is_irregular"),
        "header_border_row_indices": validation.get("header_border_row_indices") or [],
    }


def build_structure(
    table: dict[str, Any],
    cells: list[dict[str, Any]],
) -> dict[str, Any]:
    col_count = table.get("col_count")

    empty_cell_count = 0
    non_empty_cell_count = 0

    row_span_cell_count = 0
    col_span_cell_count = 0
    merged_cell_count = 0

    max_row_span = 1
    max_col_span = 1

    full_width_cell_count = 0

    for cell in cells:
        if cell.get("is_empty"):
            empty_cell_count += 1
        else:
            non_empty_cell_count += 1

        row_span = cell.get("row_span") or 1
        col_span = cell.get("col_span") or 1

        max_row_span = max(max_row_span, row_span)
        max_col_span = max(max_col_span, col_span)

        if row_span > 1:
            row_span_cell_count += 1

        if col_span > 1:
            col_span_cell_count += 1

        if row_span > 1 or col_span > 1:
            merged_cell_count += 1

        if col_count is not None and col_span == col_count:
            full_width_cell_count += 1

    return {
        "row_object_count": len(get_rows(table)),
        "origin_cell_count": len(cells),

        "empty_cell_count": empty_cell_count,
        "non_empty_cell_count": non_empty_cell_count,

        "row_span_cell_count": row_span_cell_count,
        "col_span_cell_count": col_span_cell_count,
        "merged_cell_count": merged_cell_count,

        "has_row_span": row_span_cell_count > 0,
        "has_col_span": col_span_cell_count > 0,
        "has_merged_cell": merged_cell_count > 0,

        "max_row_span": max_row_span,
        "max_col_span": max_col_span,

        "full_width_cell_count": full_width_cell_count,
        "has_full_width_cell": full_width_cell_count > 0,
    }


def build_text(cells: list[dict[str, Any]]) -> dict[str, Any]:
    plain_text_parts: list[str] = []
    plain_text_without_nested_parts: list[str] = []

    paragraph_count = 0
    run_count = 0

    empty_text_cell_count = 0
    non_empty_text_cell_count = 0

    multiline_cell_count = 0
    cell_texts: list[dict[str, Any]] = []

    for cell in cells:
        cell_id = cell.get("cell_id")
        text = cell.get("text") or ""
        nested_tables = get_nested_tables_from_cell(cell)
        has_nested_table = len(nested_tables) > 0

        if is_non_empty_text(text):
            non_empty_text_cell_count += 1
            plain_text_parts.append(text)

            # 부모 셀의 paragraphs만 사용한다.
            # nested_tables 내부 텍스트는 하위 table item에서 별도 요약된다.
            paragraph_texts = [
                paragraph.get("text") or ""
                for paragraph in as_list(cell.get("paragraphs"))
                if is_non_empty_text(paragraph.get("text"))
            ]

            if paragraph_texts:
                plain_text_without_nested_parts.append("\n".join(paragraph_texts))
            elif not has_nested_table:
                plain_text_without_nested_parts.append(text)
        else:
            empty_text_cell_count += 1

        if "\n" in text:
            multiline_cell_count += 1

        paragraphs = as_list(cell.get("paragraphs"))
        paragraph_count += len(paragraphs)

        for paragraph in paragraphs:
            run_count += len(as_list(paragraph.get("runs")))

        cell_texts.append(
            {
                "cell_id": cell_id,
                "text": text,
                "has_nested_table": has_nested_table,
            }
        )

    return {
        "plain_text": "\n".join(
            part for part in plain_text_parts
            if is_non_empty_text(part)
        ),
        "plain_text_without_nested_tables": "\n".join(
            part for part in plain_text_without_nested_parts
            if is_non_empty_text(part)
        ),

        "paragraph_count": paragraph_count,
        "run_count": run_count,

        "empty_text_cell_count": empty_text_cell_count,
        "non_empty_text_cell_count": non_empty_text_cell_count,

        "multiline_cell_count": multiline_cell_count,
        "has_multiline_cell": multiline_cell_count > 0,

        "cell_texts": cell_texts,
    }


def build_style(
    cells: list[dict[str, Any]],
) -> dict[str, Any]:
    para_pr_id_refs: list[Any] = []
    style_id_refs: list[Any] = []
    char_pr_id_refs: list[Any] = []

    for cell in cells:
        for paragraph in as_list(cell.get("paragraphs")):
            para_pr_id_refs.append(paragraph.get("para_pr_id_ref"))
            style_id_refs.append(paragraph.get("style_id_ref"))

            for run in as_list(paragraph.get("runs")):
                char_pr_id_refs.append(run.get("char_pr_id_ref"))

    return {
        "para_pr_id_refs": unique_keep_order(para_pr_id_refs),
        "style_id_refs": unique_keep_order(style_id_refs),
        "char_pr_id_refs": unique_keep_order(char_pr_id_refs),
    }


def _collect_run_char_features(
    cells: list[dict[str, Any]],
) -> tuple[int, list[float]]:
    """cells 전체 run에서 bold cell 수와 font_size 목록을 수집한다."""
    bold_cell_count = 0
    font_sizes: list[float] = []

    for cell in cells:
        cell_has_bold = False

        for paragraph in as_list(cell.get("paragraphs")):
            for run in as_list(paragraph.get("runs")):
                if run.get("bold") is True:
                    cell_has_bold = True

                fs = run.get("font_size")
                if isinstance(fs, (int, float)) and fs > 0:
                    font_sizes.append(float(fs))

        if cell_has_bold:
            bold_cell_count += 1

    return bold_cell_count, font_sizes


def build_style_features(
    cells: list[dict[str, Any]],
) -> dict[str, Any]:
    has_center_alignment = any(
        cell.get("sublist_vert_align") == "CENTER" for cell in cells
    )

    bold_cell_count, font_sizes = _collect_run_char_features(cells)
    has_bold = bold_cell_count > 0 if cells else None
    max_font_size = round(max(font_sizes), 1) if font_sizes else None
    avg_font_size = round(sum(font_sizes) / len(font_sizes), 1) if font_sizes else None

    return {
        "has_bold": has_bold,
        "bold_cell_count": bold_cell_count,
        "max_font_size": max_font_size,
        "avg_font_size": avg_font_size,
        "has_center_alignment": has_center_alignment,
    }


def build_cell_style_features(cell: dict[str, Any]) -> dict[str, Any]:
    cell_has_bold = False
    font_sizes: list[float] = []
    for paragraph in as_list(cell.get("paragraphs")):
        for run in as_list(paragraph.get("runs")):
            if run.get("bold") is True:
                cell_has_bold = True
            fs = run.get("font_size")
            if isinstance(fs, (int, float)) and fs > 0:
                font_sizes.append(float(fs))

    return {
        "has_bold": cell_has_bold,
        "max_font_size": round(max(font_sizes), 1) if font_sizes else None,
        "has_center_alignment": cell.get("sublist_vert_align") == "CENTER",
    }


def build_objects(cells: list[dict[str, Any]]) -> dict[str, Any]:
    image_ids: list[Any] = []
    binary_item_id_refs: list[Any] = []

    has_field = False
    has_shape = False

    nested_table_ids: list[Any] = []

    for cell in cells:
        if cell.get("has_field"):
            has_field = True

        if cell.get("has_shape"):
            has_shape = True

        for image in as_list(cell.get("images")):
            image_ids.append(image.get("image_id"))
            binary_item_id_refs.append(image.get("binary_item_id_ref"))

        for nested_table in get_nested_tables_from_cell(cell):
            nested_table_ids.append(nested_table.get("table_id"))

    image_ids = unique_keep_order(image_ids)
    binary_item_id_refs = unique_keep_order(binary_item_id_refs)
    nested_table_ids = unique_keep_order(nested_table_ids)

    return {
        "has_image": len(image_ids) > 0,
        "image_count": len(image_ids),
        "image_ids": image_ids,
        "binary_item_id_refs": binary_item_id_refs,

        "has_field": has_field,
        "has_shape": has_shape,

        "has_nested_table": len(nested_table_ids) > 0,
        "nested_table_count": len(nested_table_ids),
        "nested_table_ids": nested_table_ids,
    }


def build_cell_preprocess(cell: dict[str, Any]) -> dict[str, Any]:
    paragraphs = as_list(cell.get("paragraphs"))

    runs: list[dict[str, Any]] = []
    for paragraph in paragraphs:
        runs.extend(as_list(paragraph.get("runs")))

    paragraph_texts = [
        paragraph.get("text") or ""
        for paragraph in paragraphs
    ]

    # 문단 앞에 자동 렌더링되지만 hp:t에는 없는 마커(불릿/번호 형식).
    # paragraph_texts와 인덱스가 1:1로 대응하도록 같은 순서로 만든다.
    paragraph_auto_labels = [
        paragraph.get("auto_label")
        for paragraph in paragraphs
    ]

    auto_label_bullet_ids = unique_keep_order([
        label.get("bullet_id")
        for label in paragraph_auto_labels
        if isinstance(label, dict) and label.get("bullet_id") is not None
    ])

    para_pr_id_refs = unique_keep_order([
        paragraph.get("para_pr_id_ref")
        for paragraph in paragraphs
    ])

    style_id_refs = unique_keep_order([
        paragraph.get("style_id_ref")
        for paragraph in paragraphs
    ])

    char_pr_id_refs = unique_keep_order([
        run.get("char_pr_id_ref")
        for run in runs
    ])

    image_ids = [
        image.get("image_id")
        for image in as_list(cell.get("images"))
        if image.get("image_id") is not None
    ]

    nested_table_ids = [
        nested_table.get("table_id")
        for nested_table in get_nested_tables_from_cell(cell)
        if nested_table.get("table_id") is not None
    ]

    return {
        "cell_id": cell.get("cell_id"),
        "table_id": cell.get("table_id"),
        "row_id": cell.get("row_id"),
        "cell_index": cell.get("cell_index"),
        "name": cell.get("name"),

        "position": {
            "row_addr": cell.get("row_addr"),
            "col_addr": cell.get("col_addr"),
            "row_span": cell.get("row_span"),
            "col_span": cell.get("col_span"),
            "end_row": cell.get("end_row"),
            "end_col": cell.get("end_col"),
        },

        "size": {
            "width": cell.get("width"),
            "height": cell.get("height"),
            "margin_left": cell.get("margin_left"),
            "margin_right": cell.get("margin_right"),
            "margin_top": cell.get("margin_top"),
            "margin_bottom": cell.get("margin_bottom"),
        },

        "flags": {
            "header": cell.get("header"),
            "has_margin": cell.get("has_margin"),
            "protect": cell.get("protect"),
            "editable": cell.get("editable"),
            "dirty": cell.get("dirty"),

            "is_empty": cell.get("is_empty"),
            "has_image": cell.get("has_image"),
            "has_field": cell.get("has_field"),
            "has_shape": cell.get("has_shape"),

            "is_column_header": cell.get("is_column_header"),
            "is_row_header": cell.get("is_row_header"),
            "is_group_header": cell.get("is_group_header"),
            "is_data_cell": cell.get("is_data_cell"),
        },

        "text": {
            "text": cell.get("text"),
            "paragraph_count": len(paragraphs),
            "run_count": len(runs),
            "paragraph_texts": paragraph_texts,
            "paragraph_auto_labels": paragraph_auto_labels,
            "has_auto_label": any(
                isinstance(label, dict) for label in paragraph_auto_labels
            ),
            "has_line_break": any(bool(run.get("has_line_break")) for run in runs),
            "has_tab": any(bool(run.get("has_tab")) for run in runs),
            "has_fw_space": any(bool(run.get("has_fw_space")) for run in runs),
        },

        "style_refs": {
            "para_pr_id_refs": para_pr_id_refs,
            "style_id_refs": style_id_refs,
            "char_pr_id_refs": char_pr_id_refs,
            "auto_label_bullet_ids": auto_label_bullet_ids,
        },

        "sublist": {
            "sublist_id": cell.get("sublist_id"),
            "text_direction": cell.get("sublist_text_direction"),
            "line_wrap": cell.get("sublist_line_wrap"),
            "vert_align": cell.get("sublist_vert_align"),
            "link_list_id_ref": cell.get("sublist_link_list_id_ref"),
            "link_list_next_id_ref": cell.get("sublist_link_list_next_id_ref"),
            "text_width": cell.get("sublist_text_width"),
            "text_height": cell.get("sublist_text_height"),
            "has_text_ref": cell.get("sublist_has_text_ref"),
            "has_num_ref": cell.get("sublist_has_num_ref"),
        },

        "objects": {
            "image_ids": image_ids,
            "images": [
                {
                    "image_id": image.get("image_id"),
                    "binary_item_id_ref": image.get("binary_item_id_ref"),
                }
                for image in as_list(cell.get("images"))
                if image.get("image_id") is not None
            ],
            "draw_objects": as_list(cell.get("draw_objects")),
            # 개체 설명문. 셀 본문 텍스트와 분리해 보존한다.
            "captions": as_list(cell.get("captions")),
            # 머리말/꼬리말/각주/미주. 마찬가지로 셀 본문과 분리해 보존한다.
            "controls": as_list(cell.get("controls")),
            "nested_table_ids": nested_table_ids,
        },

        "style_features": build_cell_style_features(cell),
    }


#================================================
# 요약 JSON item 생성
#================================================

def build_preprocess_table_item(
    table: dict[str, Any],
    depth: int = 0,
) -> dict[str, Any]:
    children = [
        build_preprocess_table_item(
            table=nested_table,
            depth=depth + 1,
        )
        for nested_table in get_nested_tables_from_table(table)
    ]

    return {
        "table_id": table.get("table_id"),
        "is_nested": table.get("is_nested", False),
        # 머리말/꼬리말/각주 안의 표인지. None이면 일반 표다.
        "owner_control_type": table.get("owner_control_type"),
        "parent_table_id": table.get("parent_table_id"),
        "parent_cell_id": table.get("parent_cell_id"),
        "preprocess": build_table_preprocess(
            table=table,
            depth=depth,
        ),
        "children": children,
    }


def build_preprocess_tables_json(
    tables_json: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        build_preprocess_table_item(
            table=table,
            depth=0,
        )
        for table in tables_json
    ]


#================================================
# 진입점 (인메모리)
#================================================

def preprocess_tables(
    tables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    역할: 파서 직렬화 표 리스트에서 preprocess 요약 표 리스트를 생성한다.
    입력 데이터: tables(직렬화된 표 dict 리스트). 원본은 수정하지 않는다.
    출력 데이터: preprocess/children 구조의 새 표 dict 리스트.
    """
    if not isinstance(tables, list):
        raise ValueError("tables 최상위 구조는 list[dict] 이어야 합니다.")

    return build_preprocess_tables_json(tables)
