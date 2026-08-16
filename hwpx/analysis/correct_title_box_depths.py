#================================================
# correct_title_box_depths.py
# v3.1 보완 4차: title_box outline depth 보정 + scope 재앵커링
#
# Stage 8-B(apply_depth_constraints) "이후"에 실행한다.
# 8-B의 flow 전파가 title_box를 경계로 삼지 않아 title_box depth가
# 이전 heading stack에 끌려가는 문제를, outline 구조 기반으로 보정한다.
#
# 처리 순서:
# 1. title_box outline depth 보정 (numeric/roman-dash family + anchor 학습)
# 2. roman-dash family root depth 통일
# 3. title_box scope 생성 (다음 title_box까지. section 경계에서는 새 section의
#    첫 의미 블록이 strict marker heading이면 직전 scope를 carry-over한다)
# 4. scope 내부 paragraph heading 재앵커링 (marker 기반 상대 레벨)
# 5. heading 하위 flow block: shift 먼저, 그 다음 new heading 기준 clamp
#
# 원칙:
# - 문서별 문자열 하드코딩 금지. outline 표기 방식의 일반 규칙만 사용한다.
# - 모든 변경 block에 depth_correction 메타데이터를 남긴다.
# - reading_order_index / block 수는 변경하지 않는다.
#================================================

from __future__ import annotations

import re
from typing import Any

from .pipeline_models import BlocksDocument

# roman-dash root: "Ⅱ-1", "III-2" 등 (유니코드 로마숫자 + ASCII 로마자)
_ROMAN_DASH_RE = re.compile(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩIVX]+\s*-\s*\d+")
# numeric outline: "3", "3.1", "3.1.1", "2-1" 등
_NUMERIC_RE = re.compile(r"^(\d+(?:[.\-]\d+)*)\.?(?=\s|$)")

# paragraph heading marker -> title_box 기준 상대 레벨
_MARKER_RELATIVE_LEVELS = [
    ("□", 1), ("■", 1),
    ("○", 2), ("◦", 2), ("●", 2),
    ("-", 3), ("·", 3), ("ㆍ", 3),
]
_HANGUL_ITEM_RE = re.compile(r"^[가-힣]\.\s")

_SHIFT_EXCLUDED_BLOCK_TYPES = {"control", "section_control"}


def _is_toc_depth0_anchor(block: dict[str, Any]) -> bool:
    """목차 기반 depth anchor 블록 여부 (add_toc_depth0_anchors가 부여.
    toc_depth{N}_anchor 전 레벨 포함). 이 블록의 anchor depth는
    outline/marker/flow 보정보다 우선하며 변경하지 않는다."""
    return (
        (block.get("depth_source") or "").startswith("toc_depth")
        and (block.get("toc_match") or {}).get("matched") is True
    )


def _toc_anchor_depth(block: dict[str, Any]) -> int:
    """toc anchor 블록의 고정 depth (toc_match.anchor_depth, 기본 0)."""
    return (block.get("toc_match") or {}).get("anchor_depth") or 0

#------------------------------------------------
# marker 표기 클래스 (문서별 문자열이 아닌 일반 타이포그래피 클래스)
#------------------------------------------------

_DASH_MARKS = ("-", "–", "―", "—")
_DOT_MARKS = ("·", "ㆍ", "‧", "•", "◦")
_ANNOTATION_MARKS = ("*", "※")

# 서수 패밀리: 값의 연속성(가→나→다, 1→2→3)으로만 형제를 판정한다
_HANGUL_ORDINAL_SEQ = "가나다라마바사아자차카타파하"
_CIRCLED_ORDINAL_SEQ = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮"
_HANGUL_ORDINAL_RE = re.compile(r"^([가-하])[.)]\s")
_DIGIT_ORDINAL_RE = re.compile(r"^(\d{1,2})[.)]\s")

