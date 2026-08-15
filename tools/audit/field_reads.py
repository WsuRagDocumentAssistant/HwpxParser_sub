"""각 필드를 어느 단계가 실제로 읽는지 실행 중에 관측한다.

왜 정적 분석으로는 안 되는가
    필드는 문자열 키다. 이름만 보고 소비처를 찾으면 같은 이름을 쓰는 다른
    구조와 구분할 수 없고, 소스 63개 모듈 중 파이프라인 단계로 이름이
    매핑되는 것은 19개뿐이라 나머지의 읽기는 순서를 몰라 판정에서 밀린다.
    실제로 그 방식으로는 330개 필드가 '소비처 없음'으로 나왔는데, 쓰이지
    않는다는 뜻이 아니라 판정을 못 한 것이었다.

방법
    블록/표 dict 를 dict 서브클래스로 감싸 __getitem__ / get / __contains__
    를 가로챈다. 어느 단계가 돌고 있는지는 field_provenance 와 같은 방식으로
    단계 함수를 감싸 안다. 읽힌 키를 (단계, 경로) 로 기록한다.

    dict 서브클래스를 쓰는 이유는 동작이 바뀌지 않기 때문이다. 이 저장소에는
    type(x) is dict / __class__ 비교 / deepcopy / pickle 이 하나도 없고
    타입 판정은 전부 isinstance 라 서브클래스가 그대로 통과한다.
    json.dump 도 dict 서브클래스를 일반 dict 로 직렬화한다.

이 관측이 보장하는 것과 못 하는 것
    보장    '읽혔다'는 확증이다. 기록이 있으면 그 단계가 실제로 읽었다.
    못 함   '안 읽혔다'는 확증이 아니다. 코드가 dict(block) 으로 복사하거나
            values() 로 훑으면 추적이 끊긴다. 그래서 미사용 판정은 이
            기록만으로 내리지 않고 값 통계와 함께 본다.
    범위    관측한 문서에 대해서만 참이다. 다른 문서에서만 도는 분기는
            보이지 않는다.

정확도 근거 (매 실행 자동 확인)
    감싼 실행과 감싸지 않은 실행의 final_debug.json 을 해시로 대조한다.
    추적이 결과를 바꾸지 않았음을 확인하지 못하면 기록을 신뢰하지 않는다.

사용
    python -m tools.audit.field_reads --json reads.json   # 기본 문서
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from tools.audit.documents import REPO_ROOT, enable_utf8_stdout

sys.path.insert(0, str(REPO_ROOT))
enable_utf8_stdout()

from hwpx_analysis import pipeline as pipeline_mod        # noqa: E402
from tools.audit.field_provenance import (                # noqa: E402
    RETURN_SLOT, STAGE_FUNCS, norm)

# 재감싸기를 어느 단계까지 할지.
#
# 감싸기는 dict 를 새 객체로 교체하므로, 같은 dict 를 두 곳이 가리키고 있으면
# 한쪽만 바뀌어 연결이 끊긴다. 그래서 실제로 공유 참조가 생기는 지점을 먼저
# 관측했다(객체를 바꾸지 않고 id 만 세는 방식).
#
#   1~13단계                        공유 0개
#   flatten_table_internal_blocks   공유 57개, 이후 유지
#     table_internal_blocks.internal_blocks[].paragraph_auto_labels[]
#     tables.analyzed[].preprocess.cells[].text.paragraph_auto_labels[]
#     (flatten 이 셀의 auto_labels 를 복사하지 않고 그대로 참조한다)
#
# 그래서 표/블록 재감싸기는 공유가 없는 구간까지만 한다. 이 구간에 hierarchy
# 생성(4단계)이 들어 있어 사각지대는 여기서 해소된다.
REWRAP_THROUGH = 'propagate_toc_anchor_depth'

# 지금 실행 중인 단계. 래퍼가 갱신한다.
CURRENT = {'stage': '(초기)'}

# (단계, 경로) -> 읽은 횟수
READS: dict[tuple[str, str], int] = Counter()

# 감싼 dict 가 몇 개인지. 추적 범위를 정직하게 보고하기 위해 센다.
WRAPPED = Counter()


class Tracked(dict):
    """읽기를 기록하는 dict. 값은 그대로 두고 접근만 관찰한다."""

    __slots__ = ('_path',)

    def __init__(self, data, path):
        super().__init__(data)
        self._path = path

    def _hit(self, key):
        READS[(CURRENT['stage'], norm(f"{self._path}.{key}"))] += 1

    def __getitem__(self, key):
        self._hit(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        self._hit(key)
        return super().get(key, default)

    def __contains__(self, key):
        self._hit(key)
        return super().__contains__(key)


def wrap(node, path, depth=0):
    """dict 를 Tracked 로 바꿔 끼운다. 리스트는 원소를 훑는다."""
    if depth > 14:
        return node
    if isinstance(node, dict):
        WRAPPED[norm(path)] += 1
        return Tracked(
            {k: wrap(v, f"{path}.{k}", depth + 1) for k, v in node.items()},
            path,
        )
    if isinstance(node, list):
        return [wrap(item, path + '[]', depth + 1) for item in node]
    return node


def wrap_in_place(container, path):
    """리스트 원소를 감싼 것으로 교체한다. 원본 리스트 객체는 유지한다."""
    for i, item in enumerate(container):
        container[i] = wrap(item, path)


def instrument(recorder_state: dict):
    """단계 함수를 감싸 현재 단계를 갱신하고, 상태가 생기면 추적을 건다."""
    originals = {}
    for name in STAGE_FUNCS:
        original = getattr(pipeline_mod, name)
        originals[name] = original

        def make(name=name, original=original, index=STAGE_FUNCS.index(name)):
            @functools.wraps(original)
            def wrapper(*args, **kwargs):
                CURRENT['stage'] = name
                out = original(*args, **kwargs)

                slot = RETURN_SLOT.get(name)
                if slot == 'analyzed':
                    recorder_state['analyzed'] = out
                elif slot == 'blocks':
                    recorder_state['blocks'] = out
                elif slot == 'table_internal':
                    wrap_in_place(out.internal_blocks,
                                  'table_internal_blocks.internal_blocks[]')
                    wrap_in_place(out.tables, 'table_internal_blocks.tables[]')
                    recorder_state['table_internal'] = out

                # 단계가 새로 만든 dict(hierarchy 등)는 이전 감싸기에 없다.
                # 공유 참조가 없는 구간에서는 매 단계 다시 감싸 추적한다.
                if index <= STAGE_FUNCS.index(REWRAP_THROUGH):
                    if 'analyzed' in recorder_state:
                        wrap_in_place(recorder_state['analyzed'],
                                      'tables.analyzed[]')
                    if 'blocks' in recorder_state:
                        wrap_in_place(recorder_state['blocks'].blocks,
                                      'blocks_document.blocks[]')
                return out
            return wrapper

        setattr(pipeline_mod, name, make())
    return originals


def restore(originals):
    for name, func in originals.items():
        setattr(pipeline_mod, name, func)


def _run(source: Path, out_root: Path) -> Path:
    import tools.run_document as run_document
    code = run_document.main([str(source), '--out', str(out_root)])
    if code != 0:
        sys.exit(f"문서 실행 실패: {source}")
    produced = list((out_root / 'results').glob('*/final_debug.json'))
    if not produced:
        sys.exit(f"산출물이 없습니다: {out_root}")
    return produced[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description="필드 읽기 단계 관측")
    ap.add_argument('source', nargs='?', default=str(DEFAULT_SOURCE))
    ap.add_argument('--out', default=None)
    ap.add_argument('--json', default=None, help="읽기 기록 저장")
    args = ap.parse_args(argv)

    source = Path(args.source)
    if not source.exists():
        sys.exit(f"문서를 찾을 수 없습니다: {source}")

    tmp = Path(args.out or tempfile.mkdtemp(prefix='reads_'))
    work = tmp / 'run'

    # summary 에 절대 경로가 들어가므로 같은 디렉토리에 두 번 돌려야 비교된다.
    print(f"[1/2] 기준 실행 (추적 없음) - {source.name}")
    baseline = _run(source, work).read_bytes()

    print("[2/2] 추적 실행")
    state: dict = {}
    originals = instrument(state)
    try:
        produced = _run(source, work)
    finally:
        restore(originals)

    print()
    print("=" * 96)
    print("추적 무해성 확인")
    print("=" * 96)
    a = hashlib.sha256(produced.read_bytes()).hexdigest()
    b = hashlib.sha256(baseline).hexdigest()
    print(f"  추적 실행 {a[:16]}")
    print(f"  기준 실행 {b[:16]}")
    print(f"  -> {'동일 - 추적이 결과를 바꾸지 않았다' if a == b else '다름 - 신뢰 불가'}")
    if a != b:
        sys.exit(1)

    print()
    print("=" * 96)
    print("추적 범위")
    print("=" * 96)
    print(f"  감싼 dict {sum(WRAPPED.values())}개 / 경로 {len(WRAPPED)}종")
    for p, c in WRAPPED.most_common(8):
        print(f"    {p[:64]:64s} {c}개")

    by_path: dict[str, set[str]] = defaultdict(set)
    for (stage, path), _n in READS.items():
        by_path[path].add(stage)

    print()
    print("=" * 96)
    print("단계별 읽은 필드 수")
    print("=" * 96)
    per_stage = Counter(stage for (stage, _p) in READS)
    for name in STAGE_FUNCS:
        if per_stage.get(name):
            print(f"  {name:38s} {per_stage[name]:5d}종")

    print()
    print("=" * 96)
    print(f"읽힌 것으로 관측된 경로 {len(by_path)}개")
    print("=" * 96)
    for path in sorted(by_path)[:40]:
        print(f"  {path[:62]:62s} {', '.join(sorted(by_path[path]))[:60]}")
    if len(by_path) > 40:
        print(f"  ... 외 {len(by_path)-40}개")

    if args.json:
        payload = {
            'source': str(source),
            'reads': {p: sorted(s) for p, s in sorted(by_path.items())},
            'wrapped': dict(WRAPPED),
        }
        Path(args.json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n-> {args.json} 저장")
    return 0


if __name__ == '__main__':
    sys.exit(main())
