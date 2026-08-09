#================================================
# flatten_table_internal_blocks.py
# Stage 7.5-B: Table Internal Flattening
#
# tables_hierarchical.json의 표 내부 cell/nested table 정보를
# block-like 구조(table_internal_blocks.json)로 평탄화한다.
#
# blocks.json.blocks 배열에는 내부 block을 직접 삽입하지 않는다.
# top-level table block에는 table_internal_ref 요약만 추가한다.
#
# 핵심 원칙:
# - table_cell_group의 유일한 소스는 table.preprocess.cells[]다.
#   grid.slots(origin/covered)를 순회하지 않는다 — 병합 셀 중복 생성 방지.
# - table_row_group은 원본 row 엔티티가 없으므로 preprocess.cells[]를
#   row_addr 기준으로 그룹핑해 합성 생성한다.
# - nested_table_ref의 1순위 소스는 cell.objects.nested_table_ids다.
#   table 단위 preprocess.nesting.child_table_ids는 검증용으로만 쓴다.
# - depth/reading_order_index/anchor_resolution은 절대 변경하지 않는다.
#================================================

from __future__ import annotations

from typing import Any

from hwpx_analysis.pipeline_models import BlocksDocument, TableInternalBlocks


_DEPTH_ORIGIN = "table_local_offset"

_ALLOWED_RECORD_STATUSES = {"structured", "raw_only", "not_applicable"}


def normalize_record_status(table_type: str | None, record_status: str | None) -> str:
    """record_status를 항상 허용값 3개 중 하나의 문자열로 정규화한다.
    null/빈값/알 수 없는 값은 table_type과 무관하게 not_applicable로 통일한다."""
    if record_status in _ALLOWED_RECORD_STATUSES:
        return record_status
    return "not_applicable"


#------------------------------------------------
# internal block 생성 (표 1개 재귀 처리)
#------------------------------------------------

