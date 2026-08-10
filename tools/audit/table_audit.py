"""표 분류/구조화 검증. 기준은 section*.xml 원본.

XML이 제공하는 권위 있는 신호:
  hp:tbl@rowCnt/@colCnt   - 표 크기 선언
  hp:tc@header="1"        - 저자가 선언한 헤더 셀
  hp:cellAddr@rowAddr/colAddr, hp:cellSpan - 좌표/병합

산출물을 산출물로 검증하면 같은 실수를 두 번 반복하게 되므로 대조 기준은
반드시 원본 XML이다. 압축 해제 결과가 없는 문서는 건너뛴다.
"""

import glob
import json
import xml.etree.ElementTree as ET
from collections import Counter

from tools.audit.documents import enable_utf8_stdout, require_contents, resolve

enable_utf8_stdout()


def sorted_counts(counter):
    """set 순회 순서에 따라 출력이 흔들리지 않게 정렬해 돌려준다."""
    return {k: counter[k] for k in sorted(counter, key=lambda x: (x is None, x))}


def ln(t):
    return t.split('}', 1)[1] if '}' in t else t


def xml_tables(contents_dir):
    """hp:tbl@id -> {size, cells, header_rows, header_cols}"""
    out = {}
    for f in glob.glob(str(contents_dir / 'section*.xml')):
        root = ET.parse(f).getroot()
        for tbl in root.iter():
            if ln(tbl.tag) != 'tbl':
                continue
            tid = tbl.attrib.get('id')
            rows = int(tbl.attrib.get('rowCnt') or 0)
            cols = int(tbl.attrib.get('colCnt') or 0)
            cells = []
            hdr_rows, hdr_cols = set(), set()
            for tr in tbl:
                if ln(tr.tag) != 'tr':
                    continue
                for tc in tr:
                    if ln(tc.tag) != 'tc':
                        continue
                    addr = span = None
                    for c in tc:
                        if ln(c.tag) == 'cellAddr':
                            addr = (int(c.attrib.get('rowAddr') or 0),
                                    int(c.attrib.get('colAddr') or 0))
                        elif ln(c.tag) == 'cellSpan':
                            span = (int(c.attrib.get('rowSpan') or 1),
                                    int(c.attrib.get('colSpan') or 1))
                    is_hdr = tc.attrib.get('header') in ('1', 'true', 'True')
                    cells.append((addr, span, is_hdr))
                    if is_hdr and addr:
                        for r in range(addr[0], addr[0] + (span[0] if span else 1)):
                            hdr_rows.add(r)
                        for c2 in range(addr[1], addr[1] + (span[1] if span else 1)):
                            hdr_cols.add(c2)
            out[tid] = {
                'rows': rows, 'cols': cols, 'cells': cells,
                'declared_header_rows': hdr_rows, 'declared_header_cols': hdr_cols,
                'has_declared': any(h for _, _, h in cells),
            }
    return out


def analyzed_tables(final_debug_path):
    fd = json.load(open(final_debug_path, encoding='utf-8'))
    out = {}

    def walk(t):
        ident = (t.get('preprocess') or {}).get('identity') or {}
        h = t.get('hierarchy') or {}
        struct = (t.get('preprocess') or {}).get('structure') or {}
        layout = (t.get('preprocess') or {}).get('layout') or {}
        out[ident.get('xml_table_id')] = {
            'table_id': t.get('table_id'),
            'type': h.get('table_type'),
            'header_rows': set(h.get('header_rows') or []),
            'header_cols': set(h.get('header_cols') or []),
            'record_status': h.get('record_status'),
            'columns': len(h.get('columns') or []),
            'records': len(h.get('structured_records') or []),
            'rows': layout.get('row_count'), 'cols': layout.get('col_count'),
            'origin_cells': struct.get('origin_cell_count'),
            'owner': ((t.get('preprocess') or {}).get('nesting') or {}).get('owner_control_type'),
        }
        for c in t.get('children') or []:
            walk(c)

    for t in fd['tables']['analyzed']:
        walk(t)
    return out


