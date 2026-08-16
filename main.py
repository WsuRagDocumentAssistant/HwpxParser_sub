#================================================
# main.py
#
# 라이브러리를 쓰는 쪽 코드. 받아 쓰는 사람과 같은 방식이다.
#
# tools 를 거치지 않는다. hwpx 만 부른다. 그래서 이 파일은 그대로 복사해
# 다른 프로젝트에 붙여도 돌아간다(hwpx 가 설치돼 있다면).
#
# 이 파일도 기본은 조용하다. 라이브러리가 찍는 단계 보고를 보고 싶으면
# 아래 두 줄을 넣으면 된다.
#     import logging
#     logging.basicConfig(level=logging.INFO, format='%(message)s')
#
#     python main.py                문서 -> 모델 -> document_model.json. 조용하다
#     python main.py --report       무엇이 나왔는지 요약까지
#     python main.py <문서>
#
# tools/run_model.py 와 무엇이 다른가
#   저쪽은 이 저장소의 실행기다. M2~M15 자체 검증을 돌리고 조사용 산출물을
#   쓰는 옵션이 붙어 있다. 파이프라인을 고칠 때 쓰는 것이다.
#   이 파일은 "문서를 넣으면 객체가 나온다" 만 보여준다.
#================================================

from __future__ import annotations

import json
import sys
from pathlib import Path

import hwpx

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = REPO_ROOT / (
    "3주기(2025년) 대학혁신지원사업 1차년도 수정 자율혁신계획_260122 1133.hwpx"
)


def main(argv: list[str] | None = None) -> int:
    """
    역할: 문서 하나를 모델로 만들어 저장한다.
    입력 데이터: argv(문서 경로. 없으면 저장소의 기본 문서. --report 로 요약 출력).
    출력 데이터: 종료 코드. 기본은 아무것도 찍지 않는다.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    report = '--report' in args
    if report:
        args.remove('--report')
    source = Path(args[0]) if args else DEFAULT_SOURCE
    if not source.exists():
        print(f"문서를 찾을 수 없습니다: {source}", file=sys.stderr)
        return 1

    # --- 여기가 라이브러리 사용부. 두 줄이다 ---------------------
    parser, result = hwpx.run_pipeline(source, out_root=REPO_ROOT / "output")
    model = hwpx.build_document_model(result)
    # -------------------------------------------------------------

    out = REPO_ROOT / "output" / "results" / model.file.filename / "document_model.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    # indent 는 tools/build_document_model.py 와 맞춘다. 다르면 같은 모델인데
    # 파일이 달라 보인다.
    out.write_text(json.dumps(model.to_dict(), ensure_ascii=False, indent=2),
                   encoding="utf-8")

    if report:
        show(model, out)
    return 0


def show(model, out: Path) -> None:
    """
    역할: --report 일 때만 부르는 사람용 요약.
    입력 데이터: model(DocumentModel), out(저장 경로).
    출력 데이터: 반환값 없음.
    """
    # 콘솔이 cp949 면 한글이 깨진다. 표준 라이브러리만 쓴다.
    sys.stdout.reconfigure(encoding='utf-8')
    print(f"{model.file.filename}")
    print(f"  블록    {len(model.blocks)}개 (검색 대상 {len(model.searchable_blocks())}개)")
    print(f"  표      {len(list(model.tables()))}개 (수치표 {len(model.numeric_tables())}개)")
    print(f"  이미지  {len(model.images)}개")
    print()
    for block in model.blocks:
        if block.toc:
            번호 = f"{block.toc.numbering} " if block.toc.numbering else ""
            print(f"  {'  ' * block.depth}{번호}{block.toc.title}")
    print()
    print(f"  저장 -> {out}")


if __name__ == "__main__":
    sys.exit(main())
