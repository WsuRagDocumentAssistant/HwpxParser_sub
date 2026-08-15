#================================================
# hwpx_analysis/build_summary.py
#
# 파싱 결과 요약(summary)을 만든다. run_analysis_pipeline 에 넘어가고
# PipelineResult.summary 로 남는다.
#
# 왜 여기 있나
#   전에는 test.py 와 tools/run_document.py 가 같은 이름의 함수를 각각
#   따로 갖고 있었고, 두 벌이 서로 다른 값을 냈다. 최상위 키가 15개 대
#   7개였고 header 하위 키도 갈렸다. 어느 진입점으로 도느냐에 따라
#   산출물이 달라져서, tools/audit/field_provenance.py 는 "산출물 컬럼이
#   134개 어긋난다"는 주석을 달고 test.py 쪽을 기본으로 고정해 두어야 했다.
#   같은 이름이 다른 값을 내는 상태 자체가 사고 자리라 한 벌로 합쳤다.
#
# 합칠 때 어느 쪽을 버렸나
#   버리지 않았다. 두 벌은 포함 관계가 아니었다. 표 검증 집계와 경로
#   2개는 test.py 에만, header 의 bullet_count / numbering_count 는
#   run_document.py 에만 있었다. 그래서 합집합을 취했다. 어느 진입점도
#   전에 보던 키를 잃지 않는다.
#================================================

from __future__ import annotations

from typing import Any

from hwpx_parser.parser import HwpxParser


def build_summary(parser: HwpxParser, tables: list[Any]) -> dict[str, Any]:
    """
    역할: 전체 파싱 결과와 표 검증 결과를 요약 통계 dict로 집계한다.
    입력 데이터: parser(실행이 끝난 HwpxParser), tables(파싱/검증된 Table 리스트).
    출력 데이터: 파일 경로, 표 개수, 오류/경고 개수, header 참조 검증 요약 dict.
    """
    invalid_tables = []

    total_issue_count = 0
    error_count = 0
    warning_count = 0

    missing_style_ref_count = 0
    missing_para_pr_ref_count = 0
    missing_char_pr_ref_count = 0

    tables_with_missing_style_ref = []
    tables_with_missing_para_pr_ref = []
    tables_with_missing_char_pr_ref = []

    for table in tables:
        validation = table.validation

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

        "header_reference_validation": {
            "missing_style_ref_table_count": missing_style_ref_count,
            "missing_para_pr_ref_table_count": missing_para_pr_ref_count,
            "missing_char_pr_ref_table_count": missing_char_pr_ref_count,

            "tables_with_missing_style_ref": tables_with_missing_style_ref,
            "tables_with_missing_para_pr_ref": tables_with_missing_para_pr_ref,
            "tables_with_missing_char_pr_ref": tables_with_missing_char_pr_ref,
        },

        "header": {
            "para_property_count": len(header.para_properties) if header else 0,
            "char_property_count": len(header.char_properties) if header else 0,
            "style_count": len(header.styles) if header else 0,
            "style_name_count": len(header.style_names) if header else 0,
            "style_to_para_pr_count": len(header.style_to_para_pr) if header else 0,
            "style_to_char_pr_count": len(header.style_to_char_pr) if header else 0,
            "heading_level_count": len(header.para_pr_to_heading_level) if header else 0,
            "bullet_count": len(header.bullet_chars) if header else 0,
            "numbering_count": len(header.numbering_para_heads) if header else 0,
        },
    }
