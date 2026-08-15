#================================================
# test.py
#================================================

from __future__ import annotations

import argparse
from pathlib import Path

from hwpx_analysis.build_summary import build_summary
from hwpx_analysis.pipeline import run_analysis_pipeline, save_pipeline_outputs
from hwpx_analysis.table_json_serializer import (
    table_to_dict as serialize_table_to_dict,
)
from hwpx_parser.parser import HwpxParser


#------------------------------------------------
# 실행부
#------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    """
    역할: sample.zip을 대상으로 HWPX 표 파싱 샘플 실행 흐름을 수행한다.
    입력 데이터: argv(--debug), 현재 작업 폴더의 sample.zip과 output 저장 경로.
    출력 데이터: 반환값은 없고, output/results/<문서명>/ 아래에
                 계층 시각화용 txt(depth_text_preview_raw/clean.txt)와
                 llm_context.txt 를 저장한다.
                 --debug 를 주면 final_debug.json 도 함께 저장한다.
    """
    cli = argparse.ArgumentParser(description="sample.zip 파싱 파이프라인 실행")
    cli.add_argument("--debug", action="store_true",
                     help="final_debug.json 도 저장 (tools/audit/* 를 쓸 때 필요)")
    args = cli.parse_args(argv)
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
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
