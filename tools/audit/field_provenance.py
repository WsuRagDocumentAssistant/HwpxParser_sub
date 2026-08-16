"""final_debug.json의 각 필드를 어느 단계가 만들고 어느 단계가 고치는지 관측한다.

왜 코드를 읽지 않고 실행을 관측하는가
    파이프라인 단계는 blocks_doc / tables.analyzed 를 제자리 변형한다. 같은
    이름의 키가 여러 구조에 있고(block_id, table_id, depth ...), 한 필드를
    여러 단계가 덮어쓴다. 코드를 눈으로 좇으면 '누가 마지막에 썼는지'를
    보장할 수 없다. 그래서 단계 함수를 감싸 호출 전후 상태를 찍고, 필드별
    지문이 바뀐 시점을 실제 실행 순서대로 기록한다.

방법
    hwpx_analysis.pipeline 이름공간의 단계 함수를 래퍼로 교체한다.
    파이프라인 소스는 건드리지 않으므로 호출 순서는 실제 코드 그대로다.
    각 단계 직후 PipelineResult.to_debug_dict() 로 스냅샷을 만든다.
    산출물을 만드는 직렬화 경로를 그대로 쓰므로 관측 대상과 최종 JSON이
    같은 것임이 보장된다.

    필드 지문 = 그 경로에 문서 순서대로 나타난 값들의 누적 해시.
      값이 처음 채워진 단계  = 생성 단계
      지문이 바뀐 단계들     = 수정 단계 (마지막이 최종값의 주인)

    '처음 보인 단계'가 아니라 '처음 채워진 단계'인 이유는, to_debug_dict 가
    아직 채워지지 않은 섹션도 빈 컨테이너로 항상 내보내기 때문이다. 그대로
    세면 warnings 가 첫 단계에서 생겼다고 기록된다.

정확도 근거 (매 실행 자동 확인)
    1. 계측 실행 산출물과 계측 없는 실행 산출물을 해시로 대조한다.
       같은 진입점, 같은 출력 디렉토리를 써야 한다. summary 에 절대 경로가
       들어가므로 출력 위치가 다르면 그것만으로 산출물이 달라진다.
    2. 관측한 필드 집합이 실제 산출물의 필드 집합과 같은지 대조한다.
       어느 한쪽에만 있는 필드가 있으면 출처 표가 불완전한 것이다.

사용
    python -m tools.audit.field_provenance <문서경로> [--out <임시루트>]
    python -m tools.audit.field_provenance            # 기본 문서
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import importlib
import json
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from .documents import REPO_ROOT, enable_utf8_stdout
from ..defaults import DEFAULT_SOURCE

sys.path.insert(0, str(REPO_ROOT))
enable_utf8_stdout()

from hwpx_analysis import pipeline as pipeline_mod            # noqa: E402
from hwpx_analysis.pipeline_models import (                   # noqa: E402
    BlocksDocument, PipelineResult, TableAnalysis)

MAX_DEPTH = 14
DYNAMIC_KEY_KINDS = 30
DYNAMIC_KEY_RATE = 0.2
DYNAMIC_SUFFIX = '.{동적키}'

# 어느 단계도 만들지 않고 파서가 넘겨주는 입력.
PARSER_INPUT = '(입력)파서'

# 감쌀 단계 함수. 순서는 여기서 정하지 않는다. 실제 호출 순서를 기록한다.
STAGE_FUNCS = [
    'preprocess_tables',
    'add_table_grid',
    'add_table_hierarchy',
    'build_body_linking_tables',
    'build_document_blocks',
    'resolve_floating_anchors',
    'add_table_hierarchy_ref_to_blocks',
    'resolve_block_depth_candidates',
    'add_toc_depth0_anchors',
    'apply_depth_constraints',
    'assign_block_visibility',
    'correct_title_box_depths',
    'propagate_toc_anchor_depth',
    'flatten_table_internal_blocks',
    'validate_blocks',
    'validate_table_internal_blocks',
    'generate_depth_text_preview',
    'generate_llm_context',
]

# 반환값을 상태로 받아야 하는 단계. 나머지는 인자를 제자리 변형한다.
RETURN_SLOT = {
    'preprocess_tables': 'analyzed',
    'build_body_linking_tables': 'body_linking',
    'build_document_blocks': 'blocks',
    'flatten_table_internal_blocks': 'table_internal',
    'validate_blocks': 'validation',
}


def norm(path: str) -> str:
    while '.children[].' in path:
        path = path.replace('.children[].', '.', 1)
    return path.replace('.children[]', '')


def _summarize(value):
    """지문에 넣을 값 요약. 스칼라는 값 그대로, 컨테이너는 종류와 크기."""
    if isinstance(value, dict):
        return ('dict', len(value))
    if isinstance(value, list):
        return ('list', len(value))
    return value


class Recorder:
    """단계별 상태를 붙잡아 필드 지문을 남긴다."""

    def __init__(self):
        self.analyzed = []
        self.body_linking = []
        self.blocks = None
        self.table_internal = None
        self.validation = None
        self.summary = {}
        self.stages: list[str] = []
        self.prints: list[dict[str, str]] = []
        self.filled: list[set[str]] = []
        self.dynamic: set[str] = set()
        self._final_payload = None

    # -- 상태 조립 --------------------------------------------------
    def payload(self):
        tables = TableAnalysis(raw=[])
        tables.analyzed = self.analyzed or []
        tables.body_linking = self.body_linking or []
        result = PipelineResult(
            summary=self.summary,
            tables=tables,
            blocks=self.blocks or BlocksDocument(document={}, blocks=[]),
            table_internal=self.table_internal,
            validation=self.validation,
        )
        return result.to_debug_dict()

    # -- 지문 -------------------------------------------------------
    def fingerprint(self, payload, want_filled=False):
        """경로별 값 지문. want_filled=True면 '값이 채워진 경로' 집합도 준다."""
        acc: dict[str, hashlib.blake2b] = {}
        filled: set[str] = set()
        dynamic = self.dynamic

        def put(path, value, raw=None):
            h = acc.get(path)
            if h is None:
                h = acc[path] = hashlib.blake2b(digest_size=16)
            h.update(repr(value).encode('utf-8', 'replace'))
            probe = raw if raw is not None else value
            if probe is not None and not (
                    isinstance(probe, (list, dict, str)) and len(probe) == 0):
                filled.add(path)

        def walk(node, path, depth=0):
            if depth > MAX_DEPTH or not isinstance(node, (dict, list)):
                return
            if isinstance(node, list):
                for item in node:
                    walk(item, path + '[]', depth + 1)
                return
            p = norm(path)
            if p in dynamic:
                put(p + DYNAMIC_SUFFIX,
                    [(k, _summarize(v)) for k, v in node.items()])
                return
            for key, value in node.items():
                full = f"{path}.{key}" if path else key
                put(norm(full), _summarize(value), raw=value)
                walk(value, full, depth + 1)

        walk(payload, '')
        digests = {p: h.hexdigest() for p, h in acc.items()}
        return (digests, filled) if want_filled else digests

    def find_dynamic(self, payload):
        """인스턴스마다 키가 달라지는 경로(컬럼명·id 맵)를 접는다."""
        import statistics
        inst: dict[str, int] = defaultdict(int)
        keyhit: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        def walk(node, path, depth=0):
            if depth > MAX_DEPTH:
                return
            if isinstance(node, dict):
                p = norm(path)
                inst[p] += 1
                for k, v in node.items():
                    keyhit[p][k] += 1
                    walk(v, f"{path}.{k}" if path else k, depth + 1)
            elif isinstance(node, list):
                for item in node:
                    walk(item, path + '[]', depth + 1)

        walk(payload, '')
        out = set()
        for p, ks in keyhit.items():
            n = inst[p]
            if n and len(ks) > DYNAMIC_KEY_KINDS:
                if statistics.median([c / n for c in ks.values()]) < DYNAMIC_KEY_RATE:
                    out.add(p)
        return out

    # -- 단계 훅 ----------------------------------------------------
    def after_stage(self, name):
        payload = self.payload()
        if name == PARSER_INPUT:
            # to_debug_dict 는 아직 채워지지 않은 섹션도 빈 컨테이너로 항상
            # 내보낸다. 그 껍데기까지 세면 tables.analyzed 나 warnings 가
            # 파서에서 생겼다고 잘못 기록된다. 파서가 실제로 준 것은 summary뿐.
            payload = {'summary': payload['summary']}
        self.stages.append(name)
        digests, filled = self.fingerprint(payload, want_filled=True)
        self.prints.append(digests)
        self.filled.append(filled)

    def finish(self):
        self._final_payload = self.payload()
        return self._final_payload


def _capture_summary(recorder: Recorder, originals: dict):
    """summary는 단계가 만드는 값이 아니라 run_analysis_pipeline 의 인자다.

    파서가 넘겨주므로 어느 단계도 손대지 않는다. 진입 지점을 감싸 붙잡지
    않으면 산출물에는 있는데 생성 단계가 없는 필드로 남는다.
    """
    original = pipeline_mod.run_analysis_pipeline
    originals['run_analysis_pipeline'] = original

    @functools.wraps(original)
    def wrapper(*args, **kwargs):
        recorder.summary = kwargs.get('summary', {})
        # 첫 단계 이전 상태를 남겨 summary 를 파서 입력으로 귀속시킨다.
        recorder.after_stage(PARSER_INPUT)
        return original(*args, **kwargs)

    pipeline_mod.run_analysis_pipeline = wrapper
    # 진입점 모듈들은 이름을 직접 import 해 두었으므로 그쪽도 바꿔야 한다.
    # 여기 빠진 모듈로 파이프라인이 돌면 summary 30개 필드가 관측되지 않고
    # "산출물에만 있음"으로 남는다. 단계 함수는 pipeline 이름공간을 거쳐
    # 불리므로 영향이 없어서, 티가 summary 에서만 난다.
    for module_name in ('tools.run_document', 'tools.build_document_model'):
        module = importlib.import_module(module_name)
        originals[f'__entry__{module_name}'] = module.run_analysis_pipeline
        module.run_analysis_pipeline = wrapper


def instrument(recorder: Recorder):
    """pipeline 이름공간의 단계 함수를 관측 래퍼로 교체한다."""
    originals = {}
    _capture_summary(recorder, originals)
    for name in STAGE_FUNCS:
        original = getattr(pipeline_mod, name)
        originals[name] = original

        def make(name=name, original=original):
            @functools.wraps(original)
            def wrapper(*args, **kwargs):
                out = original(*args, **kwargs)
                slot = RETURN_SLOT.get(name)
                if slot:
                    setattr(recorder, slot, out)
                recorder.after_stage(name)
                return out
            return wrapper

        setattr(pipeline_mod, name, make())
    return originals


def restore(originals):
    for name, func in originals.items():
        if name.startswith('__entry__'):
            module = importlib.import_module(name[len('__entry__'):])
            module.run_analysis_pipeline = func
        else:
            setattr(pipeline_mod, name, func)


def analyze(recorder: Recorder):
    """지문 이력에서 생성/수정 단계를 뽑는다.

    to_debug_dict 는 아직 채워지지 않은 섹션도 빈 컨테이너로 항상 내보낸다.
    그래서 '경로가 처음 보인 단계'를 생성으로 삼으면 warnings 나
    table_internal_blocks 가 첫 단계에서 생겼다고 잘못 기록된다.
    값이 처음 채워진 단계를 생성으로 본다. 끝까지 비어 있는 필드는
    (항상 빈 필드가 실제로 존재한다) 처음 보인 단계로 되돌린다.
    """
    seen_at: dict[str, str] = {}
    birth: dict[str, str] = {}
    changes: dict[str, list[str]] = defaultdict(list)
    previous: dict[str, str] = {}

    for stage, fp, filled in zip(recorder.stages, recorder.prints, recorder.filled):
        for path, digest in fp.items():
            if path not in seen_at:
                seen_at[path] = stage
            if path in filled and path not in birth:
                birth[path] = stage
            if path not in previous or previous[path] != digest:
                changes[path].append(stage)
        previous.update(fp)

    for path, stage in seen_at.items():
        birth.setdefault(path, stage)

    order = {name: i for i, name in enumerate(recorder.stages)}
    writers = {p: [s for s in ss if order[s] >= order[birth[p]]]
               for p, ss in changes.items()}
    return birth, writers, previous


def module_of(name):
    if name == PARSER_INPUT:
        return 'hwpx_parser (run_analysis_pipeline 인자)'
    func = getattr(pipeline_mod, name, None)
    return getattr(func, '__module__', '?').replace('hwpx_analysis.', '')


def _load_test_module():
    """저장소 루트의 test.py 를 파일 경로로 직접 읽는다.

    import test 로 가져오면 표준 라이브러리의 test 패키지와 부딪힐 수 있다.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'hwpx_test_entry', REPO_ROOT / 'test.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_document(source: Path, out_root: Path, entry: str = 'test'):
    """정본 진입점으로 파이프라인을 돌리고 final_debug.json 경로를 준다.

    기본은 test.py 다. output/results 에 실제로 쌓이는 산출물이고 회귀
    기준선도 그쪽을 본다. (build_summary 는 이제 한 벌이라 두 진입점의
    summary 가 같다. 예전에는 15키 / 7키로 갈려 산출물 컬럼이 134개
    어긋났고, 그래서 어느 쪽으로 도는지가 감사 결과를 바꿨다.)

    두 진입점 모두 argv 를 명시해 부른다. 비워 두면 argparse 가 sys.argv 를
    읽어 이 감사 도구에 준 인자를 진입점이 자기 것으로 착각한다.
    --debug 도 반드시 준다. 그게 없으면 final_debug.json 을 안 쓰는데,
    예전에 만들어 둔 파일이 남아 있으면 그 낡은 파일을 조용히 읽게 된다.
    """
    if entry == 'test':
        module = _load_test_module()
        cwd = Path.cwd()
        os.chdir(REPO_ROOT)          # test.py 는 상대경로 output/ 에 쓴다
        try:
            module.main(['--debug'])
        finally:
            os.chdir(cwd)
        produced = (REPO_ROOT / 'output' / 'results' / DEFAULT_SOURCE.stem
                    / 'final_debug.json')
        if not produced.exists():
            sys.exit(f"산출물이 없습니다: {produced}")
        return produced

    import tools.run_document as run_document
    code = run_document.main([str(source), '--out', str(out_root), '--debug'])
    if code != 0:
        sys.exit(f"문서 실행 실패: {source}")
    produced = list((out_root / 'results').glob('*/final_debug.json'))
    if not produced:
        sys.exit(f"산출물이 없습니다: {out_root}")
    return produced[0]


