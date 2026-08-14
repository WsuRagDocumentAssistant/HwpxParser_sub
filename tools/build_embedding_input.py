#================================================
# tools/build_embedding_input.py
#
# 임베딩 입력 산출물을 만든다.
#
# final_debug.json 에서 구조를 믿을 수 없는 표를 빼고, 목차 표는 (텍스트, depth)
# 항목으로 그 자리에 전개한 산출물을 따로 쓴다. 파이프라인은 건드리지 않는다.
# 원본 final_debug.json 은 그대로 두므로 이 파일을 지우면 되돌릴 수 있다.
#
# 왜 저장 직전 후처리인가
#   표를 depth 단계 앞에서 빼면 add_table_hierarchy_ref_to_blocks 와
#   correct_title_box_depths 가 보던 표가 사라져 depth 가 달라진다. 그래서 모든
#   depth 단계가 끝난 산출물을 입력으로 받아 거른다.
#
# 판정 기준에 임계값과 문자열 상수를 쓰지 않는다
#   전부 셀 좌표·병합 정보·파이프라인 분류에서 파생되는 술어다.
#
# 사용:
#   python tools/build_embedding_input.py                      # 기본 문서
#   python tools/build_embedding_input.py --doc <결과폴더>
#   python tools/build_embedding_input.py --out <경로>
#   python tools/build_embedding_input.py --dry-run            # 쓰지 않고 보고만
#================================================

from __future__ import annotations

import argparse
import collections
import copy
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hwpx_analysis.add_toc_depth0_anchors import iter_toc_entry_levels  # noqa: E402

# 산출물에 남아도 되는 '빠진 표 id' 경로. 전부 출처 기록이다.
ALLOWED_ID_PATHS = ('.excluded_table.', '.structure_features.', '.toc_source_table_ids')

one = lambda s: re.sub(r'\s+', ' ', s or '').strip()  # noqa: E731


# ---------------------------------------------------------------- 조회 헬퍼

def index_tables(payload):
    """xml_table_id -> 표 노드. analyzed 트리만 본다(body_linking 은 사본이다)."""
    out = {}

    def walk(node):
        if isinstance(node, dict):
            if 'hierarchy' in node and 'preprocess' in node:
                tid = (node['preprocess'] or {}).get('identity', {}).get('xml_table_id')
                out[str(tid)] = node
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(payload['tables'])
    return out


def cell_text(cell):
    text = cell.get('text')
    return text.get('text', '') if isinstance(text, dict) else (text or '')


def cells_of(table):
    return (table.get('preprocess') or {}).get('cells') or []


def table_chars(table):
    return sum(len(cell_text(c)) for c in cells_of(table))


def owner_table_id(block):
    """internal 블록이 '직접' 속한 표. root 가 아니다."""
    raw = block.get('source_table_id') or block.get('root_table_id') or ''
    return str(raw).split('_')[-1]


# ---------------------------------------------------------------- 판정 술어

def gridness(table):
    """격자인가. 2개 이상의 행이 각각 2개 이상의 열을 채우면 격자다.

    임계값이 아니라 구조 판정이다. 격자가 아니면 열 헤더 개념이 성립하지 않으므로
    산문 컨테이너로 본다.
    """
    filled = [((c.get('position') or {}).get('row_addr'),
               (c.get('position') or {}).get('col_addr'))
              for c in cells_of(table) if cell_text(c).strip()]
    if not filled:
        return 'empty'
    rows = collections.defaultdict(set)
    for row, col in filled:
        rows[row].add(col)
    if len(rows) < 2 or len({col for _, col in filled}) < 2:
        return 'degenerate'
    if len([r for r, cols in rows.items() if len(cols) >= 2]) < 2:
        return 'degenerate'
    return 'grid'


def merge_cover(table):
    """병합된 칸이 덮는 좌표 -> 그 칸의 값."""
    cover = {}
    for cell in cells_of(table):
        pos = cell.get('position') or {}
        try:
            row = int(pos.get('row_addr'))
            col = int(pos.get('col_addr'))
            row_span = int(pos.get('row_span') or 1)
            col_span = int(pos.get('col_span') or 1)
        except (TypeError, ValueError):
            continue
        if row_span > 1 or col_span > 1:
            value = one(cell_text(cell))
            for dr in range(row_span):
                for dc in range(col_span):
                    if dr or dc:
                        cover[(row + dr, col + dc)] = value
    return cover


