#================================================
# tools/build_document_model.py
#
# 문서 조립본(DocumentModel)을 만든다.
#
# JSON 을 읽지 않는다. 문서를 파싱해 파이프라인을 돌리고, 그 결과 객체에서
# 모델을 조립한다. final_debug.json 은 이 경로에 관여하지 않는다.
#
# 파이프라인 산출물은 건드리지 않는다
#   save_pipeline_outputs() 를 호출하지 않으므로 기존 파일이 바뀌지 않는다.
#   --save-pipeline 을 주면 그때만 기존 산출물도 함께 쓴다.
#
# 사용:
#   python tools/build_document_model.py                     # 기본 문서
#   python tools/build_document_model.py <문서> --out <경로>
#   python tools/build_document_model.py --dry-run           # 쓰지 않고 보고만
#================================================

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hwpx_analysis.build_document_model import (  # noqa: E402
    build_document_model, verify_model,
)
from hwpx_analysis.pipeline import run_analysis_pipeline, save_pipeline_outputs  # noqa: E402
from hwpx_analysis.table_json_serializer import table_to_dict  # noqa: E402
from hwpx_parser.parser import HwpxParser  # noqa: E402
from hwpx_analysis.build_summary import build_summary  # noqa: E402
from tools.defaults import DEFAULT_SOURCE  # noqa: E402


def run_pipeline(source: Path, out_root: Path):
    """문서를 파싱하고 파이프라인을 돌린다. 파일은 쓰지 않는다."""
    parser = HwpxParser(doc_save_path=str(out_root), source=str(source))
    tables = parser.parse()
    parser.file_info()
    char_pr = parser.header.char_properties if parser.header is not None else None
    raw_tables = [table_to_dict(t, char_pr_lookup=char_pr, header=parser.header)
                  for t in tables]
    result = run_analysis_pipeline(
        raw_tables=raw_tables,
        section_paths=parser.section_file_paths,
        header=parser.header,
        summary=build_summary(parser, tables),
    )
    return parser, result


def report(model):
    tables = list(model.tables())
    print('=' * 92)
    print('문서')
    print('=' * 92)
    file = model.file
    for label, value in [
            ('제목', file.title), ('파일명', file.filename), ('생성자', file.creator),
            ('최종수정자', file.last_saved_by), ('만든날짜', file.created_at),
            ('수정날짜', file.modified_at), ('언어', file.language),
            ('작성프로그램', f'{file.application} {file.app_version or ""}'.strip()),
            ('섹션수', file.section_count), ('표수', file.table_count)]:
        print(f'  {label:10s} {value}')

    print()
    print('=' * 92)
    print('모델')
    print('=' * 92)
    print(f'  블록            {len(model.blocks)}개')
    print(f'    종류          {dict(collections.Counter(b.kind for b in model.blocks))}')
    print(f'    역할          {dict(collections.Counter(b.role for b in model.blocks))}')
    print(f'    검색대상       {len(model.searchable_blocks())}개')
    print(f'    글 있는 블록    {sum(1 for b in model.blocks if b.text)}개')
    print(f'    제목 경로 보유  {sum(1 for b in model.blocks if b.heading_path)}개')
    print(f'    목차 노드      {sum(1 for b in model.blocks if b.toc)}개')
    print(f'    목차 전개 항목  {sum(len(b.toc_entries) for b in model.blocks)}개')
    print(f'    빠진 표 자리    {sum(1 for b in model.blocks if b.excluded_table)}개')
    print(f'    그림           {sum(1 for b in model.blocks if b.figure)}개')
    print(f'  표(중첩 포함)     {len(tables)}개')
    print(f'    수치표         {len(model.numeric_tables())}개')
    print(f'    판정          {dict(collections.Counter(t.numeric_verdict for t in tables))}')
    print(f'    행 레코드 보유   {sum(1 for t in tables if t.records)}개')
    print(f'    머리글 보유     {sum(1 for t in tables if t.header)}개')
    print(f'    칸            {sum(len(t.cells) for t in tables)}개')
    print(f'  이미지 파일       {len(model.images)}개')


def main(argv=None):
    ap = argparse.ArgumentParser(description='문서 조립본 생성')
    ap.add_argument('source', nargs='?', default=str(DEFAULT_SOURCE),
                    help=f'HWPX 또는 ZIP 문서 (생략 시 {DEFAULT_SOURCE.name})')
    ap.add_argument('--out', default=None, help='저장 경로 (기본: <결과폴더>/document_model.json)')
    ap.add_argument('--work', default=str(REPO_ROOT / 'output'),
                    help='압축 해제 위치 (기본: output)')
    ap.add_argument('--dry-run', action='store_true', help='쓰지 않고 보고만')
    ap.add_argument('--save-pipeline', action='store_true',
                    help='조사용 산출물(프리뷰, llm_context)도 함께 쓴다')
    ap.add_argument('--debug', action='store_true',
                    help='--save-pipeline 에 더해 final_debug.json 까지 쓴다')
    args = ap.parse_args(argv)

    from tools.audit.documents import enable_utf8_stdout
    enable_utf8_stdout()

    source = Path(args.source)
    if not source.exists():
        sys.exit(f'문서를 찾을 수 없습니다: {source}')

    out_root = Path(args.work)
    parser, result = run_pipeline(source, out_root)
    model = build_document_model(result)

    report(model)

    print()
    print('=' * 92)
    print('검증')
    print('=' * 92)
    checks = verify_model(model, result)
    for cid, claim, ok, detail in checks:
        print(f"  [{'OK ' if ok else 'FAIL'}] {cid:4s} {claim}")
        print(f'          {detail}')
    failed = [c for c in checks if not c[2]]
    print()
    print(f'  통과 {len(checks) - len(failed)} / 실패 {len(failed)}')
    if failed:
        print('\n검증이 깨졌습니다. 저장하지 않습니다.')
        return 1

    # --debug 는 --save-pipeline 을 포함한다. final_debug.json 만 있고
    # 프리뷰가 없는 상태를 만들 이유가 없다.
    if args.save_pipeline or args.debug:
        save_pipeline_outputs(result=result,
                              output_dir=out_root / 'results' / parser.filename,
                              debug=args.debug)
        print(f"\n-> 파이프라인 산출물도 저장 ({out_root / 'results' / parser.filename})")

    if args.dry_run:
        print('\n--dry-run 이라 쓰지 않았습니다.')
        return 0

    out_path = (Path(args.out) if args.out
                else out_root / 'results' / parser.filename / 'document_model.json')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(model.to_dict(), ensure_ascii=False, indent=2),
                        encoding='utf-8')
    print(f'\n-> {out_path} 저장')
    print('   모델이 정본이고 이 파일은 직렬화 결과다. 지우면 다시 만들면 된다.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
