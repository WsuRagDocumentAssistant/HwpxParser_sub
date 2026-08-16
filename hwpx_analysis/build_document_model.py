#================================================
# hwpx_analysis/build_document_model.py
#
# PipelineResult -> DocumentModel 빌더.
#
# JSON 을 읽지 않는다. run_analysis_pipeline() 이 돌려준 인메모리 객체에서
# 값을 가져온다. 조립 시점은 flatten_table_internal_blocks 이후이며,
# PipelineResult 를 받는 시점이 이미 그 뒤다.
#
# 표 선별과 수치표 판정은 tools/build_embedding_input.py 의 규칙을 그대로 쓴다.
# 규칙을 두 곳에 두면 갈라지므로 그쪽 함수를 불러 쓴다.
#================================================

from __future__ import annotations

import collections
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from hwpx_analysis.document_model import (
    Block, Cell, DocumentModel, ExcludedTable, Figure, FileInfo, ImageFile,
    ImageRef, Table, TableColumn, TableHeader, TableParent, TableRecord,
    TocEntry, TocRef,
)

BLOCK_KIND = {'paragraph': '문단', 'table': '표', 'image': '이미지', 'shape': '도형',
              'shape_group': '도형묶음', 'control': '컨트롤', 'footer': '바닥글',
              'section_control': '섹션컨트롤'}
BLOCK_ROLE = {'section_heading': '제목', 'body_text': '본문', 'table': '표',
              'figure': '그림', 'page_footer': '바닥글',
              'empty_paragraph': '빈문단', 'document_control': '문서컨트롤'}
TABLE_KIND = {'data_table': '데이터표', 'title_box': '제목상자',
              'key_value_table': '키값표'}

_WS = re.compile(r'\s+')


def _one(value) -> str:
    return _WS.sub(' ', value or '').strip()


def _local(tag: str) -> str:
    return tag.split('}', 1)[1] if '}' in tag else tag


#------------------------------------------------
# 원본에서만 얻을 수 있는 것
#------------------------------------------------

def read_package_info(unpacked_dir) -> tuple[dict[str, str], dict[str, ImageFile]]:
    """content.hpf 에서 문서 메타와 이미지 매니페스트를 읽는다.

    파이프라인은 이 파일을 읽지 않는다. 이미지 실제 경로와 생성자·작성일이
    여기에만 있다.
    """
    base = Path(unpacked_dir)
    meta: dict[str, str] = {}
    images: dict[str, ImageFile] = {}
    hpf = base / 'Contents' / 'content.hpf'
    if not hpf.exists():
        return meta, images
    root = ET.parse(hpf).getroot()
    for node in root.iter():
        tag = _local(node.tag)
        if tag == 'meta' and node.attrib.get('name'):
            meta[node.attrib['name']] = (node.text or '').strip()
        elif tag in ('title', 'language') and (node.text or '').strip():
            meta[tag] = node.text.strip()
        elif tag == 'item' and node.attrib.get('href', '').startswith('BinData/'):
            href = node.attrib['href']
            full = base / href
            images[node.attrib['id']] = ImageFile(
                ref=node.attrib['id'], path=href,
                media_type=node.attrib.get('media-type'),
                size_bytes=full.stat().st_size if full.exists() else None)
    return meta, images


def read_application(unpacked_dir) -> dict[str, str]:
    """version.xml 에서 작성 프로그램을 읽는다."""
    path = Path(unpacked_dir) / 'version.xml'
    if not path.exists():
        return {}
    attrib = ET.parse(path).getroot().attrib
    return {'application': attrib.get('application'),
            'app_version': attrib.get('appVersion')}


#------------------------------------------------
# 계산으로 얻는 것
#------------------------------------------------