def records_complete(table):
    """레코드의 모든 값이 채워지는가. 빈칸은 병합 값으로 메워 본다.

    빈칸의 대부분은 세로 병합 때문이지 결손이 아니다. 병합을 반영하지 않으면
    멀쩡한 표가 불완전으로 잡힌다.
    """
    hierarchy = table['hierarchy'] or {}
    records = hierarchy.get('structured_records') or []
    if not records:
        return False
    cover = merge_cover(table)
    name_to_index = {}
    for column in hierarchy['columns']:
        name_to_index.setdefault(column['name'], column['col_index'])
    for record in records:
        row = record.get('source_row_addr')
        merged = {**(record.get('row_headers') or {}), **(record.get('values') or {})}
        for key, value in merged.items():
            if (value or '').strip():
                continue
            col = name_to_index.get(key.split('__')[0])
            try:
                coord = (int(row), int(col))
            except (TypeError, ValueError):
                return False
            if not cover.get(coord):
                return False
    return True


# ---------------------------------------------------------------- 캐스케이드

def classify(payload):
    """표를 포함/제외/특수로 가른다. 단계 순서가 곧 우선순위다."""
    tables = index_tables(payload)
    internal = payload['table_internal_blocks']['internal_blocks']
    quality = payload['blocks_document']['quality']

    parent = {}
    for block in internal:
        if block['internal_block_type'] != 'nested_table_ref':
            continue
        child = block['internal_block_id'].rsplit('_', 1)[-1]
        owner = str(block.get('parent_table_id') or '').split('_')[-1]
        if child in tables and owner in tables:
            parent[child] = owner

    toc_ids = {str(i).split('_')[-1]
               for i in ((quality.get('toc_depth0_anchor') or {})
                         .get('toc_source_table_ids') or [])}

    label, pool, trace = {}, set(tables), []

    def stage(name, predicate, tag):
        hit = [t for t in sorted(pool) if predicate(t)]
        for tid in hit:
            label[tid] = tag
            pool.discard(tid)
        trace.append((name, tag, len(hit), sum(table_chars(tables[t]) for t in hit), len(pool)))

    stage('S1 내용 셀 0개', lambda t: gridness(tables[t]) == 'empty', '제외:빈표')
    stage('S2 목차 표', lambda t: t in toc_ids, '특수:목차')
    stage('S3 title_box',
          lambda t: (tables[t]['hierarchy'] or {}).get('table_type') == 'title_box',
          '포함:제목')
    stage('S4 격자 아님', lambda t: gridness(tables[t]) == 'degenerate', '포함:산문')
    stage('S5 병합 채움 후 값 완전', lambda t: records_complete(tables[t]), '포함:레코드')
    stage('S5b key_value items 존재',
          lambda t: (tables[t]['hierarchy'] or {}).get('key_value_items'), '포함:키값')
    stage('S5c 나머지 격자', lambda t: True, '제외:OCR')

    moved = []
    for tid in list(label):
        if not label[tid].startswith('포함'):
            continue
        cur, seen = parent.get(tid), set()
        while cur and cur not in seen:
            seen.add(cur)
            if label.get(cur, '').startswith('제외'):
                moved.append((tid, cur, label[tid]))
                label[tid] = '제외:부모전파'
                break
            cur = parent.get(cur)
    trace.append(('S6 제외 조상 전파', '제외:부모전파', len(moved),
                  sum(table_chars(tables[t]) for t, _, _ in moved), 0))

    return tables, label, trace, moved, parent


