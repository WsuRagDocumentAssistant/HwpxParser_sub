#================================================
# make_body_linking_table_json.py
#================================================

from __future__ import annotations

from collections import Counter
from typing import Any

import logging

# 라이브러리는 조용한 것이 기본이다. 단계 보고를 보려면 쓰는 쪽에서
# logging 을 켠다. tools 는 그렇게 하고 있다.
log = logging.getLogger(__name__)


#------------------------------------------------
# 안전 접근 헬퍼
#------------------------------------------------

def _get_dict(source: Any, key: str) -> dict[str, Any]:
    """source[key]가 dict면 그대로, 아니면 빈 dict를 반환한다."""
    if isinstance(source, dict):
        value = source.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _get_list(source: Any, key: str) -> list[Any]:
    """source[key]가 list면 그대로, 아니면 빈 list를 반환한다."""
    if isinstance(source, dict):
        value = source.get(key)
        if isinstance(value, list):
            return value
    return []


def _get_value(source: Any, key: str) -> Any:
    """source[key]를 반환하고, 없으면 None을 반환한다."""
    if isinstance(source, dict):
        return source.get(key)
    return None


#------------------------------------------------
# 표 하나를 본문 연결용 경량 dict로 변환
#------------------------------------------------

def build_body_linking_table(table: dict) -> dict:
    """
    역할: tables_hierarchical.json의 표 하나에서 본문-표 계층 연결에
          필요한 최소 컬럼만 추려 경량 dict를 만든다.
    입력 데이터: table(tables_hierarchical.json의 표 dict).
    출력 데이터: 경량화된 표 dict. children도 재귀적으로 동일 기준으로 경량화한다.
                 누락된 필드는 None 또는 빈 배열/빈 dict로 채운다.
    """
    preprocess = _get_dict(table, "preprocess")
    identity = _get_dict(preprocess, "identity")
    nesting = _get_dict(preprocess, "nesting")
    layout = _get_dict(preprocess, "layout")
    candidates = _get_dict(preprocess, "candidates")
    text = _get_dict(preprocess, "text")
    hierarchy = _get_dict(table, "hierarchy")

    return {
        # 1) 최상위 필드
        "table_id": _get_value(table, "table_id"),
        "is_nested": _get_value(table, "is_nested"),
        "parent_table_id": _get_value(table, "parent_table_id"),
        "parent_cell_id": _get_value(table, "parent_cell_id"),

        # 2) identity: 문서 내 등장 순서 (본문 흐름 매핑의 기본 키)
        "identity": {
            "section_index": _get_value(identity, "section_index"),
            "table_index": _get_value(identity, "table_index"),
        },

        # 3) hierarchy/type: 제목표(title_box) 여부와 제목/캡션 셀
        "hierarchy": {
            "table_type": _get_value(hierarchy, "table_type"),
            "title_cells": _get_list(hierarchy, "title_cells"),
            "caption_or_note_cells": _get_list(hierarchy, "caption_or_note_cells"),
            "nested_table_refs": _get_list(hierarchy, "nested_table_refs"),
        },

        # 4) candidates: 표 주변 본문 문단에서 추출된 텍스트
        "candidates": {
            "caption_candidate": _get_value(candidates, "caption_candidate"),
            "note_candidate": _get_value(candidates, "note_candidate"),
            "source_candidate": _get_value(candidates, "source_candidate"),
        },

        # 5) text: 본문 제목/문단과의 내용 매칭 재료
        "text": {
            "plain_text": _get_value(text, "plain_text"),
            "plain_text_without_nested_tables": _get_value(
                text, "plain_text_without_nested_tables"
            ),
            "cell_texts": _get_list(text, "cell_texts"),
        },

        # 6) layout: 본문 흐름 인라인 여부 + 제목표 판별 보조
        "layout": {
            "treat_as_char": _get_value(layout, "treat_as_char"),
            "flow_with_text": _get_value(layout, "flow_with_text"),
            "pos_x": _get_value(layout, "pos_x"),
            "pos_y": _get_value(layout, "pos_y"),
            "width": _get_value(layout, "width"),
            "height": _get_value(layout, "height"),
        },

        # 7) nesting: 표 간 중첩 계층
        "nesting": {
            "depth": _get_value(nesting, "depth"),
            "has_child_table": _get_value(nesting, "has_child_table"),
            "child_table_ids": _get_list(nesting, "child_table_ids"),
        },

        # 8) 오판 방지 보조 정보 (본문형/도식형/중첩형 판별용)
        "structure": _get_dict(preprocess, "structure"),
        "objects": _get_dict(preprocess, "objects"),
        "text_stats": {
            "paragraph_count": _get_value(text, "paragraph_count"),
            "run_count": _get_value(text, "run_count"),
            "empty_text_cell_count": _get_value(text, "empty_text_cell_count"),
            "non_empty_text_cell_count": _get_value(text, "non_empty_text_cell_count"),
            "multiline_cell_count": _get_value(text, "multiline_cell_count"),
            "has_multiline_cell": _get_value(text, "has_multiline_cell"),
        },
        "style_features": _get_dict(preprocess, "style_features"),
        "full_width_blocks": _get_list(hierarchy, "full_width_blocks"),
        "raw_blocks": _get_list(hierarchy, "raw_blocks"),

        # children 중첩 구조 유지 (동일 기준으로 재귀 경량화)
        "children": [
            build_body_linking_table(child)
            for child in _get_list(table, "children")
            if isinstance(child, dict)
        ],
    }


