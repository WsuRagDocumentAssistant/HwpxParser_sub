#================================================
# hwpx/analysis/table_filter.py
#
# 구조를 믿을 수 없는 표를 걸러내고, 수치표 여부를 판정한다.
#
# 왜 tools 가 아니라 여기인가
#   모델 빌더(build_document_model)가 이 규칙을 쓴다. 라이브러리가 스크립트
#   폴더를 import 하면 층이 뒤집힌다. 규칙은 라이브러리에 두고 tools 의
#   CLI 가 이 모듈을 쓰는 쪽이 맞다.
#
# 임계값과 문자열 상수를 쓰지 않는다
#   판정은 전부 셀 좌표·병합 정보·파이프라인 분류에서 파생된다.
#   격자 여부는 '2개 이상의 행이 각각 2개 이상의 열을 채우는가' 로 본다.
#
# 제외는 삭제가 아니다
#   블록은 남기고 텍스트만 비운 뒤 표 id 와 사유를 남긴다. 자리를 지우면
#   reading_order 가 비고 Parent 경계와 depth 전파가 어긋난다.
#================================================

from __future__ import annotations

import collections
import copy
import json
import re

from .add_toc_depth0_anchors import iter_toc_entry_levels

ALLOWED_ID_PATHS = ('.excluded_table.', '.structure_features.', '.toc_source_table_ids')

# --- 수치표 판정 --------------------------------------------------------
# 수치표는 table_type 이 아니라 별도 판정으로 붙인다. 기존 유형
# (data_table / title_box / key_value_table) 은 건드리지 않는다.
#
# 임계값을 쓰지 않는다
#   '숫자 비율 N% 이상' 으로 잡으려 했더니 분포에 골이 없어 임계값을 어디에
#   두든 임의가 됐다. 그래서 비율을 버리고 '본문 셀이 전부 숫자인 열이
#   하나라도 있는가' 라는 구조 판정으로 바꿨다.
#
# 판정이 세 가지인 이유
#   헤더를 빼지 않으면 수치열이 하나도 안 잡힌다(헤더 셀이 글자라 열 전체가
#   숫자가 아니게 된다). 즉 이 판정은 header_rows / header_cols 에 전적으로
#   의존한다. 헤더가 없는 표는 '아님' 이 아니라 '판정불가' 다. 숫자가 없다는
#   뜻이 아니라 열의 성격을 가릴 근거가 없다는 뜻이다.
NUMERIC_TARGET_TYPES = {'data_table', 'key_value_table'}
_UNIT = (r'(명|건|개|원|점|시간|회|위|억원|백만원|천원|%|％|배|일|년|월|주|시|분|초'
         r'|㎡|km|kg|톤|권|매|팀|과목|학점|주차)')
_PURE_NUMBER = re.compile(r'^[\d][\d.,]*$')
_NUMBER_WITH_UNIT = re.compile(r'^[\d][\d.,]*\s*' + _UNIT + r'$')
_PERCENT = re.compile(r'^\(?[\d][\d.,]*\s*%\)?$')
# 2-1, Ⅰ-1-1 같은 항목 번호는 수치가 아니다
_ID_LIKE = re.compile(r'^[\dⅠ-Ⅻ]+\s*[-·.]\s*[\d]+([-·.][\d]+)*$')
# 빈칸과 줄표는 미기재다. 세지 않는다
_NEUTRAL = re.compile(r'^[-–—.\s]*$')


def is_numeric_value(value):
    text = (value or '').strip()
    if not text or _NEUTRAL.match(text) or _ID_LIKE.match(text):
        return False
    return bool(_PURE_NUMBER.match(text) or _NUMBER_WITH_UNIT.match(text)
                or _PERCENT.match(text))


def is_serial_column(values):
    """1,2,3… 처럼 1(또는 0)부터 1씩 늘어나는 정수열이면 일련번호다."""
    try:
        numbers = [int(v.replace(',', '')) for v in values]
    except ValueError:
        return False
    if len(numbers) < 2 or numbers[0] not in (0, 1):
        return False
    return numbers == list(range(numbers[0], numbers[0] + len(numbers)))


