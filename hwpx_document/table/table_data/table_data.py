#================================================
# document/table/table_data.py
#================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any

from .table_cell import TableCell
from .table_analysis import TableValidation, TableSemantic
from hwpx_document.table.table_data.table_style import BorderFill


@dataclass
class TableRow:
    """
    hp:tr 하나를 의미한다.
    """

    # 내부 식별자
    row_id: str

    # 부모 Table 참조 id
    table_id: str

    # hp:tr 등장 순서 기준 index
    row_index: int

    # hp:tr XML 등장 순서
    xml_order_index: Optional[int] = None

    # row 안 cell들의 cellAddr@rowAddr 기준 대표 row
    # hp:tr 순서와 실제 rowAddr 비교 검증용
    declared_row_addr: Optional[int] = None

    # 행 내부 셀
    cells: list[TableCell] = field(default_factory=list)

    # 원본 속성 보존
    raw_attrs: dict[str, Any] = field(default_factory=dict)