# indent 비교 허용 오차 (hwpunit)
_INDENT_TOLERANCE = 50
# 선행 공백 1문자를 indent로 환산하는 근사 단위 (hwpunit)
_LEADING_WS_UNIT = 100


def _parse_ordinal(text: str | None) -> tuple[str, int] | None:
    """서수 마커 (패밀리, 순서값)을 추출한다. 서수가 아니면 None."""
    stripped = (text or "").strip()
    if not stripped:
        return None
    m = _HANGUL_ORDINAL_RE.match(stripped)
    if m:
        idx = _HANGUL_ORDINAL_SEQ.find(m.group(1))
        return ("hangul", idx) if idx >= 0 else None
    m = _DIGIT_ORDINAL_RE.match(stripped)
    if m:
        return ("digit", int(m.group(1)))
    idx = _CIRCLED_ORDINAL_SEQ.find(stripped[0])
    if idx >= 0:
        return ("circled", idx)
    return None


def _marker_class_of(block: dict[str, Any]) -> str | None:
    """flow 블록의 선행 마커 클래스를 판정한다 (dash/dot/annotation)."""
    if block.get("block_type") != "paragraph":
        return None
    stripped = (block.get("text_content") or "").lstrip()
    if not stripped:
        return None
    ch = stripped[0]
    if ch in _ANNOTATION_MARKS:
        return "annotation"
    if ch in _DASH_MARKS:
        return "dash"
    if ch in _DOT_MARKS:
        return "dot"
    return None


def _leading_ws_units(text: str | None) -> int:
    """text 선행 공백을 indent 근사 단위로 환산한다."""
    units = 0
    for ch in text or "":
        if ch == " ":
            units += 1
        elif ch == "\t":
            units += 4
        elif ch == "　":
            units += 2
        else:
            break
    return units * _LEADING_WS_UNIT


def _indent_key_of(block: dict[str, Any]) -> int:
    """marker 상대 계층 비교용 시각 indent 키 (margin_left + 선행 공백 환산)."""
    sf = block.get("style_features") or {}
    margin_left = sf.get("margin_left") or 0
    return margin_left + _leading_ws_units(block.get("text_content"))


def _is_flow_target(block: dict[str, Any]) -> bool:
    """depth 보정 전파 대상 flow 블록 여부."""
    if block.get("block_type") in _SHIFT_EXCLUDED_BLOCK_TYPES:
        return False
    if block.get("depth_band") == "peripheral":
        return False
    return True


#------------------------------------------------
# 공통: tables_hierarchical 기반 표시 텍스트
#------------------------------------------------

def get_table_display_text_from_hierarchy(table_obj: dict[str, Any]) -> str:
    """
    tables_hierarchical.json의 preprocess.cells[].text.text를 기준으로
    row_addr, col_addr 순서대로 title/table 표시 텍스트를 만든다.
    flatten 이전에도 사용 가능해야 한다.
    nested table 텍스트는 부모 셀 텍스트에 섞지 않는다.
    """
    cells = (table_obj.get("preprocess") or {}).get("cells") or []
    ordered = sorted(
        cells,
        key=lambda c: (
            (c.get("position") or {}).get("row_addr") is None,
            (c.get("position") or {}).get("row_addr"),
            (c.get("position") or {}).get("col_addr") is None,
            (c.get("position") or {}).get("col_addr"),
        ),
    )
    texts = []
    for cell in ordered:
        text = ((cell.get("text") or {}).get("text") or "").strip()
        if text:
            texts.append(" ".join(text.split()))
    return " ".join(texts)


#------------------------------------------------
# outline 추출
#------------------------------------------------

def _parse_outline(text: str) -> dict[str, Any] | None:
    """title_box 텍스트에서 outline family / key / level을 추출한다."""
    stripped = text.strip()
    if not stripped:
        return None

    m = _ROMAN_DASH_RE.match(stripped)
    if m:
        return {
            "outline_family": "roman_dash",
            "outline_key": m.group(0).replace(" ", ""),
            "outline_level": 1,
        }

    m = _NUMERIC_RE.match(stripped)
    if m:
        key = m.group(1)
        level = len(re.split(r"[.\-]", key))
        return {
            "outline_family": "numeric",
            "outline_key": key,
            "outline_level": level,
        }
    return None