def heading_context(blocks: list[dict[str, Any]]):
    """제목 경로와 하위 제목. depth + reading_order 로 조상 스택을 쌓는다."""
    order = sorted(blocks, key=lambda b: b['reading_order_index'])
    text_of = {b['block_id']: _one(b.get('normalized_text')) for b in order}
    stack: list[dict[str, Any]] = []
    path_of: dict[str, list[str]] = {}
    kids: dict[str, list[str]] = collections.defaultdict(list)
    for block in order:
        if block['semantic_role'] == 'section_heading':
            while stack and stack[-1]['depth'] >= block['depth']:
                stack.pop()
            if stack:
                kids[stack[-1]['block_id']].append(block['block_id'])
            path_of[block['block_id']] = [x['block_id'] for x in stack] + [block['block_id']]
            stack.append(block)
        elif stack:
            path_of[block['block_id']] = [x['block_id'] for x in stack]
    return path_of, dict(kids), text_of


def table_markdown(table: dict[str, Any], cell_text) -> str | None:
    """칸 좌표·병합·내용으로 Markdown 표를 만든다. 병합 값은 덮이는 칸에 채운다."""
    grid: dict[tuple[int, int], str] = {}
    max_row = max_col = -1
    for cell in (table.get('preprocess') or {}).get('cells') or []:
        pos = cell.get('position') or {}
        row, col = pos.get('row_addr'), pos.get('col_addr')
        if row is None or col is None:
            continue
        value = _one(cell_text(cell))
        for dr in range(pos.get('row_span') or 1):
            for dc in range(pos.get('col_span') or 1):
                grid[(row + dr, col + dc)] = value
                max_row, max_col = max(max_row, row + dr), max(max_col, col + dc)
    if max_row < 0:
        return None
    header_rows = set((table.get('hierarchy') or {}).get('header_rows') or [])
    lines = []
    for row in range(max_row + 1):
        cells = [grid.get((row, col), '').replace('|', '\\|')
                 for col in range(max_col + 1)]
        lines.append('| ' + ' | '.join(cells) + ' |')
        if row in header_rows or (not header_rows and row == 0):
            lines.append('|' + '---|' * (max_col + 1))
    return '\n'.join(lines)


#------------------------------------------------
# 조립
#------------------------------------------------