def sensitivity(tables, label):
    """분류가 정의·순서 선택에 얼마나 민감한지. 0 이 아니면 사람이 봐야 한다."""
    def loose(table):
        filled = [((c.get('position') or {}).get('row_addr'),
                   (c.get('position') or {}).get('col_addr'))
                  for c in cells_of(table) if cell_text(c).strip()]
        if not filled:
            return 'empty'
        rows = collections.defaultdict(set)
        for row, col in filled:
            rows[row].add(col)
        if len(rows) < 2 or len({col for _, col in filled}) < 2:
            return 'degenerate'
        return 'grid'

    order_conflict = [t for t in tables
                      if gridness(tables[t]) == 'degenerate' and records_complete(tables[t])]
    title_conflict = [t for t in tables
                      if (tables[t]['hierarchy'] or {}).get('table_type') == 'title_box'
                      and gridness(tables[t]) == 'grid']
    kv_conflict = [t for t in tables
                   if gridness(tables[t]) == 'degenerate'
                   and (tables[t]['hierarchy'] or {}).get('key_value_items')]
    definition_diff = [t for t in tables if gridness(tables[t]) != loose(tables[t])]
    return {
        '격자아님+레코드완전': order_conflict,
        'title_box+격자': title_conflict,
        '격자아님+kv_items': kv_conflict,
        '격자 정의 A/B 차이': definition_diff,
    }


# ---------------------------------------------------------------- 필터 적용

