from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterator


# startswith 전용: 표 전체가 이 마커로 시작할 때만 캡션 판정
CAPTION_OR_NOTE_PREFIXES = (
    "표 ",
    "<표",
    "[표",
    "〈표",
    "Table ",
    "자료:",
    "자료 :",
    "출처:",
    "출처 :",
    "주:",
    "주 :",
    "※",
    "단위:",
    "단위 :",
)

# contains 전용: "표 "는 본문 단어 오탐 위험이 있어 제외
_CAPTION_CONTAINS_PREFIXES = (
    "<표",
    "[표",
    "〈표",
    "Table ",
    "자료:",
    "자료 :",
    "출처:",
    "출처 :",
    "주:",
    "주 :",
    "※",
    "단위:",
    "단위 :",
)

TITLE_PATTERNS = (
    re.compile(r"^\s*\d+[\.\)]\s*.+"),
    re.compile(r"^\s*[가-힣][\.\)]\s*.+"),
    re.compile(r"^\s*[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+[\.\)]\s*.+"),
    re.compile(r"^\s*[□■○●\-]\s*.+"),
)

# caption 키워드보다 우선 적용되는 번호형 제목 패턴
# "1 제목", "1-1 제목", "Ⅱ-2 제목" 등 기존 TITLE_PATTERNS이 잡지 못하는 형식 포함
_PRIORITY_TITLE_PATTERNS = (
    re.compile(r"^\s*\d+[\.\)]\s*.+"),                      # 1. / 1)
    re.compile(r"^\s*\d+\s+\S"),                             # 1 제목
    re.compile(r"^\s*\d+[-]\d+"),                            # 1-1 / 2-5
    re.compile(r"^\s*[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+[-]\d+"),           # Ⅱ-2
    re.compile(r"^\s*[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+[\.\)]\s*.+"),     # Ⅱ.
    re.compile(r"^\s*[가-힣][\.\)]\s*.+"),                  # 가.
)

KEY_VALUE_HEADERS = {
    ("항목", "내용"),
    ("구분", "내용"),
    ("항목", "세부내용"),
    ("구분", "세부내용"),
    ("항목", "설명"),
    ("구분", "설명"),
    ("key", "value"),
}


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def get_cell_text(cell: dict[str, Any]) -> str:
    text = cell.get("text")
    if isinstance(text, str) and text.strip():
        return normalize_text(text)
    if isinstance(text, dict):
        nested_text = text.get("text")
        if isinstance(nested_text, str) and nested_text.strip():
            return normalize_text(nested_text)

    parts: list[str] = []
    for paragraph in _as_list(cell.get("paragraphs")):
        if not isinstance(paragraph, dict):
            continue

        paragraph_text = paragraph.get("text")
        if isinstance(paragraph_text, str) and paragraph_text.strip():
            parts.append(paragraph_text)
            continue

        for run in _as_list(paragraph.get("runs")):
            if isinstance(run, dict):
                run_text = run.get("text")
                if isinstance(run_text, str) and run_text.strip():
                    parts.append(run_text)

    return normalize_text(" ".join(parts))