def _flatten_one_table(
    table: dict[str, Any],
    root_table_id: str,
    source_block_id: str | None,
    base_depth: int,
    table_base_local_depth: int,
    parent_internal_block_id: str | None,
    internal_blocks: list[dict[str, Any]],
) -> None:
    """
    하나의 table hierarchy entry(top-level 또는 nested)를 internal block으로 평탄화한다.
    nested table을 만나면 재귀 호출한다.
    """
    source_table_id = table.get("table_id")
    preprocess = table.get("preprocess") or {}
    identity = preprocess.get("identity") or {}
    cells = preprocess.get("cells") or []

    section_index = identity.get("section_index")
    table_index = identity.get("table_index")

    row_local_depth = table_base_local_depth + 1
    cell_local_depth = table_base_local_depth + 2
    text_local_depth = table_base_local_depth + 3

    # row_addr 기준으로 cell을 그룹핑해 table_row_group을 합성 생성한다 (원칙 3)
    cells_by_row: dict[int, list[dict[str, Any]]] = {}
    for cell in cells:
        row_addr = (cell.get("position") or {}).get("row_addr")
        cells_by_row.setdefault(row_addr, []).append(cell)

    # local_order_index는 flat preview에서 읽기 자연스러운
    # row → (row 내) cell → text → nested_ref(재귀) 순으로 매긴다.
    # depth 공식과 internal_block_id는 바꾸지 않는다.
    order = 0

    for row_addr in sorted(
        cells_by_row.keys(), key=lambda v: (v is None, v)
    ):
        row_group_id = f"{source_table_id}::row{row_addr}"

        internal_blocks.append({
            "internal_block_id": row_group_id,
            "internal_block_type": "table_row_group",
            "source_table_id": source_table_id,
            "root_table_id": root_table_id,
            "source_block_id": source_block_id,
            "parent_internal_block_id": parent_internal_block_id,
            "parent_table_id": table.get("parent_table_id"),
            "parent_cell_id": table.get("parent_cell_id"),
            "section_index": section_index,
            "table_index": table_index,
            "local_order_index": order,
            "local_depth": row_local_depth,
            "absolute_depth": base_depth + row_local_depth,
            "depth_origin": _DEPTH_ORIGIN,
            "text_content": None,
            "evidence": [
                "source=synthesized_from_preprocess_cells",
                f"row_addr={row_addr}",
            ],
        })
        order += 1

        # 같은 row의 cell을 col_addr 순으로 이어서 생성 (원칙 1, 4, 5)
        row_cells = sorted(
            cells_by_row[row_addr],
            key=lambda c: (
                (c.get("position") or {}).get("col_addr") is None,
                (c.get("position") or {}).get("col_addr"),
            ),
        )
        for cell in row_cells:
            position = cell.get("position") or {}
            col_addr = position.get("col_addr")

            cell_id = cell.get("cell_id")
            if not cell_id:
                cell_id = f"{source_table_id}::r{row_addr}_c{col_addr}"

            internal_blocks.append({
                "internal_block_id": cell_id,
                "internal_block_type": "table_cell_group",
                "source_table_id": source_table_id,
                "root_table_id": root_table_id,
                "source_block_id": source_block_id,
                "parent_internal_block_id": row_group_id,
                "parent_table_id": table.get("parent_table_id"),
                "parent_cell_id": table.get("parent_cell_id"),
                "section_index": section_index,
                "table_index": table_index,
                "local_order_index": order,
                "local_depth": cell_local_depth,
                "absolute_depth": base_depth + cell_local_depth,
                "depth_origin": _DEPTH_ORIGIN,
                "text_content": None,
                "evidence": [
                    "source=preprocess.cells",
                    f"row_addr={row_addr},col_addr={col_addr}",
                    f"row_span={position.get('row_span')},col_span={position.get('col_span')}",
                ],
            })
            order += 1

            # table_cell_text: 직접 텍스트가 있을 때만 생성 (원칙 5, 기준 7)
            text_info = cell.get("text") or {}
            direct_text = text_info.get("text")
            if direct_text:
                internal_blocks.append({
                    "internal_block_id": f"{cell_id}::text",
                    "internal_block_type": "table_cell_text",
                    "source_table_id": source_table_id,
                    "root_table_id": root_table_id,
                    "source_block_id": source_block_id,
                    "parent_internal_block_id": cell_id,
                    "parent_table_id": table.get("parent_table_id"),
                    "parent_cell_id": table.get("parent_cell_id"),
                    "section_index": section_index,
                    "table_index": table_index,
                    "local_order_index": order,
                    "local_depth": text_local_depth,
                    "absolute_depth": base_depth + text_local_depth,
                    "depth_origin": _DEPTH_ORIGIN,
                    "text_content": direct_text,
                    "normalized_text": " ".join(direct_text.split()),
                    "paragraph_texts": text_info.get("paragraph_texts"),
                    # 자동 렌더링 마커(불릿/번호). paragraph_texts와 인덱스가 대응한다.
                    "paragraph_auto_labels": text_info.get("paragraph_auto_labels"),
                    "evidence": ["source=cell.text.text"],
                })
                order += 1

            # table_object_ref: 셀 내부 이미지/그리기 개체의 존재를 내부 블록으로 방출.
            # 텍스트 원본은 table_cell_text이므로 text_content는 두지 않고,
            # 개체 텍스트는 참고용 object_text 필드에만 기록한다 (중복 집계 방지).
            cell_objects = cell.get("objects") or {}
            object_ref_local_depth = cell_local_depth + 1

            image_entries = cell_objects.get("images")
            if image_entries is None:
                # 구버전 preprocess 호환: image_ids만 있는 경우
                image_entries = [
                    {"image_id": image_id, "binary_item_id_ref": None}
                    for image_id in (cell_objects.get("image_ids") or [])
                ]
            for image in image_entries:
                object_id = image.get("image_id")
                if not object_id:
                    continue
                internal_blocks.append({
                    "internal_block_id": f"{cell_id}::object::{object_id}",
                    "internal_block_type": "table_object_ref",
                    "object_type": "image",
                    "object_text": None,
                    "binary_item_id_ref": image.get("binary_item_id_ref"),
                    "source_table_id": source_table_id,
                    "root_table_id": root_table_id,
                    "source_block_id": source_block_id,
                    "parent_internal_block_id": cell_id,
                    "parent_table_id": table.get("parent_table_id"),
                    "parent_cell_id": cell_id,
                    "section_index": section_index,
                    "table_index": table_index,
                    "local_order_index": order,
                    "local_depth": object_ref_local_depth,
                    "absolute_depth": base_depth + object_ref_local_depth,
                    "depth_origin": _DEPTH_ORIGIN,
                    "text_content": None,
                    "evidence": [
                        "source=cell.objects.images",
                        f"object_id={object_id}",
                    ],
                })
                order += 1

            for draw_object in cell_objects.get("draw_objects") or []:
                object_id = draw_object.get("object_id")
                if not object_id:
                    continue
                internal_blocks.append({
                    "internal_block_id": f"{cell_id}::object::{object_id}",
                    "internal_block_type": "table_object_ref",
                    "object_type": draw_object.get("object_type"),
                    "object_text": draw_object.get("draw_text"),
                    "binary_item_id_ref": None,
                    "source_table_id": source_table_id,
                    "root_table_id": root_table_id,
                    "source_block_id": source_block_id,
                    "parent_internal_block_id": cell_id,
                    "parent_table_id": table.get("parent_table_id"),
                    "parent_cell_id": cell_id,
                    "section_index": section_index,
                    "table_index": table_index,
                    "local_order_index": order,
                    "local_depth": object_ref_local_depth,
                    "absolute_depth": base_depth + object_ref_local_depth,
                    "depth_origin": _DEPTH_ORIGIN,
                    "text_content": None,
                    "evidence": [
                        "source=cell.objects.draw_objects",
                        f"object_id={object_id}",
                        f"child_pic_count={draw_object.get('child_pic_count')}",
                    ],
                })
                order += 1

            # nested_table_ref: cell.objects.nested_table_ids가 1순위 소스 (원칙 4, 기준 8)
            nested_table_ids = (cell.get("objects") or {}).get("nested_table_ids") or []
            nested_ref_local_depth = cell_local_depth + 1

            for nested_table_id in nested_table_ids:
                nested_ref_id = f"{cell_id}::nested_ref::{nested_table_id}"
                internal_blocks.append({
                    "internal_block_id": nested_ref_id,
                    "internal_block_type": "nested_table_ref",
                    "source_table_id": nested_table_id,
                    "root_table_id": root_table_id,
                    "source_block_id": source_block_id,
                    "parent_internal_block_id": cell_id,
                    "parent_table_id": source_table_id,
                    "parent_cell_id": cell_id,
                    "section_index": section_index,
                    "table_index": table_index,
                    "local_order_index": order,
                    "local_depth": nested_ref_local_depth,
                    "absolute_depth": base_depth + nested_ref_local_depth,
                    "depth_origin": _DEPTH_ORIGIN,
                    "text_content": None,
                    "evidence": [
                        "source=cell.objects.nested_table_ids",
                        f"nested_table_id={nested_table_id}",
                    ],
                })
                order += 1

                # nested table 자체도 별도 table entry로 재귀 평탄화 (기준 8)
                nested_table = _find_child_table(table, nested_table_id)
                if nested_table is not None:
                    _flatten_one_table(
                        nested_table,
                        root_table_id=root_table_id,
                        source_block_id=source_block_id,
                        base_depth=base_depth,
                        table_base_local_depth=nested_ref_local_depth,
                        parent_internal_block_id=nested_ref_id,
                        internal_blocks=internal_blocks,
                    )