def run_plain(source: Path, out_root: Path, entry: str) -> Path:
    """계측 없이 실행. 동적 키 판정과 무해성 대조의 기준이 된다."""
    return _run_document(source, out_root, entry)


def run_instrumented(source: Path, out_root: Path, dynamic: set[str], entry: str):
    recorder = Recorder()
    recorder.dynamic = dynamic
    originals = instrument(recorder)
    try:
        produced = _run_document(source, out_root, entry)
    finally:
        restore(originals)
    recorder.finish()
    return recorder, produced


def main(argv=None):
    ap = argparse.ArgumentParser(description="필드별 생성/수정 단계 관측")
    ap.add_argument('source', nargs='?', default=str(DEFAULT_SOURCE),
                    help=f'HWPX 또는 ZIP 문서 (생략 시 {DEFAULT_SOURCE.name})')
    ap.add_argument('--out', default=None, help="산출물 임시 저장 루트")
    ap.add_argument('--entry', choices=('test', 'run_document'), default='test',
                    help="정본 진입점. test.py 가 기본 (summary 구성이 다르다)")
    ap.add_argument('--json', default=None,
                    help="경로별 생성/수정 단계를 JSON으로 저장 (field_usage 입력)")
    args = ap.parse_args(argv)

    source = Path(args.source)
    if not source.exists():
        sys.exit(f"문서를 찾을 수 없습니다: {source}")

    tmp = Path(args.out or tempfile.mkdtemp(prefix='provenance_'))

    # 무해성 대조에는 두 가지 함정이 있다.
    #   1. test.py 산출물과 비교하면 summary 구성이 달라(test.py 15키 /
    #      run_document 7키) 계측과 무관한 차이가 잡힌다.
    #   2. summary 에는 unpacked_dir_path 같은 절대 경로가 들어간다.
    #      출력 디렉토리가 다르면 그것만으로 산출물이 달라진다.
    # 그래서 같은 진입점으로, 같은 출력 디렉토리에 두 번 돌려 비교한다.
    work = tmp / 'run'
    print(f"[1/3] 기준 실행 (계측 없음) - {source.name}")
    plain = run_plain(source, work, args.entry)
    baseline_bytes = plain.read_bytes()

    print("[2/3] 동적 키 판정 후 계측 실행")
    probe = Recorder()
    dynamic = probe.find_dynamic(json.loads(baseline_bytes.decode('utf-8')))
    recorder, produced = run_instrumented(source, work, dynamic, args.entry)

    print("[3/3] 분석")
    birth, writers, _ = analyze(recorder)

    print()
    print("=" * 96)
    print("계측 무해성 확인")
    print("=" * 96)
    a = hashlib.sha256(produced.read_bytes()).hexdigest()
    b = hashlib.sha256(baseline_bytes).hexdigest()
    print(f"  계측 실행 {a[:16]}")
    print(f"  기준 실행 {b[:16]}")
    print(f"  -> {'동일 - 계측이 결과를 바꾸지 않았다' if a == b else '다름 - 신뢰 불가'}")
    if a != b:
        sys.exit(1)

    print()
    print("=" * 96)
    print(f"단계 실행 순서 ({len(recorder.stages)}개)")
    print("=" * 96)
    for i, name in enumerate(recorder.stages, 1):
        created = sum(1 for p, s in birth.items() if s == name)
        touched = sum(1 for p, ws in writers.items() if name in ws) - created
        print(f"  {i:2d}. {name:36s} {module_of(name):34s} "
              f"생성 {created:5d} / 수정 {touched:5d}")

    order = {name: i for i, name in enumerate(recorder.stages)}
    sections = defaultdict(list)
    for path in birth:
        sections[path.split('.')[0].split('[')[0]].append(path)

    for root in ['summary', 'tables', 'blocks_document', 'table_internal_blocks',
                 'warnings', 'quality_report']:
        paths = sorted(sections.get(root, []))
        if not paths:
            continue
        print()
        print("=" * 96)
        print(f"[{root}]  필드 {len(paths)}개")
        print("=" * 96)
        for p in paths:
            ws = writers[p]
            extra = [w for w in ws if w != birth[p]]
            tail = f"  <- 수정 {', '.join(extra)}" if extra else ""
            print(f"  {p[:62]:62s} {birth[p]:32s}{tail}")

    multi = {p: ws for p, ws in writers.items() if len(ws) > 1}
    print()
    print("=" * 96)
    print(f"여러 단계가 쓰는 필드 {len(multi)}개 (마지막 기록자가 최종값)")
    print("=" * 96)
    for p in sorted(multi, key=lambda x: (-len(multi[x]), x))[:40]:
        ws = multi[p]
        print(f"  {p[:58]:58s} {len(ws)}회  {' -> '.join(ws)}")

    print()
    print("=" * 96)
    print("자체 점검")
    print("=" * 96)

    # 관측 집합이 실제 산출물의 필드 집합과 같은지. 어느 한쪽에만 있으면
    # 스냅샷이 최종 상태를 놓쳤다는 뜻이므로 출처 표가 불완전해진다.
    on_disk = Recorder()
    on_disk.dynamic = recorder.dynamic
    disk_paths = set(on_disk.fingerprint(
        json.loads(produced.read_text(encoding='utf-8'))))
    observed = set(birth)
    only_disk = sorted(disk_paths - observed)
    only_obs = sorted(observed - disk_paths)
    print(f"  산출물 필드 {len(disk_paths)}개 / 관측 필드 {len(observed)}개")
    print(f"  산출물에만 있음 {len(only_disk)}개 / 관측에만 있음 {len(only_obs)}개")
    for p in only_disk[:10]:
        print(f"     산출물에만: {p}")
    for p in only_obs[:10]:
        print(f"     관측에만  : {p}")
    print(f"  -> 필드 집합 {'일치' if not only_disk and not only_obs else '불일치'}")

    unattributed = [p for p in birth if p not in writers]
    print(f"  필드 {len(birth)}개 / 생성 단계 미상 {len(unattributed)}개")
    bad_order = [p for p, ws in writers.items()
                 if any(order[a] > order[b] for a, b in zip(ws, ws[1:]))]
    print(f"  기록 순서가 실행 순서를 어기는 필드 {len(bad_order)}개")
    print(f"  동적 키로 접은 경로 {len(recorder.dynamic)}개")

    if args.json:
        payload = {
            'source': str(source),
            'stage_order': recorder.stages,
            'stage_module': {s: module_of(s) for s in recorder.stages},
            'fields': {p: {'birth': birth[p], 'writers': writers.get(p, [])}
                       for p in sorted(birth)},
        }
        Path(args.json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"  -> {args.json} 저장")
    return 0


if __name__ == '__main__':
    sys.exit(main())