def report(label, contents_dir, final_debug_path):
    print(f"\n{'='*74}\n{label}\n{'='*74}")
    x = xml_tables(contents_dir)
    a = analyzed_tables(final_debug_path)
    print(f"XML 표 {len(x)}개 / 분석 표 {len(a)}개 / id 매칭 {len(set(x) & set(a))}개")

    # --- 1) 크기 선언 대조 ---
    size_bad = [tid for tid in set(x) & set(a)
                if (x[tid]['rows'], x[tid]['cols']) != (a[tid]['rows'], a[tid]['cols'])]
    print(f"[구조] rowCnt/colCnt 불일치: {len(size_bad)}개")

    # --- 2) 분류 분포 ---
    print(f"[분류] table_type 분포: {sorted_counts(Counter(v['type'] for v in a.values()))}")

    # --- 3) 저자 선언 헤더 유무별 분류 ---
    with_hdr = {tid for tid in set(x) & set(a) if x[tid]['has_declared']}
    without = (set(x) & set(a)) - with_hdr
    print(f"[분류] tc@header 선언 있는 표 {len(with_hdr)}개 -> "
          f"{sorted_counts(Counter(a[t]['type'] for t in with_hdr))}")
    print(f"[분류] 선언 없는 표 {len(without)}개 -> "
          f"{sorted_counts(Counter(a[t]['type'] for t in without))}")

    # --- 4) 헤더 판정 정확도 (선언이 있는 표만) ---
    exact = subset = superset = disjoint = empty_detect = 0
    examples = []
    for tid in sorted(with_hdr):
        d = x[tid]['declared_header_rows']
        got = a[tid]['header_rows']
        if not got:
            empty_detect += 1
            if len(examples) < 4:
                examples.append(('미검출', tid, d, got, a[tid]['type']))
        elif got == d:
            exact += 1
        elif got < d:
            subset += 1
            if len(examples) < 4:
                examples.append(('부족', tid, d, got, a[tid]['type']))
        elif got > d:
            superset += 1
        else:
            disjoint += 1
            if len(examples) < 4:
                examples.append(('불일치', tid, d, got, a[tid]['type']))
    print(f"[헤더] 선언 있는 표 {len(with_hdr)}개 기준 header_rows 판정:")
    print(f"        정확 {exact} / 과소 {subset} / 과대 {superset} / "
          f"불일치 {disjoint} / 미검출 {empty_detect}")
    for kind, tid, d, got, tp in examples:
        print(f"        - {kind}: id={tid} type={tp} 선언행={sorted(d)} 검출행={sorted(got)}")

    # --- 5) 선언 없는 data_table의 헤더 검출 (근거 없는 헤더 부여 여부) ---
    dt_wo = [t for t in without if a[t]['type'] == 'data_table']
    got_hdr = [t for t in dt_wo if a[t]['header_rows']]
    print(f"[헤더] 선언 없는 data_table {len(dt_wo)}개 중 header_rows 부여됨: {len(got_hdr)}개")

    # --- 6) 구조화 산출 ---
    dt = [v for v in a.values() if v['type'] == 'data_table']
    print(f"[구조화] data_table {len(dt)}개: record_status="
          f"{sorted_counts(Counter(v['record_status'] for v in dt))}")
    print(f"         columns 생성됨 {sum(1 for v in dt if v['columns'])}개, "
          f"structured_records 있는 표 {sum(1 for v in dt if v['records'])}개")

    # --- 7) 선언 헤더 셀이 분류상 어디에 있나 (title_box 등으로 새는지) ---
    leaked = [t for t in with_hdr if a[t]['type'] in ('title_box', 'caption_or_note_table')]
    print(f"[분류] 선언 헤더가 있는데 title_box/caption으로 분류된 표: {len(leaked)}개")


def main():
    for doc in require_contents(resolve()):
        report(doc.label, doc.contents_dir, doc.final_debug)


if __name__ == '__main__':
    main()
