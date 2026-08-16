#================================================
# add_table_hierarchy_ref_to_blocks.py
# Stage 7.5-A: 표 hierarchy 요약 메타데이터 연결
#
# blocks.json의 table block에 tables_hierarchical.json의
# "요약 메타데이터"만 붙인다.
#
# 이 단계에서 하지 않는 것 (실패 기준):
# - table_cell_group block 생성
# - structured_records / raw_rows 전체 복사
# - nested table의 별도 block 전개
# - table_type 재분류, header_rows 재추론
# - DepthResolver 로직 변경
#================================================

from __future__ import annotations

from collections import Counter
from typing import Any

from .pipeline_models import BlocksDocument
from .correct_title_box_depths import (
    get_table_display_text_from_hierarchy,
)


# 이번 단계에서 허용하는 warning 코드
_WARNING_CODES = (
    "missing_table_hierarchy",
    "table_id_mismatch",
    "raw_only_table",
    "low_record_confidence",
    "missing_header_rows",
    "nested_table_present",
    "irregular_grid",
    "missing_title_text",
)

# text_preview 최대 길이 (blocks.json 단독 가독성용 미리보기)
_TEXT_PREVIEW_MAX_LENGTH = 120


#------------------------------------------------
# record_status / size 해석
#------------------------------------------------

def _resolve_record_status(hierarchy: dict[str, Any]) -> str:
    """기존 record_status 우선, 없으면 폴백 계산."""
    existing = hierarchy.get("record_status")
    if existing:
        return existing

    structured_record_count = len(hierarchy.get("structured_records") or [])
    if structured_record_count > 0:
        return "structured"
    if hierarchy.get("table_type") == "data_table":
        return "raw_only"
    return "not_applicable"


def _resolve_size(table: dict[str, Any]) -> dict[str, Any]:
    """
    row/col_count 소스 우선순위:
    grid > validation.actual_max > validation.declared > null
    """
    grid = table.get("grid")
    if isinstance(grid, dict):
        row = grid.get("row_count")
        col = grid.get("col_count")
        if row is not None and col is not None:
            return {"row_count": row, "col_count": col, "source": "grid"}

    validation = (table.get("preprocess") or {}).get("validation") or {}

    row = validation.get("actual_max_row_count")
    col = validation.get("actual_max_col_count")
    if row is not None and col is not None:
        return {"row_count": row, "col_count": col, "source": "validation_actual"}

    row = validation.get("declared_row_count")
    col = validation.get("declared_col_count")
    if row is not None and col is not None:
        return {"row_count": row, "col_count": col, "source": "validation_declared"}

    return {"row_count": None, "col_count": None, "source": None}


#------------------------------------------------
# table_hierarchy_ref 생성
#------------------------------------------------

def _build_matched_ref(table: dict[str, Any], block: dict[str, Any]) -> dict[str, Any]:
    hierarchy = table.get("hierarchy") or {}
    preprocess = table.get("preprocess") or {}
    identity = preprocess.get("identity") or {}
    validation = preprocess.get("validation") or {}

    table_type = hierarchy.get("table_type")
    record_status = _resolve_record_status(hierarchy)
    size = _resolve_size(table)

    header_rows = hierarchy.get("header_rows") or []
    header_cols = hierarchy.get("header_cols") or []

    structured_record_count = len(hierarchy.get("structured_records") or [])
    raw_rows = hierarchy.get("raw_rows")
    raw_row_count = len(raw_rows) if raw_rows else size["row_count"]

    child_table_ids = [
        child.get("table_id")
        for child in (table.get("children") or [])
        if isinstance(child, dict) and child.get("table_id")
    ]

    warnings: list[str] = []

    # 보조 검증: section_index / table_index / xml_table_id
    sf = block.get("structure_features") or {}
    mismatches = []
    if identity.get("section_index") is not None and identity["section_index"] != block.get("section_index"):
        mismatches.append("section_index")
    if identity.get("table_index") is not None and sf.get("table_index") is not None \
            and identity["table_index"] != sf["table_index"]:
        mismatches.append("table_index")
    if identity.get("xml_table_id") and sf.get("xml_table_id") \
            and str(identity["xml_table_id"]) != str(sf["xml_table_id"]):
        mismatches.append("xml_table_id")
    if mismatches:
        warnings.append("table_id_mismatch")

    if record_status == "raw_only":
        warnings.append("raw_only_table")
    if table_type == "data_table" and structured_record_count == 0:
        warnings.append("low_record_confidence")
    if table_type == "data_table" and not header_rows:
        warnings.append("missing_header_rows")
    if child_table_ids:
        warnings.append("nested_table_present")
    if validation.get("has_issues") or validation.get("is_valid") is False:
        warnings.append("irregular_grid")

    # blocks.json 단독 가독성용 대표 텍스트.
    # title_box는 제목 전체(title_text), 나머지 표는 길이 제한 미리보기만 둔다.
    display_text = get_table_display_text_from_hierarchy(table)
    title_text = display_text if table_type == "title_box" and display_text else None
    text_preview = (
        display_text[:_TEXT_PREVIEW_MAX_LENGTH] if display_text else None
    )
    if table_type == "title_box" and not display_text:
        warnings.append("missing_title_text")

    return {
        "match_status": "matched",
        "table_id": table.get("table_id"),
        "table_type": table_type,
        "record_status": record_status,
        "title_text": title_text,
        "text_preview": text_preview,
        "nesting": {
            "is_nested": bool(table.get("is_nested")),
            "parent_table_id": table.get("parent_table_id"),
            "parent_cell_id": table.get("parent_cell_id"),
            "child_table_count": len(child_table_ids),
            "child_table_ids": child_table_ids,
        },
        "size": size,
        "headers": {
            "header_rows": header_rows,
            "header_cols": header_cols,
            "has_header_rows": len(header_rows) > 0,
            "has_header_cols": len(header_cols) > 0,
        },
        "records": {
            "structured_record_count": structured_record_count,
            "raw_row_count": raw_row_count,
        },
        "quality_warnings": warnings,
    }


