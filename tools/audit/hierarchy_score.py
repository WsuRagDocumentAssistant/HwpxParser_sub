"""문서에 보이는 번호/마커 체계와 depth가 같은 방향으로 움직이는지 채점.

채점 규칙
  1) 마커(□/○/-)는 '그 구간 안의 상대 표기'이므로 같은 anchor_scope 안에서만 비교
  2) 숫자 개요는 문서 절대 레벨이므로 scope와 무관하게 비교
  3) 서로 다른 체계(마커 vs 숫자)는 비교하지 않음
  4) 연도형 숫자(첫 성분 > 100)는 개요 번호가 아니므로 제외

1)과 4)를 빼면 불일치가 실제보다 크게 잡힌다. 마커는 구간마다 다시 시작하는
표기라 구간을 넘어 비교하면 뜻이 없고, '2024. 6.' 같은 날짜는 개요 번호가
아니기 때문이다.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

from tools.audit.documents import REPO_ROOT, enable_utf8_stdout, resolve

sys.path.insert(0, str(REPO_ROOT))
enable_utf8_stdout()

from hwpx_analysis.add_toc_depth0_anchors import (          # noqa: E402
    _numbering_anchor_level, _split_numbering, _strip_page_suffix)
from hwpx_analysis.correct_title_box_depths import _MARKER_RELATIVE_LEVELS   # noqa: E402

OUTLINE_MAX = 100   # 개요 번호가 이보다 크면 연도/수량으로 본다


def signal(text):
    """(체계, 레벨). 판정 불가면 (None, None)."""
    t = (text or '').strip()
    if not t:
        return None, None
    line, _ = _strip_page_suffix(t)
    numbering, _x = _split_numbering(line)
    lv = _numbering_anchor_level(numbering)
    if lv is not None:
        head = re.split(r'[.\-]', str(numbering).strip())[0]
        try:
            if int(re.sub(r'\D', '', head) or 0) > OUTLINE_MAX:
                return None, None          # 2024. 6. 같은 연도
        except ValueError:
            pass
        return 'numbering', lv
    for m, level in _MARKER_RELATIVE_LEVELS:
        if t.startswith(m):
            return 'marker', level
    return None, None


def scope_of(b):
    dc = b.get('depth_correction')
    if isinstance(dc, dict):
        return dc.get('anchor_scope_id')
    return None


def score(label, final_debug: Path, total: Counter, examples: list):
    fd = json.load(open(final_debug, encoding='utf-8'))
    blocks = sorted(fd['blocks_document']['blocks'],
                    key=lambda b: b.get('reading_order_index') or 0)

    sc = []
    for b in blocks:
        if (b.get('visibility') or {}).get('include_in_preview') is False:
            continue
        text = (b.get('normalized_text') or b.get('text_content') or '')
        sys_, lv = signal(text)
        if sys_ is None:
            continue
        sc.append((b, sys_, lv, text))

    doc = Counter()
    for i in range(len(sc) - 1):
        b1, s1, v1, t1 = sc[i]
        b2, s2, v2, t2 = sc[i + 1]
        d1, d2 = b1.get('depth') or 0, b2.get('depth') or 0

        if s1 != s2:
            doc['비교불가_체계다름'] += 1
            continue
        if s1 == 'marker':
            if scope_of(b1) != scope_of(b2) or scope_of(b1) is None:
                doc['비교불가_scope다름'] += 1
                continue
            doc['비교_마커(동일scope)'] += 1
        else:
            doc['비교_숫자개요'] += 1

        sv = (v2 > v1) - (v2 < v1)
        sd = (d2 > d1) - (d2 < d1)
        if sv == sd:
            doc['일치'] += 1
        else:
            doc['불일치'] += 1
            doc[f"불일치_{s1}"] += 1
            if len(examples) < 12:
                examples.append((label, s1, t1[:40], d1, v1, t2[:40], d2, v2,
                                 scope_of(b1), scope_of(b2)))

    print(f"--- {label}")
    cmp_n = doc['비교_마커(동일scope)'] + doc['비교_숫자개요']
    print(f"    비교 가능 {cmp_n}쌍 "
          f"(숫자개요 {doc['비교_숫자개요']}, 마커/동일scope {doc['비교_마커(동일scope)']})")
    print(f"    비교 불가 {doc['비교불가_체계다름'] + doc['비교불가_scope다름']}쌍 "
          f"(체계다름 {doc['비교불가_체계다름']}, scope다름 {doc['비교불가_scope다름']})")
    if cmp_n:
        print(f"    불일치 {doc['불일치']} / {cmp_n} ({100*doc['불일치']/cmp_n:.1f}%)   "
              f"일치율 {100*doc['일치']/cmp_n:.1f}%")
    total.update(doc)
    print()


def main():
    documents = resolve()
    total = Counter()
    examples = []
    for doc in documents:
        score(doc.label, doc.final_debug, total, examples)

    print("=" * 80)
    print("합계")
    print("=" * 80)
    cmp_n = total['비교_마커(동일scope)'] + total['비교_숫자개요']
    skip = total['비교불가_체계다름'] + total['비교불가_scope다름']
    print(f"  비교 가능      {cmp_n}쌍")
    print(f"     숫자 개요        {total['비교_숫자개요']}")
    print(f"     마커(동일 scope) {total['비교_마커(동일scope)']}")
    print(f"  비교 불가      {skip}쌍")
    print(f"     체계 다름        {total['비교불가_체계다름']}")
    print(f"     scope 다름       {total['비교불가_scope다름']}")
    print()
    print(f"  불일치 {total['불일치']} / {cmp_n}  ({100*total['불일치']/max(cmp_n,1):.1f}%)")
    print(f"  일치   {total['일치']} / {cmp_n}  ({100*total['일치']/max(cmp_n,1):.1f}%)")
    print(f"     불일치 내역: 숫자개요 {total['불일치_numbering']} / 마커 {total['불일치_marker']}")

    print("\n" + "=" * 80)
    print("남은 불일치 사례")
    print("=" * 80)
    for lab, s, t1, d1, v1, t2, d2, v2, sc1, sc2 in examples:
        print(f"\n  [{lab}] {s}  scope {sc1} / {sc2}")
        print(f"     눈 {v1} / depth {d1}   {t1!r}")
        print(f"     눈 {v2} / depth {d2}   {t2!r}")


if __name__ == '__main__':
    main()
