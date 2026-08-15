#================================================
# test.py
#
# 실제 서비스가 쓰는 방식 그대로 돌려서 결과를 눈으로 확인한다.
#
# 서비스는 파일을 거치지 않는다. 문서를 파싱하고 파이프라인을 돌린 뒤
# 결과 객체에서 DocumentModel 을 조립해 그대로 쓴다. 아래 세 줄이 전부다.
#
#     parser, result = run_pipeline(source, out_root)
#     model = build_document_model(result)
#     model.blocks / model.tables() / model.numeric_tables() ...
#
# 이 파일은 그 세 줄을 돌리고, 사람이 볼 수 있게 내용을 찍고,
# 뜯어보라고 document_model.json 으로 한 번 떨어뜨린다. 서비스에는
# 그 저장 단계가 없어도 된다.
#
# 사용:
#   python test.py            문서 -> 파이프라인 -> 모델 -> 검증 -> 저장
#   python test.py --debug    조사용 산출물까지 함께 저장
#                             (final_debug.json, 프리뷰 2종, llm_context.txt)
#
# 매 실행 M2~M13 을 검증하고 하나라도 깨지면 저장하지 않는다.
#
# 다른 문서로 돌리거나 저장 위치를 바꾸려면 tools/build_document_model.py 를
# 직접 쓴다. 이 파일은 tools/defaults.py 가 정한 기본 문서를 본다.
#================================================

from __future__ import annotations

import sys

from tools.build_document_model import main


def run(argv: list[str] | None = None) -> int:
    """
    역할: 모델 생성 진입점을 그대로 부른다.
    입력 데이터: argv(--debug 등).
    출력 데이터: 종료 코드.

    같은 절차를 두 벌로 두지 않는다. build_summary 가 test.py 와
    tools/run_document.py 에 따로 있다가 서로 다른 값을 냈던 일이 있어서,
    여기서는 베끼지 않고 부르기만 한다.
    """
    return main(argv)


if __name__ == "__main__":
    sys.exit(run())