def _build_missing_ref(source_table_id: str | None) -> dict[str, Any]:
    return {
        "match_status": "missing",
        "table_id": source_table_id,
        "table_type": None,
        "record_status": None,
        "title_text": None,
        "text_preview": None,
        "nesting": {
            "is_nested": None,
            "parent_table_id": None,
            "parent_cell_id": None,
            "child_table_count": 0,
            "child_table_ids": [],
        },
        "size": {"row_count": None, "col_count": None, "source": None},
        "headers": {
            "header_rows": [],
            "header_cols": [],
            "has_header_rows": False,
            "has_header_cols": False,
        },
        "records": {
            "structured_record_count": 0,
            "raw_row_count": None,
        },
        "quality_warnings": ["missing_table_hierarchy"],
    }


#------------------------------------------------
# 통계 (최상위 85 기준 / 중첩 포함 200 기준 분리)
#------------------------------------------------

def _walk_all_tables(tables: list[dict[str, Any]]):
    for table in tables:
        yield table
        for child in table.get("children") or []:
            if isinstance(child, dict):
                yield from _walk_all_tables([child])


def _build_all_table_stats(tables: list[dict[str, Any]]) -> dict[str, Any]:
    type_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    total = 0
    for table in _walk_all_tables(tables):
        total += 1
        hierarchy = table.get("hierarchy") or {}
        type_counts[hierarchy.get("table_type")] += 1
        status_counts[_resolve_record_status(hierarchy)] += 1
    return {
        "all_table_count": total,
        "table_type": dict(type_counts),
        "record_status": dict(status_counts),
    }


#------------------------------------------------
# 진입점
#------------------------------------------------

def add_table_hierarchy_ref_to_blocks(
    blocks_doc: BlocksDocument,
    tables: list[dict[str, Any]],
) -> BlocksDocument:
    """
    역할: BlocksDocument의 모든 table block에 table_hierarchy_ref 요약을 부착한다.
    입력 데이터: blocks_doc(BlocksDocument), tables(hierarchy가 반영된 표 리스트, 읽기 전용).
    출력 데이터: 갱신된 BlocksDocument.
    """
    table_index = {
        table.get("table_id"): table
        for table in tables
        if table.get("table_id")
    }

    matched = 0
    missing = 0
    top_type_counts: Counter[str] = Counter()
    top_status_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()

    table_blocks = [
        block for block in blocks_doc.blocks
        if block.get("block_type") == "table"
    ]

    for block in table_blocks:
        sf = block.get("structure_features") or {}
        source_table_id = sf.get("table_id") or block.get("source_table_id")

        table = table_index.get(source_table_id)
        if table is not None:
            ref = _build_matched_ref(table, block)
            matched += 1
            top_type_counts[ref["table_type"]] += 1
            top_status_counts[ref["record_status"]] += 1
            # role은 바꾸지 않고 evidence로만 제공한다
            block.setdefault("evidence", []).append(
                f"table_hierarchy_ref: type={ref['table_type']} "
                f"status={ref['record_status']}"
            )
        else:
            ref = _build_missing_ref(source_table_id)
            missing += 1
            block.setdefault("warnings", []).append("missing_table_hierarchy")

        block["table_hierarchy_ref"] = ref
        for code in ref["quality_warnings"]:
            warning_counts[code] += 1

    stats = {
        "top_level_block_stats": {
            "table_block_count": len(table_blocks),
            "matched": matched,
            "missing": missing,
            "table_type": dict(top_type_counts),
            "record_status": dict(top_status_counts),
            "quality_warning_counts": dict(warning_counts),
        },
        "all_table_hierarchy_stats": _build_all_table_stats(tables),
    }
    blocks_doc.quality["table_hierarchy_link"] = stats

    _print_verification_log(stats)
    return blocks_doc


def _print_verification_log(stats: dict[str, Any]) -> None:
    top = stats["top_level_block_stats"]
    all_stats = stats["all_table_hierarchy_stats"]

    print("=== Stage 7.5-A: table_hierarchy_ref 연결 결과 ===")
    print(f"table blocks: {top['table_block_count']}")
    print(f"matched table_hierarchy_ref: {top['matched']}")
    print(f"missing table_hierarchy_ref: {top['missing']}")
    print()
    print("[top_level_block_stats]")
    for name, count in sorted(top["table_type"].items(), key=lambda x: -x[1]):
        print(f"- {name}: {count}")
    for name, count in sorted(top["record_status"].items(), key=lambda x: -x[1]):
        print(f"- record_status {name}: {count}")
    for name, count in sorted(top["quality_warning_counts"].items(), key=lambda x: -x[1]):
        print(f"- warning {name}: {count}")
    print()
    print("[all_table_hierarchy_stats] (중첩 포함 참고 통계)")
    print(f"all tables including nested: {all_stats['all_table_count']}")
    for name, count in sorted(all_stats["table_type"].items(), key=lambda x: -x[1]):
        print(f"- {name}: {count}")
    for name, count in sorted(all_stats["record_status"].items(), key=lambda x: -x[1]):
        print(f"- record_status {name}: {count}")
    print("table_cell_group created: 0")
    print("nested expanded: 0")