def _infer_paragraph_heading_relative_level_strict(
    block: dict[str, Any],
) -> int | None:
    """
    section boundary carry-over 판정 전용 strict 추론.
    numbering_level → heading_level_native → outline marker → 한글 항목 패턴
    순으로 명시적 근거가 있을 때만 상대 레벨을 반환하고,
    아무 근거도 없으면 None을 반환한다 (fallback 없음).
    marker/패턴은 기존 _MARKER_RELATIVE_LEVELS / _HANGUL_ITEM_RE에서만 파생한다.
    """
    style = block.get("style_features") or {}
    numbering_level = style.get("numbering_level")
    if isinstance(numbering_level, int) and numbering_level >= 1:
        return numbering_level
    native = style.get("heading_level_native")
    if isinstance(native, int) and native >= 1:
        return native

    text = (block.get("normalized_text") or "").strip()
    for marker, level in _MARKER_RELATIVE_LEVELS:
        if text.startswith(marker):
            return level
    if _HANGUL_ITEM_RE.match(text):
        return 2
    return None


def _infer_paragraph_heading_relative_level(block: dict[str, Any]) -> int:
    """
    paragraph heading의 normalized_text, style/numbering 정보를 기준으로
    title_box 기준 상대 depth를 추정한다.
    strict 추론에 근거가 없으면 fallback 1을 반환한다 (scope 내부 reanchor 전용).
    """
    level = _infer_paragraph_heading_relative_level_strict(block)
    return level if level is not None else 1


def _is_meaningful_block(block: dict[str, Any]) -> bool:
    """
    section boundary carry-over 판정에 쓰는 '의미 블록' 여부.
    empty_paragraph / control / section_control / footer / peripheral은 제외한다.
    """
    if block.get("block_type") in ("control", "section_control", "footer"):
        return False
    if block.get("semantic_role") == "empty_paragraph":
        return False
    if block.get("depth_band") == "peripheral":
        return False
    return True


#------------------------------------------------
# 2.5단계: 서수 형제 정렬 (ordinal sibling alignment)
#------------------------------------------------

