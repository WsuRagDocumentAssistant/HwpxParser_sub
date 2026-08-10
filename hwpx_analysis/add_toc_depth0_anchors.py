#================================================
# add_toc_depth0_anchors.py
# 목차(TOC) 기반 동적 depth anchor 생성
#
# 역할:
#   A. section 0/1에서 "목차" 앵커 탐지 (공백 제거 후 text == "목차")
#   B. 앵커 이후 목차 표/블록에서 toc_entries 추출
#      - depth는 numbering 성분 수로 동적 결정 (상한 없음):
#        '1' -> depth 0, '3.1' -> depth 1, '3.1.1' -> depth 2, ...
#      - 로마숫자 그룹(Ⅱ-1, Ⅰ 등)은 anchor에서 제외
#   C. 터미널에 [TOC depth0 list] / [TOC depth0 match] 출력
#   D. 본문 blocks와 순차 매칭 (normalized title key 기준, cursor 전진)
#   E. 매칭된 block에 toc_match / heading_seed / depth_source 부여 +
#      depth 0 candidate 주입 + depth 0 확정
#
# 실행 위치: Stage 8-A(resolve_block_depth_candidates) 이후,
#            Stage 8-B(apply_depth_constraints) 이전.
#
# fallback:
#   앵커 탐지 실패 또는 매칭 0건이면 blocks.json을 변경하지 않고
#   기존 depth 0 추정 로직(title_box outline anchor 학습)이 그대로 동작한다.
#
# 이 단계가 하지 않는 것:
#   - depth 1 이하 판정 로직 변경
#   - 표/이미지/도형 내부 계층화 변경
#   - 기존 출력 schema 필드 제거/변경 (toc_match/heading_seed/depth_source만 추가)
#================================================

from __future__ import annotations

from typing import Any

from hwpx_analysis.pipeline_models import BlocksDocument

# toc 기반 anchor임을 나타내는 depth_source 값 (다른 단계에서 참조)
# depth는 목차 numbering 성분 수에서 동적으로 결정된다: "toc_depth{N}_anchor"
TOC_DEPTH0_SOURCE = "toc_depth0_anchor"
_TOC_SOURCE_PREFIX = "toc_depth"
_TOC_SOURCE_SUFFIX = "_anchor"


def toc_anchor_source(level: int) -> str:
    """anchor depth N의 depth_source 값을 만든다."""
    return f"{_TOC_SOURCE_PREFIX}{level}{_TOC_SOURCE_SUFFIX}"


# digit-insensitive fallback 매칭을 허용할 최소 key 길이
# (숫자 제거 후 key가 너무 짧으면 오매칭 위험이 커서 fallback을 쓰지 않는다)
_DIGIT_INSENSITIVE_MIN_KEY_LEN = 4

# 목차 앵커로 인정할 정규화 텍스트
_TOC_ANCHOR_TEXT = "목차"

# 앵커 탐색 대상 section
_ANCHOR_SECTIONS = (0, 1)

# 목차형 표 판정: page number를 가진 라인 비율/최소 개수
_TOC_TABLE_MIN_PAGE_LINES = 2
_TOC_TABLE_PAGE_LINE_RATIO = 0.4

# 비교 key 정규화용 문자 클래스 (문서별 문자열이 아닌 타이포그래피 변형 통일)
_QUOTE_LIKE = frozenset("'‘’‚‛“”`´ʻʼ′″\"")
_DOT_LIKE = frozenset("․‧ㆍ•∙⋅・")
_DASH_LIKE = frozenset("‐‑‒–—―⁃‧")
_TILDE_LIKE = frozenset("～∼〜")
_LEADER_CHARS = frozenset(" .…⋯·․‧")

# numbering prefix에 허용되는 로마 숫자 문자 (correct_title_box_depths와 동일 클래스)
_ROMAN_CHARS = frozenset("ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫIVX")
_NUMBERING_SEPARATORS = frozenset(".-·")


#------------------------------------------------
# 텍스트 정규화
#------------------------------------------------

def _strip_all_whitespace(text: str | None) -> str:
    return "".join((text or "").split())


def _normalize_title_key(text: str | None) -> str:
    """
    비교용 title key 생성: 공백 제거, 따옴표류 제거,
    가운뎃점/대시/물결 변형 통일. 괄호/한글/숫자 등 제목 본문은 유지한다.
    """
    out: list[str] = []
    for ch in text or "":
        if ch.isspace() or ch in _QUOTE_LIKE:
            continue
        if ch in _DOT_LIKE:
            out.append("·")
        elif ch in _DASH_LIKE:
            out.append("-")
        elif ch in _TILDE_LIKE:
            out.append("~")
        else:
            out.append(ch)
    return "".join(out)


