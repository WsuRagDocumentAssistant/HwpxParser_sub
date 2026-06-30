#================================================
# document/table/table_cell.py
#================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any
from hwpx_document.table.table_data.table_style import BorderFill


@dataclass
class ImageInfo:
    image_id: str
    parent_table_id: str
    parent_cell_id: str
    binary_item_id_ref: Optional[str] = None
    href: Optional[str] = None
    ref_id: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    raw_attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class TableRun:
    """
    hp:tc 내부 hp:run 단위.

    외부 CharacterStyle 객체를 직접 참조하지 않고
    char_pr_id_ref만 저장한다.
    """

    # 내부 식별자
    run_id: str

    # 부모 TableParagraph 참조 id
    paragraph_id: str

    # XML 안에서 몇 번째 run인지
    run_index: Optional[int] = None

    # hp:run@charPrIDRef
    char_pr_id_ref: Optional[str] = None

    # 텍스트
    text: str = ""

    # 내용 타입
    has_line_break: bool = False
    has_tab: bool = False
    has_fw_space: bool = False

    has_image: bool = False
    has_field: bool = False
    has_shape: bool = False

    raw_attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class TableParagraph:
    """
    hp:tc/hp:subList/hp:p 단위.

    외부 ParagraphStyle 객체를 직접 참조하지 않고
    style_id_ref, para_pr_id_ref만 저장한다.
    """

    # 내부 식별자
    paragraph_id: str

    # 부모 TableCell 참조 id
    cell_id: str

    # 셀 안에서 몇 번째 문단인지
    paragraph_index: Optional[int] = None

    # hp:p XML id
    xml_para_id: Optional[str] = None

    # hp:p@styleIDRef
    style_id_ref: Optional[str] = None

    # hp:p@paraPrIDRef
    para_pr_id_ref: Optional[str] = None

    # 문단 내부 run
    runs: list[TableRun] = field(default_factory=list)

    # 문단 전체 텍스트
    text: str = ""

    raw_attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class TableCell:
    """
    hp:tc 하나를 의미한다.

    외부 BorderFill 객체를 직접 참조하지 않고
    border_fill_id_ref만 저장한다.
    """

    # 내부 식별자
    cell_id: str

    # 부모 Table 참조 id
    table_id: str

    # 부모 TableRow 참조 id
    row_id: str

    # XML 안에서 몇 번째 cell인지
    cell_index: Optional[int] = None

    # hp:tc 속성
    name: Optional[str] = None
    header: bool = False
    has_margin: bool = False
    protect: bool = False
    editable: bool = True
    dirty: bool = False

    # hp:tc@borderFillIDRef
    border_fill_id_ref: Optional[str] = None

    # header.xml에서 해석된 실제 BorderFill 객체
    border_fill: Optional[BorderFill] = None

    # hp:cellAddr
    row_addr: Optional[int] = None
    col_addr: Optional[int] = None

    # hp:cellSpan
    row_span: int = 1
    col_span: int = 1

    # hp:cellSz
    width: Optional[int] = None
    height: Optional[int] = None

    # hp:cellMargin
    margin_left: Optional[int] = None
    margin_right: Optional[int] = None
    margin_top: Optional[int] = None
    margin_bottom: Optional[int] = None

    # hp:subList 원본 속성
    sublist_raw_attrs: dict[str, Any] = field(default_factory=dict)

    # hp:subList 주요 속성
    sublist_id: Optional[str] = None
    sublist_text_direction: Optional[str] = None
    sublist_line_wrap: Optional[str] = None
    sublist_vert_align: Optional[str] = None

    sublist_link_list_id_ref: Optional[str] = None
    sublist_link_list_next_id_ref: Optional[str] = None

    sublist_text_width: Optional[int] = None
    sublist_text_height: Optional[int] = None

    sublist_has_text_ref: bool = False
    sublist_has_num_ref: bool = False

    # 셀 내부 내용
    images: list[ImageInfo] = field(default_factory=list)
    paragraphs: list[TableParagraph] = field(default_factory=list)
    nested_tables: list[Any] = field(default_factory=list)
    text: str = ""

    # 내용 특징
    is_empty: bool = False
    has_image: bool = False
    has_field: bool = False
    has_shape: bool = False

    # 의미 분석 결과
    is_column_header: bool = False
    is_row_header: bool = False
    is_group_header: bool = False
    is_data_cell: bool = False

    raw_attrs: dict[str, Any] = field(default_factory=dict)

    @property
    def end_row(self) -> Optional[int]:
        """
        역할: 셀이 row_span까지 포함해 차지하는 마지막 행 인덱스를 계산한다.
        입력 데이터: self.row_addr(시작 행), self.row_span(행 병합 수).
        출력 데이터: 포함 범위의 마지막 행 인덱스를 반환하고, row_addr가 없으면 None을 반환한다.
        """
        if self.row_addr is None:
            return None

        return self.row_addr + self.row_span - 1

    @property
    def end_col(self) -> Optional[int]:
        """
        역할: 셀이 col_span까지 포함해 차지하는 마지막 열 인덱스를 계산한다.
        입력 데이터: self.col_addr(시작 열), self.col_span(열 병합 수).
        출력 데이터: 포함 범위의 마지막 열 인덱스를 반환하고, col_addr가 없으면 None을 반환한다.
        """
        if self.col_addr is None:
            return None

        return self.col_addr + self.col_span - 1