def _apply_correction(
    block: dict[str, Any],
    new_depth: int,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> bool:
    """depth를 변경하고 depth_correction 메타데이터를 남긴다. 변경 여부 반환."""
    if _is_toc_depth0_anchor(block):
        return False
    old_depth = block.get("depth") or 0
    if new_depth == old_depth:
        return False
    block["depth"] = new_depth
    block["depth_correction"] = {
        "applied": True,
        "old_depth": old_depth,
        "new_depth": new_depth,
        "reason": reason,
        "delta": new_depth - old_depth,
        **(extra or {}),
    }
    return True


def _shift_subtree_flow(
    ordered: list[dict[str, Any]],
    start_index: int,
    anchor_block_id: str,
    anchor_old_depth: int,
    anchor_new_depth: int,
    reason: str,
    is_title_box,
) -> int:
    """
    보정된 marker/서수 블록의 하위 flow 구간에 shift+clamp를 전파한다.
    다음 heading/title_box/서수 블록 또는 anchor보다 얕은 블록에서 멈춘다.
    """
    delta = anchor_new_depth - anchor_old_depth
    changed = 0
    for block in ordered[start_index:]:
        if not _is_flow_target(block):
            continue
        if is_title_box(block):
            break
        if block.get("semantic_role") == "section_heading":
            break
        if _parse_ordinal(block.get("normalized_text") or block.get("text_content")) is not None:
            break
        old_depth = block.get("depth") or 0
        if old_depth <= anchor_old_depth:
            break  # anchor 하위 subtree 종료
        new_depth = max(old_depth + delta, anchor_new_depth + 1)
        if _apply_correction(block, new_depth, reason, {
            "anchor_block_id": anchor_block_id,
        }):
            changed += 1
    return changed


def _align_ordinal_siblings(
    ordered: list[dict[str, Any]],
    is_title_box,
) -> int:
    """
    같은 패밀리의 연속 서수(가→나→다, 1→2→3, ①→②→③) 블록을
    첫 멤버의 depth로 정렬한다. 서수 연속성이 형제 판정의 유일한 근거이며,
    title_box나 그룹보다 얕은 heading이 나오면 그룹을 닫는다.
    """
    aligned = 0
    # family -> (last_value, group_depth)
    state: dict[str, tuple[int, int]] = {}

    for index, block in enumerate(ordered):
        if is_title_box(block):
            state.clear()
            continue
        if not _is_flow_target(block):
            continue

        depth = block.get("depth") or 0
        ordinal = None
        if block.get("block_type") == "paragraph":
            ordinal = _parse_ordinal(
                block.get("normalized_text") or block.get("text_content")
            )

        if ordinal is None:
            if block.get("semantic_role") == "section_heading":
                # 그룹보다 얕거나 같은 레벨의 heading은 해당 그룹을 닫는다
                for family in [
                    f for f, (_, group_depth) in state.items() if depth <= group_depth
                ]:
                    state.pop(family)
            continue

        family, value = ordinal
        previous = state.get(family)
        if previous is not None and value == previous[0] + 1:
            group_depth = previous[1]
            old_depth = depth
            if _apply_correction(block, group_depth, "ordinal_sibling_alignment", {
                "ordinal_family": family,
                "ordinal_value": value,
            }):
                aligned += 1
                aligned += _shift_subtree_flow(
                    ordered, index + 1,
                    anchor_block_id=block["block_id"],
                    anchor_old_depth=old_depth,
                    anchor_new_depth=group_depth,
                    reason="ordinal_sibling_flow_shift",
                    is_title_box=is_title_box,
                )
            state[family] = (value, group_depth)
        else:
            # 새 그룹 시작 또는 불연속: 현재 depth를 그룹 기준으로 기록
            state[family] = (value, depth)

    return aligned


#------------------------------------------------
# 2.7단계: indent 기반 marker 상대 계층 (marker indent nesting)
#------------------------------------------------

def _nest_marker_flow(
    ordered: list[dict[str, Any]],
    is_title_box,
) -> dict[str, int]:
    """
    heading 사이 flow 구간에서 dash/dot 마커 블록의 상대 계층을
    시각 indent(margin_left + 선행 공백)로 결정한다.
    - 첫 마커 블록은 기존 depth를 유지한다 (보수적 기준선)
    - indent가 더 깊으면 자식(+1), 같으면 형제, 얕으면 상위 스택으로 복귀
    - annotation(*, ※)은 직전 마커 블록의 자식으로 붙인다
    정적 marker→level 테이블로 구분 불가능한 문맥 의존 계층
    (dot이 dash의 하위이기도, 상위 라벨이기도 한 경우)을 해소한다.
    """
    stats = {"marker_indent_adjusted": 0, "annotation_adjusted": 0}
    # (indent_key, depth) 스택 — heading/title_box/section 경계에서 리셋
    stack: list[tuple[int, int]] = []
    last_marker_depth: int | None = None
    # 보정된 마커 이후 무마커 flow 전파용: (new_depth, delta, old_depth)
    pending_anchor: tuple[int, int, int] | None = None
    prev_section: Any = object()

    for block in ordered:
        if block.get("section_index") != prev_section:
            prev_section = block.get("section_index")
            stack = []
            last_marker_depth = None
            pending_anchor = None
        if not _is_flow_target(block):
            continue
        if is_title_box(block) or block.get("semantic_role") == "section_heading":
            stack = []
            last_marker_depth = None
            pending_anchor = None
            continue

        marker_class = _marker_class_of(block)
        old_depth = block.get("depth") or 0

        if marker_class is None:
            # 무마커 flow: 직전 마커 보정의 delta를 shift+clamp로 전파
            if pending_anchor is not None:
                anchor_new, delta, anchor_old = pending_anchor
                if old_depth <= anchor_old:
                    pending_anchor = None
                else:
                    new_depth = max(old_depth + delta, anchor_new + 1)
                    if _apply_correction(
                        block, new_depth, "marker_indent_flow_shift",
                    ):
                        stats["marker_indent_adjusted"] += 1
            continue

        if marker_class == "annotation":
            if last_marker_depth is not None:
                new_depth = last_marker_depth + 1
                if _apply_correction(
                    block, new_depth, "annotation_depth_under_marker",
                ):
                    stats["annotation_adjusted"] += 1
                pending_anchor = (
                    (new_depth, new_depth - old_depth, old_depth)
                    if new_depth != old_depth else None
                )
            continue

        indent_key = _indent_key_of(block)
        while stack and indent_key < stack[-1][0] - _INDENT_TOLERANCE:
            stack.pop()

        if stack and abs(indent_key - stack[-1][0]) <= _INDENT_TOLERANCE:
            new_depth = stack[-1][1]  # 형제
        elif stack and indent_key > stack[-1][0] + _INDENT_TOLERANCE:
            new_depth = stack[-1][1] + 1  # 자식
            stack.append((indent_key, new_depth))
        else:
            new_depth = old_depth  # 구간 첫 마커: 기존 depth 유지
            stack.append((indent_key, new_depth))

        if _apply_correction(block, new_depth, "marker_indent_nesting", {
            "marker_class": marker_class,
            "indent_key": indent_key,
        }):
            stats["marker_indent_adjusted"] += 1
            pending_anchor = (new_depth, new_depth - old_depth, old_depth)
        else:
            pending_anchor = None
        last_marker_depth = new_depth

    return stats


#------------------------------------------------
# 진입점
#------------------------------------------------

def correct_title_box_depths(
    blocks_doc: BlocksDocument,
    tables: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    역할: 8-B 이후의 BlocksDocument에서 title_box outline depth를 보정하고,
          scope 내부 paragraph heading 재앵커링과 flow shift+clamp를 수행한다.
    입력 데이터: blocks_doc(BlocksDocument), tables(hierarchy 표 리스트 — 텍스트 소스, 읽기 전용).
    출력 데이터: 보정 통계 dict. blocks_doc의 block depth가 갱신된다.
    """
    blocks = blocks_doc.blocks
    block_count_before = len(blocks)

    # 텍스트 소스: tables_hierarchical.json (top-level만 필요 — title_box는 top-level)
    table_text_by_id = {
        t.get("table_id"): get_table_display_text_from_hierarchy(t) for t in tables
    }

    ordered = sorted(blocks, key=lambda b: b.get("reading_order_index") or 0)

    def _is_title_box(b: dict[str, Any]) -> bool:
        return (b.get("table_hierarchy_ref") or {}).get("table_type") == "title_box"

    #--- 1단계: title_box outline depth 보정 -------------------------
    # anchor 학습: outline_level=1을 고정 depth로 두지 않고 문서에서 배운다.
    numeric_anchor_depth: int | None = None
    roman_family_root_depth: int | None = None
    scope_seq = 0
    title_corrections: list[tuple[dict[str, Any], int, dict[str, Any]]] = []

    # 목차 기반 depth 0 anchor가 이 문서에서 활성화되어 있는지
    # (활성 시 roman-dash root는 depth 0까지 허용해 anchor와 정합을 맞춘다)
    toc_anchor_active = any(_is_toc_depth0_anchor(b) for b in ordered)

    for b in ordered:
        if not _is_title_box(b):
            continue

        if _is_toc_depth0_anchor(b):
            # 목차 anchor로 확정된 title_box: outline 추정보다 우선해
            # anchor depth(depth0=0, depth1=1)로 고정한다.
            # numbering level과 anchor depth가 일치하므로 numeric anchor
            # 기준선은 0이 되고, 이후 하위 outline(3.1.1 등)은 이를 따른다.
            pinned_depth = _toc_anchor_depth(b)
            numeric_anchor_depth = 0
            scope_seq += 1
            title_corrections.append((b, pinned_depth, {
                "outline_family": b.get("depth_source") or "toc_depth0_anchor",
                "outline_level": pinned_depth + 1,
                "anchor_scope_id": f"scope_{scope_seq:03d}",
            }))
            continue

        table_id = b["table_hierarchy_ref"].get("table_id")
        outline = _parse_outline(table_text_by_id.get(table_id, ""))
        old_depth = b.get("depth") or 0

        if outline is None:
            continue  # outline 없으면 기존 depth 유지 (4순위 fallback)

        if outline["outline_family"] == "roman_dash":
            # roman-dash family는 하나의 상위 family: 첫 root의 depth로 통일.
            # roman-dash 키는 (로마자 부 + 숫자 인덱스) 2성분 표기이므로
            # 구조적으로 numeric root(장)보다 한 랭크 위 부(部) 레벨이다.
            # 8-B flow 전파가 끌어내린 old_depth 대신 numeric anchor에서 유도한다.
            if roman_family_root_depth is None:
                if numeric_anchor_depth is not None:
                    roman_family_root_depth = max(
                        numeric_anchor_depth - 1,
                        0 if toc_anchor_active else 1,
                    )
                else:
                    roman_family_root_depth = old_depth
            new_depth = roman_family_root_depth
            # roman root는 새 anchor scope를 연다: 이후 numeric은 roman+1부터 재시작
            numeric_anchor_depth = new_depth + 1
        else:
            if numeric_anchor_depth is None:
                if outline["outline_level"] == 1:
                    numeric_anchor_depth = old_depth  # 첫 신뢰 가능한 root에서 anchor 학습
                else:
                    continue  # anchor 없이 하위 레벨만 나오면 보정하지 않음
            new_depth = numeric_anchor_depth + (outline["outline_level"] - 1)

        scope_seq += 1
        title_corrections.append((b, new_depth, {
            **outline,
            "anchor_scope_id": f"scope_{scope_seq:03d}",
        }))

    corrected_title_count = 0
    for b, new_depth, outline in title_corrections:
        old_depth = b.get("depth") or 0
        if new_depth != old_depth:
            corrected_title_count += 1
        b["depth"] = new_depth
        b["depth_correction"] = {
            "applied": new_depth != old_depth,
            "old_depth": old_depth,
            "new_depth": new_depth,
            "reason": (
                outline["outline_family"]
                if outline["outline_family"].startswith("toc_depth")
                else "title_box_outline_correction"
            ),
            "outline_family": outline["outline_family"],
            "outline_level": outline["outline_level"],
            "anchor_scope_id": outline["anchor_scope_id"],
        }
        # depth_candidates는 Stage 8-B 기준 후보 기록으로 유지한다.
        # 보정 후보를 append하지 않으며, 보정 근거는 depth_correction에만 남긴다.

    #--- 2단계: scope 생성 + paragraph heading 재앵커링 + flow shift/clamp ---
    # scope = title_box ~ 다음 title_box 직전.
    # section 경계에서는 즉시 리셋하지 않고 새 section의 첫 의미 블록을 보고 결정한다:
    #   - 첫 의미 블록이 title_box → 새 scope 시작 (기존 동작)
    #   - 첫 의미 블록이 paragraph heading이고 strict 추론 성공 → 직전 scope carry-over
    #   - 그 외 (strict 추론 실패 포함) → scope 리셋
    # paragraph heading은 scope 종료 조건이 아니라 재앵커링 대상이다.
    reanchored_heading_count = 0
    shifted_flow_count = 0
    clamped_flow_count = 0
    carry_over_count = 0

    scope_title: dict[str, Any] | None = None
    scope_id: str | None = None
    # carry-over된 scope 하에서 보정 중인지 (depth_correction 메타데이터용)
    scope_carried_over = False
    # 현재 flow의 anchor: (anchor_block, anchor_new_depth, delta)
    anchor_block_id: str | None = None
    anchor_new_depth: int | None = None
    anchor_delta = 0

    corrected_by_block_id = {
        b["block_id"]: meta["anchor_scope_id"] for b, _, meta in title_corrections
    }

    def _apply_flow(b: dict[str, Any]) -> None:
        nonlocal shifted_flow_count, clamped_flow_count
        if anchor_new_depth is None:
            return
        if _is_toc_depth0_anchor(b):
            return
        if b.get("block_type") in _SHIFT_EXCLUDED_BLOCK_TYPES:
            return
        if b.get("depth_band") == "peripheral":
            return

        old_depth = b.get("depth") or 0
        min_allowed = anchor_new_depth + 1
        new_depth = old_depth + anchor_delta  # 1) 항상 shift 먼저
        if new_depth < min_allowed:           # 2) new anchor 기준 clamp
            new_depth = min_allowed
            reason = "flow_depth_clamp_under_paragraph_heading"
            clamped_flow_count += 1
        else:
            reason = "flow_shift_from_paragraph_heading"
            if anchor_delta != 0:
                shifted_flow_count += 1

        if new_depth == old_depth:
            return
        b["depth"] = new_depth
        b["depth_correction"] = {
            "applied": True,
            "old_depth": old_depth,
            "new_depth": new_depth,
            "reason": reason,
            "anchor_block_id": anchor_block_id,
            "anchor_scope_id": scope_id,
            "delta": new_depth - old_depth,
            "min_allowed_depth": min_allowed,
        }
        if scope_carried_over:
            b["depth_correction"]["carried_over_scope"] = True

    prev_section: Any = object()  # 첫 block에서 반드시 경계 판정이 시작되도록 sentinel
    boundary_pending = False
    for b in ordered:
        if b.get("section_index") != prev_section:
            # section 경계: scope 유지 여부는 첫 의미 블록에서 결정한다.
            # anchor는 section을 넘겨 적용하지 않으므로 즉시 끊는다.
            boundary_pending = True
            anchor_block_id = None
            anchor_new_depth = None
            anchor_delta = 0
            prev_section = b.get("section_index")

        if boundary_pending and _is_meaningful_block(b):
            boundary_pending = False
            if _is_title_box(b):
                # 아래 title_box 분기가 새 scope를 연다
                scope_carried_over = False
            elif (
                scope_title is not None
                and b.get("semantic_role") == "section_heading"
                and _infer_paragraph_heading_relative_level_strict(b) is not None
            ):
                # 직전 section의 active title_box scope continuation
                scope_carried_over = True
                carry_over_count += 1
            else:
                scope_title = None
                scope_id = None
                scope_carried_over = False

        if _is_title_box(b):
            scope_title = b
            scope_id = corrected_by_block_id.get(b["block_id"])
            scope_carried_over = False
            # title_box 직후 ~ 첫 paragraph heading 전 flow의 anchor는 title_box 자신
            anchor_block_id = b["block_id"]
            anchor_new_depth = b.get("depth") or 0
            dc = b.get("depth_correction") or {}
            anchor_delta = (
                (dc.get("new_depth") - dc.get("old_depth"))
                if dc.get("applied") else 0
            )
            continue

        if scope_title is None:
            continue  # 첫 title_box 이전 구간은 보정하지 않는다

        if b.get("semantic_role") == "section_heading":
            if _is_toc_depth0_anchor(b):
                # 목차 anchor heading: depth 0 유지, 이후 flow의 anchor로만 쓴다
                anchor_block_id = b["block_id"]
                anchor_new_depth = b.get("depth") or 0
                anchor_delta = 0
                continue
            # scope 내부 paragraph heading 재앵커링
            relative_level = _infer_paragraph_heading_relative_level(b)
            title_depth = scope_title.get("depth") or 0
            old_depth = b.get("depth") or 0
            new_depth = title_depth + relative_level
            if new_depth != old_depth:
                reanchored_heading_count += 1
                b["depth"] = new_depth
                b["depth_correction"] = {
                    "applied": True,
                    "old_depth": old_depth,
                    "new_depth": new_depth,
                    "reason": "paragraph_heading_reanchor_in_title_scope",
                    "anchor_block_id": scope_title["block_id"],
                    "anchor_scope_id": scope_id,
                    "relative_level": relative_level,
                    "delta": new_depth - old_depth,
                }
                if scope_carried_over:
                    b["depth_correction"]["carried_over_scope"] = True
            # 이 heading이 이후 flow의 새 anchor가 된다
            anchor_block_id = b["block_id"]
            anchor_new_depth = new_depth
            anchor_delta = new_depth - old_depth
            continue

        _apply_flow(b)

    #--- 2.5단계: 서수 형제 정렬 ---------------------------------------
    ordinal_aligned_count = _align_ordinal_siblings(ordered, _is_title_box)

    #--- 2.7단계: indent 기반 marker 상대 계층 -------------------------
    marker_stats = _nest_marker_flow(ordered, _is_title_box)

    #--- 3단계: 역전 검증 (v3.1 성공 기준) ---------------------------
    # 보정 루프와 동일한 section boundary carry-over 규칙을 적용해,
    # 경계에서 이어진 scope의 역전도 검출한다.
    heading_inversion_count = 0
    flow_inversion_count = 0
    scope_title = None
    anchor_depth = None
    prev_section = object()
    boundary_pending = False
    for b in ordered:
        if b.get("section_index") != prev_section:
            boundary_pending = True
            anchor_depth = None
            prev_section = b.get("section_index")
        if boundary_pending and _is_meaningful_block(b):
            boundary_pending = False
            if not _is_title_box(b) and not (
                scope_title is not None
                and b.get("semantic_role") == "section_heading"
                and _infer_paragraph_heading_relative_level_strict(b) is not None
            ):
                scope_title = None
        if _is_title_box(b):
            scope_title = b
            anchor_depth = b.get("depth") or 0
            continue
        if scope_title is None:
            continue
        if b.get("semantic_role") == "section_heading":
            if (b.get("depth") or 0) <= (scope_title.get("depth") or 0):
                heading_inversion_count += 1
            anchor_depth = b.get("depth") or 0
            continue
        if b.get("block_type") in _SHIFT_EXCLUDED_BLOCK_TYPES:
            continue
        if b.get("depth_band") == "peripheral":
            continue
        if anchor_depth is not None and (b.get("depth") or 0) <= anchor_depth:
            flow_inversion_count += 1

    assert len(blocks) == block_count_before

    stats = {
        "title_box_count": sum(1 for b in blocks if _is_title_box(b)),
        "title_box_corrected_count": corrected_title_count,
        "paragraph_heading_reanchored_count": reanchored_heading_count,
        "flow_shifted_count": shifted_flow_count,
        "flow_clamped_count": clamped_flow_count,
        "section_boundary_carry_over_count": carry_over_count,
        "ordinal_sibling_aligned_count": ordinal_aligned_count,
        "marker_indent_adjusted_count": marker_stats["marker_indent_adjusted"],
        "annotation_adjusted_count": marker_stats["annotation_adjusted"],
        "heading_inversion_count": heading_inversion_count,
        "flow_inversion_count": flow_inversion_count,
    }

    print("=== title_box depth 보정 결과 ===")
    for key, value in stats.items():
        print(f"{key}: {value}")

    return stats
