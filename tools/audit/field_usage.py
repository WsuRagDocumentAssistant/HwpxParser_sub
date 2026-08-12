"""각 필드가 무엇이고 최종 결과로 쓸 값인지, 관측된 근거로만 분류한다.

근거는 셋이고 전부 실행에서 나온다. 이름 매칭으로 추측하지 않는다.
  1. 출처  field_provenance  어느 단계가 만들고 어느 단계가 고쳤는가
  2. 소비  field_reads       어느 단계가 실제로 읽었는가
  3. 값    final_debug.json  인스턴스 수, 서로 다른 값의 수, 빈 값 비율

분류
  진단          warnings / quality_report 아래. 결과가 아니라 점검 기록이다.
  산출물기여    generate_llm_context 또는 generate_depth_text_preview 가 읽었다.
                사람과 LLM이 보는 텍스트가 이 값에서 나온다.
  알고리즘입력  생성 단계보다 뒤의 단계가 읽었다. 결과를 만드는 데 쓰인다.
  무정보(항상빔) 모든 인스턴스가 비어 있다.
  무정보(상수)  서로 다른 값이 하나뿐이라 구분에 쓸 수 없다.
  읽기미관측    읽는 것을 보지 못했다. '안 쓰인다'가 아니다.

'읽기미관측' 을 미사용으로 읽으면 안 되는 이유
  추적은 dict 접근을 가로채는 방식이라, 코드가 dict(x) 로 복사하거나
  values() 로 훑으면 기록이 끊긴다. 그리고 관측한 문서에 없는 분기는
  애초에 돌지 않는다. 그래서 이 칸은 '미사용'이 아니라 '판정 보류'다.
  버릴지 말지는 값 통계와 함께 사람이 정해야 한다.

사용
    python -m tools.audit.field_provenance sample.zip --json prov.json
    python -m tools.audit.field_reads      sample.zip --json reads.json
    python -m tools.audit.field_usage prov.json reads.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from tools.audit.documents import enable_utf8_stdout, resolve

enable_utf8_stdout()

ARTIFACT_STAGES = {'generate_llm_context', 'generate_depth_text_preview'}
DIAGNOSTIC_ROOTS = {'warnings', 'quality_report'}
MAX_DISTINCT = 5000


def norm(path: str) -> str:
    while '.children[].' in path:
        path = path.replace('.children[].', '.', 1)
    return path.replace('.children[]', '')


def collect_values(payload):
    """경로별 값 통계. 다른 감사 도구와 같은 정규화를 쓴다."""
    stats: dict[str, dict] = defaultdict(
        lambda: {'n': 0, 'empty': 0, 'distinct': set(), 'sample': None})

    def walk(node, path, depth=0):
        if depth > 14 or not isinstance(node, (dict, list)):
            return
        if isinstance(node, list):
            for item in node:
                walk(item, path + '[]', depth + 1)
            return
        for key, value in node.items():
            full = f"{path}.{key}" if path else key
            s = stats[norm(full)]
            s['n'] += 1
            if value is None or (isinstance(value, (list, dict, str)) and not value):
                s['empty'] += 1
            else:
                # 컨테이너도 세야 한다. 스칼라만 세면 header_rows 나
                # structured_records 처럼 리스트로 담기는 핵심 결과가
                # '서로 다른 값 0개'가 되어 상수로 오분류된다.
                if len(s['distinct']) < MAX_DISTINCT:
                    if isinstance(value, (list, dict)):
                        s['distinct'].add(
                            json.dumps(value, ensure_ascii=False,
                                       sort_keys=True)[:400])
                    else:
                        s['distinct'].add(value)
                if s['sample'] is None:
                    s['sample'] = str(value)[:34]
            walk(value, full, depth + 1)

    walk(payload, '')
    return stats


def classify(path, stat, readers, birth, stage_order):
    root = path.split('.')[0].split('[')[0]
    if root in DIAGNOSTIC_ROOTS:
        return '진단'
    if readers & ARTIFACT_STAGES:
        return '산출물기여'

    n, empty = stat['n'], stat['empty']
    if n and empty == n:
        return '무정보(항상빔)'

    after = [r for r in readers
             if stage_order.get(r, -1) > stage_order.get(birth, -1)]
    if after:
        return '알고리즘입력'

    if n > 1 and len(stat['distinct']) <= 1:
        return '무정보(상수)'
    if readers:
        return '알고리즘입력'
    return '읽기미관측'


def main(argv=None):
    ap = argparse.ArgumentParser(description="필드 의미/유의미성 분류")
    ap.add_argument('provenance', help="field_provenance --json 산출")
    ap.add_argument('reads', help="field_reads --json 산출")
    ap.add_argument('--doc', default=None, help="대상 결과 디렉토리")
    ap.add_argument('--json', default=None, help="분류 결과 저장")
    args = ap.parse_args(argv)

    prov = json.loads(Path(args.provenance).read_text(encoding='utf-8'))
    reads = json.loads(Path(args.reads).read_text(encoding='utf-8'))
    stage_order = {name: i for i, name in enumerate(prov['stage_order'])}
    read_map = {p: set(s) for p, s in reads['reads'].items()}

    # None 을 넘기면 resolve 가 sys.argv 를 다시 읽어 이 도구의 인자를
    # 문서 경로로 오해한다. 빈 리스트를 넘겨 기본 탐색을 시킨다.
    doc = resolve([args.doc] if args.doc else [])[0]
    stats = collect_values(json.loads(doc.final_debug.read_text(encoding='utf-8')))

    rows = []
    for path, info in sorted(prov['fields'].items()):
        stat = stats.get(path, {'n': 0, 'empty': 0, 'distinct': set(), 'sample': None})
        readers = read_map.get(path, set())
        rows.append({
            'path': path,
            'kind': classify(path, stat, readers, info['birth'], stage_order),
            'birth': info['birth'],
            'writers': info['writers'],
            'readers': sorted(readers),
            'n': stat['n'],
            'empty': stat['empty'],
            'distinct': len(stat['distinct']),
            'sample': stat['sample'],
        })

    print("=" * 104)
    print(f"필드 {len(rows)}개 분류   문서: {doc.label}")
    print("=" * 104)
    for kind, count in Counter(r['kind'] for r in rows).most_common():
        print(f"  {kind:16s} {count:5d}개")
    print()
    print("  '읽기미관측' 은 미사용이 아니라 판정 보류다. 추적은 dict 접근을")
    print("  가로채므로 복사/일괄순회는 기록되지 않고, 이 문서에 없는 분기는")
    print("  돌지 않는다.")

    sections = defaultdict(list)
    for r in rows:
        sections[r['path'].split('.')[0].split('[')[0]].append(r)

    for root in ['summary', 'tables', 'blocks_document', 'table_internal_blocks',
                 'warnings', 'quality_report']:
        group = sections.get(root, [])
        if not group:
            continue
        print()
        print("=" * 104)
        print(f"[{root}]  {len(group)}개  "
              f"{dict(Counter(r['kind'] for r in group).most_common())}")
        print("=" * 104)
        for r in sorted(group, key=lambda x: (x['kind'], x['path'])):
            readers = ','.join(s[:18] for s in r['readers'][:2])
            print(f"  {r['path'][:56]:56s} {r['kind']:14s} "
                  f"n={r['n']:<6d} 값{r['distinct']:<5d} {readers[:38]}")

    print()
    print("=" * 104)
    print("최종 결과 후보 (산출물기여 + 알고리즘입력)")
    print("=" * 104)
    keep = [r for r in rows if r['kind'] in ('산출물기여', '알고리즘입력')]
    for r in sorted(keep, key=lambda x: x['path']):
        print(f"  {r['path'][:60]:60s} {r['kind']:12s} {r['birth']}")
    print(f"  합계 {len(keep)}개")

    if args.json:
        Path(args.json).write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n-> {args.json} 저장")
    return 0


if __name__ == '__main__':
    sys.exit(main())
