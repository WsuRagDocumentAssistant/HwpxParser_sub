"""final_debug.json 필드 인벤토리.

동적 키 판정
  '키 종류가 많다'가 아니라 '인스턴스마다 키가 달라진다'로 본다.
  고정 스키마는 모든 인스턴스에 같은 키가 나오므로 키 출현율이 높다.
  데이터 키(컬럼명, id, 분포 맵)는 인스턴스마다 달라 출현율이 낮다.

    동적키 = (키 종류 > 30) and (키 출현율 중앙값 < 0.2)

  출현율을 보지 않고 키 종류만 세면 선택적 필드를 가진 고정 스키마
  (summary, depth_correction)까지 접혀서 필드가 통째로 사라진다.
  아래 '검증' 절이 그 경계를 지킨다.

children[] 재귀는 같은 스키마이므로 부모 경로로 접는다.
"""

import json
import statistics
from collections import Counter, defaultdict

from tools.audit.documents import enable_utf8_stdout, resolve

enable_utf8_stdout()

MAX_DEPTH = 14
DYNAMIC_KEY_KINDS = 30      # 이보다 키 종류가 많고
DYNAMIC_KEY_RATE = 0.2      # 출현율 중앙값이 이보다 낮으면 동적 키

# 접기 판정이 뒤집히지 않았는지 확인하는 기준. 구조를 아는 경로만 골랐다.
KNOWN = [
    ('blocks_document.blocks[]', False, '고정 스키마여야 함'),
    ('tables.analyzed[].preprocess.cells[]', False, '고정 스키마여야 함'),
    ('table_internal_blocks.internal_blocks[]', False, '고정 스키마여야 함'),
    ('summary', False, '고정 스키마여야 함 (선택 필드 있음)'),
    ('blocks_document.blocks[].depth_correction', False, '고정 스키마여야 함 (선택 필드 있음)'),
    ('tables.analyzed[].hierarchy.structured_records[].values', True, '동적 키여야 함'),
    ('tables.analyzed[].hierarchy.structured_records[].source_cell_ids', True, '동적 키여야 함'),
]

SECTIONS = ['summary', 'tables', 'blocks_document', 'table_internal_blocks',
            'warnings', 'quality_report']


def norm(path):
    while '.children[].' in path:
        path = path.replace('.children[].', '.', 1)
    return path.replace('.children[]', '')


def tname(v):
    if v is None:
        return 'null'
    for t, n in ((bool, 'bool'), (int, 'int'), (float, 'float'),
                 (str, 'str'), (list, 'list'), (dict, 'dict')):
        if isinstance(v, t):
            return n
    return type(v).__name__


def find_dynamic_paths(payloads):
    """1차 순회 - 경로별 인스턴스 수와 키 출현 횟수로 동적 키를 가린다."""
    inst = Counter()
    keyhit = defaultdict(Counter)

    def walk(node, path, depth=0):
        if depth > MAX_DEPTH:
            return
        if isinstance(node, dict):
            p = norm(path)
            inst[p] += 1
            for k, v in node.items():
                keyhit[p][k] += 1
                walk(v, f"{path}.{k}" if path else k, depth + 1)
        elif isinstance(node, list):
            for item in node:
                walk(item, f"{path}[]", depth + 1)

    for payload in payloads:
        walk(payload, '')

    dynamic = set()
    for p, ks in keyhit.items():
        n = inst[p]
        if n == 0 or len(ks) <= DYNAMIC_KEY_KINDS:
            continue
        if statistics.median([c / n for c in ks.values()]) < DYNAMIC_KEY_RATE:
            dynamic.add(p)
    return dynamic, inst, keyhit


def inventory(payloads, labels, dynamic):
    """2차 순회 - 경로별 문서별 출현 횟수/타입/예시."""
    seen = defaultdict(lambda: defaultdict(int))
    types = defaultdict(set)
    nonnull = defaultdict(int)
    sample = {}

    def walk(node, path, doc, depth=0):
        if depth > MAX_DEPTH:
            return
        if isinstance(node, dict):
            p = norm(path)
            if p in dynamic:
                key = f"{p}.{{동적키}}"
                seen[key][doc] += len(node)
                for v in node.values():
                    types[key].add(tname(v))
                    if v not in (None, [], {}):
                        nonnull[key] += 1
                    if key not in sample and isinstance(v, (str, int, float, bool)):
                        sample[key] = str(v)[:38]
                return
            for k, v in node.items():
                full = f"{path}.{k}" if path else k
                np_ = norm(full)
                seen[np_][doc] += 1
                types[np_].add(tname(v))
                if v not in (None, [], {}):
                    nonnull[np_] += 1
                if np_ not in sample and isinstance(v, (str, int, float, bool)) and v is not None:
                    sample[np_] = str(v)[:38]
                walk(v, full, doc, depth + 1)
        elif isinstance(node, list):
            for item in node:
                walk(item, f"{path}[]", doc, depth + 1)

    for payload, label in zip(payloads, labels):
        walk(payload, '', label)
    return seen, types, nonnull, sample


def main():
    documents = resolve()
    labels = [d.label for d in documents]
    payloads = [json.load(open(d.final_debug, encoding='utf-8')) for d in documents]

    dynamic, inst, keyhit = find_dynamic_paths(payloads)
    seen, types, nonnull, sample = inventory(payloads, labels, dynamic)

    print(f"필드 경로 {len(seen)}개 (문서 {len(documents)}종 합집합)")
    print(f"동적 키로 접은 경로 {len(dynamic)}개:")
    for p in sorted(dynamic):
        print(f"    {p}  (키 {len(keyhit[p])}종, 인스턴스 {inst[p]})")
    print()

    print("=" * 100)
    print("검증 - 알려진 구조 대조")
    print("=" * 100)
    failed = 0
    for path, want_dynamic, expect in KNOWN:
        ok = (path in dynamic) == want_dynamic
        failed += not ok
        print(f"  [{'OK ' if ok else 'NG '}] {path:62s} {expect}")
    if failed:
        print(f"  -> {failed}건 어긋남. 접기 임계값이 이 문서 조합에 맞지 않는다.")
    print()

    sections = defaultdict(list)
    for p in seen:
        sections[p.split('.')[0].split('[')[0]].append(p)

    head = ' '.join(f"{lab[:6]:>6s}" for lab in labels)
    for root in SECTIONS:
        paths = sorted(sections.get(root, []))
        print("=" * 100)
        print(f"[{root}]  필드 {len(paths)}개")
        print("=" * 100)
        print(f"  {'경로':58s} {'타입':15s} {head}  예시")
        for p in paths:
            counts = ' '.join(f"{seen[p].get(lab, 0):6d}" for lab in labels)
            print(f"  {p[:58]:58s} {'/'.join(sorted(types[p]))[:14]:15s} "
                  f"{counts}  {sample.get(p, '')[:30]}")
        print()

    uneven = [(p, [lab for lab in labels if seen[p].get(lab, 0) > 0])
              for p in seen
              if len([lab for lab in labels if seen[p].get(lab, 0) > 0]) < len(labels)]
    print("=" * 100)
    print(f"문서마다 출현이 갈리는 필드 {len(uneven)}개")
    print("=" * 100)
    for p, present in sorted(uneven):
        print(f"  {p[:72]:72s} {', '.join(present)}")

    empty = sorted(p for p in seen if nonnull[p] == 0)
    print("\n" + "=" * 100)
    print(f"항상 비어 있는 필드 {len(empty)}개")
    print("=" * 100)
    for p in empty:
        print(f"  {p}")


if __name__ == '__main__':
    main()
