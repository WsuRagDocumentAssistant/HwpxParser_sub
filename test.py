#================================================
# test.py
#================================================

from __future__ import annotations

from pathlib import Path
from typing import Any

from hwpx_analysis.pipeline import run_analysis_pipeline, save_pipeline_outputs
from hwpx_analysis.table_json_serializer import (
    table_to_dict as serialize_table_to_dict,
)
from hwpx_parser.parser import HwpxParser


#------------------------------------------------
# 요약 정보 생성
#------------------------------------------------

def build_summary(parser: HwpxParser, tables: list[Any]) -> dict[str, Any]:
    """
    역할: 전체 파싱 결과와 표 검증 결과를 요약 통계 dict로 집계한다.
    입력 데이터: parser(HwpxParser), tables(파싱/검증된 Table 리스트).
    출력 데이터: 파일 경로, 표 개수, 오류/경고 개수, header 참조 검증 요약을 담은 dict를 반환한다.
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
        },
    }


#------------------------------------------------
# 실행부
#------------------------------------------------

def main() -> None:
    """
    역할: sample.zip을 대상으로 HWPX 표 파싱 샘플 실행 흐름을 수행한다.
    입력 데이터: 현재 작업 폴더의 sample.zip 파일과 output 저장 경로.
    출력 데이터: 반환값은 없고, output/results/<문서명>/ 아래에
                 디버깅용 최종 JSON(final_debug.json)과
                 계층 시각화용 txt(depth_text_preview_raw/clean.txt)를 저장한다.
    """
    """
    test.py는 실행기 역할만 한다.

    전체 파싱은 HwpxParser.parse()에, 분석은 run_analysis_pipeline()에 맡긴다.
    파이프라인 단계 간 데이터는 데이터 클래스(pipeline_models)로 인메모리 전달되며
    중간 JSON 파일은 만들지 않는다.
    """

    source = "sample.zip"
    output_root = Path("output")

    parser = HwpxParser(
        doc_save_path=str(output_root),
        source=source,
    )

    tables = parser.parse()

    parser.file_info()

    # 파서 결과(Table 객체)를 직렬화 dict 리스트로 변환 (구 tables.json 내용)
    char_pr_lookup = parser.header.char_properties if parser.header is not None else None
    raw_tables = [
        serialize_table_to_dict(
            table,
            char_pr_lookup=char_pr_lookup,
            header=parser.header,
        )
        for table in tables
    ]

    summary = build_summary(parser, tables)

    result = run_analysis_pipeline(
        raw_tables=raw_tables,
        section_paths=parser.section_file_paths,
        header=parser.header,
        summary=summary,
    )

    save_pipeline_outputs(
        result=result,
        output_dir=output_root / "results" / parser.filename,
    )


if __name__ == "__main__":
    main()
