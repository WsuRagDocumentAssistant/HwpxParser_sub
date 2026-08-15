#================================================
# tools/refactor_guard.py
#
# 리팩토링 전용 가드. 산출물이 바이트 단위로 동일한지만 본다.
#
# regression_check.py는 "불변식이 유지되는가"를 보지만, 리팩토링에서는
# 그것으로 부족하다. 동작을 바꾸지 않는 것이 목적이므로 산출물 해시가
# 하나라도 달라지면 실패다.
#
# 사용:
#   python tools/refactor_guard.py snapshot <결과폴더> [<결과폴더> ...]
#   python tools/refactor_guard.py verify
#
# 파일 없이 쓰기 (권장):
#   python tools/refactor_guard.py snapshot-pipeline
#   python tools/refactor_guard.py verify-pipeline
#
#   문서를 직접 파싱해 파이프라인을 돌리고, 결과 객체를 부분별로 해시한다.
#   final_debug.json 을 --debug 뒤로 숨기면 파일 모드는 잴 것이 없어져
#   조용히 통과해 버린다. 가드가 아무것도 안 지키면서 PASS 하는 것이
#   가장 나쁜 실패라 객체를 직접 재는 쪽으로 옮긴다.
#
#   document_model.json 을 재지 않는 이유: 모델은 필터를 통과한 것만 담는다.
#   버려진 표, tables.body_linking, table_internal_blocks 는 모델에 없으므로
#   그쪽이 망가져도 모델 해시는 안 변한다. 실제로 body_linking 에 버려진 표
#   텍스트 20,078자가 남아 있던 버그를 그런 식으로 놓친 적이 있다.
#   파이프라인 상태(state_view)는 필터 이전이라 전부 덮는다.
#
#   summary 의 경로 필드는 해시에서 뺀다. 실행 위치에 따라 달라지는 값이라
#   동작이 안 바뀌었는데도 FAIL 이 나기 때문이다. 나머지는 절대경로를
#   담지 않는 것을 확인했다.
#================================================

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_STORE = REPO_ROOT / "tools" / "baseline" / "refactor_hashes.json"
DEFAULT_PIPELINE_STORE = REPO_ROOT / "tools" / "baseline" / "pipeline_hashes.json"

# 해시 대상 산출물 (없으면 건너뛴다)
ARTIFACTS = (
    "final_debug.json",
    "llm_context.txt",
    "depth_text_preview_raw.txt",
    "depth_text_preview_clean.txt",
)

# summary 에서 해시 대상으로 삼지 않는 필드.
# 어디서 실행했는지에 따라 달라지는 값이라 동작 변화가 아니다.
SUMMARY_VOLATILE = ("source", "unpacked_dir_path", "contents_dir_path",
                    "header_file_path", "image_dir_path")


