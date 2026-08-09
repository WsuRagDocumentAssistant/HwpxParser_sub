#================================================
# table.py
#================================================

from dataclasses import dataclass, field
from typing import Optional, Any

from .elements.table_row import TableRow
from .elements.table_analysis import TableValidation, TableSemantic
#────────────────────────────────────────────────

@dataclass
class Table:
    """
    hp:tbl 하나를 의미한다.
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

    # 이 표가 머리말/꼬리말/각주/미주 안에 들어 있는 경우 그 종류.
    # HWPX는 머리말 내용을 표로 짜는 경우가 있는데, 표시하지 않으면
    # 본문 데이터 표와 구분할 수 없다. None이면 일반 표다.
    owner_control_type: Optional[str] = None