#------------------------------------------------
# 검증 통계 집계
#------------------------------------------------

def _count_tables_recursive(tables: list[dict]) -> int:
    """children을 포함한 전체 표 개수를 센다."""
    count = 0
    for table in tables:
        count += 1
        count += _count_tables_recursive(table.get("children", []))
    return count


def _collect_stats_recursive(
    tables: list[dict],
    type_counts: Counter[str],
    missing_core_ids: list[str],
) -> None:
    """children 포함 전체 표의 table_type 분포와 핵심 필드 누락 표를 집계한다."""
    core_missing_checks = (
        lambda t: t.get("table_id") is None,
        lambda t: t["identity"].get("section_index") is None,
        lambda t: t["identity"].get("table_index") is None,
        lambda t: t["hierarchy"].get("table_type") is None,
        lambda t: t["text"].get("plain_text") is None,
    )

    for table in tables:
        table_type = table["hierarchy"].get("table_type")
        type_counts[table_type if table_type is not None else "(missing)"] += 1

        if any(check(table) for check in core_missing_checks):
            missing_core_ids.append(str(table.get("table_id")))

        _collect_stats_recursive(
            table.get("children", []),
            type_counts,
            missing_core_ids,
        )


#------------------------------------------------
# 전체 변환 + 저장
#------------------------------------------------

def build_body_linking_tables(
    tables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    역할: hierarchy가 반영된 표 리스트에서 본문-표 계층 연결용 경량 리스트를 생성한다.
    입력 데이터: tables(hierarchy 표 dict 리스트). 원본은 수정하지 않는다.
    출력 데이터: 경량화된 새 표 dict 리스트. 변환/검증 통계를 콘솔에 출력한다.
    """
    if not isinstance(tables, list):
        raise ValueError(
            f"tables 최상위 구조는 list[table] 이어야 합니다. got {type(tables).__name__}"
        )

    linked_tables = [
        build_body_linking_table(table)
        for table in tables
        if isinstance(table, dict)
    ]

    type_counts: Counter[str] = Counter()
    missing_core_ids: list[str] = []
    _collect_stats_recursive(linked_tables, type_counts, missing_core_ids)

    log.info("body linking tables created")
    log.info(f"input tables (top-level)  : {len(tables)}")
    log.info(f"output tables (top-level) : {len(linked_tables)}")
    log.info(f"total tables (with children): {_count_tables_recursive(linked_tables)}")
    log.info(f"table_type counts: {dict(sorted(type_counts.items()))}")
    log.info(f"tables missing core fields: {len(missing_core_ids)}")
    if missing_core_ids:
        log.info(f"  ids: {missing_core_ids[:10]}")

    return linked_tables
