#================================================
# tools/compare_model_vs_json.py
#
# 객체 경로(DocumentModel)와 JSON 경로(final_debug.json 후처리)가 같은 값을
# 내는지 대조한다.
#
# 왜 필요한가
#   "JSON 을 빼도 된다" 는 두 경로가 같은 값을 낼 때만 성립한다. 이 대조가
#   그 근거다. 통과하지 않으면 JSON 제거를 진행하면 안 된다.
#
# 파일을 만들지 않는다
#   두 경로를 한 프로세스에서 메모리로 계산해 비교한다. 예전에는
#   embedding_input.json 을 저장해 두고 그걸 기준선으로 썼는데, 그 파일은
#   모델이 같은 필터를 내부에서 돌리므로 중복이었다.
#
# 사용:
#   python -m tools.compare_model_vs_json
#   python -m tools.compare_model_vs_json <문서>
#================================================

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hwpx.analysis.build_document_model import build_document_model  # noqa: E402
from hwpx.analysis.table_filter import (  # noqa: E402
    apply_filter, cell_text, cells_of, index_tables, one, state_view,
)
try:
    from hwpx import run_pipeline  # noqa: E402
except ImportError as exc:            # noqa: E402
    # tools 가 패키지가 된 뒤로 이 파일은 모듈로 실행해야 한다.
    # 직접 실행하면 부모 패키지를 몰라 상대 import 가 풀리지 않는다.
    raise SystemExit(
        "이 파일은 모듈로 실행하세요.\n"
        "  python -m tools.compare_model_vs_json ..."
    ) from exc
from .defaults import DEFAULT_SOURCE  # noqa: E402


def compare(model, filtered, filtered_labels):
    """모델과 필터 산출물을 값으로 대조한다."""
    checks = []

    def check(name, ok, detail=''):
        checks.append((name, bool(ok), detail))

    json_blocks = {b['block_id']: b for b in filtered['blocks_document']['blocks']}
    json_tables = index_tables(filtered)
    model_tables = {t.id: t for t in model.tables()}

    check('블록 수', len(model.blocks) == len(json_blocks),
          f'{len(model.blocks)} / {len(json_blocks)}')
    check('블록 id 집합', {b.id for b in model.blocks} == set(json_blocks))

    mismatched = [b.id for b in model.blocks
                  if b.depth != json_blocks[b.id]['depth']
                  or b.order != json_blocks[b.id]['reading_order_index']
                  or b.section != json_blocks[b.id]['section_index']]
    check('depth·순서·섹션', not mismatched, f'다른 블록 {len(mismatched)}개')

    text_diff = [b.id for b in model.blocks
                 if (b.text or '') != one(json_blocks[b.id].get('normalized_text'))]
    check('본문 텍스트', not text_diff, f'다른 블록 {len(text_diff)}개')

    gate_diff = [b.id for b in model.blocks
                 if b.searchable != bool((json_blocks[b.id].get('visibility') or {})
                                         .get('include_in_llm_context'))]
    check('검색대상', not gate_diff, f'다른 블록 {len(gate_diff)}개')

    check('표 수', len(model_tables) == len(json_tables),
          f'{len(model_tables)} / {len(json_tables)}')
    check('표 id 집합', set(model_tables) == set(json_tables),
          f'모델에만 {sorted(set(model_tables) - set(json_tables))[:3]} / '
          f'JSON에만 {sorted(set(json_tables) - set(model_tables))[:3]}')

    verdict_diff = [tid for tid in model_tables
                    if model_tables[tid].numeric_verdict
                    != (json_tables[tid]['hierarchy'] or {}).get('numeric_verdict')]
    check('수치표 판정', not verdict_diff, f'다른 표 {len(verdict_diff)}개')

    cell_diff = [tid for tid in model_tables
                 if len(model_tables[tid].cells) != len(cells_of(json_tables[tid]))]
    check('셀 수', not cell_diff, f'다른 표 {len(cell_diff)}개')

    # 레코드 원천은 둘이다. 행 단위 표는 structured_records, 키-값 표는
    # key_value_records. 모델과 같은 규칙으로 세야 대조가 성립한다.
    def json_record_count(table):
        hier = table['hierarchy'] or {}
        rows = hier.get('structured_records') or []
        if rows:
            return len(rows)
        return len([r for r in (hier.get('key_value_records') or [])
                    if one(r.get('key'))])

    record_diff = [tid for tid in model_tables
                   if len(model_tables[tid].records)
                   != json_record_count(json_tables[tid])]
    check('레코드 수', not record_diff, f'다른 표 {len(record_diff)}개')

    model_chars = sum(len(c.text) for t in model.tables() for c in t.cells)
    json_chars = sum(len(one(cell_text(c))) for t in json_tables.values()
                     for c in cells_of(t))
    kept_diff = [tid for tid in model_tables
                 if model_tables[tid].kept_as
                 != (filtered_labels.get(tid) or '').split(':')[-1]]
    check('남은 근거', not kept_diff, f'다른 표 {len(kept_diff)}개')

    check('셀 텍스트 총량', model_chars == json_chars,
          f'{model_chars:,} / {json_chars:,}')

    check('목차 노드 수',
          sum(1 for b in model.blocks if b.toc)
          == sum(1 for b in json_blocks.values()
                 if (b.get('toc_match') or {}).get('toc_title')))
    check('목차 전개 항목',
          sum(len(b.toc_entries) for b in model.blocks)
          == sum(len(b.get('toc_entries') or []) for b in json_blocks.values()))
    check('빠진 표 자리',
          sum(1 for b in model.blocks if b.excluded_table)
          == sum(1 for b in json_blocks.values() if b.get('excluded_table')))

    return checks


def main(argv=None):
    ap = argparse.ArgumentParser(description='객체 경로 vs JSON 경로 대조')
    ap.add_argument('source', nargs='?', default=str(DEFAULT_SOURCE))
    ap.add_argument('--work', default=str(REPO_ROOT / 'output'))
    args = ap.parse_args(argv)

    from .audit.documents import enable_utf8_stdout
    enable_utf8_stdout()

    source = Path(args.source)
    if not source.exists():
        sys.exit(f'문서를 찾을 수 없습니다: {source}')

    _, result = run_pipeline(source, Path(args.work))
    model = build_document_model(result)
    filtered, report = apply_filter(state_view(result))

    print('=' * 92)
    print('객체 경로 vs JSON 경로 — 같은 값을 내는가')
    print('=' * 92)
    checks = compare(model, filtered,
                     {str(k).split('_')[-1]: v for k, v in report['label'].items()})
    for name, ok, detail in checks:
        print(f"  [{'OK ' if ok else 'FAIL'}] {name:16s} {detail}")
    failed = [c for c in checks if not c[1]]
    print()
    print(f'  통과 {len(checks) - len(failed)} / 실패 {len(failed)}')
    if failed:
        print('\n두 경로가 갈라졌습니다. JSON 제거를 진행하면 안 됩니다.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