def _find_child_table(table: dict[str, Any], child_table_id: str) -> dict[str, Any] | None:
    for child in table.get("children") or []:
        if child.get("table_id") == child_table_id:
            return child
    return None


#------------------------------------------------
# top-level table 순회
#------------------------------------------------

def _flatten_top_level_table(
    table: dict[str, Any],
    table_block: dict[str, Any] | None,
    internal_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """top-level table 1개를 평탄화하고 table_internal_ref 요약을 반환한다."""
    table_id = table.get("table_id")
    source_block_id = table_block.get("block_id") if table_block else None
    base_depth = table_block.get("depth") if table_block else 0

    start_index = len(internal_blocks)

    _flatten_one_table(
        table,
        root_table_id=table_id,
        source_block_id=source_block_id,
        base_depth=base_depth or 0,
        table_base_local_depth=0,
        parent_internal_block_id=None,
        internal_blocks=internal_blocks,
    )

    generated = internal_blocks[start_index:]
    row_group_count = sum(1 for b in generated if b["internal_block_type"] == "table_row_group")
    cell_group_count = sum(1 for b in generated if b["internal_block_type"] == "table_cell_group")
    text_block_count = sum(1 for b in generated if b["internal_block_type"] == "table_cell_text")
    nested_ref_count = sum(1 for b in generated if b["internal_block_type"] == "nested_table_ref")
    object_ref_count = sum(1 for b in generated if b["internal_block_type"] == "table_object_ref")
    max_local_depth = max((b["local_depth"] for b in generated), default=0)
    max_absolute_depth = max((b["absolute_depth"] for b in generated), default=0)

    return {
        "status": "generated",
        "output_file": "table_internal_blocks.json",
        "internal_block_count": len(generated),
        "row_group_count": row_group_count,
        "cell_group_count": cell_group_count,
        "text_block_count": text_block_count,
        "nested_table_ref_count": nested_ref_count,
        "table_object_ref_count": object_ref_count,
        "max_local_depth": max_local_depth,
        "max_absolute_depth": max_absolute_depth,
    }


#------------------------------------------------
# 진입점
#------------------------------------------------

def flatten_table_internal_blocks(
    blocks_doc: BlocksDocument,
    tables: list[dict[str, Any]],
) -> TableInternalBlocks:
    """
    역할: hierarchy 표 리스트의 표 내부 구조를 TableInternalBlocks로 평탄화하고,
          BlocksDocument의 top-level table block에 table_internal_ref 요약만 추가한다.
    입력 데이터: blocks_doc(Stage 8-B까지 반영된 BlocksDocument — base_depth로 최종 depth 사용),
                tables(hierarchy가 반영된 표 리스트, 읽기 전용).
    출력 데이터: TableInternalBlocks(document/tables/internal_blocks).
    """
    blocks = blocks_doc.blocks
    block_count_before = len(blocks)
    depth_snapshot_before = {b["block_id"]: b.get("depth") for b in blocks}
    reading_order_snapshot_before = {
        b["block_id"]: b.get("reading_order_index") for b in blocks
    }

    table_blocks_by_table_id = {
        (b.get("table_hierarchy_ref") or {}).get("table_id"): b
        for b in blocks
        if b.get("block_type") == "table"
    }

    internal_blocks: list[dict[str, Any]] = []
    generated_count = 0
    all_table_entries: list[dict[str, Any]] = []

    for table in tables:
        table_id = table.get("table_id")
        table_block = table_blocks_by_table_id.get(table_id)

        ref_summary = _flatten_top_level_table(table, table_block, internal_blocks)
        generated_count += 1

        preprocess = table.get("preprocess") or {}
        identity = preprocess.get("identity") or {}
        hierarchy = table.get("hierarchy") or {}

        all_table_entries.append({
            "table_id": table_id,
            "root_table_id": table_id,
            "source_block_id": table_block.get("block_id") if table_block else None,
            "section_index": identity.get("section_index"),
            "table_index": identity.get("table_index"),
            "table_type": hierarchy.get("table_type"),
            "record_status": normalize_record_status(
                hierarchy.get("table_type"), hierarchy.get("record_status"),
            ),
            "base_depth": table_block.get("depth") if table_block else None,
            "internal_block_count": ref_summary["internal_block_count"],
        })

        if table_block is not None:
            table_block["table_internal_ref"] = ref_summary

    top_level_tables_with_nested_refs = sum(
        1 for entry in all_table_entries
        if any(
            b["internal_block_type"] == "nested_table_ref"
            and b["root_table_id"] == entry["table_id"]
            for b in internal_blocks
        )
    )

    document = TableInternalBlocks(
        document={
            "source_type": "hwpx",
            "stage": "7.5-B",
            "top_level_table_count": len(tables),
            "internal_block_count": len(internal_blocks),
        },
        tables=all_table_entries,
        internal_blocks=internal_blocks,
    )

    # 검증 로그용 통계
    block_count_after = len(blocks)
    depth_changed_count = sum(
        1 for b in blocks if depth_snapshot_before.get(b["block_id"]) != b.get("depth")
    )
    reading_order_changed_count = sum(
        1 for b in blocks
        if reading_order_snapshot_before.get(b["block_id"]) != b.get("reading_order_index")
    )
    row_group_count = sum(1 for b in internal_blocks if b["internal_block_type"] == "table_row_group")
    cell_group_count = sum(1 for b in internal_blocks if b["internal_block_type"] == "table_cell_group")
    text_block_count = sum(1 for b in internal_blocks if b["internal_block_type"] == "table_cell_text")
    nested_ref_count = sum(1 for b in internal_blocks if b["internal_block_type"] == "nested_table_ref")
    object_ref_count = sum(1 for b in internal_blocks if b["internal_block_type"] == "table_object_ref")

    ids = [b["internal_block_id"] for b in internal_blocks]
    duplicate_count = len(ids) - len(set(ids))

    id_set = set(ids)
    missing_parent_count = sum(
        1 for b in internal_blocks
        if b.get("parent_internal_block_id") is not None
        and b["parent_internal_block_id"] not in id_set
    )

    print("=== Stage 7.5-B: Table Internal Flattening 결과 ===")
    print(f"blocks block_count before/after: {block_count_before} / {block_count_after}")
    print(f"depth_changed_count: {depth_changed_count}")
    print(f"reading_order_changed_count: {reading_order_changed_count}")
    print(f"top_level_table_count: {len(tables)}")
    print(f"table_internal_ref generated count: {generated_count}")
    print(f"internal_block_count: {len(internal_blocks)}")
    print(f"row_group_count: {row_group_count}")
    print(f"cell_group_count: {cell_group_count}")
    print(f"text_block_count: {text_block_count}")
    print(f"nested_table_ref_count: {nested_ref_count}")
    print(f"table_object_ref_count: {object_ref_count}")
    print(f"top_level_tables_with_nested_refs: {top_level_tables_with_nested_refs}")
    print(f"duplicate_internal_block_id_count: {duplicate_count}")
    print(f"missing_parent_ref_count: {missing_parent_count}")
    print(f"max_local_depth: {max((b['local_depth'] for b in internal_blocks), default=0)}")
    print(f"max_absolute_depth: {max((b['absolute_depth'] for b in internal_blocks), default=0)}")

    return document
