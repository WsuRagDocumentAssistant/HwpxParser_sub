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
# 기본으로 파일을 쓰지 않는다
#   이 산출물은 모델이 같은 필터를 내부에서 돌리므로 중복이다. 두 경로가 같은
#   값을 내는지는 tools/compare_model_vs_json.py 가 메모리에서 대조한다.
#   여기는 필터 결과를 눈으로 보는 용도이고, 파일이 필요하면 --out 을 준다.
#
# 사용:
#   python tools/build_embedding_input.py                      # 보고만
#   python tools/build_embedding_input.py --doc <결과폴더>
#   python tools/build_embedding_input.py --out <경로>         # 이때만 저장
#   python tools/build_embedding_input.py --out <경로> --preview
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

# 산출물에 남아도 되는 '빠진 표 id' 경로. 전부 출처 기록이다.
# 표 선별·수치표 판정 규칙은 hwpx_analysis/table_filter.py 에 있다.
# 여기는 그 규칙을 쓰는 CLI 다.
from hwpx_analysis.table_filter import (  # noqa: E402
    ALLOWED_ID_PATHS, NUMERIC_TARGET_TYPES, apply_filter, apply_filter_to_state,
    cell_text, cells_of, classify, gridness, index_tables, is_numeric_value,
    is_serial_column, merge_cover, numeric_table_verdict, owner_table_id,
    one, records_complete, sensitivity, state_view, table_chars,
)



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

    # --- 수치표 판정 ---
    missing = [tid for tid, t in tables_after.items()
               if 'numeric_verdict' not in (t['hierarchy'] or {})]
    check('V15', '남은 표 전부에 수치표 판정이 붙음',
          not missing, f'{len(tables_after)}개 중 누락 {len(missing)}개')

    counted = collections.Counter((t['hierarchy'] or {}).get('numeric_verdict')
                                  for t in tables_after.values())
    recomputed = collections.Counter(numeric_table_verdict(t)
                                     for t in tables_after.values())
    check('V16', '붙은 판정이 다시 계산한 값과 같음',
          counted == recomputed, f'{dict(counted)}')

    wrong_flag = [tid for tid, t in tables_after.items()
                  if bool((t['hierarchy'] or {}).get('numeric_table'))
                  != ((t['hierarchy'] or {}).get('numeric_verdict') == '수치표')]
    check('V17', 'numeric_table 불리언이 판정과 어긋나지 않음',
          not wrong_flag, f'어긋남 {len(wrong_flag)}개')

    # title_box 는 제목이라 수치표 대상이 아니어야 한다
    bad_type = [tid for tid, t in tables_after.items()
                if (t['hierarchy'] or {}).get('table_type') not in NUMERIC_TARGET_TYPES
                and (t['hierarchy'] or {}).get('numeric_verdict') != '대상아님']
    check('V18', '대상 아닌 유형(title_box 등)은 전부 대상아님',
          not bad_type, f'예외 {len(bad_type)}개')

    # 수치표로 판정된 표는 헤더가 반드시 있어야 한다 (판정 근거)
    no_header = [tid for tid, t in tables_after.items()
                 if (t['hierarchy'] or {}).get('numeric_verdict') == '수치표'
                 and not ((t['hierarchy'] or {}).get('header_rows')
                          or (t['hierarchy'] or {}).get('header_cols'))]
    check('V19', '수치표는 전부 헤더를 가짐 (판정 근거가 있음)',
          not no_header, f'헤더 없는 수치표 {len(no_header)}개')

    # 판정불가는 헤더가 없어서 그런 것이어야 한다
    bad_unknown = [tid for tid, t in tables_after.items()
                   if (t['hierarchy'] or {}).get('numeric_verdict') == '판정불가'
                   and ((t['hierarchy'] or {}).get('header_rows')
                        or (t['hierarchy'] or {}).get('header_cols'))
                   and any(cell_text(c).strip() for c in cells_of(t))]
    check('V20', '판정불가는 헤더가 없는 표뿐',
          not bad_unknown, f'헤더 있는데 판정불가 {len(bad_unknown)}개')

    return checks


# ---------------------------------------------------------------- 실행

def main(argv=None):
    ap = argparse.ArgumentParser(description='임베딩 입력 산출물 생성')
    ap.add_argument('--doc', default=None, help='결과 폴더 (기본: output/results/sample)')
    ap.add_argument('--out', default=None,
                    help='저장 경로. 주지 않으면 파일을 쓰지 않는다')
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
    print('수치표 판정 (기존 table_type 은 그대로, 판정만 추가)')
    print('=' * 92)
    for key in ('수치표', '아님', '판정불가', '대상아님'):
        note = {'판정불가': '헤더가 없어 열의 성격을 가릴 수 없음',
                '대상아님': 'title_box 등 표가 아닌 것'}.get(key, '')
        print(f"  {key:8s} {report['numeric'][key]:4d}개  {note}")
    decidable = report['numeric']['수치표'] + report['numeric']['아님']
    if decidable:
        print(f"  판정 가능 모집단 {decidable}개 중 수치표 "
              f"{report['numeric']['수치표'] / decidable:.0%}")

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
    if not args.out:
        print('\n--out 을 주지 않아 파일을 쓰지 않았습니다.')
        print('   이 산출물은 모델과 중복이라 기본으로 저장하지 않습니다.')
        print('   두 경로 대조는 tools/compare_model_vs_json.py 를 쓰십시오.')
        return 0

    out_path = Path(args.out)
    out_path.write_text(json.dumps(after, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n-> {out_path} 저장')
    print('   원본 final_debug.json 은 그대로다. 이 파일을 지우면 되돌아간다.')

    if args.preview:
        for name, path in write_preview(after, out_path.parent, before).items():
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
