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
#================================================

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STORE = REPO_ROOT / "tools" / "baseline" / "refactor_hashes.json"

# 해시 대상 산출물 (없으면 건너뛴다)
ARTIFACTS = (
    "final_debug.json",
    "llm_context.txt",
    "depth_text_preview_raw.txt",
    "depth_text_preview_clean.txt",
)


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
    parser.add_argument("command", choices=("snapshot", "verify"))
    parser.add_argument("dirs", nargs="*", help="결과 폴더 (snapshot에서만 사용)")
    parser.add_argument("--store", default=str(DEFAULT_STORE))
    args = parser.parse_args(argv)

    if args.command == "snapshot":
        if not args.dirs:
            print("[ERROR] snapshot에는 결과 폴더가 최소 1개 필요합니다.")
            return 1
        return command_snapshot(args)

    return command_verify(args)


if __name__ == "__main__":
    sys.exit(main())
