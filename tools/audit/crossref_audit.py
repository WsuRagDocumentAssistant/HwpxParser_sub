"""산출물 섹션 간 상호 참조 무결성 검증.

final_debug.json은 네 가지 식별자로 서로를 가리킨다.
    block_id            blocks_document.blocks[]
    table_id            tables.analyzed[] (children 재귀 포함)
    cell_id             tables.analyzed[].preprocess.cells[]
    internal_block_id   table_internal_blocks.internal_blocks[]

참조가 가리키는 대상이 실제로 존재하는지 전수 확인한다. '미아'가 하나라도
나오면 어느 단계에서 id를 흘렸다는 뜻이므로 곧바로 회귀로 본다.
"""

import json
from collections import Counter

from tools.audit.documents import enable_utf8_stdout, resolve

enable_utf8_stdout()


def collect_ids(fd):
    table_ids, cell_ids = set(), set()

    def walk(t):
        table_ids.add(t.get('table_id'))
        for c in (t.get('preprocess') or {}).get('cells') or []:
            cell_ids.add(c.get('cell_id'))
        for ch in t.get('children') or []:
            walk(ch)

    for t in fd['tables']['analyzed']:
        walk(t)

    return (
        {b['block_id'] for b in fd['blocks_document']['blocks']},
        table_ids,
        cell_ids,
        {x['internal_block_id'] for x in fd['table_internal_blocks']['internal_blocks']},
    )


def audit(label, final_debug, totals):
    fd = json.load(open(final_debug, encoding='utf-8'))
    blocks = fd['blocks_document']['blocks']
    internal = fd['table_internal_blocks']['internal_blocks']
    itabs = fd['table_internal_blocks']['tables']
    block_ids, table_ids, cell_ids, internal_ids = collect_ids(fd)

    print("=" * 92)
    print(label)
    print("=" * 92)
    print(f"  식별자: block_id {len(block_ids)} / table_id {len(table_ids)} / "
          f"cell_id {len(cell_ids)} / internal_block_id {len(internal_ids)}")

    checks = []

    def check(name, refs, valid):
        refs = [r for r in refs if r is not None]
        checks.append((name, len(refs), len([r for r in refs if r not in valid])))

    check('blocks[].table_hierarchy_ref.table_id  ->  tables.analyzed[].table_id',
          [(b.get('table_hierarchy_ref') or {}).get('table_id')
           for b in blocks if b.get('table_hierarchy_ref')], table_ids)
    check('internal_blocks[].source_block_id  ->  blocks[].block_id',
          [x.get('source_block_id') for x in internal], block_ids)
    check('internal_blocks[].source_table_id  ->  tables.analyzed[].table_id',
          [x.get('source_table_id') for x in internal], table_ids)
    check('internal_blocks[].root_table_id  ->  tables.analyzed[].table_id',
          [x.get('root_table_id') for x in internal], table_ids)
    check('internal_blocks[].parent_internal_block_id  ->  internal_block_id',
          [x.get('parent_internal_block_id') for x in internal], internal_ids)
    check('internal_blocks[type=table_cell_group].id  ->  preprocess.cells[].cell_id',
          [x['internal_block_id'] for x in internal
           if x['internal_block_type'] == 'table_cell_group'], cell_ids)
    check('table_internal_blocks.tables[].source_block_id  ->  blocks[].block_id',
          [t.get('source_block_id') for t in itabs], block_ids)

    parents = []

    def walk(t):
        if t.get('parent_table_id'):
            parents.append((t['parent_table_id'], t.get('parent_cell_id')))
        for ch in t.get('children') or []:
            walk(ch)

    for t in fd['tables']['analyzed']:
        walk(t)
    check('tables.analyzed[].parent_table_id  ->  table_id',
          [p for p, _ in parents], table_ids)
    check('tables.analyzed[].parent_cell_id  ->  cells[].cell_id',
          [c for _, c in parents], cell_ids)

    check('warnings[].block_id  ->  blocks[].block_id',
          [w.get('block_id') for w in fd.get('warnings') or []], block_ids)

    toc = (fd['blocks_document']['quality'].get('toc_depth0_anchor') or {})
    check('quality.toc_depth0_anchor.matched_block_ids  ->  blocks[].block_id',
          toc.get('matched_block_ids') or [], block_ids)
    check('quality.toc_depth0_anchor.toc_source_table_ids  ->  table_id',
          toc.get('toc_source_table_ids') or [], table_ids)

    for name, total, bad in checks:
        print(f"    [{'OK ' if bad == 0 else 'NG '}] {name:74s} {total:5d}건 / 미아 {bad}")
        totals['참조'] += total
        totals['미아'] += bad
    print()


def main():
    documents = resolve()
    totals = Counter()
    for doc in documents:
        audit(doc.label, doc.final_debug, totals)

    print("=" * 92)
    print(f"합계 - 참조 {totals['참조']}건 / 미아 {totals['미아']}건")
    print("=" * 92)
    if totals['미아']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