def apply_filter(payload):
    """빠진 표를 산출물 전체에서 제거하고 자리 표시만 남긴다."""
    out = copy.deepcopy(payload)
    tables, label, trace, moved, _ = classify(out)
    dropped = {t for t, tag in label.items() if tag.startswith('제외')}
    toc_ids = {t for t, tag in label.items() if tag == '특수:목차'}
    gone = dropped | toc_ids

    # 1) 제외 표 자리: 블록은 남기고 텍스트를 비운다.
    #    셀 글자를 이어붙여 넣으면 구조를 못 믿어 뺀 이유가 무효가 된다.
    marked = {}
    for block in out['blocks_document']['blocks']:
        tid = (block.get('structure_features') or {}).get('xml_table_id')
        tid = str(tid) if tid else None
        if tid not in dropped:
            continue
        block['text_content'] = ''
        block['normalized_text'] = ''
        block['table_hierarchy_ref'] = None
        block['table_internal_ref'] = None
        block['excluded_table'] = {'xml_table_id': tid, 'reason': label[tid]}
        marked.setdefault(tid, []).append(block['block_id'])

    # 2) 목차 표 자리: (텍스트, depth) 항목으로 전개한다. depth 골격의 기점이다.
    raw_toc_ids = ((out['blocks_document']['quality'].get('toc_depth0_anchor') or {})
                   .get('toc_source_table_ids') or [])
    entries = iter_toc_entry_levels(payload['table_internal_blocks']['internal_blocks'],
                                    set(raw_toc_ids))
    toc_blocks = []
    for block in out['blocks_document']['blocks']:
        tid = (block.get('structure_features') or {}).get('xml_table_id')
        if str(tid) not in toc_ids:
            continue
        block['toc_entries'] = [{'text': text, 'depth': depth} for text, depth in entries]
        block['table_hierarchy_ref'] = None
        block['table_internal_ref'] = None
        toc_blocks.append(block['block_id'])

    # 3) tables.analyzed
    def prune_analyzed(node):
        if isinstance(node, list):
            keep = []
            for item in node:
                if isinstance(item, dict) and 'hierarchy' in item and 'preprocess' in item:
                    tid = str((item['preprocess'] or {}).get('identity', {}).get('xml_table_id'))
                    if tid in gone:
                        continue
                prune_analyzed(item)
                keep.append(item)
            node[:] = keep
        elif isinstance(node, dict):
            for value in node.values():
                prune_analyzed(value)

    prune_analyzed(out['tables'])

    # 4) tables.body_linking — analyzed 와 별개 트리이고 셀 텍스트를 그대로 들고 있다.
    #    항목 모양이 달라(preprocess 없음) analyzed 용 조건에 걸리지 않는다.
    def table_id_of(node):
        return str(node.get('table_id') or '').split('_')[-1]

    def prune_linking(nodes):
        keep = []
        for node in nodes:
            if table_id_of(node) in gone:
                continue
            if node.get('children'):
                node['children'] = prune_linking(node['children'])
            keep.append(node)
        return keep

    if isinstance(out['tables'].get('body_linking'), list):
        out['tables']['body_linking'] = prune_linking(out['tables']['body_linking'])

    # 5) internal 블록 / internal 표 목록
    out['table_internal_blocks']['internal_blocks'] = [
        b for b in out['table_internal_blocks']['internal_blocks']
        if owner_table_id(b) not in gone
        and str(b.get('root_table_id') or '').split('_')[-1] not in toc_ids]
    internal_tables = out['table_internal_blocks'].get('tables')
    if isinstance(internal_tables, list):
        out['table_internal_blocks']['tables'] = [
            t for t in internal_tables
            if str(t.get('table_id') or '').split('_')[-1] not in gone]

    # 6) 남은 곳에 매달린 '없는 자식' 참조 정리
    def clean_refs(node):
        if isinstance(node, dict):
            for key in ('child_table_ids', 'nested_table_ids'):
                value = node.get(key)
                if isinstance(value, list):
                    node[key] = [x for x in value if str(x).split('_')[-1] not in gone]
            refs = node.get('nested_table_refs')
            if isinstance(refs, list):
                node['nested_table_refs'] = [
                    r for r in refs
                    if str((r or {}).get('nested_table_id') or '').split('_')[-1] not in gone]
            if isinstance(node.get('child_table_count'), int) and 'child_table_ids' in node:
                node['child_table_count'] = len(node['child_table_ids'])
            for value in node.values():
                clean_refs(value)
        elif isinstance(node, list):
            for value in node:
                clean_refs(value)

    for section in ('tables', 'blocks_document', 'table_internal_blocks'):
        clean_refs(out[section])

    # 7) 없는 표를 가리키는 진단 제거
    warnings = out.get('warnings') or []
    kept_warnings = [w for w in warnings
                     if not any(t in json.dumps(w, ensure_ascii=False) for t in gone)]
    dropped_warnings = len(warnings) - len(kept_warnings)
    if 'warnings' in out:
        out['warnings'] = kept_warnings

    # 8) 집계 갱신 — 없는 표를 세는 집계를 두면 산출물이 자기모순이 된다
    after = index_tables(out)
    top_after = {str((b.get('structure_features') or {}).get('xml_table_id'))
                 for b in out['blocks_document']['blocks']
                 if (b.get('structure_features') or {}).get('xml_table_id')} & set(after)
    out['summary']['table_count'] = len(top_after)
    stats = ((out['blocks_document']['quality'].get('table_hierarchy_link') or {})
             .get('top_level_block_stats'))
    if isinstance(stats, dict):
        stats['table_block_count'] = len(top_after)
        stats['matched'] = len(top_after)
        stats['excluded'] = len(marked)
        stats['table_type'] = dict(collections.Counter(
            (after[t]['hierarchy'] or {}).get('table_type') for t in top_after))
        stats['record_status'] = dict(collections.Counter(
            (after[t]['hierarchy'] or {}).get('record_status') for t in top_after))

    report = {
        'label': label, 'trace': trace, 'moved': moved,
        'dropped': dropped, 'toc_ids': toc_ids, 'gone': gone,
        'marked': marked, 'toc_blocks': toc_blocks, 'entries': entries,
        'dropped_warnings': dropped_warnings,
        'sensitivity': sensitivity(tables, label),
    }
    return out, report


# ---------------------------------------------------------------- 검증

