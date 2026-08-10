#================================================
# document/table/utils.py
#================================================

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from hwpx_document.table.table import Table
    from hwpx_document.table.elements.table_cell import TableCell

#────────────────────────────────────────────────


def get_table_cells(table: Table) -> list[TableCell]:
    """table.rows에 있는 모든 셀을 하나의 리스트로 반환한다."""
    result: list[TableCell] = []
    for row in table.rows:
        result.extend(row.cells)
    return result


def get_cell_end_row(cell: TableCell) -> Optional[int]:
    """셀이 차지하는 마지막 행 인덱스를 반환한다. row_addr가 없으면 None."""
    if cell.row_addr is None:
        return None
    return cell.row_addr + cell.row_span - 1


def get_cell_end_col(cell: TableCell) -> Optional[int]:
    """셀이 차지하는 마지막 열 인덱스를 반환한다. col_addr가 없으면 None."""
    if cell.col_addr is None:
        return None
    return cell.col_addr + cell.col_span - 1
