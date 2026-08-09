#================================================
# validate_table_internal_blocks.py
# Stage 9-C: Table Internal Validator
#
# Stage 7.5-B가 생성한 table_internal_blocks.json의 구조 무결성을 검증한다.
#
# 검증 결과는 warnings.json / quality_report.json에만 반영한다.
# blocks.json / tables_hierarchical.json / table_internal_blocks.json은
# 읽기 전용으로 두며 절대 수정하지 않는다.
#
# 핵심 원칙:
# - tables_hierarchical.json은 top-level table만 배열에 직접 있으므로
#   children[]을 재귀 순회한 recursive table index를 기준으로 삼는다.
# - internal_block의 evidence 문자열은 파싱하지 않는다.
#   주소/span 검사는 원본 preprocess.cells[] 기준으로 수행한다.
# - absolute_depth 검증의 base_depth는 blocks.json에서
#   source_block_id에 해당하는 table block의 depth를 사용한다.
# - validate_blocks(9-A/9-B)가 warnings.json / quality_report.json을
#   새로 생성하므로, 이 validator는 그 뒤에 실행해 append/merge 한다.
#   재실행 시 중복을 막기 위해 기존 stage9c warning은 제거 후 추가한다.
#================================================

from __future__ import annotations

from typing import Any

from hwpx_analysis.pipeline_models import (
    BlocksDocument,
    TableInternalBlocks,
    ValidationReport,
)

_SOURCE_STAGE = "stage9c"

_ALLOWED_INTERNAL_BLOCK_TYPES = {
    "table_row_group",
    "table_cell_group",
    "table_cell_text",
    "nested_table_ref",
    "table_object_ref",
    # 셀 내부 개체(그림 등)의 hp:caption. 셀 본문 텍스트와 분리해 보존한다.
    "table_caption",
}

_SEVERITY_BY_CODE = {
    # error
    "duplicate_internal_block_id": "error",
    "missing_internal_block_id": "error",
    "invalid_internal_block_type": "error",
    "missing_parent_ref": "error",
    "invalid_parent_ref": "error",
    "missing_source_table_ref": "error",
    "missing_root_table_ref": "error",
    "invalid_nested_ref_parent_type": "error",
    "invalid_cell_parent_type": "error",
    "invalid_text_parent_type": "error",
    "invalid_object_parent_type": "error",
    "cell_group_count_mismatch": "error",
    "nested_ref_count_mismatch": "error",
    "object_ref_count_mismatch": "error",
    "record_status_null": "error",
    "record_status_mismatch": "error",
    # warning
    "invalid_internal_block_order": "warning",
    "missing_source_block_ref": "warning",
    "invalid_local_depth": "warning",
    "invalid_absolute_depth": "warning",
    "invalid_depth_parent_order": "warning",
    "missing_cell_address": "warning",
    "invalid_cell_span": "warning",
    "nested_table_presence_mismatch": "warning",
    # info
    "possible_nested_text_contamination": "info",
}

# validation_passed 판정에 쓰는 count 키 (기준 15)
_VALIDATION_PASSED_KEYS = (
    "duplicate_internal_block_id_count",
    "missing_parent_ref_count",
    "invalid_parent_ref_count",
    "missing_source_table_ref_count",
    "missing_root_table_ref_count",
    "cell_group_count_mismatch_count",
    "nested_ref_count_mismatch_count",
    "object_ref_count_mismatch_count",
    "nested_table_presence_mismatch_count",
    "missing_cell_address_count",
    "invalid_cell_span_count",
    "possible_nested_text_contamination_count",
    "record_status_null_count",
    "record_status_mismatch_count",
    "invalid_internal_block_order_count",
)


#------------------------------------------------
# recursive table index 구성
#------------------------------------------------

