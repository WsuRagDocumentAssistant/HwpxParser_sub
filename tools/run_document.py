#================================================
# tools/run_document.py
#
# 임의의 HWPX/ZIP 문서로 파싱 파이프라인을 실행한다.
#
# test.py는 sample.zip에 고정되어 있어서 다른 문서로 검증할 수단이 없었다.
# 이 스크립트는 산출물 위치를 인자로 받으므로, 저장소 밖에 있는 문서를
# 저장소를 건드리지 않고 검증할 수 있다.
#
# 사용 예:
#   python tools/run_document.py "D:/docs/report.hwpx" --out /tmp/hwpx_check
#   python tools/regression_check.py check \
#       --contents /tmp/hwpx_check/unpacked/report/Contents \
#       --current  /tmp/hwpx_check/results/report/final_debug.json \
#       --baseline /tmp/hwpx_check/report.baseline.json
#================================================

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hwpx_analysis.pipeline import run_analysis_pipeline, save_pipeline_outputs
from hwpx_analysis.table_json_serializer import table_to_dict
from hwpx_parser.parser import HwpxParser


def build_summary(parser: HwpxParser, tables: list[Any]) -> dict[str, Any]:
    """
    역할: 파이프라인에 넘길 최소 요약 정보를 만든다.
    입력 데이터: parser(실행이 끝난 HwpxParser), tables(파싱된 Table 리스트).
    출력 데이터: 요약 dict.
    """
    header = parser.header

    return {
        "source": str(parser.source_path),
        "filename": parser.filename,
        "unpacked_dir_path": str(parser.unpacked_dir_path),
        "contents_dir_path": str(parser.contents_dir_path),
        "section_count": len(parser.section_file_paths),
        "table_count": len(tables),
        "header": {
            "para_property_count": len(header.para_properties) if header else 0,
            "char_property_count": len(header.char_properties) if header else 0,
            "style_count": len(header.styles) if header else 0,
            "bullet_count": len(header.bullet_chars) if header else 0,
            "numbering_count": len(header.numbering_para_heads) if header else 0,
        },
    }


def main(argv: list[str] | None = None) -> int:
    """
    역할: CLI 진입점. 지정한 문서로 파싱+분석 파이프라인을 실행하고 산출물을 저장한다.
    입력 데이터: argv(source 경로, --out 저장 루트).
    출력 데이터: 종료 코드.
    """
    parser_cli = argparse.ArgumentParser(
        description="임의 HWPX 문서로 파싱 파이프라인 실행",
    )
    parser_cli.add_argument("source", help="HWPX 또는 ZIP 문서 경로")
    parser_cli.add_argument(
        "--out",
        required=True,
        help="압축 해제/산출물 저장 루트 (저장소 밖 경로 권장)",
    )

    args = parser_cli.parse_args(argv)

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"[ERROR] 문서를 찾을 수 없습니다: {source_path}")
        return 1

    output_root = Path(args.out)

    parser = HwpxParser(doc_save_path=str(output_root), source=str(source_path))
    tables = parser.parse()
    parser.file_info()

    char_pr_lookup = parser.header.char_properties if parser.header is not None else None
    raw_tables = [
        table_to_dict(table, char_pr_lookup=char_pr_lookup, header=parser.header)
        for table in tables
    ]

    result = run_analysis_pipeline(
        raw_tables=raw_tables,
        section_paths=parser.section_file_paths,
        header=parser.header,
        summary=build_summary(parser, tables),
    )

    save_pipeline_outputs(
        result=result,
        output_dir=output_root / "results" / parser.filename,
    )

    print("===========================================")
    print("[검증 명령]")
    print("python tools/regression_check.py check \\")
    print(f'  --contents "{parser.contents_dir_path}" \\')
    print(f'  --current  "{output_root / "results" / parser.filename / "final_debug.json"}" \\')
    print(f'  --baseline "{output_root / (parser.filename + ".baseline.json")}"')
    print("===========================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())