def _split_numbering(text: str | None) -> tuple[str | None, str]:
    """
    선두 numbering prefix와 나머지 제목을 분리한다.
    numbering으로 인정하는 조건:
      - 선두 연속 구간이 숫자/로마숫자/구분자(., -)로만 구성
      - 숫자 또는 로마숫자를 최소 1자 포함
      - 구간 끝이 문자열 끝이거나 공백 앞이거나 '.'로 종료
        ("2024년", "3S 지수"처럼 제목이 숫자로 시작하는 경우는 제외)
    """
    stripped = (text or "").strip()
    if not stripped:
        return None, ""

    i = 0
    while i < len(stripped) and (
        stripped[i].isdigit()
        or stripped[i] in _NUMBERING_SEPARATORS
        or stripped[i] in _ROMAN_CHARS
    ):
        i += 1

    prefix = stripped[:i]
    has_number = any(ch.isdigit() or ch in _ROMAN_CHARS for ch in prefix)
    boundary_ok = i >= len(stripped) or stripped[i].isspace() or prefix.endswith(".")

    if not prefix or not has_number or not boundary_ok:
        return None, stripped

    numbering = prefix.rstrip(".")
    title = stripped[i:].strip()
    return (numbering or None), title


def _numbering_anchor_level(numbering: str | None) -> int | None:
    """
    numbering의 anchor depth를 성분 수로 동적으로 판정한다.
    - 모든 성분이 아라비아 숫자면: depth = 성분 수 - 1 (상한 없음)
      예) '1' -> 0, '3.1' -> 1, '3.1.1' -> 2, '1.2.3.4' -> 3, ...
    - 로마숫자 등 아라비아 숫자가 아닌 성분이 있으면 anchor 대상 아님 (None)
      예) 'Ⅱ-1', 'Ⅰ'
    구분자는 '.', '-'를 동일하게 취급한다.
    """
    if not numbering:
        return None
    parts = [p for p in numbering.replace("-", ".").split(".") if p]
    if not parts or not all(p.isdigit() for p in parts):
        return None
    return len(parts) - 1


def _strip_page_suffix(line: str) -> tuple[str, str | None]:
    """
    목차 라인 끝의 page number와 점선 leader를 분리한다.
    tab 구분이 있으면 tab 우측을 page로 본다. 없으면 점선/넓은 공백으로
    분리된 끝자리 숫자만 page로 본다 (제목 자체의 숫자는 유지).
    """
    if "\t" in line:
        left, page = line.rsplit("\t", 1)
        return left.rstrip(), (page.strip() or None)

    stripped = line.rstrip()
    j = len(stripped)
    while j > 0 and stripped[j - 1].isdigit():
        j -= 1
    if j == len(stripped) or j == 0:
        return stripped, None

    k = j
    while k > 0 and stripped[k - 1] in _LEADER_CHARS:
        k -= 1
    separator = stripped[k:j]
    if len(separator) >= 2:
        return stripped[:k].rstrip(), stripped[j:]
    return stripped, None


#------------------------------------------------
# 역할 A: 목차 앵커 탐지
#------------------------------------------------

def _iter_table_paragraph_texts(table: dict[str, Any]):
    """tables.json 표의 셀 텍스트를 row_addr, col_addr 순서로 순회한다."""
    cells: list[dict[str, Any]] = []
    for row in table.get("rows") or []:
        cells.extend(row.get("cells") or [])
    cells.sort(key=lambda c: (c.get("row_addr") or 0, c.get("col_addr") or 0))
    for cell in cells:
        for paragraph in cell.get("paragraphs") or []:
            yield paragraph.get("text") or ""