def _build_recursive_table_index(tables: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """top-level table 배열에서 children[]을 재귀 순회해 모든 table을 색인한다."""
    index: dict[str, dict[str, Any]] = {}

    def _walk(table: dict[str, Any]) -> None:
        table_id = table.get("table_id")
        if table_id is not None:
            index[table_id] = table
        for child in table.get("children") or []:
            _walk(child)

    for table in tables:
        _walk(table)
    return index


def _table_cells(table: dict[str, Any]) -> list[dict[str, Any]]:
    return (table.get("preprocess") or {}).get("cells") or []


def _cell_nested_table_ids(cell: dict[str, Any]) -> list[str]:
    return (cell.get("objects") or {}).get("nested_table_ids") or []


def _cell_object_count(cell: dict[str, Any]) -> int:
    """셀의 이미지 + 그리기 개체 수 (table_object_ref 패리티 기준)."""
    objects = cell.get("objects") or {}
    images = objects.get("images")
    image_count = len(images) if images is not None else len(objects.get("image_ids") or [])
    return image_count + len(objects.get("draw_objects") or [])


#------------------------------------------------
# warning 생성 헬퍼
#------------------------------------------------

def _make_warning(
    warning_code: str,
    message: str,
    block_id: str | None,
    evidence: dict[str, Any],
    text_preview: str | None = None,
) -> dict[str, Any]:
    return {
        "warning_code": warning_code,
        "severity": _SEVERITY_BY_CODE[warning_code],
        "block_id": block_id,
        "source_stage": _SOURCE_STAGE,
        "message": message,
        "evidence": evidence,
        "text_preview": text_preview,
    }


#------------------------------------------------
# 개별 검증
#------------------------------------------------

def _validate_id_integrity(
    internal_blocks: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    seen: set[str] = set()
    duplicated: set[str] = set()
    for b in internal_blocks:
        internal_id = b.get("internal_block_id")
        if not internal_id:
            warnings.append(_make_warning(
                "missing_internal_block_id",
                "internal_block_id is missing.",
                b.get("source_block_id"),
                {"source_table_id": b.get("source_table_id")},
            ))
            continue
        if internal_id in seen and internal_id not in duplicated:
            duplicated.add(internal_id)
            warnings.append(_make_warning(
                "duplicate_internal_block_id",
                "internal_block_id is duplicated.",
                b.get("source_block_id"),
                {"internal_block_id": internal_id},
            ))
        seen.add(internal_id)

    for b in internal_blocks:
        block_type = b.get("internal_block_type")
        if block_type not in _ALLOWED_INTERNAL_BLOCK_TYPES:
            warnings.append(_make_warning(
                "invalid_internal_block_type",
                f"internal_block_type '{block_type}' is not allowed.",
                b.get("source_block_id"),
                {
                    "internal_block_id": b.get("internal_block_id"),
                    "internal_block_type": block_type,
                },
            ))


def _validate_parent_refs(
    internal_blocks: list[dict[str, Any]],
    blocks_by_internal_id: dict[str, dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    # 기대 parent type:
    # - table_row_group: parent 없음(top-level) 또는 nested_table_ref(중첩 표)
    # - table_cell_group -> table_row_group
    # - table_cell_text  -> table_cell_group
    # - nested_table_ref -> table_cell_group
    parent_type_rules = {
        "table_cell_group": ("table_row_group", "invalid_cell_parent_type"),
        "table_cell_text": ("table_cell_group", "invalid_text_parent_type"),
        "nested_table_ref": ("table_cell_group", "invalid_nested_ref_parent_type"),
        "table_object_ref": ("table_cell_group", "invalid_object_parent_type"),
    }

    for b in internal_blocks:
        block_type = b.get("internal_block_type")
        parent_id = b.get("parent_internal_block_id")

        if parent_id is None:
            if block_type in parent_type_rules:
                warnings.append(_make_warning(
                    "missing_parent_ref",
                    f"{block_type} requires parent_internal_block_id.",
                    b.get("source_block_id"),
                    {"internal_block_id": b.get("internal_block_id")},
                ))
            continue

        parent = blocks_by_internal_id.get(parent_id)
        if parent is None:
            warnings.append(_make_warning(
                "invalid_parent_ref",
                "parent_internal_block_id does not exist.",
                b.get("source_block_id"),
                {
                    "internal_block_id": b.get("internal_block_id"),
                    "parent_internal_block_id": parent_id,
                },
            ))
            continue

        parent_type = parent.get("internal_block_type")
        if block_type in parent_type_rules:
            expected_type, code = parent_type_rules[block_type]
            if parent_type != expected_type:
                warnings.append(_make_warning(
                    code,
                    f"{block_type} parent must be {expected_type}, got {parent_type}.",
                    b.get("source_block_id"),
                    {
                        "internal_block_id": b.get("internal_block_id"),
                        "parent_internal_block_id": parent_id,
                        "parent_internal_block_type": parent_type,
                    },
                ))
        elif block_type == "table_row_group" and parent_type != "nested_table_ref":
            warnings.append(_make_warning(
                "invalid_parent_ref",
                "table_row_group parent must be null or nested_table_ref.",
                b.get("source_block_id"),
                {
                    "internal_block_id": b.get("internal_block_id"),
                    "parent_internal_block_id": parent_id,
                    "parent_internal_block_type": parent_type,
                },
            ))


def _validate_table_refs(
    internal_blocks: list[dict[str, Any]],
    table_index: dict[str, dict[str, Any]],
    table_block_ids: set[str],
    warnings: list[dict[str, Any]],
) -> None:
    for b in internal_blocks:
        source_table_id = b.get("source_table_id")
        if source_table_id not in table_index:
            warnings.append(_make_warning(
                "missing_source_table_ref",
                "source_table_id does not exist in recursive table index.",
                b.get("source_block_id"),
                {
                    "internal_block_id": b.get("internal_block_id"),
                    "source_table_id": source_table_id,
                },
            ))

        root_table_id = b.get("root_table_id")
        if root_table_id not in table_index:
            warnings.append(_make_warning(
                "missing_root_table_ref",
                "root_table_id does not exist in recursive table index.",
                b.get("source_block_id"),
                {
                    "internal_block_id": b.get("internal_block_id"),
                    "root_table_id": root_table_id,
                },
            ))

        # nested table의 source_block_id는 root top-level table block을 가리켜도 허용
        source_block_id = b.get("source_block_id")
        if source_block_id is None or source_block_id not in table_block_ids:
            warnings.append(_make_warning(
                "missing_source_block_ref",
                "source_block_id does not exist in blocks.json table blocks.",
                source_block_id,
                {
                    "internal_block_id": b.get("internal_block_id"),
                    "source_block_id": source_block_id,
                },
            ))


def _validate_depth(
    internal_blocks: list[dict[str, Any]],
    blocks_by_internal_id: dict[str, dict[str, Any]],
    depth_by_block_id: dict[str, int],
    warnings: list[dict[str, Any]],
) -> None:
    for b in internal_blocks:
        internal_id = b.get("internal_block_id")
        local_depth = b.get("local_depth")

        if local_depth is None or local_depth < 1:
            warnings.append(_make_warning(
                "invalid_local_depth",
                "local_depth must be >= 1.",
                b.get("source_block_id"),
                {"internal_block_id": internal_id, "local_depth": local_depth},
            ))
            continue

        # base_depth는 source_block_id에 해당하는 table block의 depth (기준 6)
        base_depth = depth_by_block_id.get(b.get("source_block_id"))
        if base_depth is not None:
            expected_absolute = base_depth + local_depth
            if b.get("absolute_depth") != expected_absolute:
                warnings.append(_make_warning(
                    "invalid_absolute_depth",
                    "absolute_depth != source_block.depth + local_depth.",
                    b.get("source_block_id"),
                    {
                        "internal_block_id": internal_id,
                        "base_depth": base_depth,
                        "local_depth": local_depth,
                        "absolute_depth": b.get("absolute_depth"),
                        "expected_absolute_depth": expected_absolute,
                    },
                ))

        parent_id = b.get("parent_internal_block_id")
        parent = blocks_by_internal_id.get(parent_id) if parent_id else None
        if parent is not None:
            parent_local_depth = parent.get("local_depth")
            if parent_local_depth is not None and local_depth <= parent_local_depth:
                warnings.append(_make_warning(
                    "invalid_depth_parent_order",
                    "child local_depth must be greater than parent local_depth.",
                    b.get("source_block_id"),
                    {
                        "internal_block_id": internal_id,
                        "local_depth": local_depth,
                        "parent_internal_block_id": parent_id,
                        "parent_local_depth": parent_local_depth,
                    },
                ))


def _validate_source_cells(
    table_index: dict[str, dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    """주소/span 검사는 원본 preprocess.cells[] 기준으로 수행한다 (기준 5)."""
    for table_id, table in table_index.items():
        for cell in _table_cells(table):
            position = cell.get("position") or {}
            row_addr = position.get("row_addr")
            col_addr = position.get("col_addr")
            if row_addr is None or col_addr is None:
                warnings.append(_make_warning(
                    "missing_cell_address",
                    "cell has no row_addr or col_addr.",
                    None,
                    {
                        "table_id": table_id,
                        "cell_id": cell.get("cell_id"),
                        "row_addr": row_addr,
                        "col_addr": col_addr,
                    },
                ))

            row_span = position.get("row_span")
            col_span = position.get("col_span")
            if (row_span is not None and row_span < 1) or (col_span is not None and col_span < 1):
                warnings.append(_make_warning(
                    "invalid_cell_span",
                    "row_span/col_span must be >= 1.",
                    None,
                    {
                        "table_id": table_id,
                        "cell_id": cell.get("cell_id"),
                        "row_span": row_span,
                        "col_span": col_span,
                    },
                ))


def _validate_cell_group_counts(
    internal_blocks: list[dict[str, Any]],
    table_index: dict[str, dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    """table별 cell_group 수 == 해당 table.preprocess.cells[] 길이 (기준 2)."""
    cell_group_count_by_table: dict[str, int] = {}
    for b in internal_blocks:
        if b.get("internal_block_type") == "table_cell_group":
            table_id = b.get("source_table_id")
            cell_group_count_by_table[table_id] = cell_group_count_by_table.get(table_id, 0) + 1

    for table_id, table in table_index.items():
        expected = len(_table_cells(table))
        actual = cell_group_count_by_table.get(table_id, 0)
        if expected != actual:
            warnings.append(_make_warning(
                "cell_group_count_mismatch",
                "Cell group count does not match preprocess.cells count for table.",
                None,
                {
                    "table_id": table_id,
                    "expected_cell_count": expected,
                    "actual_cell_group_count": actual,
                },
            ))


def _validate_nested_ref_counts(
    internal_blocks: list[dict[str, Any]],
    table_index: dict[str, dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    """table별 nested_table_ref 수 == 해당 table cells의 nested_table_ids 총합 (기준 3).
    nested_table_ref의 소속 table은 parent_table_id(참조를 담은 셀의 table)다."""
    nested_ref_count_by_table: dict[str, int] = {}
    for b in internal_blocks:
        if b.get("internal_block_type") == "nested_table_ref":
            table_id = b.get("parent_table_id")
            nested_ref_count_by_table[table_id] = nested_ref_count_by_table.get(table_id, 0) + 1

    for table_id, table in table_index.items():
        expected = sum(len(_cell_nested_table_ids(cell)) for cell in _table_cells(table))
        actual = nested_ref_count_by_table.get(table_id, 0)
        if expected != actual:
            warnings.append(_make_warning(
                "nested_ref_count_mismatch",
                "Nested table ref count does not match cell.objects.nested_table_ids count for table.",
                None,
                {
                    "table_id": table_id,
                    "expected_nested_ref_count": expected,
                    "actual_nested_ref_count": actual,
                },
            ))


def _validate_object_ref_counts(
    internal_blocks: list[dict[str, Any]],
    table_index: dict[str, dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    """table별 table_object_ref 수 == 해당 table cells의 이미지+그리기 개체 총합.
    개체 유실(표 내부 이미지/도형이 블록으로 안 나오는 회귀)을 구조적으로 차단한다."""
    object_ref_count_by_table: dict[str, int] = {}
    for b in internal_blocks:
        if b.get("internal_block_type") == "table_object_ref":
            table_id = b.get("source_table_id")
            object_ref_count_by_table[table_id] = object_ref_count_by_table.get(table_id, 0) + 1

    for table_id, table in table_index.items():
        expected = sum(_cell_object_count(cell) for cell in _table_cells(table))
        actual = object_ref_count_by_table.get(table_id, 0)
        if expected != actual:
            warnings.append(_make_warning(
                "object_ref_count_mismatch",
                "Object ref count does not match cell images + draw_objects count for table.",
                None,
                {
                    "table_id": table_id,
                    "expected_object_count": expected,
                    "actual_object_ref_count": actual,
                },
            ))


def _validate_nested_presence(
    internal_blocks: list[dict[str, Any]],
    table_blocks: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> tuple[int, int]:
    """nested_table_ref가 있는 root_table_id 수
    == table_hierarchy_ref.quality_warnings에 nested_table_present가 있는 top-level table block 수 (기준 4)."""
    roots_with_nested_refs = {
        b.get("root_table_id")
        for b in internal_blocks
        if b.get("internal_block_type") == "nested_table_ref"
    }

    blocks_with_presence_warning = {
        (b.get("table_hierarchy_ref") or {}).get("table_id")
        for b in table_blocks
        if "nested_table_present" in ((b.get("table_hierarchy_ref") or {}).get("quality_warnings") or [])
    }

    if roots_with_nested_refs != blocks_with_presence_warning:
        only_refs = sorted(x for x in roots_with_nested_refs - blocks_with_presence_warning if x)
        only_warns = sorted(x for x in blocks_with_presence_warning - roots_with_nested_refs if x)
        warnings.append(_make_warning(
            "nested_table_presence_mismatch",
            "Tables with nested_table_ref do not match tables flagged nested_table_present.",
            None,
            {
                "tables_with_nested_refs_count": len(roots_with_nested_refs),
                "tables_with_presence_warning_count": len(blocks_with_presence_warning),
                "only_in_nested_refs": only_refs,
                "only_in_presence_warnings": only_warns,
            },
        ))

    return len(roots_with_nested_refs), len(blocks_with_presence_warning)


def _validate_text_contamination(
    internal_blocks: list[dict[str, Any]],
    blocks_by_internal_id: dict[str, dict[str, Any]],
    table_index: dict[str, dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    """nested_table_ref를 담은 부모 cell의 text에
    nested table cell text가 통째로 섞였는지 구조적 방어 검사 (기준 11)."""
    for b in internal_blocks:
        if b.get("internal_block_type") != "nested_table_ref":
            continue

        parent_cell_id = b.get("parent_internal_block_id")
        text_block = blocks_by_internal_id.get(f"{parent_cell_id}::text")
        if text_block is None:
            continue
        parent_text = text_block.get("text_content") or ""
        if not parent_text:
            continue

        nested_table = table_index.get(b.get("source_table_id"))
        if nested_table is None:
            continue

        # 단어 단위 우연 일치는 오탐이므로, nested table의 비어있지 않은
        # cell text 대다수(80% 이상)가 통째로 포함될 때만 contamination으로 본다.
        nested_texts = {
            nested_text
            for cell in _table_cells(nested_table)
            if (nested_text := ((cell.get("text") or {}).get("text") or "").strip())
        }
        if not nested_texts:
            continue
        contaminated_texts = [t for t in nested_texts if t in parent_text]
        if len(contaminated_texts) / len(nested_texts) >= 0.8:
            warnings.append(_make_warning(
                "possible_nested_text_contamination",
                "Parent cell text may contain nested table cell text.",
                b.get("source_block_id"),
                {
                    "internal_block_id": b.get("internal_block_id"),
                    "parent_cell_id": parent_cell_id,
                    "nested_table_id": b.get("source_table_id"),
                    "matched_text_count": len(contaminated_texts),
                },
                text_preview=parent_text[:80],
            ))


def _validate_internal_block_order(
    internal_blocks: list[dict[str, Any]],
    blocks_by_internal_id: dict[str, dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    """local_order_index가 row → cell → text/nested 순서를 지키는지 검사한다 (v3.1)."""
    for b in internal_blocks:
        parent_id = b.get("parent_internal_block_id")
        parent = blocks_by_internal_id.get(parent_id) if parent_id else None
        if parent is None:
            continue
        # 같은 table의 order 공간 안에서만 비교한다.
        # nested_table_ref 하위(nested table 내부)는 자기 order 공간을 새로 시작한다.
        if parent.get("source_table_id") != b.get("source_table_id"):
            continue
        if parent.get("internal_block_type") == "nested_table_ref":
            continue
        parent_order = parent.get("local_order_index")
        child_order = b.get("local_order_index")
        if parent_order is None or child_order is None:
            continue
        if parent_order >= child_order:
            warnings.append(_make_warning(
                "invalid_internal_block_order",
                "parent local_order_index must be less than child local_order_index.",
                b.get("source_block_id"),
                {
                    "internal_block_id": b.get("internal_block_id"),
                    "local_order_index": child_order,
                    "parent_internal_block_id": parent_id,
                    "parent_local_order_index": parent_order,
                },
            ))


def _validate_record_status(
    table_entries: list[dict[str, Any]],
    table_blocks: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    """tables summary의 record_status가 null이 아니고 blocks ref와 일치하는지 검사한다 (v3.1)."""
    allowed = {"structured", "raw_only", "not_applicable"}
    ref_by_table_id = {
        (b.get("table_hierarchy_ref") or {}).get("table_id"):
            (b.get("table_hierarchy_ref") or {}).get("record_status")
        for b in table_blocks
    }
    for entry in table_entries:
        table_id = entry.get("table_id")
        status = entry.get("record_status")
        if status is None or status not in allowed:
            warnings.append(_make_warning(
                "record_status_null",
                "tables summary record_status must be one of structured/raw_only/not_applicable.",
                entry.get("source_block_id"),
                {"table_id": table_id, "record_status": status},
            ))
            continue
        ref_status = ref_by_table_id.get(table_id)
        if ref_status is not None and ref_status != status:
            warnings.append(_make_warning(
                "record_status_mismatch",
                "record_status differs between blocks.json ref and tables summary.",
                entry.get("source_block_id"),
                {
                    "table_id": table_id,
                    "blocks_ref_record_status": ref_status,
                    "tables_summary_record_status": status,
                },
            ))


#------------------------------------------------
# quality_report 통계 구성
#------------------------------------------------

def _count_code(warnings: list[dict[str, Any]], code: str) -> int:
    return sum(1 for w in warnings if w["warning_code"] == code)


def _build_validation_stats(
    internal_blocks: list[dict[str, Any]],
    table_index: dict[str, dict[str, Any]],
    table_blocks: list[dict[str, Any]],
    top_level_tables_with_nested_refs: int,
    new_warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    type_counts: dict[str, int] = {}
    for b in internal_blocks:
        t = b.get("internal_block_type")
        type_counts[t] = type_counts.get(t, 0) + 1

    stats = {
        "table_internal_block_count": len(internal_blocks),
        "row_group_count": type_counts.get("table_row_group", 0),
        "cell_group_count": type_counts.get("table_cell_group", 0),
        "text_block_count": type_counts.get("table_cell_text", 0),
        "nested_table_ref_count": type_counts.get("nested_table_ref", 0),
        "table_object_ref_count": type_counts.get("table_object_ref", 0),
        "table_caption_count": type_counts.get("table_caption", 0),
        "expected_recursive_cell_count": sum(
            len(_table_cells(t)) for t in table_index.values()
        ),
        "expected_recursive_nested_ref_count": sum(
            len(_cell_nested_table_ids(cell))
            for t in table_index.values()
            for cell in _table_cells(t)
        ),
        "expected_recursive_object_count": sum(
            _cell_object_count(cell)
            for t in table_index.values()
            for cell in _table_cells(t)
        ),
        "top_level_tables_with_internal_ref": sum(
            1 for b in table_blocks if b.get("table_internal_ref")
        ),
        "top_level_tables_with_nested_refs": top_level_tables_with_nested_refs,
        "duplicate_internal_block_id_count": _count_code(new_warnings, "duplicate_internal_block_id"),
        "missing_parent_ref_count": _count_code(new_warnings, "missing_parent_ref"),
        "invalid_parent_ref_count": _count_code(new_warnings, "invalid_parent_ref"),
        "missing_source_table_ref_count": _count_code(new_warnings, "missing_source_table_ref"),
        "missing_root_table_ref_count": _count_code(new_warnings, "missing_root_table_ref"),
        "missing_source_block_ref_count": _count_code(new_warnings, "missing_source_block_ref"),
        "cell_group_count_mismatch_count": _count_code(new_warnings, "cell_group_count_mismatch"),
        "nested_ref_count_mismatch_count": _count_code(new_warnings, "nested_ref_count_mismatch"),
        "object_ref_count_mismatch_count": _count_code(new_warnings, "object_ref_count_mismatch"),
        "nested_table_presence_mismatch_count": _count_code(new_warnings, "nested_table_presence_mismatch"),
        "missing_cell_address_count": _count_code(new_warnings, "missing_cell_address"),
        "invalid_cell_span_count": _count_code(new_warnings, "invalid_cell_span"),
        "possible_nested_text_contamination_count": _count_code(new_warnings, "possible_nested_text_contamination"),
        "record_status_null_count": _count_code(new_warnings, "record_status_null"),
        "record_status_mismatch_count": _count_code(new_warnings, "record_status_mismatch"),
        "invalid_internal_block_order_count": _count_code(new_warnings, "invalid_internal_block_order"),
        "max_local_depth": max((b.get("local_depth") or 0 for b in internal_blocks), default=0),
        "max_absolute_depth": max((b.get("absolute_depth") or 0 for b in internal_blocks), default=0),
    }
    stats["validation_passed"] = all(stats[key] == 0 for key in _VALIDATION_PASSED_KEYS)
    return stats


#------------------------------------------------
# 진입점
#------------------------------------------------

def validate_table_internal_blocks(
    blocks_doc: BlocksDocument,
    tables: list[dict[str, Any]],
    table_internal: TableInternalBlocks,
    report: ValidationReport,
) -> dict[str, Any]:
    """
    역할: TableInternalBlocks의 구조 무결성을 검증해
          ValidationReport.warnings에 stage9c warning을 append하고
          ValidationReport.quality_report에 table_internal_validation 키를 추가한다.
    입력 데이터: blocks_doc / tables / table_internal (읽기 전용),
                report (9-A/9-B가 생성한 ValidationReport, merge 대상).
    출력 데이터: {"warnings": [...], "table_internal_validation": {...}} 형태의 dict.
    """
    blocks = blocks_doc.blocks
    internal_blocks = table_internal.internal_blocks

    table_index = _build_recursive_table_index(tables)
    table_blocks = [b for b in blocks if b.get("block_type") == "table"]
    table_block_ids = {b["block_id"] for b in table_blocks}
    depth_by_block_id = {b["block_id"]: b.get("depth") for b in table_blocks}
    blocks_by_internal_id = {
        b["internal_block_id"]: b
        for b in internal_blocks
        if b.get("internal_block_id")
    }

    new_warnings: list[dict[str, Any]] = []

    _validate_id_integrity(internal_blocks, new_warnings)
    _validate_parent_refs(internal_blocks, blocks_by_internal_id, new_warnings)
    _validate_table_refs(internal_blocks, table_index, table_block_ids, new_warnings)
    _validate_depth(internal_blocks, blocks_by_internal_id, depth_by_block_id, new_warnings)
    _validate_source_cells(table_index, new_warnings)
    _validate_cell_group_counts(internal_blocks, table_index, new_warnings)
    _validate_nested_ref_counts(internal_blocks, table_index, new_warnings)
    _validate_object_ref_counts(internal_blocks, table_index, new_warnings)
    tables_with_nested_refs, _presence_warning_count = _validate_nested_presence(
        internal_blocks, table_blocks, new_warnings,
    )
    _validate_text_contamination(
        internal_blocks, blocks_by_internal_id, table_index, new_warnings,
    )
    _validate_internal_block_order(internal_blocks, blocks_by_internal_id, new_warnings)
    _validate_record_status(
        table_internal.tables, table_blocks, new_warnings,
    )

    stats = _build_validation_stats(
        internal_blocks, table_index, table_blocks,
        tables_with_nested_refs, new_warnings,
    )

    # warnings merge: 기존 stage9c warning은 제거 후 append (재실행 안전)
    report.warnings[:] = [
        w for w in report.warnings if w.get("source_stage") != _SOURCE_STAGE
    ] + new_warnings

    # quality_report merge: table_internal_validation 키 추가
    report.quality_report["table_internal_validation"] = stats

    print("=== Stage 9-C: Table Internal Validation 결과 ===")
    for key in (
        "table_internal_block_count", "row_group_count", "cell_group_count",
        "text_block_count", "nested_table_ref_count", "table_object_ref_count",
        "table_caption_count",
        "expected_recursive_cell_count", "expected_recursive_nested_ref_count",
        "expected_recursive_object_count",
        "top_level_tables_with_nested_refs",
        "duplicate_internal_block_id_count", "missing_parent_ref_count",
        "invalid_parent_ref_count", "cell_group_count_mismatch_count",
        "nested_ref_count_mismatch_count", "object_ref_count_mismatch_count",
        "validation_passed",
    ):
        print(f"{key}: {stats[key]}")
    print(f"stage9c warning count: {len(new_warnings)}")

    return {"warnings": new_warnings, "table_internal_validation": stats}