def get_direct_cells(table: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in _as_list(table.get("rows")):
        if not isinstance(row, dict):
            continue
        for cell in _as_list(row.get("cells")):
            if isinstance(cell, dict):
                result.append(cell)

    if result:
        return result

    cells = table.get("cells")
    if isinstance(cells, list):
        return [cell for cell in cells if isinstance(cell, dict)]

    return get_summary_cells(table)


def get_summary_cells(table: dict[str, Any]) -> list[dict[str, Any]]:
    preprocess = table.get("preprocess")
    if not isinstance(preprocess, dict):
        return []

    cells = preprocess.get("cells")
    if isinstance(cells, list):
        return [cell for cell in cells if isinstance(cell, dict)]

    return []


def get_non_empty_cells(table: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        cell for cell in get_direct_cells(table)
        if get_cell_text(cell) != ""
    ]


def get_all_text(table: dict[str, Any]) -> str:
    return normalize_text(" ".join(get_cell_text(cell) for cell in get_direct_cells(table)))


def iter_nested_tables(table: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yielded = False

    for row in _as_list(table.get("rows")):
        if not isinstance(row, dict):
            continue
        for cell in _as_list(row.get("cells")):
            if not isinstance(cell, dict):
                continue
            for nested_table in _as_list(cell.get("nested_tables")):
                if isinstance(nested_table, dict):
                    yielded = True
                    yield nested_table

    if yielded:
        return

    for cell in _as_list(table.get("cells")):
        if not isinstance(cell, dict):
            continue
        for nested_table in _as_list(cell.get("nested_tables")):
            if isinstance(nested_table, dict):
                yielded = True
                yield nested_table

    if yielded:
        return

    for child in _as_list(table.get("children")):
        if isinstance(child, dict):
            yield child


def add_hierarchy_recursive(
    table: dict[str, Any],
    stats: Counter[str] | None = None,
    depth: int = 0,
) -> None:
    hierarchy = build_hierarchy(table)
    table["hierarchy"] = hierarchy

    if stats is not None:
        stats["total_tables"] += 1
        stats[f"type:{hierarchy['table_type']}"] += 1
        stats["warnings"] += len(hierarchy["quality"]["warnings"])
        if depth > 0:
            stats["nested_tables"] += 1

    recursed = add_nested_hierarchy_from_rows(table, hierarchy, stats, depth)
    if recursed:
        return

    recursed = add_nested_hierarchy_from_direct_cells(table, hierarchy, stats, depth)
    if recursed:
        return

    add_nested_hierarchy_from_summary_children(table, hierarchy, stats, depth)


def build_hierarchy(table: dict[str, Any]) -> dict[str, Any]:
    hierarchy = _base_hierarchy()
    table_type = classify_table(table)
    hierarchy["table_type"] = table_type

    if table_type == "caption_or_note_table":
        hierarchy["caption_or_note_cells"] = _cell_ids(get_non_empty_cells(table))
        hierarchy["quality"]["warnings"].append("records_skipped_for_caption_or_note_table")
        return hierarchy

    if table_type == "title_box":
        hierarchy["title_cells"] = _cell_ids(get_non_empty_cells(table))
        hierarchy["quality"]["warnings"].append("records_skipped_for_title_box")
        return hierarchy

    if table_type == "key_value_table":
        records, header_rows, body_cells, orientation = build_key_value_records(table)
        hierarchy["key_value_records"] = records
        hierarchy["key_value_orientation"] = orientation
        hierarchy["header_rows"] = header_rows
        hierarchy["body_cells"] = body_cells
        if not records:
            hierarchy["quality"]["warnings"].append("no_key_value_records_created")
        return hierarchy

    header_rows, ambiguous = infer_header_rows(table)
    hierarchy["header_rows"] = header_rows
    hierarchy["body_cells"] = build_body_cells(table, excluded_rows=set(header_rows))
    if ambiguous:
        hierarchy["quality"]["warnings"].append("ambiguous_header_rows")
    return hierarchy


def add_nested_hierarchy_from_rows(
    table: dict[str, Any],
    hierarchy: dict[str, Any],
    stats: Counter[str] | None,
    depth: int,
) -> bool:
    found = False
    for row in _as_list(table.get("rows")):
        if not isinstance(row, dict):
            continue

        for cell in _as_list(row.get("cells")):
            if not isinstance(cell, dict):
                continue

            nested_tables = cell.get("nested_tables")
            if not isinstance(nested_tables, list):
                continue

            for index, nested_table in enumerate(nested_tables):
                if not isinstance(nested_table, dict):
                    continue
                found = True
                hierarchy["nested_table_refs"].append(
                    {
                        "parent_cell_id": cell.get("cell_id"),
                        "nested_table_id": nested_table.get("table_id"),
                        "nested_table_index": index,
                    }
                )
                add_hierarchy_recursive(nested_table, stats=stats, depth=depth + 1)

    return found


def add_nested_hierarchy_from_direct_cells(
    table: dict[str, Any],
    hierarchy: dict[str, Any],
    stats: Counter[str] | None,
    depth: int,
) -> bool:
    found = False
    for cell in _as_list(table.get("cells")):
        if not isinstance(cell, dict):
            continue

        nested_tables = cell.get("nested_tables")
        if not isinstance(nested_tables, list):
            continue

        for index, nested_table in enumerate(nested_tables):
            if not isinstance(nested_table, dict):
                continue
            found = True
            hierarchy["nested_table_refs"].append(
                {
                    "parent_cell_id": cell.get("cell_id"),
                    "nested_table_id": nested_table.get("table_id"),
                    "nested_table_index": index,
                }
            )
            add_hierarchy_recursive(nested_table, stats=stats, depth=depth + 1)

    return found


def add_nested_hierarchy_from_summary_children(
    table: dict[str, Any],
    hierarchy: dict[str, Any],
    stats: Counter[str] | None,
    depth: int,
) -> bool:
    found = False
    for index, child in enumerate(_as_list(table.get("children"))):
        if not isinstance(child, dict):
            continue
        found = True
        hierarchy["nested_table_refs"].append(
            {
                "parent_cell_id": child.get("parent_cell_id"),
                "nested_table_id": child.get("table_id"),
                "nested_table_index": index,
            }
        )
        add_hierarchy_recursive(child, stats=stats, depth=depth + 1)
    return found


def _is_nested_table(table: dict[str, Any]) -> bool:
    if table.get("is_nested"):
        return True
    if table.get("parent_table_id") is not None:
        return True
    if table.get("parent_cell_id") is not None:
        return True
    return "_nested_tbl" in str(table.get("table_id", ""))


def _common_additional_title_preconditions(table: dict[str, Any], text: str) -> bool:
    if _is_nested_table(table):
        return False
    existing_hierarchy = table.get("hierarchy")
    if isinstance(existing_hierarchy, dict):
        if existing_hierarchy.get("header_rows"):
            return False
        if existing_hierarchy.get("header_cols"):
            return False
    if is_caption_or_note_table(table, text):
        return False
    return True


def _is_title_box_condition1(table: dict[str, Any], text: str) -> bool:
    if not _common_additional_title_preconditions(table, text):
        return False
    direct_cells = get_direct_cells(table)
    cell_count = len(direct_cells)
    non_empty_count = sum(1 for c in direct_cells if get_cell_text(c))
    empty_count = cell_count - non_empty_count
    if not (cell_count <= 4 and non_empty_count <= 2 and empty_count >= 1):
        return False
    direct_text = " ".join(get_cell_text(c) for c in direct_cells if get_cell_text(c))
    return 8 <= len(direct_text.strip()) <= 80


def _is_title_box_condition2(table: dict[str, Any], text: str) -> bool:
    if not _common_additional_title_preconditions(table, text):
        return False
    row_count, col_count = get_table_size(table)
    if row_count != 1 or col_count != 2:
        return False
    direct_cells = get_direct_cells(table)
    non_empty = [c for c in direct_cells if get_cell_text(c)]
    if len(non_empty) != 2:
        return False
    cells_by_col = sorted(non_empty, key=lambda c: _cell_col(c) or 0)
    first_text = get_cell_text(cells_by_col[0]).strip()
    second_text = get_cell_text(cells_by_col[1]).strip()
    first_len = len(first_text)
    if first_len == 0:
        return False
    return first_len <= 3 and len(second_text) >= first_len * 3 and len(second_text) <= 120


def _is_priority_title_box(
    table: dict[str, Any],
    text: str,
    non_empty_cells: list[dict[str, Any]],
) -> bool:
    """번호형 제목 패턴이면 caption 키워드 검사보다 우선하여 title_box로 판정한다."""
    if not text:
        return False
    if _is_nested_table(table):
        return False
    if not any(p.match(text) for p in _PRIORITY_TITLE_PATTERNS):
        return False
    row_count, col_count = get_table_size(table)
    if col_count >= 3 and row_count >= 3:
        return False
    if len(non_empty_cells) > 3:
        return False
    if not (row_count <= 2 or col_count <= 2):
        return False
    return not has_repetitive_data_structure(table)


def classify_table(table: dict[str, Any]) -> str:
    text = get_all_text(table)
    non_empty_cells = get_non_empty_cells(table)

    if _is_priority_title_box(table, text, non_empty_cells):
        return "title_box"

    if is_caption_or_note_table(table, text):
        return "caption_or_note_table"

    if is_title_box(table, text, non_empty_cells):
        return "title_box"

    if _is_title_box_condition1(table, text) or _is_title_box_condition2(table, text):
        return "title_box"

    if is_key_value_table(table):
        return "key_value_table"

    return "data_table"


def is_caption_or_note_table(table: dict[str, Any], text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    row_count, col_count = get_table_size(table)
    non_empty_count = len(get_non_empty_cells(table))

    if row_count >= 3 or col_count >= 3:
        return False

    if non_empty_count >= 4:
        return False

    if _starts_with_caption_prefix(stripped):
        return True

    if non_empty_count <= 3 and _contains_caption_prefix(stripped):
        return True

    return False


def is_title_box(
    table: dict[str, Any],
    text: str,
    non_empty_cells: list[dict[str, Any]],
) -> bool:
    if not text or is_caption_or_note_table(table, text):
        return False

    row_count, col_count = get_table_size(table)
    if col_count >= 3 and row_count >= 3:
        return False

    if len(non_empty_cells) > 3:
        return False

    if not (row_count <= 2 or col_count <= 2):
        return False

    if not any(pattern.match(text) for pattern in TITLE_PATTERNS):
        return False

    return not has_repetitive_data_structure(table)


def _has_uniform_row_structure(table: dict[str, Any]) -> bool:
    """행 컬럼 패턴이 균일한지 판단한다 (반복 레코드 구조 감지).

    동일한 컬럼 패턴이 절반 이상의 행에서 나타나면 True.
    """
    row_cells = group_origin_cells_by_row(table)
    # 2개 이상 셀이 있는 행만 패턴 대상으로 삼음
    patterns = [
        tuple(sorted(
            col for c in cells
            if (col := _cell_col(c)) is not None and get_cell_text(c)
        ))
        for cells in row_cells.values()
        if sum(1 for c in cells if get_cell_text(c)) >= 2
    ]
    if len(patterns) < 2:
        return False
    most_common_count = Counter(patterns).most_common(1)[0][1]
    return most_common_count / len(patterns) > 0.5


def _count_adjacent_kv_pairs(table: dict[str, Any], key_max_len: int = 20) -> int:
    """각 행에서 짧은 key + 비어있지 않은 value 인접 쌍 수를 반환한다."""
    count = 0
    for cells in group_origin_cells_by_row(table).values():
        cols_cells = sorted(
            [(col, c) for c in cells if (col := _cell_col(c)) is not None],
            key=lambda x: x[0],
        )
        for i in range(len(cols_cells) - 1):
            _, left = cols_cells[i]
            _, right = cols_cells[i + 1]
            left_text = get_cell_text(left)
            right_text = get_cell_text(right)
            if left_text and right_text and len(left_text) <= key_max_len:
                count += 1
    return count


def _is_form_kv_table(table: dict[str, Any]) -> bool:
    """병합 포함 서식형 key-value 표 감지.

    - 행 구조가 다양하고 (균일한 반복 레코드가 아님)
    - 짧은 key + value 인접 쌍이 3개 이상이면 True.
    """
    row_count, col_count = get_table_size(table)
    if row_count < 3 or col_count < 2:
        return False
    if len(group_origin_cells_by_row(table)) < 3:
        return False
    # 균일한 반복 구조이면 data_table
    if _has_uniform_row_structure(table):
        return False
    return _count_adjacent_kv_pairs(table) >= 3


def _detect_kv_orientation(table: dict[str, Any]) -> str | None:
    """key-value 방향을 감지한다.

    반환값:
      "row_pairs"    — 2열 구조: 각 행이 key/value 쌍
      "column_pairs" — 2행 구조: 첫 행이 key, 둘째 행이 value
      "form_kv"      — 병합 포함 서식형 표
      None           — key_value_table 아님
    """
    row_count, col_count = get_table_size(table)

    # ── 단순 2열 row_pairs ──────────────────────────────────────
    if col_count == 2 and row_count >= 2:
        if has_repetitive_data_structure(table):
            return None

        row_pairs = get_key_value_row_pairs(table)
        if len(row_pairs) < 2:
            return None

        left_texts = [get_cell_text(l) for l, _ in row_pairs]
        right_texts = [get_cell_text(r) for _, r in row_pairs]
        left_non_empty = [t for t in left_texts if t]
        right_non_empty = [t for t in right_texts if t]

        if len(left_non_empty) < 2 or len(right_non_empty) < 2:
            return None
        if (1 - len(left_non_empty) / len(left_texts)) > 0.25:
            return None
        if (1 - len(right_non_empty) / len(right_texts)) > 0.35:
            return None

        left_avg = _avg_len(left_non_empty)
        right_avg = _avg_len(right_non_empty)
        if left_avg <= 12 and right_avg >= left_avg:
            return "row_pairs"
        return None

    # ── 단순 2행 column_pairs ───────────────────────────────────
    if row_count == 2 and col_count >= 2:
        row_cells = group_origin_cells_by_row(table)
        if len(row_cells) != 2:
            return None
        rows = sorted(row_cells.items())
        key_cells = rows[0][1]
        val_cells = rows[1][1]

        key_texts = [get_cell_text(c) for c in key_cells]
        val_texts = [get_cell_text(c) for c in val_cells]
        key_non_empty = [t for t in key_texts if t]
        val_non_empty = [t for t in val_texts if t]

        if len(key_non_empty) < 2 or len(val_non_empty) < 2:
            return None
        if len(key_non_empty) != len(val_non_empty):
            return None

        key_avg = _avg_len(key_non_empty)
        val_avg = _avg_len(val_non_empty)
        val_min = min(len(t) for t in val_non_empty)

        if key_avg > 6:
            return None
        if val_avg < key_avg * 2:
            return None
        if val_min < 3:
            return None
        return "column_pairs"

    # ── 서식형 form-style (3행+, 2열+) ─────────────────────────
    if _is_form_kv_table(table):
        return "form_kv"

    return None


def is_key_value_table(table: dict[str, Any]) -> bool:
    return _detect_kv_orientation(table) is not None


def build_key_value_records(
    table: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[int], list[Any], str]:
    """key_value_table의 pairs, header_rows, body_cells, orientation을 반환한다."""
    records: list[dict[str, Any]] = []
    header_rows: list[int] = []
    body_cells: list[Any] = []

    orientation = _detect_kv_orientation(table) or "row_pairs"

    if orientation == "row_pairs":
        row_pairs = get_key_value_row_pairs(table)
        start_index = 0

        if row_pairs:
            first_left, first_right = row_pairs[0]
            first_pair = (
                normalize_text(get_cell_text(first_left)).lower(),
                normalize_text(get_cell_text(first_right)).lower(),
            )
            if first_pair in KEY_VALUE_HEADERS:
                row_index = _cell_row(first_left)
                if row_index is not None:
                    header_rows.append(row_index)
                start_index = 1

        for left_cell, right_cell in row_pairs[start_index:]:
            key = get_cell_text(left_cell)
            value = get_cell_text(right_cell)
            if not key and not value:
                continue
            key_cell_id = left_cell.get("cell_id")
            value_cell_id = right_cell.get("cell_id")
            records.append({
                "key": key,
                "value": value,
                "key_cell_id": key_cell_id,
                "value_cell_id": value_cell_id,
                "source_cells": [key_cell_id, value_cell_id],
            })
            body_cells.extend([key_cell_id, value_cell_id])

    elif orientation == "column_pairs":
        row_cells = group_origin_cells_by_row(table)
        rows = sorted(row_cells.items())
        key_row_index, key_cells = rows[0]
        val_row_index, val_cells = rows[1]

        header_rows.append(key_row_index)

        key_by_col = {_cell_col(c): c for c in key_cells if _cell_col(c) is not None}
        val_by_col = {_cell_col(c): c for c in val_cells if _cell_col(c) is not None}

        for col in sorted(key_by_col):
            key_cell = key_by_col[col]
            val_cell = val_by_col.get(col)
            if val_cell is None:
                continue
            key = get_cell_text(key_cell)
            value = get_cell_text(val_cell)
            if not key and not value:
                continue
            key_cell_id = key_cell.get("cell_id")
            value_cell_id = val_cell.get("cell_id")
            records.append({
                "key": key,
                "value": value,
                "key_cell_id": key_cell_id,
                "value_cell_id": value_cell_id,
                "source_cells": [key_cell_id, value_cell_id],
            })
            body_cells.extend([key_cell_id, value_cell_id])

    else:  # form_kv
        for cells in group_origin_cells_by_row(table).values():
            cols_cells = sorted(
                [(col, c) for c in cells if (col := _cell_col(c)) is not None],
                key=lambda x: x[0],
            )
            for i in range(len(cols_cells) - 1):
                _, left = cols_cells[i]
                _, right = cols_cells[i + 1]
                key = get_cell_text(left)
                value = get_cell_text(right)
                if not key or not value or len(key) > 20:
                    continue
                key_cell_id = left.get("cell_id")
                value_cell_id = right.get("cell_id")
                records.append({
                    "key": key,
                    "value": value,
                    "key_cell_id": key_cell_id,
                    "value_cell_id": value_cell_id,
                    "source_cells": [key_cell_id, value_cell_id],
                })
                body_cells.extend([key_cell_id, value_cell_id])

    return records, _unique(header_rows), _unique(body_cells), orientation


def infer_header_rows(table: dict[str, Any]) -> tuple[list[int], bool]:
    row_cells = group_origin_cells_by_row(table)
    if not row_cells:
        return [], True

    first_row_index = min(row_cells)
    first_cells = row_cells[first_row_index]
    first_texts = [get_cell_text(cell) for cell in first_cells]
    non_empty_count = sum(1 for text in first_texts if text)
    row_count, col_count = get_table_size(table)
    ratio = non_empty_count / max(len(first_cells), col_count, 1)
    avg_first = _avg_len([text for text in first_texts if text])

    later_texts = [
        get_cell_text(cell)
        for row_index, cells in row_cells.items()
        if row_index != first_row_index
        for cell in cells
        if get_cell_text(cell)
    ]
    later_avg = _avg_len(later_texts)

    repeat_header = table.get("repeat_header")
    is_repeat_header = repeat_header is True or str(repeat_header).lower() == "true"
    short_label_row = non_empty_count > 0 and avg_first <= 18

    if is_repeat_header and non_empty_count:
        return [first_row_index], False

    if row_count > 1 and ratio >= 0.5 and short_label_row and (later_avg == 0 or avg_first <= later_avg):
        return [first_row_index], False

    return [], row_count > 1


def build_body_cells(table: dict[str, Any], excluded_rows: set[int]) -> list[Any]:
    body_cells: list[Any] = []
    for row_index, cells in group_origin_cells_by_row(table).items():
        if row_index in excluded_rows:
            continue
        for cell in cells:
            if get_cell_text(cell):
                body_cells.append(cell.get("cell_id"))
    return _unique(body_cells)


def get_key_value_row_pairs(table: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for _, cells in sorted(group_origin_cells_by_row(table).items()):
        cells_with_col = [
            (col, cell)
            for cell in cells
            if (col := _cell_col(cell)) is not None
        ]
        if len(cells_with_col) < 2:
            continue
        cells_with_col.sort(key=lambda item: item[0])
        pairs.append((cells_with_col[0][1], cells_with_col[1][1]))
    return pairs


def group_origin_cells_by_row(table: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for cell in get_direct_cells(table):
        row_index = _cell_row(cell)
        if row_index is None:
            continue
        result.setdefault(row_index, []).append(cell)

    for cells in result.values():
        cells.sort(key=lambda cell: _cell_col(cell) or 0)

    return dict(sorted(result.items()))


def has_repetitive_data_structure(table: dict[str, Any]) -> bool:
    row_cells = group_origin_cells_by_row(table)
    if len(row_cells) < 3:
        return False

    non_empty_rows = 0
    for cells in row_cells.values():
        if sum(1 for cell in cells if get_cell_text(cell)) >= 2:
            non_empty_rows += 1

    _, col_count = get_table_size(table)
    return non_empty_rows >= 3 and col_count >= 2


def get_table_size(table: dict[str, Any]) -> tuple[int, int]:
    row_count = _to_int(table.get("row_count"))
    col_count = _to_int(table.get("col_count"))

    grid = table.get("grid")
    if isinstance(grid, dict):
        grid_row_count = _to_int(grid.get("row_count"))
        grid_col_count = _to_int(grid.get("col_count"))
        row_count = row_count if row_count is not None else grid_row_count
        col_count = col_count if col_count is not None else grid_col_count

    if row_count is None or col_count is None:
        preprocess = table.get("preprocess")
        preprocess_grid = preprocess.get("grid") if isinstance(preprocess, dict) else None
        if isinstance(preprocess_grid, dict):
            row_count = row_count if row_count is not None else _to_int(preprocess_grid.get("row_count"))
            col_count = col_count if col_count is not None else _to_int(preprocess_grid.get("col_count"))

        layout = preprocess.get("layout") if isinstance(preprocess, dict) else None
        if isinstance(layout, dict):
            row_count = row_count if row_count is not None else _to_int(layout.get("row_count"))
            col_count = col_count if col_count is not None else _to_int(layout.get("col_count"))

    return row_count or 0, col_count or 0


def add_table_hierarchy_to_json(
    input_path: str | Path = "tables_preprocessed.json",
    output_path: str | Path = "tables_hierarchical.json",
) -> None:
    input_file = Path(input_path)
    output_file = Path(output_path)

    with input_file.open("r", encoding="utf-8") as f:
        tables = json.load(f)

    if not isinstance(tables, list):
        raise ValueError("top-level JSON must be list[table]")

    stats: Counter[str] = Counter()
    for table in tables:
        if isinstance(table, dict):
            add_hierarchy_recursive(table, stats=stats)

    for table in tables:
        if isinstance(table, dict):
            normalize_grid_location_recursive(table)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(tables, f, ensure_ascii=False, indent=2)

    type_counts = {
        key.removeprefix("type:"): value
        for key, value in sorted(stats.items())
        if key.startswith("type:")
    }

    print("table hierarchy added")
    print(f"total tables processed: {stats['total_tables']}")
    print(f"table_type counts: {type_counts}")
    print(f"nested tables processed: {stats['nested_tables']}")
    print(f"warnings count: {stats['warnings']}")


def normalize_grid_location_recursive(table: dict[str, Any]) -> None:
    preprocess = table.get("preprocess")
    preprocess_grid = preprocess.get("grid") if isinstance(preprocess, dict) else None

    if isinstance(preprocess_grid, dict) and not is_valid_grid(table.get("grid")):
        table["grid"] = preprocess_grid

    grid = table.get("grid")
    if isinstance(grid, dict):
        grid.pop("cells", None)

    if isinstance(preprocess, dict):
        preprocess.pop("grid", None)

    recursed = False
    for row in _as_list(table.get("rows")):
        if not isinstance(row, dict):
            continue
        for cell in _as_list(row.get("cells")):
            if not isinstance(cell, dict):
                continue
            nested_tables = cell.get("nested_tables")
            if not isinstance(nested_tables, list):
                continue
            recursed = True
            for nested_table in nested_tables:
                if isinstance(nested_table, dict):
                    normalize_grid_location_recursive(nested_table)

    if recursed:
        return

    for cell in _as_list(table.get("cells")):
        if not isinstance(cell, dict):
            continue
        nested_tables = cell.get("nested_tables")
        if not isinstance(nested_tables, list):
            continue
        recursed = True
        for nested_table in nested_tables:
            if isinstance(nested_table, dict):
                normalize_grid_location_recursive(nested_table)

    if recursed:
        return

    for child in _as_list(table.get("children")):
        if isinstance(child, dict):
            normalize_grid_location_recursive(child)


def is_valid_grid(grid: Any) -> bool:
    if not isinstance(grid, dict):
        return False

    if grid.get("row_count") is None or grid.get("col_count") is None:
        return False

    slots = grid.get("slots")
    return isinstance(slots, list) and len(slots) > 0


def _base_hierarchy() -> dict[str, Any]:
    return {
        "table_type": "data_table",
        "title_cells": [],
        "caption_or_note_cells": [],
        "key_value_records": [],
        "header_rows": [],
        "header_cols": [],
        "body_cells": [],
        "nested_table_refs": [],
        "quality": {
            "warnings": [],
        },
    }


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _cell_ids(cells: list[dict[str, Any]]) -> list[Any]:
    return _unique([cell.get("cell_id") for cell in cells])


def _unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        key = str(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _starts_with_caption_prefix(text: str) -> bool:
    lower_text = text.lower()
    for prefix in CAPTION_OR_NOTE_PREFIXES:
        if lower_text.startswith(prefix.lower()):
            return True
    return False


def _contains_caption_prefix(text: str) -> bool:
    lower_text = text.lower()
    for prefix in _CAPTION_CONTAINS_PREFIXES:
        if prefix.lower() in lower_text:
            return True
    return False


def _avg_len(texts: list[str]) -> float:
    if not texts:
        return 0.0
    return sum(len(text) for text in texts) / len(texts)


def _cell_row(cell: dict[str, Any]) -> int | None:
    row = _to_int(cell.get("row_addr"))
    if row is not None:
        return row

    position = cell.get("position")
    if isinstance(position, dict):
        return _to_int(position.get("row_addr"))

    return None


def _cell_col(cell: dict[str, Any]) -> int | None:
    col = _to_int(cell.get("col_addr"))
    if col is not None:
        return col

    position = cell.get("position")
    if isinstance(position, dict):
        return _to_int(position.get("col_addr"))

    return None


def _to_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


if __name__ == "__main__":
    add_table_hierarchy_to_json()
