#================================================
# test.py
#================================================

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
import io
import json
import sys

from hwpx_analysis.table_json_serializer import (
    save_tables_json_struct,
    table_to_dict as serialize_table_to_dict,
)
from hwpx_analysis.add_table_grid_to_json import add_table_grid_to_json
from hwpx_analysis.add_table_hierarchy_to_json import add_table_hierarchy_to_json
from hwpx_analysis.add_table_preprocess_to_json import convert_tables_json_with_preprocess
from hwpx_analysis.table_hierarchy import debug_simple_tables, debug_table_hierarchy_input
from hwpx_analysis.table_hierarchy.debug_title_texts import debug_title_texts
from hwpx_parser.parser import HwpxParser



#------------------------------------------------
# dataclass / 일반 객체를 JSON으로 바꾸기 위한 함수
#------------------------------------------------

def to_jsonable(value: Any) -> Any:
    """
    역할: 파싱 결과 객체를 json.dump가 처리할 수 있는 자료형으로 재귀 변환한다.
    입력 데이터: value(기본형, Path, list, tuple, dict, dataclass/일반 객체 등 임의 값).
    출력 데이터: None/str/int/float/bool/list/dict 또는 문자열로 변환된 JSON 직렬화 가능 값을 반환한다.
    """
    """
    Table, TableRow, TableCell, TableValidation 같은 객체를
    json.dump 가능한 dict/list/str/int/bool 형태로 변환한다.
    """

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

    if hasattr(value, "__dict__"):
        return {
            key: to_jsonable(val)
            for key, val in vars(value).items()
            if not key.startswith("_")
        }

    return str(value)


#------------------------------------------------
# borderFill raw 조회
#------------------------------------------------

def get_border_fill_raw(
    parser: HwpxParser,
    border_fill_id_ref: Optional[str],
) -> Optional[dict[str, Any]]:
    """
    역할: parser.header를 통해 borderFillIDRef에 해당하는 header.xml 원본 borderFill 데이터를 조회한다.
    입력 데이터: parser(HwpxParser), border_fill_id_ref(borderFillIDRef 문자열 또는 None).
    출력 데이터: borderFill 원본 dict를 반환하고, parser/header/ID가 없거나 매칭 실패 시 None을 반환한다.
    """
    """
    Table / TableCell에는 BorderFill 객체를 직접 넣지 않는다.

    대신 border_fill_id_ref를 기준으로
    parser.header.border_fills에서 실제 header.xml의 borderFill raw를 조회한다.
    """

    if border_fill_id_ref is None:
        return None

    if parser.header is None:
        return None

    return parser.header.get_border_fill_raw(str(border_fill_id_ref))


def get_border_fill_ref_exists(
    parser: HwpxParser,
    border_fill_id_ref: Optional[str],
) -> bool:
    """
    역할: borderFillIDRef가 실제 header.xml의 borderFill로 해석되는지 확인한다.
    입력 데이터: parser(HwpxParser), border_fill_id_ref(borderFillIDRef 문자열 또는 None).
    출력 데이터: 참조가 존재하면 True, 없으면 False를 반환한다.
    """
    """
    borderFillIDRef가 header.xml의 borderFill 목록에 실제 존재하는지 확인한다.
    """

    if border_fill_id_ref is None:
        return False

    return get_border_fill_raw(parser, border_fill_id_ref) is not None


#------------------------------------------------
# 표 하나를 사람이 보기 쉬운 dict로 변환
#------------------------------------------------

from dataclasses import asdict, is_dataclass
from typing import Any


