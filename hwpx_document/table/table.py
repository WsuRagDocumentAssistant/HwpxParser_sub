#================================================
# table.py
#================================================

from dataclasses import dataclass, field
from typing import Optional, Any

from .table_data.table_data import TableRow, TableCell, TableValidation, TableSemantic
from .table_data.table_style import BorderFill

#────────────────────────────────────────────────

@dataclass
class Table:
    """
    hp:tbl 하나를 의미한다.

    border_fill_id_ref에는 hp:tbl@borderFillIDRef 원본 참조값을 저장하고,
    border_fill에는 header.xml의 실제 borderFill 정보를 연결해 저장한다.
    """

    # 내부 식별자
    table_id: str

    # section 위치
    section_index: Optional[int] = None

    # section 안에서 몇 번째 표인지
    table_index: Optional[int] = None

    # hp:tbl XML id
    xml_table_id: Optional[str] = None

    # hp:tbl 기본 속성
    row_count: int = 0
    col_count: int = 0

    cell_spacing: Optional[int] = None

    # hp:tbl@borderFillIDRef 원본 참조값
    border_fill_id_ref: Optional[str] = None

    # header.xml에서 해석된 실제 borderFill 정보
    border_fill: Optional[BorderFill] = None

    repeat_header: bool = False
    page_break: bool = False

    text_wrap: Optional[str] = None
    text_flow: Optional[str] = None

    # 위치 / 크기
    width: Optional[int] = None
    height: Optional[int] = None

    pos_x: Optional[int] = None
    pos_y: Optional[int] = None

    treat_as_char: Optional[bool] = None
    flow_with_text: Optional[bool] = None

    # 표 내부 여백
    in_margin_left: Optional[int] = None
    in_margin_right: Optional[int] = None
    in_margin_top: Optional[int] = None
    in_margin_bottom: Optional[int] = None

    # 표 외부 여백
    out_margin_left: Optional[int] = None
    out_margin_right: Optional[int] = None
    out_margin_top: Optional[int] = None
    out_margin_bottom: Optional[int] = None

    # 계층 구조
    rows: list[TableRow] = field(default_factory=list)

    # 분석 결과
    validation: Optional[TableValidation] = None
    semantic: Optional[TableSemantic] = None

    # 표 앞뒤 문단 기반 후보
    caption_candidate: Optional[str] = None
    note_candidate: Optional[str] = None
    source_candidate: Optional[str] = None

    # 원본 속성 보존
    raw_attrs: dict[str, Any] = field(default_factory=dict)

    # 중첩 표 추적 정보
    is_nested: bool = False
    parent_table_id: Optional[str] = None
    parent_cell_id: Optional[str] = None

    @property
    def cells(self) -> list[TableCell]:
        """
        역할: Table.rows에 들어 있는 모든 행의 셀을 하나의 리스트로 펼친다.
        입력 데이터: self.rows(TableRow 리스트와 각 row.cells).
        출력 데이터: 표 전체의 TableCell 객체를 행 순서대로 담은 리스트를 반환한다.
        """
        result: list[TableCell] = []

        for row in self.rows:
            result.extend(row.cells)

        return result