def numeric_table_verdict(table):
    """'수치표' / '아님' / '판정불가' / '대상아님'."""
    hierarchy = table['hierarchy'] or {}
    if hierarchy.get('table_type') not in NUMERIC_TARGET_TYPES:
        return '대상아님'
    header_rows = set(hierarchy.get('header_rows') or [])
    header_cols = set(hierarchy.get('header_cols') or [])
    if not header_rows and not header_cols:
        return '판정불가'

    by_column = collections.defaultdict(list)
    for cell in cells_of(table):
        pos = cell.get('position') or {}
        if pos.get('row_addr') in header_rows or pos.get('col_addr') in header_cols:
            continue
        value = cell_text(cell).strip()
        if value and not _NEUTRAL.match(value):
            by_column[pos.get('col_addr')].append(value)
    if not by_column:
        return '판정불가'

    for values in by_column.values():
        if all(is_numeric_value(v) for v in values) and not is_serial_column(values):
            return '수치표'
    return '아님'

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

    # 8) 수치표 판정을 붙인다. 기존 table_type 은 건드리지 않고 필드만 더한다.
    numeric = collections.Counter()
    for table in index_tables(out).values():
        verdict = numeric_table_verdict(table)
        table['hierarchy']['numeric_table'] = (verdict == '수치표')
        table['hierarchy']['numeric_verdict'] = verdict
        numeric[verdict] += 1

    # 9) 집계 갱신 — 없는 표를 세는 집계를 두면 산출물이 자기모순이 된다
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
        # 집합을 그대로 돌면 순회 순서가 실행마다 달라져 산출물 바이트가 흔들린다.
        # 같은 입력에 같은 파일이 나와야 해시로 회귀를 볼 수 있으므로 정렬해서 센다.
        ordered = sorted(top_after)
        stats['table_type'] = dict(collections.Counter(
            (after[t]['hierarchy'] or {}).get('table_type') for t in ordered))
        stats['record_status'] = dict(collections.Counter(
            (after[t]['hierarchy'] or {}).get('record_status') for t in ordered))

    report = {
        'label': label, 'trace': trace, 'moved': moved,
        'dropped': dropped, 'toc_ids': toc_ids, 'gone': gone,
        'marked': marked, 'toc_blocks': toc_blocks, 'entries': entries,
        'dropped_warnings': dropped_warnings,
        'sensitivity': sensitivity(tables, label),
        'numeric': numeric,
    }
    return out, report


def state_view(result):
    """PipelineResult 를 payload 모양으로 '가리킨다'. 직렬화하지 않는다.

    단계들은 이미 인메모리 dict/dataclass 를 주고받으므로 같은 객체를 그대로
    참조한다. JSON 을 거치지 않는다는 뜻이 여기서 지켜진다.
    """
    internal = result.table_internal
    return {
        'summary': result.summary or {},
        'tables': {'raw': result.tables.raw,
                   'analyzed': result.tables.analyzed,
                   'body_linking': result.tables.body_linking},
        'blocks_document': {'document': result.blocks.document,
                            'blocks': result.blocks.blocks,
                            'quality': result.blocks.quality},
        'table_internal_blocks': {
            'document': getattr(internal, 'document', {}) if internal else {},
            'tables': getattr(internal, 'tables', []) if internal else [],
            'internal_blocks': getattr(internal, 'internal_blocks', []) if internal else []},
        'warnings': list(result.validation.warnings) if result.validation else [],
        'quality_report': (result.validation.quality_report
                           if result.validation else {}),
    }


def apply_filter_to_state(result):
    """PipelineResult 에 필터를 적용하고 조립에 필요한 상태를 돌려준다.

    JSON 파일을 읽지 않는다. 파이프라인이 돌려준 객체에서 바로 만든다.
    반환값의 blocks / tables 는 필터가 적용된 사본이므로 원본 객체는 안 바뀐다.
    """
    filtered, report = apply_filter(state_view(result))
    return {
        'blocks': filtered['blocks_document']['blocks'],
        'tables': index_tables(filtered),
        'labels': report['label'],
        'toc_entries': report['entries'],
        'report': report,
        'payload': filtered,
    }