def table_to_dict(table: Any) -> dict[str, Any]:
    """
    Table 객체를 JSON 저장 가능한 dict로 변환한다.

    전제:
    - BorderFillResolver.resolve(table, context)가 먼저 실행되어 있어야
      table.border_fill, cell.border_fill 값이 None이 아니라 실제 값으로 출력된다.

    출력:
    - border_fill_id_ref: XML 원본 참조값
    - border_fill: header.xml에서 resolve된 실제 BorderFill 정보
    """

    def to_jsonable(value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

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
            }

        return str(value)

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
            {
                "row_id": row.row_id,
                "table_id": row.table_id,
                "row_index": row.row_index,
                "raw_attrs": to_jsonable(getattr(row, "raw_attrs", {})),

                "cells": [
                    {
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
                            {
                                "paragraph_id": paragraph.paragraph_id,
                                "cell_id": paragraph.cell_id,
                                "paragraph_index": paragraph.paragraph_index,
                                "text": paragraph.text,
                                "para_pr_id_ref": paragraph.para_pr_id_ref,
                                "style_id_ref": paragraph.style_id_ref,
                                "raw_attrs": to_jsonable(paragraph.raw_attrs),

                                "runs": [
                                    {
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
                                    for run in paragraph.runs
                                ],
                            }
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
                    for cell in row.cells
                ],
            }
            for row in table.rows
        ],
    }

#------------------------------------------------
# 행 변환
#------------------------------------------------

def row_to_dict(
    row,
    parser: HwpxParser,
) -> dict[str, Any]:
    """
    역할: 하나의 TableRow 객체를 JSON/리포트 출력용 dict로 변환한다.
    입력 데이터: row(TableRow), parser(하위 셀 변환 시 header 참조 조회에 사용).
    출력 데이터: 행 ID/순서/원본 속성과 변환된 cells 리스트를 담은 dict를 반환한다.
    """
    return {
        "row_id": row.row_id,
        "table_id": row.table_id,
        "row_index": row.row_index,
        "xml_order_index": row.xml_order_index,
        "declared_row_addr": row.declared_row_addr,
        "raw_attrs": row.raw_attrs,
        "cells": [
            cell_to_dict(
                cell=cell,
                parser=parser,
            )
            for cell in row.cells
        ],
    }


#------------------------------------------------
# 셀 변환
#------------------------------------------------

def cell_to_dict(
    cell,
    parser: HwpxParser,
) -> dict[str, Any]:
    """
    역할: 하나의 TableCell 객체를 JSON/리포트 출력용 dict로 변환한다.
    입력 데이터: cell(TableCell), parser(borderFill 원본 조회가 가능한 HwpxParser).
    출력 데이터: 셀 좌표/병합/크기/여백/내용/역할/원본 속성/문단 목록을 담은 dict를 반환한다.
    """
    cell_border_fill_raw = get_border_fill_raw(
        parser=parser,
        border_fill_id_ref=cell.border_fill_id_ref,
    )

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

        # hp:tc@borderFillIDRef 원본 참조값
        "border_fill_id_ref": cell.border_fill_id_ref,

        # header.xml의 hh:borderFill에 실제 존재하는지
        "border_fill_ref_exists": cell_border_fill_raw is not None,

        # header.xml에서 조회한 실제 borderFill raw
        # Cell 객체 안에 직접 담는 것이 아니라, test 출력에서만 조회해서 보여준다.
        "border_fill_raw": cell_border_fill_raw,

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

        "sublist_raw_attrs": cell.sublist_raw_attrs,
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

        "text": cell.text,
        "is_empty": cell.is_empty,
        "has_image": cell.has_image,
        "has_field": cell.has_field,
        "has_shape": cell.has_shape,

        "is_column_header": cell.is_column_header,
        "is_row_header": cell.is_row_header,
        "is_group_header": cell.is_group_header,
        "is_data_cell": cell.is_data_cell,

        "raw_attrs": cell.raw_attrs,

        "paragraphs": [
            paragraph_to_dict(paragraph)
            for paragraph in cell.paragraphs
        ],
    }


#------------------------------------------------
# 문단 변환
#------------------------------------------------

def paragraph_to_dict(paragraph) -> dict[str, Any]:
    """
    역할: 하나의 TableParagraph 객체를 JSON/리포트 출력용 dict로 변환한다.
    입력 데이터: paragraph(TableParagraph).
    출력 데이터: 문단 ID, style/paraPr 참조, 텍스트, 원본 속성, run 목록을 담은 dict를 반환한다.
    """
    return {
        "paragraph_id": paragraph.paragraph_id,
        "cell_id": paragraph.cell_id,
        "xml_para_id": paragraph.xml_para_id,
        "paragraph_index": paragraph.paragraph_index,
        "style_id_ref": paragraph.style_id_ref,
        "para_pr_id_ref": paragraph.para_pr_id_ref,
        "text": paragraph.text,
        "raw_attrs": paragraph.raw_attrs,
        "runs": [
            run_to_dict(run)
            for run in paragraph.runs
        ],
    }