def build_document_model(result, unpacked_dir=None) -> DocumentModel:
    """PipelineResult 에서 DocumentModel 을 만든다."""
    from hwpx_analysis.table_filter import (
        apply_filter_to_state, cell_text, cells_of,
    )

    summary = result.summary or {}
    unpacked = unpacked_dir or summary.get('unpacked_dir_path')
    meta, images = read_package_info(unpacked) if unpacked else ({}, {})
    app = read_application(unpacked) if unpacked else {}

    # 표 선별 / 수치표 판정 / 목차 전개 / 빠진 자리 표시
    state = apply_filter_to_state(result)
    blocks_raw = state['blocks']
    tables_by_id = state['tables']
    labels = state['labels']
    toc_entries = state['toc_entries']

    path_of, kids, text_of = heading_context(blocks_raw)

    def image_ref(ref: str | None) -> ImageRef | None:
        if not ref:
            return None
        found = images.get(ref)
        return ImageRef(ref=ref,
                        path=found.path if found else None,
                        media_type=found.media_type if found else None)

    def build_cell(cell: dict[str, Any]) -> Cell:
        pos = cell['position']
        objects = cell.get('objects') or {}
        paragraphs = [_one(x) for x in ((cell.get('text') or {}).get('paragraph_texts') or [])]
        paragraphs = [x for x in paragraphs if x]
        return Cell(
            row=pos['row_addr'], col=pos['col_addr'],
            row_span=pos.get('row_span') or 1, col_span=pos.get('col_span') or 1,
            text=_one(cell_text(cell)),
            paragraphs=paragraphs if len(paragraphs) > 1 else [],
            images=[r for r in (image_ref(i.get('binary_item_id_ref'))
                                for i in (objects.get('images') or [])) if r],
            child_tables=[str(x).split('_')[-1]
                          for x in (objects.get('nested_table_ids') or [])])

    def merge_cover(table):
        cover = {}
        for cell in cells_of(table):
            pos = cell.get('position') or {}
            rows, cols = pos.get('row_span') or 1, pos.get('col_span') or 1
            if rows > 1 or cols > 1:
                value = _one(cell_text(cell))
                for dr in range(rows):
                    for dc in range(cols):
                        if dr or dc:
                            cover[(pos['row_addr'] + dr, pos['col_addr'] + dc)] = value
        return cover

    def build_table(table_id: str, seen: set[str] | None = None) -> Table | None:
        seen = seen if seen is not None else set()
        if table_id in seen or table_id not in tables_by_id:
            return None
        seen.add(table_id)
        raw = tables_by_id[table_id]
        pre = raw['preprocess'] or {}
        hier = raw['hierarchy'] or {}
        nesting = pre.get('nesting') or {}

        cover = merge_cover(raw)
        name_to_col: dict[str, int] = {}
        for column in (hier.get('columns') or []):
            name_to_col.setdefault(column['name'], column['col_index'])

        records = []
        for record in (hier.get('structured_records') or []):
            merged = {**(record.get('row_headers') or {}),
                      **(record.get('values') or {})}
            values, inherited = {}, []
            for key, value in merged.items():
                if (value or '').strip():
                    values[key] = _one(value)
                else:
                    got = cover.get((record.get('source_row_addr'),
                                     name_to_col.get(key.split('__')[0])))
                    values[key] = _one(got) if got else ''
                    if got:
                        inherited.append(key)
            records.append(TableRecord(index=record['row_index'], values=values,
                                       inherited=inherited))

        # 파이프라인은 행 단위 표를 structured_records 에, 키-값 표를
        # key_value_records 에 담는다. 앞의 것만 읽으면 키값표는 칸만 남고
        # 쌍이 사라진다. 원천이 둘이니 둘 다 받는다.
        if not records:
            for record in (hier.get('key_value_records') or []):
                key = _one(record.get('key'))
                if not key:
                    continue
                records.append(TableRecord(index=record.get('row_addr') or 0,
                                           values={key: _one(record.get('value'))}))

        # 헤더가 있는지는 헤더 지정으로 판단한다. 전에는 columns 유무로 갈랐는데
        # columns 는 31개 표에만 있고 header_rows/cols 는 57개 표에 있다.
        # 그 차이인 26개 표가 헤더 지정을 통째로 잃고 있었다.
        header = None
        if hier.get('columns') or hier.get('header_rows') or hier.get('header_cols'):
            header = TableHeader(
                header_rows=hier.get('header_rows') or [],
                header_cols=hier.get('header_cols') or [],
                columns=[TableColumn(index=c['col_index'], name=c['name'],
                                     is_row_header=bool(c.get('is_row_header')))
                         for c in (hier.get('columns') or [])])

        parent = None
        if nesting.get('is_nested'):
            parent = TableParent(
                table_id=str(nesting.get('parent_table_id') or '').split('_')[-1],
                cell_id=str(nesting.get('parent_cell_id') or ''))

        # title_cells 는 셀 ID 목록이다. 그대로 넣으면 제목 자리에
        # section0_tbl5_..._r0_c0 같은 내부 식별자가 들어간다. 칸을 찾아
        # 텍스트를 꺼낸다.
        text_by_cell = {c.get('cell_id'): _one(cell_text(c)) for c in cells_of(raw)}
        titles = []
        for entry in (hier.get('title_cells') or []):
            cell_id = entry.get('cell_id') if isinstance(entry, dict) else entry
            titles.append(text_by_cell.get(cell_id, ''))

        children = [t for t in (build_table(str(cid).split('_')[-1], seen)
                               for cid in (nesting.get('child_table_ids') or [])) if t]

        # 필터가 이미 매긴 라벨을 그대로 옮긴다. 여기서 다시 판정하지 않는다.
        # 두 곳에서 따로 판정하면 언젠가 서로 다른 답을 낸다.
        return Table(
            id=table_id,
            kind=TABLE_KIND.get(hier.get('table_type'), hier.get('table_type') or ''),
            kept_as=(labels.get(table_id) or '').split(':')[-1],
            rows=(pre.get('layout') or {}).get('row_count') or 0,
            cols=(pre.get('layout') or {}).get('col_count') or 0,
            numeric=bool(hier.get('numeric_table')),
            numeric_verdict=hier.get('numeric_verdict') or '',
            row_records_available=hier.get('record_status') == 'structured',
            title=[t for t in titles if t],
            header=header, records=records,
            cells=[build_cell(c) for c in sorted(
                cells_of(raw),
                key=lambda c: (c['position']['row_addr'], c['position']['col_addr']))],
            markdown=table_markdown(raw, cell_text),
            raw_row_count=(len(hier['raw_rows']) if not records and hier.get('raw_rows')
                           else None),
            parent=parent, children=children)

    blocks: list[Block] = []
    for raw in sorted(blocks_raw, key=lambda b: b['reading_order_index']):
        features = raw.get('structure_features') or {}
        layout = raw.get('layout_position') or {}
        text = _one(raw.get('normalized_text'))
        path = path_of.get(raw['block_id'], [])

        figure = None
        if raw['block_type'] in ('image', 'shape', 'shape_group'):
            size = layout.get('size') or {}
            figure = Figure(
                shape=BLOCK_KIND.get(raw['block_type'], raw['block_type']),
                z_order=layout.get('z_order'),
                placement='글자처럼' if layout.get('anchor_type') == 'inline' else '떠있음',
                paragraph_index=layout.get('paragraph_index'),
                image=image_ref(features.get('binary_item_id_ref')),
                shape_type=features.get('object_type'),
                width=size.get('width'), height=size.get('height'),
                contains=features.get('child_object_summary') or {})

        toc = None
        match = raw.get('toc_match') or {}
        if match.get('toc_title'):
            toc = TocRef(title=match['toc_title'], numbering=match.get('toc_numbering'))

        excluded = None
        if raw.get('excluded_table'):
            excluded = ExcludedTable(table_id=raw['excluded_table']['xml_table_id'],
                                     reason=raw['excluded_table']['reason'])

        entries = []
        if raw.get('toc_entries'):
            entries = [TocEntry(text=e['text'], depth=e['depth'])
                       for e in raw['toc_entries']]

        table_id = str(features.get('xml_table_id')) if features.get('xml_table_id') else None
        table = build_table(table_id) if table_id in tables_by_id else None

        blocks.append(Block(
            id=raw['block_id'], order=raw['reading_order_index'],
            section=raw['section_index'], depth=raw['depth'],
            area='본문' if raw.get('depth_band') == 'body' else '주변부',
            kind=BLOCK_KIND.get(raw['block_type'], raw['block_type']),
            role=BLOCK_ROLE.get(raw['semantic_role'], raw['semantic_role']),
            searchable=bool((raw.get('visibility') or {}).get('include_in_llm_context')),
            text=text or None,
            heading_path=path,
            heading_path_text=[text_of.get(x, '') for x in path],
            child_headings=kids.get(raw['block_id'], []),
            toc=toc, toc_entries=entries, excluded_table=excluded,
            figure=figure, table=table))

    model_file = FileInfo(
        title=summary.get('filename') or '',
        filename=summary.get('filename') or '',
        creator=meta.get('creator') or None,
        last_saved_by=meta.get('lastsaveby') or None,
        created_at=meta.get('CreatedDate') or None,
        modified_at=meta.get('ModifiedDate') or None,
        language=meta.get('language') or None,
        application=app.get('application'),
        app_version=app.get('app_version'),
        section_count=summary.get('section_count') or 0,
        table_count=len([t for t, label in labels.items() if label.startswith('포함')]),
    )
    return DocumentModel(file=model_file, images=images, blocks=blocks)


