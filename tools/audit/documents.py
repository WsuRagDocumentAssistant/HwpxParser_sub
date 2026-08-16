"""감사 대상 문서를 찾아 준다.

산출물 디렉토리 규약
    <베이스>/results/<문서명>/final_debug.json     분석 산출물
    <베이스>/unpacked/<문서명>/Contents/           원본 XML

두 경로는 <베이스>와 <문서명>을 공유하므로 결과 디렉토리 하나만 주면
원본 XML 위치까지 따라간다.

인자 없이 실행하면 저장소의 output/results 아래를 전부 훑는다.
다른 문서를 보려면 결과 디렉토리를 인자로 준다. tools/run_document.py 로
저장소 밖 문서를 분석한 뒤 그 결과 디렉토리를 넘기면 된다.

    python -m tools.audit.depth_audit
    python -m tools.audit.depth_audit D:/out/results/보고서
    python -m tools.audit.depth_audit 문서A=D:/out/results/2주기_수정사업계획서

'라벨=경로' 형태로 주면 출력에 쓸 이름을 직접 정할 수 있다. 생략하면
디렉토리 이름을 줄여서 쓴다.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]

# 라벨이 이보다 길면 줄인다. 표 형태 출력이 무너지지 않을 정도로 잡았다.
_LABEL_MAX = 22


class Document(NamedTuple):
    """감사 대상 문서 하나."""

    label: str
    results_dir: Path
    final_debug: Path
    contents_dir: Path | None   # 원본 XML. 압축 해제 결과가 없으면 None


def enable_utf8_stdout() -> None:
    """한글 출력이 콘솔 코드페이지에 걸려 죽지 않게 한다."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except AttributeError:      # 리다이렉트된 스트림
            pass


def _shorten(name: str) -> str:
    return name if len(name) <= _LABEL_MAX else name[:_LABEL_MAX - 1] + '…'


def _contents_dir(results_dir: Path) -> Path | None:
    """결과 디렉토리에서 같은 문서의 압축 해제 디렉토리를 찾는다."""
    if results_dir.parent.name != 'results':
        return None
    candidate = results_dir.parent.parent / 'unpacked' / results_dir.name / 'Contents'
    return candidate if candidate.is_dir() else None


def _build(label: str | None, results_dir: Path) -> Document:
    results_dir = results_dir.resolve()
    return Document(
        label=label or _shorten(results_dir.name),
        results_dir=results_dir,
        final_debug=results_dir / 'final_debug.json',
        contents_dir=_contents_dir(results_dir),
    )


def _default_documents() -> list[Document]:
    root = REPO_ROOT / 'output' / 'results'
    if not root.is_dir():
        return []
    return [_build(None, d) for d in sorted(root.iterdir())
            if (d / 'final_debug.json').is_file()]


def resolve(argv: list[str] | None = None) -> list[Document]:
    """인자를 문서 목록으로 바꾼다. 산출물이 없으면 안내 후 종료한다."""
    args = sys.argv[1:] if argv is None else argv

    if args:
        documents = []
        for arg in args:
            label, sep, path = arg.partition('=')
            documents.append(_build(label, Path(path)) if sep else _build(None, Path(label)))
    else:
        documents = _default_documents()

    if not documents:
        # 자동 탐색은 final_debug.json 이 있는 폴더만 문서로 센다. 그 파일은
        # --debug 를 줄 때만 저장되므로, 폴더가 있어도 여기서 걸릴 수 있다.
        # "실행을 안 했다"가 아니라 "--debug 없이 실행했다"가 흔한 원인이다.
        hint = ""
        root = REPO_ROOT / 'output' / 'results'
        if root.is_dir() and any(root.iterdir()):
            hint = ("\n분석 결과 폴더는 있는데 final_debug.json 이 없습니다.\n"
                    "감사 도구는 그 파일을 읽으므로 --debug 로 다시 만드세요.\n")
        sys.exit(
            "감사할 문서가 없습니다."
            + hint
            + "\n  python test.py --debug                     기본 문서 분석\n"
              "  python -m tools.run_document <문서> --out <폴더> --debug\n"
              "그 뒤 결과 디렉토리를 인자로 주거나 인자 없이 다시 실행하세요."
        )

    missing = [d for d in documents if not d.final_debug.is_file()]
    if missing:
        # final_debug.json 은 --debug 를 줄 때만 저장된다. 감사 도구는 이 파일을
        # 읽으므로, 없을 때 "왜 없는지"를 같이 알려주지 않으면 막힌다.
        sys.exit(
            "final_debug.json 이 없습니다:\n"
            + "\n".join(f"  {d.final_debug}" for d in missing)
            + "\n\n이 파일은 --debug 를 줄 때만 저장됩니다. 감사 도구는 이 파일을\n"
              "읽으므로 아래처럼 다시 만드세요.\n"
              "  python test.py --debug                       기본 문서\n"
              "  python -m tools.run_document <문서> --out <폴더> --debug"
        )

    return documents


def require_contents(documents: list[Document]) -> list[Document]:
    """원본 XML이 필요한 도구용. 없는 문서는 알리고 건너뛴다."""
    usable = [d for d in documents if d.contents_dir]
    for d in documents:
        if not d.contents_dir:
            print(f"  [건너뜀] {d.label}: 압축 해제 결과가 없어 XML 대조 불가 "
                  f"({d.results_dir.parent.parent / 'unpacked' / d.results_dir.name})")
    if not usable:
        sys.exit("XML 대조가 가능한 문서가 없습니다.")
    return usable