#------------------------------------------------
# run 변환
#------------------------------------------------

def run_to_dict(run) -> dict[str, Any]:
    """
    역할: 하나의 TableRun 객체를 JSON/리포트 출력용 dict로 변환한다.
    입력 데이터: run(TableRun).
    출력 데이터: run ID, charPr 참조, 텍스트, 줄바꿈/탭/이미지/필드/도형 플래그, 원본 속성을 담은 dict를 반환한다.
    """
    return {
        "run_id": run.run_id,
        "paragraph_id": run.paragraph_id,
        "run_index": run.run_index,
        "char_pr_id_ref": run.char_pr_id_ref,
        "text": run.text,

        "has_line_break": run.has_line_break,
        "has_tab": run.has_tab,
        "has_fw_space": run.has_fw_space,

        "has_image": run.has_image,
        "has_field": run.has_field,
        "has_shape": run.has_shape,

        "raw_attrs": run.raw_attrs,
    }


#------------------------------------------------
# 요약 정보 생성
#------------------------------------------------

def build_summary(parser: HwpxParser, tables: list[Any]) -> dict[str, Any]:
    """
    역할: 전체 파싱 결과와 표 검증 결과를 요약 통계 dict로 집계한다.
    입력 데이터: parser(HwpxParser), tables(파싱/검증된 Table 리스트).
    출력 데이터: 파일 경로, 표 개수, 오류/경고 개수, header 참조 검증 요약, borderFill 참조 요약을 담은 dict를 반환한다.
    """
    invalid_tables = []

    total_issue_count = 0
    error_count = 0
    warning_count = 0

    missing_border_fill_ref_count = 0
    missing_style_ref_count = 0
    missing_para_pr_ref_count = 0
    missing_char_pr_ref_count = 0

    tables_with_missing_border_fill_ref = []
    tables_with_missing_style_ref = []
    tables_with_missing_para_pr_ref = []
    tables_with_missing_char_pr_ref = []

    used_table_border_fill_ids = set()
    used_cell_border_fill_ids = set()

    for table in tables:
        validation = table.validation

        if table.border_fill_id_ref is not None:
            used_table_border_fill_ids.add(str(table.border_fill_id_ref))

        for cell in table.cells:
            if cell.border_fill_id_ref is not None:
                used_cell_border_fill_ids.add(str(cell.border_fill_id_ref))

        if validation is None:
            continue

        if not validation.is_valid:
            invalid_tables.append(table.table_id)

        total_issue_count += len(validation.issues)

        for issue in validation.issues:
            if issue.get("severity") == "ERROR":
                error_count += 1
            elif issue.get("severity") == "WARNING":
                warning_count += 1

        if validation.has_missing_border_fill_ref:
            missing_border_fill_ref_count += 1
            tables_with_missing_border_fill_ref.append(table.table_id)

        if validation.has_missing_style_ref:
            missing_style_ref_count += 1
            tables_with_missing_style_ref.append(table.table_id)

        if validation.has_missing_para_pr_ref:
            missing_para_pr_ref_count += 1
            tables_with_missing_para_pr_ref.append(table.table_id)

        if validation.has_missing_char_pr_ref:
            missing_char_pr_ref_count += 1
            tables_with_missing_char_pr_ref.append(table.table_id)

    header = parser.header

    header_border_fill_ids = set(header.border_fills.keys()) if header else set()

    unresolved_table_border_fill_ids = sorted(
        used_table_border_fill_ids - header_border_fill_ids
    )
    unresolved_cell_border_fill_ids = sorted(
        used_cell_border_fill_ids - header_border_fill_ids
    )

    return {
        "source": str(parser.source_path),
        "filename": parser.filename,

        "unpacked_dir_path": str(parser.unpacked_dir_path),
        "contents_dir_path": str(parser.contents_dir_path),
        "header_file_path": str(parser.header_file_path),
        "image_dir_path": str(parser.image_dir_path),

        "section_count": len(parser.section_file_paths),
        "table_count": len(tables),

        "invalid_table_count": len(invalid_tables),
        "invalid_table_ids": invalid_tables,

        "total_issue_count": total_issue_count,
        "error_count": error_count,
        "warning_count": warning_count,

        # header 참조 검증 요약
        "header_reference_validation": {
            "missing_border_fill_ref_table_count": missing_border_fill_ref_count,
            "missing_style_ref_table_count": missing_style_ref_count,
            "missing_para_pr_ref_table_count": missing_para_pr_ref_count,
            "missing_char_pr_ref_table_count": missing_char_pr_ref_count,

            "tables_with_missing_border_fill_ref": tables_with_missing_border_fill_ref,
            "tables_with_missing_style_ref": tables_with_missing_style_ref,
            "tables_with_missing_para_pr_ref": tables_with_missing_para_pr_ref,
            "tables_with_missing_char_pr_ref": tables_with_missing_char_pr_ref,
        },

        # borderFill 사용/조회 요약
        "border_fill_reference_summary": {
            "used_table_border_fill_ids": sorted(used_table_border_fill_ids),
            "used_cell_border_fill_ids": sorted(used_cell_border_fill_ids),
            "unresolved_table_border_fill_ids": unresolved_table_border_fill_ids,
            "unresolved_cell_border_fill_ids": unresolved_cell_border_fill_ids,
        },

        "header": {
            "border_fill_count": len(header.border_fills) if header else 0,
            "para_property_count": len(header.para_properties) if header else 0,
            "char_property_count": len(header.char_properties) if header else 0,
            "style_count": len(header.styles) if header else 0,
            "style_name_count": len(header.style_names) if header else 0,
            "style_to_para_pr_count": len(header.style_to_para_pr) if header else 0,
            "style_to_char_pr_count": len(header.style_to_char_pr) if header else 0,
            "heading_level_count": len(header.para_pr_to_heading_level) if header else 0,
        },
    }