def _find_toc_anchor(
    tables: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    section 0/1에서 공백 제거 후 '목차'인 텍스트를 찾는다.
    paragraph block 앵커와 표 셀 내부 앵커를 모두 지원하며,
    앵커의 문서 내 위치(reading_order_index)를 함께 기록한다.
    """
    block_by_table_id = {
        (b.get("structure_features") or {}).get("table_id"): b
        for b in blocks
        if (b.get("structure_features") or {}).get("table_id")
    }

    # 1) 본문 paragraph block 자체가 "목차"인 경우
    for block in blocks:
        if block.get("section_index") not in _ANCHOR_SECTIONS:
            continue
        if block.get("block_type") != "paragraph":
            continue
        if _strip_all_whitespace(block.get("text_content")) == _TOC_ANCHOR_TEXT:
            return {
                "kind": "paragraph_block",
                "section_index": block["section_index"],
                "block_id": block["block_id"],
                "reading_order_index": block.get("reading_order_index") or 0,
                "table_id": None,
            }

    # 2) 표 셀 문단 중 "목차" 문단이 있는 경우 (표지형 title box 등)
    for table in tables:
        if table.get("section_index") not in _ANCHOR_SECTIONS:
            continue
        for paragraph_text in _iter_table_paragraph_texts(table):
            if _strip_all_whitespace(paragraph_text) == _TOC_ANCHOR_TEXT:
                anchor_block = block_by_table_id.get(table.get("table_id"))
                return {
                    "kind": "table_cell",
                    "section_index": table["section_index"],
                    "block_id": anchor_block["block_id"] if anchor_block else None,
                    "reading_order_index": (
                        anchor_block.get("reading_order_index")
                        if anchor_block else 0
                    ) or 0,
                    "table_id": table.get("table_id"),
                }
    return None


#------------------------------------------------
# 역할 B: 목차 항목 추출
#------------------------------------------------

def _parse_toc_line(line: str) -> dict[str, Any] | None:
    """목차 라인 하나를 entry dict로 파싱한다. 빈 라인은 None."""
    raw = line.strip()
    if not raw:
        return None
    title_part, page_text = _strip_page_suffix(raw)
    numbering, title = _split_numbering(title_part)
    return {
        "raw_text": raw,
        "numbering_text": numbering,
        "title": title,
        "title_key": _normalize_title_key(title),
        "page_text": page_text,
    }


def _extract_entries_from_table(table: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for paragraph_text in _iter_table_paragraph_texts(table):
        for line in paragraph_text.split("\n"):
            entry = _parse_toc_line(line)
            if entry is not None:
                entries.append(entry)
    return entries


def _looks_like_toc_entries(entries: list[dict[str, Any]]) -> bool:
    """page number를 가진 라인이 충분하면 목차형 블록으로 판정한다."""
    if not entries:
        return False
    page_lines = sum(1 for e in entries if e["page_text"] is not None)
    if page_lines < _TOC_TABLE_MIN_PAGE_LINES:
        return False
    return page_lines / len(entries) >= _TOC_TABLE_PAGE_LINE_RATIO


def _extract_toc_entries(
    tables: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
    anchor: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    앵커 이후의 목차 내용 표를 문서 순서대로 읽어 entries를 만든다.
    연속된 목차형 표를 모두 소비하고, 목차형이 아닌 표에서 멈춘다.
    표가 없으면 앵커 이후 paragraph 블록에서 목차형 라인을 읽는다(fallback).
    반환: (entries, 목차 소스 table_id 목록)
    """
    section = anchor["section_index"]
    ordered_tables = sorted(
        (t for t in tables if t.get("section_index") == section),
        key=lambda t: t.get("table_index") or 0,
    )

    # 앵커 이후 표부터 스캔 (앵커가 표 자신이면 그 다음 표부터)
    start_index = 0
    if anchor["table_id"] is not None:
        for i, table in enumerate(ordered_tables):
            if table.get("table_id") == anchor["table_id"]:
                start_index = i + 1
                break

    entries: list[dict[str, Any]] = []
    source_table_ids: list[str] = []
    for table in ordered_tables[start_index:]:
        table_entries = _extract_entries_from_table(table)
        if not _looks_like_toc_entries(table_entries):
            if source_table_ids:
                break  # 목차형 표 연속 구간 종료
            continue
        entries.extend(table_entries)
        source_table_ids.append(table.get("table_id"))

    if entries:
        return entries, source_table_ids

    # fallback: 목차가 표가 아니라 문단 나열인 문서
    anchor_order = anchor["reading_order_index"]
    miss_streak = 0
    for block in blocks:
        if block.get("section_index") != section:
            continue
        if (block.get("reading_order_index") or 0) <= anchor_order:
            continue
        if block.get("block_type") != "paragraph":
            continue
        entry = _parse_toc_line(block.get("text_content") or "")
        if entry is None:
            continue
        if entry["page_text"] is not None or entry["numbering_text"] is not None:
            entries.append(entry)
            miss_streak = 0
        else:
            miss_streak += 1
            if entries and miss_streak >= 3:
                break
    return entries, source_table_ids


def _select_anchor_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    anchor 대상 entry(depth 0/1)를 목차 등장 순서대로 선별한다.
    toc_index는 같은 depth 레벨 내에서의 순번이다.
    """
    selected: list[dict[str, Any]] = []
    level_counters: dict[int, int] = {}
    for entry in entries:
        level = _numbering_anchor_level(entry["numbering_text"])
        if level is None or not entry["title_key"]:
            continue
        selected.append({
            **entry,
            "anchor_depth": level,
            "toc_index": level_counters.get(level, 0),
        })
        level_counters[level] = level_counters.get(level, 0) + 1
    return selected


#------------------------------------------------
# 역할 D: 본문 순차 매칭
#------------------------------------------------

def _block_match_source_text(block: dict[str, Any]) -> str:
    """블록의 제목 비교 대상 텍스트 (paragraph text 또는 title_box title)."""
    text = (block.get("text_content") or "").strip()
    if text:
        return text
    ref = block.get("table_hierarchy_ref") or {}
    return (ref.get("title_text") or "").strip()


def _block_title_key(block: dict[str, Any]) -> str:
    """블록 텍스트에서 numbering prefix를 떼고 정규화한 비교 key."""
    text = _block_match_source_text(block)
    if not text:
        return ""
    _, title = _split_numbering(text)
    return _normalize_title_key(title)


def _strip_digits(key: str) -> str:
    """digit-insensitive 비교용: key에서 숫자만 제거한다.
    (목차 '자율성과지표명 1 : ...' vs 본문 '자율성과지표명 : ...'처럼
    번호 삽입 여부만 다른 제목을 흡수하기 위한 2차 기준)"""
    return "".join(ch for ch in key if not ch.isdigit())


def _match_anchor_entries_to_blocks(
    anchor_entries: list[dict[str, Any]],
    ordered_blocks: list[dict[str, Any]],
    anchor: dict[str, Any],
    toc_source_table_ids: list[str],
) -> list[dict[str, Any]]:
    """
    toc anchor entry(depth 0/1)를 본문 blocks와 순차 매칭한다.
    entry는 목차 등장 순서 그대로이며, toc[i]가 매칭된 위치 다음부터
    toc[i+1]을 찾는다 (cursor 전진 — 동일 제목 오매칭 방지).
    1차: 정규화 key 완전일치. 2차: 숫자 제거 key 일치(fallback).
    반환: [{entry, block or None, match_method}] (entry 순서 유지)
    """
    excluded_table_ids = set(toc_source_table_ids)
    if anchor["table_id"] is not None:
        excluded_table_ids.add(anchor["table_id"])

    anchor_order = anchor["reading_order_index"]
    candidates: list[dict[str, Any]] = []
    for block in ordered_blocks:
        if (block.get("reading_order_index") or 0) <= anchor_order:
            continue
        table_id = (block.get("structure_features") or {}).get("table_id")
        if table_id in excluded_table_ids:
            continue
        candidates.append(block)

    results: list[dict[str, Any]] = []
    cursor = 0
    for entry in anchor_entries:
        matched_block = None
        match_method = None
        base = f"toc_depth{entry['anchor_depth']}_sequential_normalized"

        # 1차: 완전일치
        for index in range(cursor, len(candidates)):
            if _block_title_key(candidates[index]) == entry["title_key"]:
                matched_block = candidates[index]
                match_method = base
                cursor = index + 1
                break

        # 2차: digit-insensitive fallback
        if matched_block is None:
            entry_loose = _strip_digits(entry["title_key"])
            if len(entry_loose) >= _DIGIT_INSENSITIVE_MIN_KEY_LEN:
                for index in range(cursor, len(candidates)):
                    block_key = _block_title_key(candidates[index])
                    if block_key and _strip_digits(block_key) == entry_loose:
                        matched_block = candidates[index]
                        match_method = base + "_digit_insensitive"
                        cursor = index + 1
                        break

        results.append({
            "entry": entry,
            "block": matched_block,
            "match_method": match_method,
        })
    return results


#------------------------------------------------
# 역할 E: depth 0 anchor 반영
#------------------------------------------------

def _apply_toc_anchor_to_block(
    block: dict[str, Any],
    entry: dict[str, Any],
    match_method: str,
) -> None:
    old_depth = block.get("depth")
    anchor_depth = entry["anchor_depth"]
    source = toc_anchor_source(anchor_depth)

    block["toc_match"] = {
        "matched": True,
        "toc_index": entry["toc_index"],
        "toc_numbering": entry["numbering_text"],
        "toc_title": entry["title"],
        "anchor_depth": anchor_depth,
        "match_method": match_method,
    }
    block["heading_seed"] = True
    block["depth_source"] = source
    block["depth"] = anchor_depth

    # depth 후보에 최우선 anchor 후보 주입 (기존 후보는 근거로 보존)
    candidates = block.get("depth_candidates") or []
    for candidate in candidates:
        if candidate.get("depth") == anchor_depth:
            candidate["score"] = 1.0
            if source not in candidate.get("signals", []):
                candidate.setdefault("signals", []).append(source)
            break
    else:
        candidates.insert(0, {
            "depth": anchor_depth,
            "score": 1.0,
            "signals": [source],
        })
    candidates.sort(key=lambda c: (-c["score"], c["depth"]))
    block["depth_candidates"] = candidates
    block["selected_depth_candidate_index"] = next(
        i for i, c in enumerate(candidates) if c["depth"] == anchor_depth
    )

    block.setdefault("evidence", []).append(
        f"{source}: toc_index={entry['toc_index']} "
        f"numbering={entry['numbering_text']} depth {old_depth} -> {anchor_depth}"
    )


#------------------------------------------------
# 역할 C: 터미널 출력
#------------------------------------------------

def _print_entry_list(level: int, entries: list[dict[str, Any]]) -> None:
    print()
    print(f"[TOC depth{level} list]")
    for entry in entries:
        print(
            f"  [{entry['toc_index']}] numbering={entry['numbering_text']} "
            f"| title={entry['title']}"
        )
    print()


def _print_match_results(level: int, results: list[dict[str, Any]]) -> None:
    print(f"[TOC depth{level} match]")
    for result in results:
        entry = result["entry"]
        block = result["block"]
        if block is not None:
            print(
                f"  [{entry['toc_index']}] MATCHED   "
                f"toc=\"{entry['title']}\" -> block_id={block['block_id']}"
            )
        else:
            print(f"  [{entry['toc_index']}] UNMATCHED toc=\"{entry['title']}\"")
    print()


#------------------------------------------------
# 진입점
#------------------------------------------------

def add_toc_depth0_anchors(
    blocks_doc: BlocksDocument,
    tables_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    역할: 목차 기반 depth 0 anchor를 탐지/추출/매칭해 BlocksDocument에 반영한다.
    입력 데이터: blocks_doc(Stage 8-A까지 반영된 BlocksDocument),
                 tables_data(파서 직렬화 원본 표 리스트 — 목차 표 셀 텍스트 소스, 읽기 전용).
    출력 데이터: 요약 dict. 매칭 성공 시 block에 anchor를 반영하고,
                 앵커 미탐지/매칭 0건이면 block을 변경하지 않는다(fallback).
    """
    tables = tables_data if isinstance(tables_data, list) else (
        tables_data.get("tables") or []
    )
    ordered_blocks = sorted(
        blocks_doc.blocks,
        key=lambda b: b.get("reading_order_index") or 0,
    )

    summary: dict[str, Any] = {
        "enabled": False,
        "anchor_found": False,
        "toc_entry_count": 0,
        "depth0_entry_count": 0,
        "matched_count": 0,
        "unmatched_count": 0,
    }

    # A. 목차 앵커 탐지
    anchor = _find_toc_anchor(tables, ordered_blocks)
    if anchor is None:
        print("[TOC] anchor not found: 기존 depth 0 로직으로 fallback")
        blocks_doc.quality["toc_depth0_anchor"] = summary
        return summary

    summary["anchor_found"] = True
    summary["anchor"] = {
        "section_index": anchor["section_index"],
        "block_id": anchor["block_id"],
        "table_id": anchor["table_id"],
    }
    print(
        f"[TOC] anchor found: section={anchor['section_index']}, "
        f"block_id={anchor['block_id']}"
    )

    # B. 목차 항목 추출 + anchor candidate 선별
    # (depth는 numbering 성분 수로 동적 결정: N성분 -> depth N-1, 상한 없음)
    entries, toc_source_table_ids = _extract_toc_entries(
        tables, ordered_blocks, anchor,
    )
    anchor_entries = _select_anchor_entries(entries)
    levels = sorted({e["anchor_depth"] for e in anchor_entries})
    entries_by_level = {
        level: [e for e in anchor_entries if e["anchor_depth"] == level]
        for level in levels
    }
    summary["toc_entry_count"] = len(entries)
    summary["anchor_levels"] = levels
    summary["entry_count_by_level"] = {
        str(level): len(entries_by_level[level]) for level in levels
    }
    summary["depth0_entry_count"] = len(entries_by_level.get(0, []))
    summary["toc_source_table_ids"] = toc_source_table_ids
    for level in levels:
        print(
            f"[TOC] depth{level} entries extracted: "
            f"{len(entries_by_level[level])}"
        )

    if not entries_by_level.get(0):
        print("[TOC] depth0 entry 없음: 기존 depth 0 로직으로 fallback")
        blocks_doc.quality["toc_depth0_anchor"] = summary
        return summary

    # C. 레벨별 리스트 출력
    for level in levels:
        _print_entry_list(level, entries_by_level[level])

    # D. 본문 순차 매칭 (모든 레벨을 목차 등장 순서 그대로 단일 cursor로 매칭)
    results = _match_anchor_entries_to_blocks(
        anchor_entries, ordered_blocks, anchor, toc_source_table_ids,
    )
    results_by_level = {
        level: [r for r in results if r["entry"]["anchor_depth"] == level]
        for level in levels
    }
    matched_by_level = {
        level: [r for r in results_by_level[level] if r["block"] is not None]
        for level in levels
    }
    summary["matched_count"] = len(matched_by_level.get(0, []))
    summary["unmatched_count"] = (
        len(results_by_level.get(0, [])) - summary["matched_count"]
    )
    summary["matched_count_by_level"] = {
        str(level): len(matched_by_level[level]) for level in levels
    }

    for level in levels:
        _print_match_results(level, results_by_level[level])

    if not matched_by_level.get(0):
        print("[TOC] depth0 본문 매칭 0건: 기존 depth 0 로직으로 fallback")
        blocks_doc.quality["toc_depth0_anchor"] = summary
        return summary

    # E. 매칭 성공: 모든 레벨 anchor 반영
    # (하위 레벨은 depth0 anchor가 최소 1건 성립한 경우에만 함께 반영한다)
    summary["enabled"] = True
    all_matched = [r for r in results if r["block"] is not None]
    for result in all_matched:
        _apply_toc_anchor_to_block(
            result["block"], result["entry"], result["match_method"],
        )
    summary["matched_block_ids"] = [
        r["block"]["block_id"] for r in matched_by_level.get(0, [])
    ]
    summary["matched_block_ids_by_level"] = {
        str(level): [r["block"]["block_id"] for r in matched_by_level[level]]
        for level in levels
    }

    blocks_doc.quality["toc_depth0_anchor"] = summary

    print(
        "[TOC] anchor 반영 완료: "
        + ", ".join(
            f"depth{level} {len(matched_by_level[level])}"
            f"/{len(entries_by_level[level])}"
            for level in levels
        )
        + " matched"
    )
    return summary


#------------------------------------------------
# 산출물 렌더링 지원: 목차 표 항목의 선언 depth
#------------------------------------------------

def iter_toc_entry_levels(
    internal_blocks: list[dict[str, Any]],
    toc_table_ids: set[str] | list[str] | None,
) -> list[tuple[str, int]]:
    """
    역할: 목차 표의 셀 텍스트를 문서 순서대로 훑어 (텍스트, 선언 depth)를 만든다.
          depth는 항목 번호의 성분 수에서 나온다 ('3'->0, '3.1'->1, '3.1.1'->2).
          번호가 없는 항목(로마숫자 장 표기 등)은 직전 항목의 레벨을 잇는다.
    입력 데이터: internal_blocks(TableInternalBlocks.internal_blocks),
                toc_table_ids(quality.toc_depth0_anchor.toc_source_table_ids).
    출력 데이터: [(텍스트, depth), ...]. 목차 표가 없으면 빈 리스트.

    주의: 목차 표 식별은 문자열 매칭이 아니라 add_toc_depth0_anchors가 이미
          산출해 둔 toc_source_table_ids를 그대로 쓴다.
    """
    if not toc_table_ids:
        return []

    ids = set(toc_table_ids)
    entries: list[tuple[str, int]] = []
    last_level: int | None = None

    for block in internal_blocks:
        if block.get("root_table_id") not in ids:
            continue
        if block.get("internal_block_type") != "table_cell_text":
            continue

        raw = (block.get("text_content") or "").strip()
        if not raw:
            continue

        line, _page = _strip_page_suffix(raw)
        numbering, _title = _split_numbering(line)
        level = _numbering_anchor_level(numbering)

        if level is None:
            level = last_level if last_level is not None else 0
        else:
            last_level = level

        entries.append((" ".join(raw.split()), level))

    return entries