def verify(before, after, report):
    """매 실행 확인한다. 하나라도 깨지면 산출물을 쓰지 않는다."""
    checks = []

    def check(cid, claim, ok, detail):
        checks.append((cid, claim, bool(ok), detail))

    b0 = before['blocks_document']['blocks']
    b1 = after['blocks_document']['blocks']
    gone = report['gone']

    def sig(blocks, key):
        return json.dumps([b.get(key) for b in blocks], ensure_ascii=False)

    check('V1', 'depth 가 전후 완전 동일',
          sig(b0, 'depth') == sig(b1, 'depth'), f'블록 {len(b1)}개')
    check('V2', 'reading_order_index 동일하고 빈 자리 없음',
          sig(b0, 'reading_order_index') == sig(b1, 'reading_order_index')
          and sorted(b['reading_order_index'] for b in b1)
          == list(range(len(b1))), f'0~{len(b1)-1}')
    check('V3', 'block_id / semantic_role / section_index 동일',
          all(sig(b0, k) == sig(b1, k)
              for k in ('block_id', 'semantic_role', 'section_index')),
          f'{len(b0)} -> {len(b1)}')

    top_level = {str((b.get('structure_features') or {}).get('xml_table_id'))
                 for b in b0 if (b.get('structure_features') or {}).get('xml_table_id')}
    want_marked = report['dropped'] & top_level
    check('V4', '제외된 최상위 표마다 자리 표시 1개',
          set(report['marked']) == want_marked
          and all(len(v) == 1 for v in report['marked'].values()),
          f"최상위 {len(want_marked)} / 표시 {len(report['marked'])}")
    check('V5', '자리 표시 블록은 텍스트가 비어 있고 표 id·사유만 남음',
          all(not one(b.get('text_content')) and b['excluded_table'].get('reason')
              for b in b1 if b.get('excluded_table')),
          f"{sum(1 for b in b1 if b.get('excluded_table'))}개")

    left = [b['internal_block_id'] for b in after['table_internal_blocks']['internal_blocks']
            if owner_table_id(b) in gone]
    check('V6', '빠진 표의 셀 텍스트가 코퍼스에서 전부 빠짐', not left, f'잔존 {len(left)}개')

    keep_ids = {t for t, tag in report['label'].items() if tag.startswith('포함')}
    kept_before = {b['internal_block_id']
                   for b in before['table_internal_blocks']['internal_blocks']
                   if owner_table_id(b) in keep_ids}
    kept_after = {b['internal_block_id']
                  for b in after['table_internal_blocks']['internal_blocks']}
    check('V7', '포함 표의 셀 텍스트는 하나도 안 빠짐',
          not (kept_before - kept_after),
          f'{len(kept_before)}개 중 유실 {len(kept_before - kept_after)}개')

    holders = [b for b in b1 if b.get('toc_entries')]
    want = ((after['blocks_document']['quality'].get('toc_depth0_anchor') or {})
            .get('toc_entry_count'))
    check('V8', '목차 항목 수가 toc_entry_count 와 일치',
          len(report['entries']) == want, f"{len(report['entries'])} == {want}")
    check('V9', '목차 항목이 원래 목차 표 자리 블록에 들어감',
          len(holders) == 1 and len(holders[0]['toc_entries']) == want,
          f"블록 {[h['block_id'] for h in holders]}")
    bad_depth = [t for t, d in report['entries']
                 if re.match(r'^\s*(\d+(?:\.\d+)*)', t)
                 and re.match(r'^\s*(\d+(?:\.\d+)*)', t).group(1).count('.') != d]
    check('V10', '목차 항목 depth 가 번호 성분 수와 일치',
          not bad_depth, f'불일치 {len(bad_depth)}개')

    tables_after = index_tables(after)
    incomplete = []
    for tid, table in tables_after.items():
        hierarchy = table['hierarchy'] or {}
        if hierarchy.get('table_type') == 'title_box':
            continue
        if gridness(table) == 'degenerate':
            continue
        if records_complete(table) or hierarchy.get('key_value_items'):
            continue
        incomplete.append(tid)
    check('V11', '남은 표 중 불완전한 것이 없음',
          not incomplete, f'{len(tables_after)}개 중 {len(incomplete)}개')

    _, label2, _, _, _ = classify(after)
    again = [t for t, tag in label2.items() if tag.startswith('제외')]
    check('V12', '멱등 — 다시 돌려도 더 빠지지 않음', not again, f'추가 {len(again)}개')

    ib_ids = {b['internal_block_id'] for b in after['table_internal_blocks']['internal_blocks']}
    broken = []
    for block in b1:
        ref = block.get('table_hierarchy_ref')
        if isinstance(ref, dict) and ref.get('table_id'):
            if str(ref['table_id']).split('_')[-1] not in tables_after:
                broken.append(block['block_id'])
        ref = block.get('table_internal_ref')
        if isinstance(ref, dict) and any(x not in ib_ids
                                         for x in (ref.get('internal_block_ids') or [])):
            broken.append(block['block_id'])
    check('V13', '남은 블록의 표 참조가 전부 해소됨', not broken, f'깨짐 {len(broken)}개')

    hits = collections.Counter()

    def sweep(node, path=''):
        if isinstance(node, dict):
            for key, value in node.items():
                sweep(value, f'{path}.{key}')
        elif isinstance(node, list):
            for value in node:
                sweep(value, path + '[]')
        else:
            text = str(node)
            if any(t in text for t in gone) and not any(a in path for a in ALLOWED_ID_PATHS):
                hits[path] += 1

    sweep(after)
    check('V14', '산출물 전체에 빠진 표 흔적이 없음 (전수 스윕)',
          not hits, f'허용 외 경로 {len(hits)}개 {list(hits)[:2]}')

    return checks


