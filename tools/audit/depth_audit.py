"""DEPTH가 원본 문서의 시각 구조와 일치하는지 전수 감사.

시각 신호(원본 XML paraPr/charPr에서 온 값):
  indent_key = margin_left + intent   들여쓰기
  font_size                            글자 크기
  bold_ratio                           굵기
문서 순서: reading_order_index (= XML 등장 순서)

모든 위반 유형을 빠짐없이 집계한다.
"""

import json
from collections import Counter, defaultdict

from .documents import enable_utf8_stdout, resolve

enable_utf8_stdout()

TOTAL = Counter()
SAMPLES = defaultdict(list)


def indent_of(b):
    sf = b.get('style_features') or {}
    ml = sf.get('margin_left') or 0
    ind = sf.get('indent') or 0
    return ml + ind


def audit(label, path):
    fd = json.load(open(path, encoding='utf-8'))
    blocks = sorted(fd['blocks_document']['blocks'],
                    key=lambda b: b.get('reading_order_index') or 0)
    print(f"\n{'='*76}\n{label}  (블록 {len(blocks)}개)\n{'='*76}")

    body = [b for b in blocks if b.get('depth_band') == 'body']
    stat = Counter()

    # ── 1. depth 트리 유효성: depth d 블록 앞에 같은 섹션 d-1 블록이 있어야 함
    seen_depth_by_sec = defaultdict(set)
    for b in blocks:
        if b.get('depth_band') != 'body':
            continue
        sec = b.get('section_index')
        d = b.get('depth') or 0
        if d > 0 and (d - 1) not in seen_depth_by_sec[sec]:
            stat['1_부모없는depth'] += 1
            if len(SAMPLES['1_부모없는depth']) < 5:
                SAMPLES['1_부모없는depth'].append(
                    (label, b['block_id'], d, (b.get('text_content') or '')[:38]))
        seen_depth_by_sec[sec].add(d)

    # ── 2. depth 점프 (직전 의미 블록 대비 +2 이상)
    prev = None
    for b in body:
        if not (b.get('text_content') or '').strip() and b['block_type'] == 'paragraph':
            continue
        d = b.get('depth') or 0
        if prev is not None and d - prev > 1:
            stat['2_depth점프'] += 1
            if len(SAMPLES['2_depth점프']) < 5:
                SAMPLES['2_depth점프'].append(
                    (label, b['block_id'], f"{prev}->{d}", (b.get('text_content') or '')[:38]))
        prev = d

    # ── 3. 들여쓰기 역전: 더 깊은 블록이 더 왼쪽
    paras = [b for b in body if b['block_type'] == 'paragraph'
             and (b.get('text_content') or '').strip()]
    by_depth_indent = defaultdict(list)
    for b in paras:
        by_depth_indent[b.get('depth') or 0].append(indent_of(b))

    depths = sorted(by_depth_indent)
    for i in range(len(depths) - 1):
        d1, d2 = depths[i], depths[i + 1]
        m1 = sorted(by_depth_indent[d1])[len(by_depth_indent[d1]) // 2]
        m2 = sorted(by_depth_indent[d2])[len(by_depth_indent[d2]) // 2]
        if m2 < m1:
            stat['3_들여쓰기역전(depth중앙값)'] += 1
            SAMPLES['3_들여쓰기역전(depth중앙값)'].append(
                (label, f"depth{d1}(중앙값 {m1}) > depth{d2}(중앙값 {m2})", '', ''))

    # ── 4. 인접 문단 들여쓰기와 depth 방향 불일치
    for a, b in zip(paras, paras[1:]):
        da, db = a.get('depth') or 0, b.get('depth') or 0
        ia, ib = indent_of(a), indent_of(b)
        if da < db and ib < ia - 50:
            stat['4_깊어졌는데_왼쪽으로'] += 1
            if len(SAMPLES['4_깊어졌는데_왼쪽으로']) < 5:
                SAMPLES['4_깊어졌는데_왼쪽으로'].append(
                    (label, b['block_id'], f"d{da}->{db} indent {ia}->{ib}",
                     (b.get('text_content') or '')[:34]))
        if da > db and ib > ia + 50:
            stat['5_얕아졌는데_오른쪽으로'] += 1
            if len(SAMPLES['5_얕아졌는데_오른쪽으로']) < 5:
                SAMPLES['5_얕아졌는데_오른쪽으로'].append(
                    (label, b['block_id'], f"d{da}->{db} indent {ia}->{ib}",
                     (b.get('text_content') or '')[:34]))

    # ── 6. heading 글자 크기 역전: 얕은 heading이 더 작음
    heads = [b for b in paras if b.get('semantic_role') == 'section_heading']
    size_by_depth = defaultdict(list)
    for b in heads:
        fs = (b.get('style_features') or {}).get('font_size')
        if fs:
            size_by_depth[b.get('depth') or 0].append(fs)
    hd = sorted(size_by_depth)
    for i in range(len(hd) - 1):
        d1, d2 = hd[i], hd[i + 1]
        a1 = sum(size_by_depth[d1]) / len(size_by_depth[d1])
        a2 = sum(size_by_depth[d2]) / len(size_by_depth[d2])
        if a2 > a1 + 0.1:
            stat['6_heading글자크기역전'] += 1
            SAMPLES['6_heading글자크기역전'].append(
                (label, f"depth{d1}={a1:.1f}pt < depth{d2}={a2:.1f}pt", '', ''))

    # ── 7. 같은 스타일 클러스터인데 depth가 갈림
    cl = defaultdict(set)
    for b in paras:
        cid = (b.get('style_features') or {}).get('style_cluster_id')
        if cid:
            cl[cid].add(b.get('depth') or 0)
    for cid, ds in cl.items():
        if len(ds) > 1:
            stat['7_동일스타일_depth분산'] += 1
            if len(SAMPLES['7_동일스타일_depth분산']) < 6:
                SAMPLES['7_동일스타일_depth분산'].append(
                    (label, cid, f"depth {sorted(ds)}", ''))

    # ── 8. 표/이미지가 직전 heading보다 얕음
    last_head = None
    for b in body:
        if b.get('semantic_role') == 'section_heading':
            last_head = b.get('depth') or 0
        elif b['block_type'] in ('table', 'image', 'shape', 'shape_group'):
            d = b.get('depth') or 0
            if last_head is not None and d <= last_head:
                stat['8_개체가_직전heading보다_얕음'] += 1
                if len(SAMPLES['8_개체가_직전heading보다_얕음']) < 5:
                    SAMPLES['8_개체가_직전heading보다_얕음'].append(
                        (label, b['block_id'], f"heading d{last_head} >= obj d{d}", b['block_type']))

    # ── 9. depth 미부여 / 음수
    for b in blocks:
        if b.get('depth') is None:
            stat['9_depth없음'] += 1
        elif (b.get('depth') or 0) < 0:
            stat['9_depth음수'] += 1

    # ── 10. 목차 anchor 블록의 depth가 목차 선언과 다름
    for b in blocks:
        tm = b.get('toc_match') or {}
        if tm.get('matched'):
            want = tm.get('anchor_depth')
            got = b.get('depth')
            if want is not None and want != got:
                stat['10_toc선언과_depth불일치'] += 1
                if len(SAMPLES['10_toc선언과_depth불일치']) < 5:
                    SAMPLES['10_toc선언과_depth불일치'].append(
                        (label, b['block_id'], f"toc {want} != depth {got}",
                         (b.get('text_content') or '')[:34]))

    print(f"  body 블록 {len(body)} / 텍스트 문단 {len(paras)} / heading {len(heads)}")
    print(f"  depth 분포: {dict(sorted(Counter((b.get('depth') or 0) for b in body).items()))}")
    for k in sorted(stat):
        print(f"    {k:32s} {stat[k]:5d}")
        TOTAL[k] += stat[k]
    if not stat:
        print("    이상 없음")
    return stat


def main():
    documents = resolve()
    for doc in documents:
        audit(doc.label, doc.final_debug)

    print(f"\n{'='*76}\n{len(documents)}개 문서 합계\n{'='*76}")
    for k in sorted(TOTAL):
        print(f"  {k:32s} {TOTAL[k]:5d}")

    print(f"\n{'='*76}\n유형별 표본\n{'='*76}")
    for k in sorted(SAMPLES):
        print(f"\n[{k}]")
        for s in SAMPLES[k][:5]:
            print(f"   {s[0]:6s} {s[1]}  {s[2]}  {s[3]}")


if __name__ == '__main__':
    main()
