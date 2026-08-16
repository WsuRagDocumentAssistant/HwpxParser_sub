"""산출물 값을 원본의 바로 그 노드와 1:1로 맞춰 본다.

도메인 포함은 '이 값이 그 속성의 값 집합 안에 있다'까지만 말한다. 값이
열거형이면 그것만으로는 어느 속성에서 왔는지 가려지지 않는다. 표 계열
컬럼에는 식별자가 있으므로 거기까지 가지 않아도 된다.

    표   xml_table_id            <-> hp:tbl@id
    셀   position.row_addr/col_addr <-> hp:cellAddr@rowAddr/colAddr

이 키로 이으면 '이 표 이 셀의 그 속성'과 직접 비교할 수 있다. 도메인
멤버십이 아니라 인스턴스 대응이므로, 값이 CENTER 하나뿐이어도 출처를
말할 수 있다.

원본 범위는 source_index 와 같다(section*.xml). masterpage 는 본문 추출
대상이 아니라 제외한다.

사용
    python -m tools.audit.instance_join
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from .documents import enable_utf8_stdout, resolve
from .source_index import local

enable_utf8_stdout()

# 산출물 경로 -> (조인 범위, 원본에서 읽을 요소/속성)
#
# 셀 범위는 hp:tc 안의 hp:subList 속성, 표 범위는 hp:tbl 자신의 속성이다.
CELL_COLUMNS = {
    'sublist.vert_align': ('subList', 'vertAlign'),
    'sublist.line_wrap': ('subList', 'lineWrap'),
    'sublist.text_direction': ('subList', 'textDirection'),
    'sublist.link_list_id_ref': ('subList', 'linkListIDRef'),
    'sublist.link_list_next_id_ref': ('subList', 'linkListNextIDRef'),
    'sublist.text_width': ('subList', 'textWidth'),
    'sublist.text_height': ('subList', 'textHeight'),
}
TABLE_COLUMNS = {
    'layout.text_wrap': ('tbl', 'textWrap'),
    'layout.text_flow': ('tbl', 'textFlow'),
    'layout.page_break': ('tbl', 'pageBreak'),
    'layout.repeat_header': ('tbl', 'repeatHeader'),
    'layout.cell_spacing': ('tbl', 'cellSpacing'),
}


def read_source(contents_dir: Path):
    """xml_table_id -> {'attrs': {...}, 'cells': {(row, col): {속성}}}"""
    tables: dict[str, dict] = {}
    for f in sorted(glob.glob(str(contents_dir / 'section*.xml'))):
        for tbl in ET.parse(f).getroot().iter():
            if local(tbl.tag) != 'tbl':
                continue
            tid = tbl.attrib.get('id')
            cells: dict[tuple[int, int], dict] = {}
            for tr in tbl:
                if local(tr.tag) != 'tr':
                    continue
                for tc in tr:
                    if local(tc.tag) != 'tc':
                        continue
                    addr = None
                    sub = None
                    for child in tc:
                        name = local(child.tag)
                        if name == 'cellAddr':
                            addr = (int(child.attrib.get('rowAddr') or 0),
                                    int(child.attrib.get('colAddr') or 0))
                        elif name == 'subList':
                            sub = {local(k): v for k, v in child.attrib.items()}
                    if addr is not None:
                        cells[addr] = {'subList': sub or {}}
            tables[tid] = {
                'attrs': {local(k): v for k, v in tbl.attrib.items()},
                'cells': cells,
            }
    return tables


def grade_mapping(pairs):
    """(원본값, 산출물값) 쌍에서 대응 관계를 도출한다.

    접힘 규칙을 손으로 적어 두지 않는다. 상수표로 두면 이 문서에서 관측한
    매핑을 코드에 박는 셈이라, 다른 문서에서 다른 대응이 나와도 표가 덮어써
    조용히 통과시킨다. 대응은 측정 결과로 나와야 한다.

        함수다   한 원본 값이 항상 같은 산출물 값으로 간다   -> 일치
        단사가 아니다  서로 다른 원본 값이 같은 산출물 값으로 -> 손실 있음
        함수가 아니다  같은 원본 값이 서로 다른 값으로        -> 불일치

    hp:tbl@pageBreak 이 그 예다. CELL/TABLE -> true, NONE -> false 로 함수이지만
    단사가 아니다. 값은 원본과 맞지만 true 를 받은 쪽은 CELL 인지 TABLE 인지
    복원할 수 없다.
    """
    mapping = defaultdict(Counter)
    for source, artifact in pairs:
        mapping[source][artifact] += 1

    ambiguous = {s: dict(c) for s, c in mapping.items() if len(c) > 1}
    if ambiguous:
        return {
            'grade': '불일치',
            'lossy': False,
            'mapping': {s: dict(c) for s, c in mapping.items()},
            'ambiguous': ambiguous,
            'total': len(pairs),
        }

    images = [next(iter(c)) for c in mapping.values()]
    lossy = len(set(map(str, images))) < len(mapping)
    return {
        'grade': '일치',
        'lossy': lossy,
        'mapping': {s: next(iter(c)) for s, c in mapping.items()},
        'ambiguous': {},
        'total': len(pairs),
    }


def dig(node, dotted):
    for part in dotted.split('.'):
        node = (node or {}).get(part)
        if node is None:
            return None
    return node


def main(argv=None):
    ap = argparse.ArgumentParser(description="표/셀 컬럼을 원본 노드와 1:1 대조")
    ap.add_argument('--doc', default=None)
    ap.add_argument('--json', default=None)
    args = ap.parse_args(argv)

    doc = resolve([args.doc] if args.doc else [])[0]
    if not doc.contents_dir:
        sys.exit("원본 XML 이 없어 대조할 수 없습니다.")
    source = read_source(doc.contents_dir)
    payload = json.loads(doc.final_debug.read_text(encoding='utf-8'))

    tables = []

    def walk(t):
        tables.append(t)
        for c in t.get('children') or []:
            walk(c)

    for t in payload['tables']['analyzed']:
        walk(t)

    print(f"원본 표 {len(source)}개 / 산출물 표 {len(tables)}개")

    result = {}
    for column, (_elem, attr) in TABLE_COLUMNS.items():
        pairs, unjoined = [], 0
        for t in tables:
            pre = t.get('preprocess') or {}
            src = source.get((pre.get('identity') or {}).get('xml_table_id'))
            if src is None:
                unjoined += 1
                continue
            pairs.append((src['attrs'].get(attr), dig(pre, column)))
        entry = grade_mapping(pairs)
        entry['unjoined'] = unjoined
        result[f'tables.analyzed[].preprocess.{column}'] = entry

    for column, (_elem, attr) in CELL_COLUMNS.items():
        pairs, unjoined = [], 0
        for t in tables:
            pre = t.get('preprocess') or {}
            src = source.get((pre.get('identity') or {}).get('xml_table_id'))
            for cell in pre.get('cells') or []:
                pos = cell.get('position') or {}
                cs = (src or {}).get('cells', {}).get(
                    (pos.get('row_addr'), pos.get('col_addr')))
                if cs is None:
                    unjoined += 1
                    continue
                pairs.append((cs['subList'].get(attr), dig(cell, column)))
        entry = grade_mapping(pairs)
        entry['unjoined'] = unjoined
        result[f'tables.analyzed[].preprocess.cells[].{column}'] = entry

    print()
    print("=" * 92)
    print("인스턴스 1:1 대조")
    print("=" * 92)
    for path, entry in result.items():
        mark = entry['grade'] + ('·손실' if entry['lossy'] else '')
        shown = entry['mapping'] if len(entry['mapping']) <= 6 else \
            f"{len(entry['mapping'])}종 대응"
        print(f"  [{mark:8s}] {path[-52:]:52s} "
              f"{entry['total']}건 조인실패 {entry['unjoined']}  {shown}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n-> {args.json} 저장")
    return 0


if __name__ == '__main__':
    sys.exit(main())
