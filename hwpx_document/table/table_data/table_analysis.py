#================================================
# document/table/table_analysis.py
#================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class TableValidation:
    """
    TableAnalyzer가 수행한 검증 결과를 담는 객체.

    별도 ValidationIssue, GridSlot 클래스를 만들지 않고
    issues, grid를 dict 구조로 보관한다.
    """

    # 어떤 Table에 대한 검증인지
    table_id: Optional[str] = None

    is_valid: bool = True

    # 선언값
    declared_row_count: int = 0
    declared_col_count: int = 0

    # 실제 구조값
    actual_tr_count: int = 0
    actual_cell_count: int = 0
    actual_max_row_count: int = 0
    actual_max_col_count: int = 0

    # grid 점유 결과
    # 예:
    # grid[row][col] = {
    #     "row_index": 0,
    #     "col_index": 0,
    #     "table_id": "section0_tbl0",
    #     "row_id": "section0_tbl0_row0",
    #     "cell_id": "section0_tbl0_r0_c0",
    #     "is_origin": True,
    #     "is_covered": False,
    #     "is_empty": False
    # }
    grid: list[list[dict[str, Any]]] = field(default_factory=list)

    # 오류/경고 목록
    # 예:
    # {
    #     "code": "ROW_COUNT_MISMATCH",
    #     "message": "rowCnt와 실제 hp:tr 개수가 다릅니다.",
    #     "severity": "ERROR",
    #     "table_id": "section0_tbl0",
    #     "row_id": "section0_tbl0_row0",
    #     "cell_id": "section0_tbl0_r0_c0",
    #     "row_index": 0,
    #     "col_index": 0,
    #     "details": {}
    # }
    issues: list[dict[str, Any]] = field(default_factory=list)

    # 구조 검증
    has_row_count_mismatch: bool = False
    has_col_count_mismatch: bool = False

    # 좌표 검증
    has_missing_cell_addr: bool = False
    has_invalid_cell_addr: bool = False
    has_out_of_range_cell: bool = False
    has_row_order_mismatch: bool = False

    # 병합 검증
    has_invalid_cell_span: bool = False
    has_duplicated_slot: bool = False
    has_empty_slot: bool = False

    # 스타일 참조 검증
    has_missing_border_fill_ref: bool = False
    has_missing_style_ref: bool = False
    has_missing_para_pr_ref: bool = False
    has_missing_char_pr_ref: bool = False

    # 크기/여백 검증
    has_size_mismatch: bool = False
    has_margin_difference: bool = False

    # 내용 검증
    has_empty_cell: bool = False
    has_nested_object: bool = False

    # 불규칙 표 여부
    is_irregular: bool = False


@dataclass
class TableSemantic:
    """
    표 의미 계층 분석 결과.
    """

    # 어떤 Table에 대한 의미 분석인지
    table_id: Optional[str] = None

    table_title: Optional[str] = None
    table_note: Optional[str] = None
    table_source: Optional[str] = None

    # 헤더 후보
    header_cell_ids: list[str] = field(default_factory=list)
    column_header_cell_ids: list[str] = field(default_factory=list)
    row_header_cell_ids: list[str] = field(default_factory=list)
    group_header_cell_ids: list[str] = field(default_factory=list)

    # 데이터 셀 후보
    data_cell_ids: list[str] = field(default_factory=list)

    # 특수 셀
    empty_cell_ids: list[str] = field(default_factory=list)
    image_cell_ids: list[str] = field(default_factory=list)
    object_cell_ids: list[str] = field(default_factory=list)

    # 의미 분석 근거
    reasons: list[str] = field(default_factory=list)

    confidence: float = 0.0