# ---------------------------------------------------------------- 실행

def main(argv=None):
    ap = argparse.ArgumentParser(description='임베딩 입력 산출물 생성')
    ap.add_argument('--doc', default=None, help='결과 폴더 (기본: output/results/sample)')
    ap.add_argument('--out', default=None, help='저장 경로 (기본: <결과폴더>/embedding_input.json)')
    ap.add_argument('--dry-run', action='store_true', help='쓰지 않고 보고만')
    ap.add_argument('--preview', action='store_true',
                    help='필터 결과로 프리뷰 텍스트도 만든다 (사람이 눈으로 볼 용도)')
    args = ap.parse_args(argv)

    from tools.audit.documents import enable_utf8_stdout
    enable_utf8_stdout()

    doc_dir = Path(args.doc) if args.doc else REPO_ROOT / 'output' / 'results' / 'sample'
    src = doc_dir / 'final_debug.json'
    if not src.exists():
        sys.exit(f'입력이 없습니다: {src}')
    before = json.loads(src.read_text(encoding='utf-8'))
    after, report = apply_filter(before)

    print(f'입력 {src}')
    print('=' * 92)
    print('표 선별 캐스케이드')
    print('=' * 92)
    tables = index_tables(before)
    print(f"  {'입력':34s} {len(tables):4d}개 {sum(table_chars(t) for t in tables.values()):8,}자")
    for name, tag, count, chars, left in report['trace']:
        print(f'  {name:34s} {count:4d}개 {chars:8,}자  -> {tag:12s} 남은 {left}')

    counts, chars = collections.Counter(), collections.Counter()
    for tid, tag in report['label'].items():
        counts[tag] += 1
        chars[tag] += table_chars(tables[tid])
    total = sum(chars.values())
    print()
    print('=' * 92)
    print('결과')
    print('=' * 92)
    for tag in sorted(counts):
        print(f'  {tag:14s} {counts[tag]:4d}개 {chars[tag]:8,}자 {chars[tag]/total:6.1%}')
    included = [k for k in counts if k.startswith('포함')]
    print(f"  {'포함 합계':14s} {sum(counts[k] for k in included):4d}개 "
          f"{sum(chars[k] for k in included):8,}자")
    print(f"  목차 항목 {len(report['entries'])}개 전개, warnings {report['dropped_warnings']}건 제거")

    print()
    print('=' * 92)
    print('민감도 (0 이 아니면 사람이 봐야 한다)')
    print('=' * 92)
    for key, value in report['sensitivity'].items():
        print(f'  {key:22s} {len(value)}개 {value[:3] if value else ""}')

    print()
    print('=' * 92)
    print('검증')
    print('=' * 92)
    checks = verify(before, after, report)
    for cid, claim, ok, detail in checks:
        print(f"  [{'OK ' if ok else 'FAIL'}] {cid:4s} {claim}")
        print(f'          {detail}')
    failed = [c for c in checks if not c[2]]
    print()
    print(f"  통과 {len(checks)-len(failed)} / 실패 {len(failed)}")

    if failed:
        print('\n검증이 깨졌습니다. 산출물을 쓰지 않습니다.')
        return 1
    if args.dry_run:
        print('\n--dry-run 이라 쓰지 않았습니다.')
        return 0

    out_path = Path(args.out) if args.out else doc_dir / 'embedding_input.json'
    out_path.write_text(json.dumps(after, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n-> {out_path} 저장')
    print('   원본 final_debug.json 은 그대로다. 이 파일을 지우면 되돌아간다.')

    if args.preview:
        for name, path in write_preview(after, doc_dir, before).items():
            print(f'-> {path} 저장 ({name})')
    return 0


def write_preview(payload, doc_dir, source_payload=None):
    """필터 결과를 사람이 볼 수 있는 텍스트로 뽑는다.

    파이프라인의 프리뷰 생성기를 그대로 쓴다. 따로 렌더러를 만들면 무엇이
    실제로 들어갔는지가 아니라 렌더러가 그린 그림을 보게 된다.

    목차 internal 블록만 그리기용으로 되돌린다
        산출물에서 목차는 blocks[].toc_entries 가 정본이고 internal 블록은
        중복이라 뺐다. 그런데 프리뷰 생성기는 목차를 internal 블록에서 뽑기
        때문에, 그대로 넘기면 목차가 통째로 빠진 그림이 나온다. 파일에는
        넣지 않고 렌더링 입력에만 되돌린다.
    """
    from hwpx_analysis.generate_depth_text_preview import generate_depth_text_preview
    from hwpx_analysis.generate_llm_context import generate_llm_context
    from hwpx_analysis.pipeline_models import BlocksDocument, TableInternalBlocks

    blocks_doc = BlocksDocument(
        document=payload['blocks_document'].get('document') or {},
        blocks=payload['blocks_document']['blocks'],
        quality=payload['blocks_document'].get('quality') or {},
    )
    render_blocks = list(payload['table_internal_blocks']['internal_blocks'])
    if source_payload is not None:
        toc_ids = set((payload['blocks_document']['quality'].get('toc_depth0_anchor') or {})
                      .get('toc_source_table_ids') or [])
        src_internal = source_payload['table_internal_blocks']['internal_blocks']
        order = {b['internal_block_id']: i for i, b in enumerate(src_internal)}
        have = {b['internal_block_id'] for b in render_blocks}
        render_blocks += [b for b in src_internal
                          if b.get('root_table_id') in toc_ids
                          and b['internal_block_id'] not in have]
        render_blocks.sort(key=lambda b: order.get(b['internal_block_id'], 10 ** 9))

        # 생성기는 block['table_hierarchy_ref']['table_id'] 로 목차 표를 찾는다.
        # 산출물에서는 그 ref 를 비웠으므로 그리기용 블록에만 되돌린다.
        src_blocks = {b['block_id']: b for b in source_payload['blocks_document']['blocks']}
        render_doc_blocks = []
        for block in blocks_doc.blocks:
            if block.get('toc_entries'):
                block = dict(block)
                block['table_hierarchy_ref'] = \
                    (src_blocks.get(block['block_id']) or {}).get('table_hierarchy_ref')
            render_doc_blocks.append(block)
        blocks_doc.blocks = render_doc_blocks

    internal = TableInternalBlocks(
        document=payload['table_internal_blocks'].get('document') or {},
        tables=payload['table_internal_blocks'].get('tables') or [],
        internal_blocks=render_blocks,
    )
    preview = generate_depth_text_preview(blocks_doc, internal)
    context = generate_llm_context(blocks_doc, internal)

    written = {}
    for name, text in (
            ('depth 프리뷰 raw', preview.raw_text),
            ('depth 프리뷰 clean', preview.clean_text),
            ('llm context', context.text)):
        suffix = {'depth 프리뷰 raw': 'depth_text_preview_raw',
                  'depth 프리뷰 clean': 'depth_text_preview_clean',
                  'llm context': 'llm_context'}[name]
        path = doc_dir / f'embedding_{suffix}.txt'
        path.write_text(text, encoding='utf-8')
        written[name] = path
    return written


if __name__ == '__main__':
    sys.exit(main())