#------------------------------------------------
# 사람이 읽기 쉬운 txt 리포트 생성
#------------------------------------------------

def build_text_report(
    parser: HwpxParser,
    tables: list[Any],
    summary: dict[str, Any],
) -> str:
    """
    역할: 파싱 결과와 요약 정보를 사람이 읽기 쉬운 텍스트 리포트로 구성한다.
    입력 데이터: parser(HwpxParser), tables(Table 리스트), summary(build_summary가 만든 요약 dict).
    출력 데이터: 줄바꿈으로 연결된 전체 리포트 문자열을 반환한다.
    """
    lines: list[str] = []

    lines.append("===========================================")
    lines.append("[HWPX TABLE PARSE RESULT]")
    lines.append("===========================================")
    lines.append(f"source          : {summary['source']}")
    lines.append(f"filename        : {summary['filename']}")
    lines.append(f"unpacked        : {summary['unpacked_dir_path']}")
    lines.append(f"contents        : {summary['contents_dir_path']}")
    lines.append(f"header          : {summary['header_file_path']}")
    lines.append(f"image_dir       : {summary['image_dir_path']}")
    lines.append(f"section_count   : {summary['section_count']}")
    lines.append(f"table_count     : {summary['table_count']}")
    lines.append("")

    lines.append("===========================================")
    lines.append("[HEADER CHECK]")
    lines.append("===========================================")
    lines.append(f"border_fills     : {summary['header']['border_fill_count']}")
    lines.append(f"para_properties  : {summary['header']['para_property_count']}")
    lines.append(f"char_properties  : {summary['header']['char_property_count']}")
    lines.append(f"styles           : {summary['header']['style_count']}")
    lines.append(f"style_names      : {summary['header']['style_name_count']}")
    lines.append(f"style_to_para_pr : {summary['header']['style_to_para_pr_count']}")
    lines.append(f"style_to_char_pr : {summary['header']['style_to_char_pr_count']}")
    lines.append("")

    lines.append("===========================================")
    lines.append("[SUMMARY]")
    lines.append("===========================================")
    lines.append(f"table_count         : {summary['table_count']}")
    lines.append(f"invalid_table_count : {summary['invalid_table_count']}")
    lines.append(f"total_issue_count   : {summary['total_issue_count']}")
    lines.append(f"error_count         : {summary['error_count']}")
    lines.append(f"warning_count       : {summary['warning_count']}")
    lines.append("")

    lines.append("===========================================")
    lines.append("[BORDER FILL REFERENCE SUMMARY]")
    lines.append("===========================================")

    border_summary = summary["border_fill_reference_summary"]

    lines.append(
        f"used_table_border_fill_ids      : "
        f"{border_summary['used_table_border_fill_ids']}"
    )
    lines.append(
        f"used_cell_border_fill_ids       : "
        f"{border_summary['used_cell_border_fill_ids']}"
    )
    lines.append(
        f"unresolved_table_border_fill_ids: "
        f"{border_summary['unresolved_table_border_fill_ids']}"
    )
    lines.append(
        f"unresolved_cell_border_fill_ids : "
        f"{border_summary['unresolved_cell_border_fill_ids']}"
    )
    lines.append("")

    lines.append("===========================================")
    lines.append("[HEADER REFERENCE VALIDATION]")
    lines.append("===========================================")

    header_ref = summary["header_reference_validation"]

    lines.append(
        f"missing_border_fill_ref_table_count : "
        f"{header_ref['missing_border_fill_ref_table_count']}"
    )
    lines.append(
        f"missing_style_ref_table_count       : "
        f"{header_ref['missing_style_ref_table_count']}"
    )
    lines.append(
        f"missing_para_pr_ref_table_count     : "
        f"{header_ref['missing_para_pr_ref_table_count']}"
    )
    lines.append(
        f"missing_char_pr_ref_table_count     : "
        f"{header_ref['missing_char_pr_ref_table_count']}"
    )
    lines.append("")

    for table in tables:
        validation = table.validation

        table_border_fill_raw = getattr(table, "border_fill", None)

        lines.append("===================================")
        lines.append(f"table_id       : {table.table_id}")
        lines.append(f"section_index  : {table.section_index}")
        lines.append(f"table_index    : {table.table_index}")
        lines.append(f"declared       : {table.row_count} x {table.col_count}")
        lines.append(f"actual rows    : {len(table.rows)}")
        lines.append(f"actual cells   : {len(table.cells)}")
        lines.append(f"borderFillIDRef: {table.border_fill_id_ref}")
        lines.append(f"borderFillFound: {table_border_fill_raw is not None}")

        if table_border_fill_raw is not None:
            lines.append(f"borderFill     : {table_border_fill_raw}")

            if hasattr(table_border_fill_raw, "__dict__"):
                lines.append(f"borderFillAttrs: {table_border_fill_raw.__dict__}")

        if validation is None:
            lines.append("validation     : None")
            lines.append("")
            continue

        lines.append(f"is_valid       : {validation.is_valid}")
        lines.append(
            f"actual max size: "
            f"{validation.actual_max_row_count} x {validation.actual_max_col_count}"
        )

        lines.append(f"row mismatch   : {validation.has_row_count_mismatch}")
        lines.append(f"col mismatch   : {validation.has_col_count_mismatch}")
        lines.append(f"empty slot     : {validation.has_empty_slot}")
        lines.append(f"duplicated slot: {validation.has_duplicated_slot}")
        lines.append(f"missing style  : {validation.has_missing_style_ref}")
        lines.append(f"missing border : {validation.has_missing_border_fill_ref}")
        lines.append(f"missing paraPr : {validation.has_missing_para_pr_ref}")
        lines.append(f"missing charPr : {validation.has_missing_char_pr_ref}")

        if validation.issues:
            lines.append("issues:")
            for issue in validation.issues:
                lines.append(
                    f"  [{issue.get('severity')}] "
                    f"{issue.get('code')} - "
                    f"{issue.get('message')} "
                    f"/ row={issue.get('row_index')} "
                    f"/ col={issue.get('col_index')} "
                    f"/ cell={issue.get('cell_id')} "
                    f"/ details={issue.get('details')}"
                )

        lines.append("")

    return "\n".join(lines)