#------------------------------------------------
# 검증
#------------------------------------------------

_MD_SEPARATOR = re.compile(r'^\|(\s*-{3,}\s*\|)+$')


def verify_model(model: DocumentModel, result) -> list[tuple[str, str, bool, str]]:
    """모델이 파이프라인 상태와 어긋나지 않는지 매 실행 확인한다.

    하나라도 깨지면 조립이 잘못된 것이므로 저장하지 않는다.
    """
    checks: list[tuple[str, str, bool, str]] = []

    def check(cid, claim, ok, detail):
        checks.append((cid, claim, bool(ok), detail))

    raw_blocks = {b['block_id']: b for b in result.blocks.blocks}
    tables = list(model.tables())

    check('M2', '블록 수가 파이프라인과 같다',
          len(model.blocks) == len(raw_blocks),
          f'{len(model.blocks)} / {len(raw_blocks)}')

    bad = [b.id for b in model.blocks
           if b.id not in raw_blocks
           or b.depth != raw_blocks[b.id]['depth']
           or b.order != raw_blocks[b.id]['reading_order_index']
           or b.section != raw_blocks[b.id]['section_index']]
    check('M9', 'depth·순서·섹션이 파이프라인 최종값과 같다',
          not bad, f'어긋난 블록 {len(bad)}개')

    verdicts = collections.Counter(t.numeric_verdict for t in tables)
    check('M4', '수치표 판정이 네 갈래로 빠짐없이 붙는다',
          sum(verdicts.values()) == len(tables) and '' not in verdicts,
          f'{dict(verdicts)}')

    refs = [f.image for f in (b.figure for b in model.blocks) if f and f.image]
    cell_refs = [i for t in tables for c in t.cells for i in c.images]
    unresolved = [r.ref for r in refs + cell_refs if not r.path]
    check('M5', '이미지 참조가 전부 실제 경로로 풀린다',
          not unresolved,
          f'참조 {len(refs) + len(cell_refs)}개 중 미해소 {len(unresolved)}개')

    depth_of = {b.id: b.depth for b in model.blocks}
    broken = []
    for block in model.blocks:
        if not block.heading_path:
            continue
        depths = [depth_of[x] for x in block.heading_path if x in depth_of]
        if any(a >= b for a, b in zip(depths, depths[1:])):
            broken.append(block.id)
    check('M6', '제목 경로의 depth 가 단조 증가한다',
          not broken, f'경로 {sum(1 for b in model.blocks if b.heading_path)}개 중 '
                      f'어긋남 {len(broken)}개')

    mismatched = []
    for table in tables:
        if not table.markdown:
            continue
        lines = [ln for ln in table.markdown.split('\n') if not _MD_SEPARATOR.match(ln)]
        rows = len(lines)
        cols = max((ln.count('|') - 1 for ln in lines), default=0)
        if rows != table.rows or cols != table.cols:
            mismatched.append((table.id, rows, table.rows, cols, table.cols))
    check('M7', '마크다운 격자가 선언 크기와 맞는다',
          not mismatched,
          f'표 {sum(1 for t in tables if t.markdown)}개 중 불일치 {len(mismatched)}개 '
          f'{mismatched[:2]}')

    joined = repr(model.to_dict())
    leaked = [k for k in ('source_block_id', 'internal_block_type', 'local_order_index',
                          'root_table_id', 'parent_internal_block_id')
              if k in joined]
    check('M8', '조립용 연결 키가 모델에 남지 않는다',
          not leaked, f'남은 키 {leaked}')

    orphan = [t.id for t in tables
              if t.parent and t.parent.table_id
              and t.parent.table_id not in {x.id for x in tables}]
    check('M10', '중첩 표의 상위표가 모델 안에 있다',
          not orphan, f'끊긴 상위표 참조 {len(orphan)}개')

    # regression_check 의 I5(무결성) / I6(depth 해소)를 모델 형태로 옮긴 것.
    # 모델에는 internal_blocks 가 없다(칸·표로 흡수됐다). 그래서 같은 취지를
    # 모델이 실제로 가진 id 로 다시 세운다.
    block_ids = [b.id for b in model.blocks]
    table_ids = [t.id for t in tables]
    cell_dup = 0
    for table in tables:
        seen = collections.Counter((c.row, c.col) for c in table.cells)
        cell_dup += sum(n - 1 for n in seen.values() if n > 1)
    orders = [b.order for b in model.blocks]
    child_ids = {c.id for t in tables for c in t.children}
    no_parent = [t.id for t in tables if t.id in child_ids and t.parent is None]
    duplicates = (len(block_ids) - len(set(block_ids))
                  + len(table_ids) - len(set(table_ids))
                  + cell_dup + len(orders) - len(set(orders)))
    check('M11', 'id·좌표·순서에 중복이 없고 자식 표에 상위표가 있다',
          duplicates == 0 and not no_parent,
          f'블록 id 중복 {len(block_ids) - len(set(block_ids))} / '
          f'표 id 중복 {len(table_ids) - len(set(table_ids))} / '
          f'셀 좌표 중복 {cell_dup} / order 중복 {len(orders) - len(set(orders))} / '
          f'parent 없는 자식 표 {len(no_parent)}')

    missing_field = [b.id for b in model.blocks
                     if b.depth is None or b.order is None or b.section is None]
    check('M12', '모든 블록에 depth·순서·섹션이 해소되어 있다',
          not missing_field, f'미해소 블록 {len(missing_field)}개')

    unknown_image = [b.id for b in model.blocks
                     if b.figure and b.figure.image
                     and b.figure.image.ref not in model.images]
    check('M13', '그림이 가리키는 파일이 이미지 목록에 있다',
          not unknown_image, f'목록에 없는 참조 {len(unknown_image)}개')

    # 파이프라인이 만든 헤더·레코드가 조립에서 새는지 본다.
    # 전에는 columns 가 있을 때만 헤더를 만들어서, columns 없이 header_rows 만
    # 있는 표 26개가 헤더를 잃었다. 키값표의 쌍도 통째로 빠져 있었다.
    # 어느 쪽도 M2~M13 에 걸리지 않았다. 값이 틀린 게 아니라 없어진 것이라
    # 개수만 맞춰 보는 검사에는 안 잡힌다.
    from hwpx_analysis.table_filter import index_tables, state_view

    source_tables = index_tables(state_view(result))
    model_tables = {t.id: t for t in model.tables()}
    header_lost, record_lost = [], []
    for table_id, table in model_tables.items():
        hier = (source_tables.get(table_id) or {}).get('hierarchy') or {}
        if (hier.get('header_rows') or hier.get('header_cols')
                or hier.get('columns')) and table.header is None:
            header_lost.append(table_id)
        if (hier.get('structured_records') or hier.get('key_value_records')) \
                and not table.records:
            record_lost.append(table_id)
    from hwpx_analysis.table_filter import apply_filter_to_state
    kept_labels = {str(k).split('_')[-1]: v
                   for k, v in apply_filter_to_state(result)['labels'].items()}
    bad_kept = [t.id for t in model.tables()
                if t.kept_as != (kept_labels.get(t.id) or '').split(':')[-1]]
    check('M15', '표가 남은 근거(kept_as)가 필터 판정과 같다',
          not bad_kept, f'어긋난 표 {len(bad_kept)}개 {bad_kept[:3]}')

    check('M14', '파이프라인이 만든 헤더·레코드가 모델에 남아 있다',
          not header_lost and not record_lost,
          f'헤더 잃은 표 {len(header_lost)}개 {header_lost[:3]} / '
          f'레코드 잃은 표 {len(record_lost)}개 {record_lost[:3]}')

    return checks
