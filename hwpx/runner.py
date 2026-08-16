#================================================
# hwpx/runner.py
#
# 문서 하나를 받아 파싱과 분석을 끝까지 돌린다.
#
# 왜 라이브러리에 있나
#   쓰는 쪽이 필요한 건 "문서를 넣으면 결과 객체가 나온다" 하나다. 전에는
#   이 조립이 tools 안에 있어서, 라이브러리만 가져다 쓰는 사람은 파서 호출·
#   직렬화·summary 구성을 직접 베껴야 했다. 순서를 틀려도(예: file_info 를
#   빼먹어도) 에러가 안 나고 결과만 달라진다.
#
#   실제로 tools 안에서도 두 벌로 갈라져 있었다. build_document_model 과
#   run_document 가 같은 여덟 줄을 각자 갖고 있었다. build_summary 가 같은
#   식으로 갈렸다가 서로 다른 값을 냈던 적이 있어 한 벌로 모은다.
#================================================

from __future__ import annotations

from pathlib import Path

from .analysis.build_summary import build_summary
from .analysis.pipeline import run_analysis_pipeline
from .analysis.table_json_serializer import table_to_dict
from .parser.parser import HwpxParser


def run_pipeline(source: str | Path, out_root: str | Path):
    """
    역할: 문서를 파싱하고 분석 파이프라인을 돌린다. 파일은 쓰지 않는다.
    입력 데이터: source(HWPX/ZIP 경로), out_root(압축 해제 위치).
    출력 데이터: (HwpxParser, PipelineResult).
    """
    parser = HwpxParser(doc_save_path=str(out_root), source=str(source))
    tables = parser.parse()
    parser.file_info()
    char_pr = parser.header.char_properties if parser.header is not None else None
    raw_tables = [table_to_dict(t, char_pr_lookup=char_pr, header=parser.header)
                  for t in tables]
    result = run_analysis_pipeline(
        raw_tables=raw_tables,
        section_paths=parser.section_file_paths,
        header=parser.header,
        summary=build_summary(parser, tables),
    )
    return parser, result