#------------------------------------------------
# 결과 저장
#------------------------------------------------

def save_results(
    parser: HwpxParser,
    tables: list[Any],
    output_root: Path,
) -> None:
    """
    역할: summary.json, tables.json, parse_result.txt 파일로 파싱 결과를 저장한다.
    입력 데이터: parser(HwpxParser), tables(Table 리스트), output_root(결과 저장 루트 Path).
    출력 데이터: 반환값은 없고, output_root/results/<문서명>/ 아래에 결과 파일 3개를 생성 또는 덮어쓴다.
    """
    result_dir = output_root / "results" / parser.filename
    result_dir.mkdir(parents=True, exist_ok=True)

    summary = build_summary(parser, tables)

    tables_data = [
        serialize_table_to_dict(table)
        for table in tables
    ]

    summary_path = result_dir / "summary.json"
    tables_path = result_dir / "tables.json"
    text_path = result_dir / "parse_result.txt"
    struct_path = result_dir / "struct.md"

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2,
        )

    with tables_path.open("w", encoding="utf-8") as f:
        json.dump(
            tables_data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    report_text = build_text_report(
        parser=parser,
        tables=tables,
        summary=summary,
    )

    with text_path.open("w", encoding="utf-8") as f:
        f.write(report_text)

    save_tables_json_struct(struct_path)

    print("===========================================")
    print("[RESULT SAVED]")
    print("summary:", summary_path)
    print("tables :", tables_path)
    print("report :", text_path)
    print("struct :", struct_path)
    print("===========================================")


#------------------------------------------------
# 실행부
#------------------------------------------------

def main() -> None:
    """
    역할: sample.zip을 대상으로 HWPX 표 파싱 샘플 실행 흐름을 수행한다.
    입력 데이터: 현재 작업 폴더의 sample.zip 파일과 output 저장 경로.
    출력 데이터: 반환값은 없고, 파싱 정보 출력 및 output/results/sample 아래 결과 파일 저장을 수행한다.
    """
    """
    test.py는 실행기 역할만 한다.

    여기서 직접 TableParser, TableAnalyzer를 호출하지 않는다.
    전체 파싱은 HwpxParser.parse() 내부 파이프라인에 맡긴다.
    """

    source = "sample.zip"
    output_root = Path("output")

    parser = HwpxParser(
        doc_save_path=str(output_root),
        source=source,
    )

    tables = parser.parse()

    parser.file_info()

    save_results(
        parser=parser,
        tables=tables,
        output_root=output_root,
    )

    tables_path = output_root / "results" / parser.filename / "tables.json"
    tables_preprocessed_path = output_root / "results" / parser.filename / "tables_preprocessed.json"
    tables_hierarchical_path = output_root / "results" / parser.filename / "tables_hierarchical.json"

    convert_tables_json_with_preprocess(
        input_path=tables_path,
        output_path=tables_preprocessed_path,
    )

    add_table_grid_to_json(
        input_path=tables_preprocessed_path,
        output_path=tables_preprocessed_path,
    )

    add_table_hierarchy_to_json(
        input_path=tables_preprocessed_path,
        output_path=tables_hierarchical_path,
    )

    debug_table_hierarchy_input(
        input_path=tables_hierarchical_path,
        limit=10,
        include_cells=True,
        include_nested=True,
    )

    try:
        debug_simple_tables(
            input_path=tables_hierarchical_path,
            limit=20,
            include_nested=True,
        )
    except UnicodeEncodeError:
        pass

    print("tables_preprocessed:", tables_preprocessed_path)
    print("tables_hierarchical:", tables_hierarchical_path)

    debug_title_texts(tables_hierarchical_path)


if __name__ == "__main__":
    main()
