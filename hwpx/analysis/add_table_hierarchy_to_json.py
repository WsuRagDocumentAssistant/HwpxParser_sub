#================================================
# add_table_hierarchy_to_json.py
#================================================

from __future__ import annotations

from collections import Counter
from typing import Any

from .table_hierarchy.grid_normalizer import normalize_grid_location_recursive
from .table_hierarchy.orchestrator import add_hierarchy_recursive

import logging

# 라이브러리는 조용한 것이 기본이다. 단계 보고를 보려면 쓰는 쪽에서
# logging 을 켠다. tools 는 그렇게 하고 있다.
log = logging.getLogger(__name__)


def add_table_hierarchy(
    tables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    역할: preprocess+grid가 반영된 표 리스트에 hierarchy 정보를 추가한다.
    입력 데이터: tables(표 dict 리스트). in-place로 hierarchy 키를 추가한다.
    출력 데이터: hierarchy가 추가된 동일 리스트.
    """
    if not isinstance(tables, list):
        raise ValueError("tables 최상위 구조는 list[table] 이어야 합니다.")

    stats: Counter[str] = Counter()
    for table in tables:
        if isinstance(table, dict):
            add_hierarchy_recursive(table, stats=stats)

    for table in tables:
        if isinstance(table, dict):
            normalize_grid_location_recursive(table)

    type_counts = {
        key.removeprefix("type:"): value
        for key, value in sorted(stats.items())
        if key.startswith("type:")
    }

    log.info("table hierarchy added")
    log.info(f"total tables processed: {stats['total_tables']}")
    log.info(f"table_type counts: {type_counts}")
    log.info(f"nested tables processed: {stats['nested_tables']}")
    log.info(f"warnings count: {stats['warnings']}")

    return tables