def file_hash(path: Path) -> str:
    """
    역할: 파일의 sha256을 계산한다.
    입력 데이터: path.
    출력 데이터: hex 문자열.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(dirs: list[str]) -> dict[str, dict[str, str]]:
    """
    역할: 결과 폴더들에서 산출물 해시를 모은다.
    입력 데이터: dirs(결과 폴더 경로 목록).
    출력 데이터: {폴더: {파일명: sha256}}.
    """
    out: dict[str, dict[str, str]] = {}
    for d in dirs:
        base = Path(d)
        entry: dict[str, str] = {}
        for name in ARTIFACTS:
            p = base / name
            if p.exists():
                entry[name] = file_hash(p)
        if not entry:
            print(f"[WARN] 산출물이 없습니다: {base}")
        out[str(base)] = entry
    return out


def value_hash(value: object) -> str:
    """
    역할: JSON 직렬화 가능한 값의 안정적인 sha256 을 만든다.
    입력 데이터: value(dict/list/str).
    출력 데이터: hex 문자열.

    키를 정렬해 직렬화한다. dict 순서가 흔들려도 같은 내용이면 같은 해시가
    나와야 "동작이 안 바뀌었다"를 판정할 수 있다.
    """
    if isinstance(value, str):
        payload = value
    else:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def pipeline_hashes(result) -> dict[str, str]:
    """
    역할: 파이프라인 결과 객체를 부분별로 해시한다.
    입력 데이터: result(PipelineResult).
    출력 데이터: {부분 이름: sha256}.

    한 덩어리로 묶지 않고 나눈다. 해시 하나만 있으면 "달라졌다"까지만 알고
    어디가 달라졌는지 모른다.
    """
    from hwpx_analysis.table_filter import state_view

    view = state_view(result)
    summary = {k: v for k, v in (view["summary"] or {}).items()
               if k not in SUMMARY_VOLATILE}

    parts: dict[str, object] = {
        "summary": summary,
        "tables.raw": view["tables"]["raw"],
        "tables.analyzed": view["tables"]["analyzed"],
        "tables.body_linking": view["tables"]["body_linking"],
        "blocks_document": view["blocks_document"],
        "table_internal_blocks": view["table_internal_blocks"],
        "warnings": view["warnings"],
        "quality_report": view["quality_report"],
    }
    if result.preview is not None:
        parts["preview.raw"] = result.preview.raw_text
        parts["preview.clean"] = result.preview.clean_text
    if result.llm_context is not None:
        parts["llm_context"] = result.llm_context.text

    return {name: value_hash(value) for name, value in parts.items()}


def collect_pipeline(source: Path, work: Path) -> dict[str, str]:
    """
    역할: 문서를 파싱해 파이프라인을 돌리고 부분 해시를 모은다.
    입력 데이터: source(문서), work(압축 해제 위치).
    출력 데이터: {부분 이름: sha256}.
    """
    from tools.build_document_model import run_pipeline

    _, result = run_pipeline(source, work)
    return pipeline_hashes(result)


def command_snapshot_pipeline(args: argparse.Namespace) -> int:
    from tools.audit.documents import enable_utf8_stdout
    enable_utf8_stdout()

    source = Path(args.source)
    if not source.exists():
        print(f"[ERROR] 문서를 찾을 수 없습니다: {source}")
        return 1

    data = collect_pipeline(source, Path(args.work))
    store = Path(args.store)
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("w", encoding="utf-8") as f:
        json.dump({"source_name": source.name, "parts": data}, f,
                  ensure_ascii=False, indent=2)

    print("===========================================")
    print("[파이프라인 기준 해시 저장]")
    print(f"  문서: {source}")
    for name, h in data.items():
        print(f"      {name:24s} {h[:16]}...")
    print(f"  대상 {len(data)}개 -> {store}")
    print("===========================================")
    return 0


def command_verify_pipeline(args: argparse.Namespace) -> int:
    from tools.audit.documents import enable_utf8_stdout
    enable_utf8_stdout()

    store = Path(args.store)
    if not store.exists():
        print(f"[ERROR] 기준 해시가 없습니다: {store}")
        print("        먼저 snapshot-pipeline 을 실행하세요.")
        return 1

    with store.open(encoding="utf-8") as f:
        base = json.load(f).get("parts") or {}
    if not base:
        print(f"[ERROR] 기준 해시가 비어 있습니다: {store}")
        return 1

    source = Path(args.source)
    if not source.exists():
        print(f"[ERROR] 문서를 찾을 수 없습니다: {source}")
        return 1

    current = collect_pipeline(source, Path(args.work))

    changed = [n for n, h in base.items() if current.get(n) not in (None, h)]
    missing = [n for n in base if n not in current]
    added = [n for n in current if n not in base]

    print("===========================================")
    print("[파이프라인 결과 동일성 검증]")
    print(f"  문서: {source}")
    print(f"  대상 {len(base)}개 / 변경 {len(changed)}개 / "
          f"누락 {len(missing)}개 / 신규 {len(added)}개")
    for n in changed:
        print(f"      [변경] {n:24s} {base[n][:16]} -> {current[n][:16]}")
    for n in missing:
        print(f"      [누락] {n}")
    for n in added:
        print(f"      [신규] {n}")
    print("===========================================")

    if changed or missing:
        print("결과: FAIL - 파이프라인 결과가 달라졌습니다. 이번 수정을 되돌리세요.")
        return 1

    print("결과: PASS - 파이프라인 결과가 부분별로 동일합니다.")
    return 0


def command_snapshot(args: argparse.Namespace) -> int:
    store = Path(args.store)
    data = collect(args.dirs)

    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in data.values())
    print("===========================================")
    print("[리팩토링 기준 해시 저장]")
    for d, files in data.items():
        print(f"  {d}")
        for name, h in files.items():
            print(f"      {name:32s} {h[:16]}...")
    print(f"  대상 파일 {total}개 -> {store}")
    print("===========================================")
    return 0


def command_verify(args: argparse.Namespace) -> int:
    store = Path(args.store)
    if not store.exists():
        print(f"[ERROR] 기준 해시가 없습니다: {store}")
        print("        먼저 snapshot을 실행하세요.")
        return 1

    with store.open(encoding="utf-8") as f:
        base = json.load(f)

    current = collect(list(base.keys()))

    changed: list[str] = []
    missing: list[str] = []
    for d, files in base.items():
        for name, h in files.items():
            got = current.get(d, {}).get(name)
            if got is None:
                missing.append(f"{d}/{name}")
            elif got != h:
                changed.append(f"{d}/{name}")

    print("===========================================")
    print("[리팩토링 산출물 동일성 검증]")
    total = sum(len(v) for v in base.values())
    print(f"  대상 {total}개 / 변경 {len(changed)}개 / 누락 {len(missing)}개")
    for x in changed:
        print(f"      [변경] {x}")
    for x in missing:
        print(f"      [누락] {x}")
    print("===========================================")

    if changed or missing:
        print("결과: FAIL - 산출물이 달라졌습니다. 이번 삭제를 되돌리세요.")
        return 1

    print("결과: PASS - 산출물이 바이트 단위로 동일합니다.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="리팩토링 산출물 동일성 가드")
    parser.add_argument("command", choices=("snapshot", "verify",
                                            "snapshot-pipeline",
                                            "verify-pipeline"))
    parser.add_argument("dirs", nargs="*", help="결과 폴더 (snapshot에서만 사용)")
    parser.add_argument("--store", default=None)
    parser.add_argument("--source", default=str(REPO_ROOT / "sample.zip"),
                        help="*-pipeline 대상 문서")
    parser.add_argument("--work", default=str(REPO_ROOT / "output"),
                        help="*-pipeline 압축 해제 위치")
    args = parser.parse_args(argv)

    if args.store is None:
        args.store = str(DEFAULT_PIPELINE_STORE
                         if args.command.endswith("-pipeline")
                         else DEFAULT_STORE)

    if args.command == "snapshot-pipeline":
        return command_snapshot_pipeline(args)
    if args.command == "verify-pipeline":
        return command_verify_pipeline(args)

    if args.command == "snapshot":
        if not args.dirs:
            print("[ERROR] snapshot에는 결과 폴더가 최소 1개 필요합니다.")
            return 1
        return command_snapshot(args)

    return command_verify(args)


if __name__ == "__main__":
    sys.exit(main())
