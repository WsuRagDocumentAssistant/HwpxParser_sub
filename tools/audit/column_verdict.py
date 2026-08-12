"""컬럼별 최종값 출처와 유의미성 판정.

각 컬럼에 대해 이렇게 답한다.
    이 값을 마지막으로 쓴 곳은 어디인가        final_source
    덮어쓰기가 있었다면 어떤 순서였나           overwrite_trace
    그 값이 최종 산출물에 쓸 값인가             verdict
    무엇에 근거해 그렇게 보는가                 evidence_kind

근거의 종류 (evidence_kind)
    code    추출식을 직접 확인했다. 가장 결정적이다. 속성 출처는 파서 시점의
            단일 표현식이라 코드를 읽으면 끝나는 문제다. 단계 순서와 달리
            제자리 변형/동명 키 위험이 없어 코드 읽기를 피할 이유가 없다.
    text    문자열 값을 원본 텍스트와 전수 대조했다.
    domain  값 집합이 원본 속성의 값 집합에 포함된다. '그 속성에서 추출됐다'가
            아니라 '그 속성의 도메인 안에 있다'까지만 말한다.
    none    어느 근거도 얻지 못했다.

비대칭 규칙 (반드시 지킨다)
    포함 성립  -> 약한 긍정.
    불성립     -> 아무 결론도 아니다. 정규화/병합/변환된 값일 수 있다.
    이름 매핑(snake -> camel)은 후보 생성기로만 쓰고 판정 근거로 쓰지 않는다.
    이 비대칭을 어겨서 heading_type 을 '파이프라인이 채우는 값'이라고 단정한
    사고가 났다. 측정이 뒷받침한 것은 '그 이름의 속성을 못 찾았다'까지였다.

개수 등급
    도메인 포함만 보면 개수 불일치를 놓친다. (부모, 요소, 속성) 기준으로
    원본 출현 수와 컬럼의 비지 않은 인스턴스 수를 비교해 등급을 남긴다.
        일치        개수까지 같다
        개수불일치  값은 포함되나 개수가 다르다   <- 결함 리드가 되는 자리

채움률은 판정에 쓰지 않는다
    binary_item_id_ref 가 97% 비어 있는 것은 이미지가 붙은 블록에만 있는 게
    정상이기 때문이고, caption_candidate 가 199/200 비어 있는 것은 미검출일
    수 있다. 성격이 반대인데 비율이 같아 하나의 임계값으로 가르면 어느 쪽이든
    틀린다. 그래서 fill_rate 는 보고만 하고 valid 조건에서 뺀다.

이 도구가 보장하지 못하는 것 (반드시 알고 쓸 것)
    1. 상수 게이트는 문서 분포에 의존한다.
       heading_type 을 지금 막는 것은 이 문서에서 값이 한 종류이기 때문이다.
       BULLET 문단이 하나라도 산출물에 살아남은 문서에서는 distinct 가 2가
       되어 게이트를 통과한다. 추출 결함은 그대로인데도 그렇다. 회귀 fixture
       가 지금 통과하는 것은 규칙의 보증이 아니라 이 문서의 데이터가 그렇게
       생겼기 때문이다.
    2. ATTRIBUTE_READ 는 이름 기반 휴리스틱이다.
       변수를 거쳐 대입되는 추출식을 못 잡는다. 실제로 heading_type 은
       h_type 이라는 변수를 거쳐 대입돼 code 근거를 얻지 못했다. 정확히
       하려면 AST 로 대입식의 데이터 흐름을 따라가야 한다.

mismatched 는 자동으로 낼 수 없다
    '값은 있으나 컬럼 의도와 다른 정보'는 의미 판단이라 측정으로 가려지지
    않는다. 이 도구는 mismatched 를 만들지 않는다.

사용
    python -m tools.audit.field_provenance --json prov.json
    python -m tools.audit.column_verdict prov.json --json verdict.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from tools.audit.documents import REPO_ROOT, enable_utf8_stdout, resolve
from tools.audit.source_index import SourceIndex, norm_text

enable_utf8_stdout()

PLACEHOLDERS = {'', '-', 'N/A', 'n/a', '없음', '해당없음', '미상', '.', '_'}

# 원본 텍스트 대조는 124만 자에 대한 substring 검색이라 짧은 값은 반드시 맞는다.
# 무작위 숫자 2000개씩 넣어 잰 우연 히트율:
#     2자리 100% / 3자리 100% / 4자리 52% / 5자리 3.8% / 6자리 0.1%
# 그래서 순수 숫자 문자열은 6자리 이상만 증거로 인정한다.
MIN_DIGIT_LEN = 6
MIN_MATCH_LEN = 2
MAX_DISTINCT = 5000

# 추출식을 찾을 소스 범위.
CODE_DIRS = ('hwpx_analysis', 'hwpx_document', 'hwpx_parser')

# 표현식이 원본 XML 을 읽는가를 가리는 표지.
#
# .get( 을 표지로 쓰면 안 된다. 파이썬 dict 접근 전반에 쓰여서
#     "old_depth": block.get("depth")        내부 값 복사
#     "z_order": anchor_info.get("z_order")  내부 dict
# 까지 원본 읽기로 잡힌다. 실제로 그 기준으로는 117개가 code 근거로 올라왔고
# 표현식을 열어보니 대부분 파이프라인 내부 값 이동이거나 상수 대입이었다.
# XML 속성 접근을 뜻하는 이름이 실제로 나타나야 한다.
ATTRIBUTE_READ = re.compile(
    r'\battrs\b|\battrib\b|raw_attrs|_find_child_raw|\.attrib\b')

# 열거형 토큰. 출처를 문자열 대조로 가릴 수 없는 값의 모양이다.
#
# "CENTER" 나 "NONE" 은 원본에도 있고 파이프라인 기본값으로도 쓰인다. 문서
# 전체 대조를 통과해도 이 컬럼이 원본에서 가져왔다는 증거가 되지 못한다.
# 이런 값은 text 근거를 아예 부여하지 않고 domain(요소 경로 + 개수)으로만
# 판정한다.
ENUM_TOKEN = re.compile(r'^[A-Z][A-Z0-9_]*$')

# 값이 한 종류뿐인 컬럼은 어떤 근거로도 valid 로 올리지 않는다.
#
# 열거형 토큰은 원본에도 있고 파이프라인 기본값으로도 쓰여서, 문서 전체
# 대조로는 둘을 원리상 구분할 수 없다. heading_type 이 그 예다. 251개 전부
# "NONE" 이고 "NONE" 은 원본에도 있어 대조를 통과하지만, 실제로는 본문 57개
# 문단이 BULLET 을 선언한 paraPr 를 참조하는데 그 참조를 따라가지 않아
# 전부 NONE 으로 떨어진 추출 결함이다. 값 종류가 하나라는 사실 자체가
# '구분할 수 없음'을 뜻하므로 여기서 막는다.
MIN_DISTINCT_FOR_VALID = 2

# 결함으로 확정된 컬럼. valid 로 나오면 판정 체계가 무너진 것이다.
#
# 규칙은 재작성 중에 조용히 사라진다. 실제로 상수 배제 규칙이 한 번 소실돼
# heading_type 이 valid 로 인증됐고, 같은 세션의 결함 기록은 그 컬럼이
# 망가졌다고 적고 있었다. 그걸 알아챈 것은 우연히 그 컬럼을 따로 조사하고
# 있었기 때문이다. 다음에는 이 검사가 잡는다.
KNOWN_NOT_VALID = [
    ('blocks_document.blocks[].style_features.heading_type',
     'unresolved',
     '본문 57개 문단이 BULLET 선언 paraPr 를 참조하는데 산출물은 전부 NONE'),
    ('blocks_document.blocks[].style_features.numbering_level',
     'unresolved',
     '411개 전부 null. heading_type 과 같은 원인'),
]


def norm_path(path: str) -> str:
    while '.children[].' in path:
        path = path.replace('.children[].', '.', 1)
    return path.replace('.children[]', '')


def norm_text(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def find_extraction_sites(leaf: str):
    """이 컬럼을 채우는 코드 줄을 찾는다. 근거 종류 code 의 출처다.

    통계 대조는 추출식이 불명일 때 쓰는 도구다. alignment 처럼
    features["alignment"] = align.get("attrs", {}).get("horizontal") 로
    한 줄에 적혀 있는 것을 값 집합 포함관계로 추정할 이유가 없다.
    """
    quoted = "[\"']" + re.escape(leaf) + "[\"']"
    pattern = re.compile(r"^\s*(?:\w+\[)?" + quoted + r"\]?\s*[=:]\s*(.+)$")
    sites = []
    for d in CODE_DIRS:
        for path in sorted((REPO_ROOT / d).rglob('*.py')):
            if '__pycache__' in path.parts:
                continue
            text = path.read_text(encoding='utf-8', errors='replace')
            for i, line in enumerate(text.splitlines(), 1):
                m = pattern.match(line)
                if not m:
                    continue
                rhs = m.group(1).strip().rstrip(',')
                sites.append({
                    'location': f"{path.relative_to(REPO_ROOT).as_posix()}:{i}",
                    'module': path.stem,
                    'expression': rhs[:100],
                    # 원본을 읽는 표현식인가. .get( 만으로는 안 된다.
                    # 파이썬 dict 접근 전반에 쓰여서 "old_depth": block.get("depth")
                    # 같은 내부 값 복사까지 원본 읽기로 잡힌다. XML 속성 접근을
                    # 뜻하는 이름이 실제로 나타나야 한다.
                    'reads_attribute': bool(ATTRIBUTE_READ.search(rhs)),
                })
    return sites


def collect(payload, dynamic=frozenset()):
    """경로별 인스턴스 수, 빈 값 수, 서로 다른 값, 문자열 값 전수.

    dynamic 은 field_provenance 가 접은 것과 같은 동적 키 경로다. 여기서도
    똑같이 접지 않으면 컬럼명 하나하나가 별도 경로가 되어 출처 표와 경로가
    어긋나고, 그 경로들은 매칭 실패로 instances 0 이 된다.
    """
    stats = defaultdict(lambda: {
        'n': 0, 'empty': 0, 'distinct': set(), 'samples': [],
        'types': set(), 'first': None,
    })

    def walk(node, path, depth=0):
        if depth > 14 or not isinstance(node, (dict, list)):
            return
        if isinstance(node, list):
            for item in node:
                walk(item, path + '[]', depth + 1)
            return
        folded = norm_path(path)
        if folded in dynamic:
            s = stats[folded + '.{동적키}']
            for value in node.values():
                s['n'] += 1
                s['types'].add(type(value).__name__)
                if value is None or (isinstance(value, (list, dict, str)) and not value):
                    s['empty'] += 1
                    continue
                if s['first'] is None:
                    s['first'] = value
                if len(s['distinct']) < MAX_DISTINCT:
                    s['distinct'].add(value if not isinstance(value, (list, dict))
                                      else json.dumps(value, ensure_ascii=False)[:400])
                if isinstance(value, str):
                    s['samples'].append(value)
            return
        for key, value in node.items():
            full = f"{path}.{key}" if path else key
            s = stats[norm_path(full)]
            s['n'] += 1
            s['types'].add(type(value).__name__)
            if value is None or (isinstance(value, (list, dict, str)) and not value):
                s['empty'] += 1
            else:
                if s['first'] is None:
                    s['first'] = value if not isinstance(value, (list, dict)) \
                        else json.dumps(value, ensure_ascii=False)[:80]
                if len(s['distinct']) < MAX_DISTINCT:
                    s['distinct'].add(
                        json.dumps(value, ensure_ascii=False, sort_keys=True)[:400]
                        if isinstance(value, (list, dict)) else value)
                if isinstance(value, str):
                    s['samples'].append(value)      # 상한 없음. 전수 대조한다.
            walk(value, full, depth + 1)

    walk(payload, '')
    return stats


def is_evidence(value: str) -> bool:
    """원본 텍스트 대조의 증거로 쓸 수 있는 문자열인가."""
    t = norm_text(value)
    if len(t) < MIN_MATCH_LEN:
        return False
    if t.isdigit():
        return len(t) >= MIN_DIGIT_LEN
    return True


def domain_evidence(stat, index, power):
    """값 집합을 받아주는 원본 속성 후보와 개수 등급.

    이름 매핑은 쓰지 않는다. 값 집합 포함관계로만 후보를 찾고, 후보가 몇
    개인지와 각 후보의 판별력(그 도메인이 몇 개 컬럼을 함께 받아주는가)을
    함께 남겨 근거 강도를 임의 임계값 없이 드러낸다.

    이 근거만으로는 valid 를 주지 않는다. 측정이 보여준 이유:
    raw_attrs.fullSz 가 footer/subList@linkListIDRef 와, sublist.link_list_id_ref
    가 tr/tc@header 와 맞았다. 값이 "0"/"1" 이라 후보 423개가 전부 받아주고,
    셀 단위 컬럼끼리는 개수까지 같아 등급도 '일치'가 나온다. 도메인 포함은
    약한 긍정까지만이라는 비대칭 규칙 그대로다.
    """
    values = {v for v in stat['distinct'] if isinstance(v, str)}
    if not values:
        return None
    keys = index.candidates(values)
    if not keys:
        return None
    filled = stat['n'] - stat['empty']
    exact = [k for k in keys if index.occurrences(k) == filled]
    best = (exact or keys)[0]
    return {
        # 개수 일치 후보가 '유일'할 때만 그 속성에서 왔다고 말할 수 있다.
        # 임의 임계값이 아니라 유일성이다. 측정하면 이렇게 갈린다:
        #   text_direction 후보 5   개수일치 1  -> tc/subList@textDirection
        #   vert_align     후보 1   개수일치 1  -> tc/subList@vertAlign
        #   text_flow      후보 13  개수일치 1  -> run/tbl@textFlow
        #   fullSz         후보 423 개수일치 25 -> 모호
        #   link_list_id_ref 후보 423 개수일치 18 -> 모호
        'grade': '일치' if exact else '개수불일치',
        'unique_exact': len(exact) == 1,
        'exact_count': len(exact),
        'attribute': index.describe(best),
        'occurrences': index.occurrences(best),
        'filled': filled,
        'candidate_count': len(keys),
        'accepts_columns': power.get(best, 0),
    }


def judge(path, stat, index, power, sites, text_unique, birth_module, claims):
    """(verdict, evidence_kind, basis, blocked_reason, needed_info)

    평가 순서는 근거가 강한 것부터다. 약한 근거가 먼저 통과해 판정을
    확정해 버리면 강한 검사에 닿지도 못한다. heading_type 이 text 분기에서
    단락되어 도메인 검사에 가지 못한 것이 그 사고였다.
        code   -> domain(보조) -> text
    """
    n, empty = stat['n'], stat['empty']
    if n and empty == n:
        return ('empty', 'none', f'인스턴스 {n}개 전부 비어 있음', None, None)

    fill = (n - empty) / n if n else 0.0
    fill_note = f'채움률 {fill:.0%} ({n - empty}/{n})'   # 보고만. 판정에 쓰지 않는다.

    nonempty = list(stat['distinct'])
    if nonempty and all(isinstance(v, str) and v.strip() in PLACEHOLDERS
                        for v in nonempty):
        return ('placeholder', 'none',
                f'비지 않은 값이 전부 형식값 ({len(nonempty)}종), {fill_note}',
                None, None)

    dom = domain_evidence(stat, index, power)
    dom_note = ''
    if dom:
        dom_note = (f' | {dom["attribute"]} 도메인 [{dom["grade"]}] '
                    f'원본 {dom["occurrences"]}/컬럼 {dom["filled"]}, '
                    f'후보 {dom["candidate_count"]}개 중 개수일치 {dom["exact_count"]}개, '
                    f'이 도메인이 받아주는 컬럼 {dom["accepts_columns"]}개')

    # 1.5) domain - 개수 일치 후보가 유일하면 그 속성에서 왔다고 말할 수 있다.
    #      문서 분포가 아니라 원본 구조에 기댄 근거라 text 보다 강하다.
    #
    #      유일성은 양방향으로 봐야 한다. '이 컬럼을 받아주는 속성이 유일한가'
    #      만 보면 한 속성이 여러 컬럼의 근거가 될 수 있다. 실제로
    #      para_pr_id_ref 와 resolved_para_pr_id 가 둘 다 sec/p@paraPrIDRef 를
    #      주장했다. 이 문서에서 두 컬럼은 251개 전부 값이 같아 도메인 대조로는
    #      어느 쪽이 직접 추출인지 가려지지 않는다. 구분 불가면 결론 없음이다.
    if dom and dom['unique_exact']:
        rivals = [p for p in claims.get(dom['attribute'], ()) if p != path]
        if rivals:
            return ('unresolved', 'domain',
                    f'{dom["attribute"]} 를 {len(rivals) + 1}개 컬럼이 함께 주장, '
                    f'{fill_note}',
                    f'같은 원본 속성을 {", ".join(rivals[:2])} 도 주장한다. '
                    f'둘 중 최대 하나만 직접 추출인데 도메인 대조로는 어느 쪽인지 '
                    f'가려지지 않는다',
                    '두 컬럼의 추출식, 또는 값이 갈리는 문서에서의 재측정')
        return ('valid', 'domain',
                f'{dom["attribute"]} 요소 경로에서 값·개수 모두 일치하고 '
                f'개수 일치 후보가 유일(양방향), {fill_note}', None, None)

    # 1) code - 두 조건을 모두 만족해야 한다.
    #    (a) 원본을 읽는 표현식이어야 한다. 단순 대입(다른 변수 대입, dict
    #        리터럴 구성)은 값의 출처를 말해주지 않는다.
    #    (b) birth 단계 모듈에 있어야 한다. 같은 leaf 이름이 다른 구조에도
    #        있으므로 이름만으로 승격하면 코드 읽기를 피했던 그 오탐이 난다.
    #    (b)만으로는 근거가 되지 않는다. 컬럼이 birth 모듈에서 대입되는 것은
    #    birth 모듈의 정의상 거의 자명해서 판별력이 없다.
    confirmed = [x for x in sites
                 if x['module'] == birth_module and x['reads_attribute']]
    if confirmed:
        return ('valid', 'code',
                f'추출식 {confirmed[0]["location"]} '
                f'(birth 단계 모듈 {birth_module} 과 일치), {fill_note}{dom_note}',
                None, None)

    # 상수 게이트. domain/code 로 원본 출처가 확인되지 않은 상수는
    # 문자열 대조로 가릴 수 없다.
    if len(stat['distinct']) < MIN_DISTINCT_FOR_VALID:
        only = next(iter(stat['distinct']), None)
        return ('unresolved', 'none',
                f'값이 {only!r} 한 종류뿐, {fill_note}{dom_note}',
                '값 종류가 하나뿐이라 원본에서 온 값인지 단계가 채우는 '
                '기본값인지 구분할 수 없다. 열거형 토큰은 원본에도 있고 '
                '기본값으로도 쓰여 문서 전체 대조로는 원리상 갈리지 않는다',
                '이 값을 채우는 표현식이 읽는 원본 노드, 그리고 그 값이 '
                '원본마다 달라질 수 있는 값인지')

    # 2) text - 판별력을 본다. 이 컬럼에만 나타나는 값이 하나라도 있어야
    #    문서 고유 내용을 담았다고 볼 수 있다. 여러 컬럼이 공유하는
    #    토큰뿐이면 대조를 통과해도 이 컬럼의 것이라는 증거가 아니다.
    samples = [v for v in stat['samples']
               if is_evidence(v) and not ENUM_TOKEN.match(norm_text(v))]
    if samples:
        miss = [v for v in samples if norm_text(v) not in index.text]
        if miss:
            return ('unresolved', 'none',
                    f'원본 확인 {len(samples)-len(miss)}/{len(samples)}, '
                    f'{fill_note}{dom_note}',
                    f'값 {len(miss)}개가 원본 텍스트에서 확인되지 않음 '
                    f'(예: {norm_text(miss[0])[:40]!r}). 정규화/병합/변환된 값일 '
                    f'수 있어 원본 부재를 뜻하지 않는다',
                    '해당 값을 만든 변환 규칙, 또는 원본에서의 대응 위치')
        if text_unique:
            return ('valid', 'text',
                    f'값 {len(samples)}개 전부 원본 확인, 이 컬럼에만 나타나는 값 '
                    f'{text_unique}종, {fill_note}{dom_note}', None, None)
        return ('unresolved', 'none',
                f'값 {len(samples)}개 전부 원본 확인, 그러나 고유 값 0종, '
                f'{fill_note}{dom_note}',
                '모든 값이 다른 컬럼과 공유하는 토큰이라 원본 대조를 통과해도 '
                '이 컬럼이 원본에서 가져온 값이라는 증거가 되지 못한다',
                '이 컬럼을 채우는 표현식과 그것이 읽는 원본 노드')

    if dom:
        return ('unresolved', 'domain', f'{dom_note.lstrip(" |")}, {fill_note}',
                '값이 원본 속성 도메인 안이지만 도메인 포함만으로는 그 속성에서 '
                '온 값이라 할 수 없다. 후보가 여럿이고 셀 단위 컬럼끼리는 개수도 '
                '같아 등급이 일치로 나온다',
                '이 컬럼을 채우는 표현식, 또는 인스턴스 단위 조인 키')

    if sites:
        return ('unresolved', 'none',
                f'추출식 후보 {len(sites)}곳 있으나 birth 모듈({birth_module})과 '
                f'일치하는 것 없음, {fill_note}',
                f'같은 이름의 다른 구조일 가능성이 있어 code 근거로 올리지 않음. '
                f'예: {sites[0]["location"]}',
                '이 컬럼을 실제로 채우는 표현식의 위치')

    return ('unresolved', 'none',
            f'계산값 (타입: {"/".join(sorted(stat["types"]))}), {fill_note}',
            '원본 대조 기준 없음. 값 집합을 받아주는 원본 속성도, 추출식도 '
            '찾지 못했다. 다만 이는 도메인 대조와 코드 탐색의 한계일 뿐이며 '
            '원본에 대응 속성이 없다는 뜻은 아니다',
            '이 컬럼을 채우는 코드 위치와 그것이 읽는 원본 노드')


def main(argv=None):
    ap = argparse.ArgumentParser(description="컬럼별 최종값 출처·유의미성 판정")
    ap.add_argument('provenance', help="field_provenance --json 산출")
    ap.add_argument('--doc', default=None)
    ap.add_argument('--json', default=None, help="컬럼별 판정 결과 저장")
    args = ap.parse_args(argv)

    prov = json.loads(Path(args.provenance).read_text(encoding='utf-8'))
    stage_module = prov['stage_module']

    doc = resolve([args.doc] if args.doc else [])[0]
    if not doc.contents_dir:
        sys.exit("원본 XML(압축 해제 결과)이 없어 대조할 수 없습니다.")
    payload = json.loads(doc.final_debug.read_text(encoding='utf-8'))
    # 출처 표와 같은 규칙으로 동적 키를 접는다. 접지 않으면 경로가 어긋나
    # 그 컬럼들이 instances 0 으로 떨어진다.
    from tools.audit.field_provenance import Recorder
    probe = Recorder()
    stats = collect(payload, dynamic=probe.find_dynamic(payload))

    index = SourceIndex(doc.contents_dir)
    print(f"원본 {len(index.files)}개 파일 ({', '.join(index.files[:3])} ...) / "
          f"속성 키 {len(index.attrs)}종 / 텍스트 {len(index.text):,}자")
    print(f"  범위: {'  '.join(index.globs)}  ({__import__('tools.audit.source_index', fromlist=['x']).EXCLUDED_NOTE})")

    # 판별력: 한 속성 도메인이 몇 개 컬럼의 값 집합을 받아주는가.
    # 값이 흔할수록 많은 컬럼을 받아주고, 그만큼 근거가 약하다는 뜻이다.
    # 임의 임계값을 두는 대신 이 수치를 판정문에 그대로 노출한다.
    power = Counter()
    value_owners = defaultdict(set)
    for path in prov['fields']:
        st = stats.get(path)
        if not st:
            continue
        values = {v for v in st['distinct'] if isinstance(v, str)}
        if not values:
            continue
        for key in index.candidates(values):
            power[key] += 1
        for v in values:
            value_owners[v].add(path)

    # text 근거의 판별력. 이 컬럼에만 나타나는 값이 몇 종인가.
    # 여러 컬럼이 공유하는 열거형 토큰("NONE" 등)뿐이면 원본 대조를 통과해도
    # 이 컬럼의 값이라는 증거가 되지 못한다. domain 티어에만 판별력을 재고
    # text 는 통과/불통과 이진으로 두는 것이 비대칭이라 같은 방식으로 잰다.
    unique_counts = {}
    for path in prov['fields']:
        st = stats.get(path)
        if not st:
            unique_counts[path] = 0
            continue
        values = {v for v in st['distinct'] if isinstance(v, str)}
        unique_counts[path] = sum(1 for v in values if len(value_owners[v]) == 1)

    # 역방향 유일성용: 어느 원본 속성을 어느 컬럼들이 주장하는가.
    claims = defaultdict(list)
    for path in prov['fields']:
        st = stats.get(path)
        if not st:
            continue
        dom = domain_evidence(st, index, power)
        if dom and dom['unique_exact']:
            claims[dom['attribute']].append(path)

    out = {}
    for path, info in sorted(prov['fields'].items()):
        stat = stats.get(path)
        if stat is None:
            stat = {'n': 0, 'empty': 0, 'distinct': set(), 'samples': [],
                    'types': set(), 'first': None}
        writers = info['writers']
        last = writers[-1] if writers else info['birth']
        sites = find_extraction_sites(path.split('.')[-1])
        birth_module = stage_module.get(info['birth'], '')
        verdict, kind, basis, blocked, needed = judge(
            path, stat, index, power, sites, unique_counts.get(path, 0),
            birth_module, claims)

        out[path] = {
            # 최종값이 아니라 표본이다. 한 컬럼에 인스턴스가 수백 개이므로
            # 단일 '최종값'이 존재하지 않는다. 워크 순서상 처음 만난 비지
            # 않은 값을 성격 파악용으로 싣는다.
            'sample_value': stat['first'],
            'verdict': verdict,
            'evidence_kind': kind,
            'final_source': f"{last} ({stage_module.get(last, '?')})",
            'overwrite_trace': (' -> '.join(writers) if len(writers) > 1 else None),
            'basis': basis,
            'blocked_reason': blocked,
            'needed_info': needed,
            'evidence_detail': {
                'extraction_sites': [x['location'] for x in sites][:3],
                'birth_module': birth_module,
                'module_confirmed': [x['location'] for x in sites
                                     if x['module'] == birth_module][:3],
                'unique_values': unique_counts.get(path, 0),
                'shared_with': [p for p in claims.get(
                    (domain_evidence(stat, index, power) or {}).get('attribute'), ())
                    if p != path][:3],
            },
            'instances': stat['n'],
            'empty': stat['empty'],
            'fill_rate': round((stat['n'] - stat['empty']) / stat['n'], 4) if stat['n'] else 0,
            'distinct': len(stat['distinct']),
            'checked_values': len([v for v in stat['samples'] if is_evidence(v)]),
        }

    counts = Counter(v['verdict'] for v in out.values())
    overwritten = [p for p, v in out.items() if v['overwrite_trace']]
    unresolved = [p for p, v in out.items() if v['verdict'] == 'unresolved']

    print()
    print("=" * 96)
    print("요약")
    print("=" * 96)
    print(f"  전체 컬럼        {len(out)}개")
    print(f"  덮어쓰기 발생    {len(overwritten)}개")
    print(f"  unresolved       {len(unresolved)}개")
    print()
    for k in ('valid', 'empty', 'placeholder', 'unresolved', 'mismatched'):
        print(f"    {k:12s} {counts.get(k, 0):5d}개")
    print()
    print("  근거 종류:", dict(Counter(
        v['evidence_kind'] for v in out.values() if v['verdict'] == 'valid')),
        "(valid 기준)")
    print()
    print("  mismatched 는 이 도구가 만들지 않는다. '값은 있으나 컬럼 의도와")
    print("  다른 정보'는 의미 판단이라 측정으로 가려지지 않는다.")

    print()
    print("=" * 96)
    print("덮어쓰기 발생 컬럼 전체")
    print("=" * 96)
    for p in sorted(overwritten):
        print(f"  {p}")
        print(f"      {out[p]['overwrite_trace']}")
        print(f"      최종: {out[p]['final_source']}  판정: {out[p]['verdict']}")

    print()
    print("=" * 96)
    print("unresolved 사유별 분포")
    print("=" * 96)
    reasons = Counter(v['blocked_reason'].split('.')[0] if v['blocked_reason'] else '?'
                      for v in out.values() if v['verdict'] == 'unresolved')
    for r, c in reasons.most_common():
        print(f"  {c:5d}개  {r[:80]}")

    print()
    print("=" * 96)
    print("valid 판정 컬럼 (원본 XML 에서 확인된 값)")
    print("=" * 96)
    for p, v in sorted(out.items()):
        if v['verdict'] == 'valid':
            print(f"  [{v['evidence_kind']:6s}] {p[:52]:52s} {v['basis'][:56]}")

    print()
    print("=" * 96)
    print("회귀 검사")
    print("=" * 96)
    failures = []
    for path, expect, why in KNOWN_NOT_VALID:
        got = out.get(path, {}).get('verdict')
        ok = got != 'valid'
        print(f"  [{'OK ' if ok else 'FAIL'}] {path[-58:]:58s} {got} / {why}")
        if not ok:
            failures.append(path)
    if failures:
        print(f"  -> {len(failures)}건 실패. 결함으로 확정된 컬럼이 valid 로 나왔다.")

    if args.json:
        Path(args.json).write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"\n-> {args.json} 저장 (컬럼 {len(out)}개 전수)")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
