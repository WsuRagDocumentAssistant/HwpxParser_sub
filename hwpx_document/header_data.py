#================================================
# document/header_data.py
#================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class HeaderData:
    """
    header.xml에서 추출한 참조 정보를 저장하는 객체.

    여기서는 BorderFill, ParagraphStyle, CharacterStyle 같은
    table_style 객체로 변환하지 않는다.

    단순히 header.xml의 id 기반 정보를 dict로 보관한다.
    """

    # hh:borderFill@id → borderFill 원본 정보
    border_fills: dict[str, dict[str, Any]] = field(default_factory=dict)

    # hh:paraPr@id → paraPr 원본 정보
    para_properties: dict[str, dict[str, Any]] = field(default_factory=dict)

    # hh:charPr@id → charPr 원본 정보
    char_properties: dict[str, dict[str, Any]] = field(default_factory=dict)

    # hh:style@id → style 원본 정보
    styles: dict[str, dict[str, Any]] = field(default_factory=dict)

    # style id → style name
    style_names: dict[str, str] = field(default_factory=dict)

    # style id → paraPrIDRef
    style_to_para_pr: dict[str, str] = field(default_factory=dict)

    # style id → charPrIDRef
    style_to_char_pr: dict[str, str] = field(default_factory=dict)

    # paraPr id → heading level
    para_pr_to_heading_level: dict[str, int] = field(default_factory=dict)

    # header.xml 최상위 속성
    raw_attrs: dict[str, Any] = field(default_factory=dict)

    def get_border_fill_raw(self, border_fill_id: Optional[str]) -> Optional[dict[str, Any]]:
        """
        역할: HeaderData에 저장된 borderFill 원본 데이터를 ID로 조회한다.
        입력 데이터: border_fill_id(borderFill ID 또는 None).
        출력 데이터: 일치하는 borderFill 원본 dict를 반환하고, 없으면 None을 반환한다.
        """
        if border_fill_id is None:
            return None

        return self.border_fills.get(border_fill_id)

    def get_para_pr_raw(self, para_pr_id: Optional[str]) -> Optional[dict[str, Any]]:
        """
        역할: HeaderData에 저장된 paraPr 원본 데이터를 ID로 조회한다.
        입력 데이터: para_pr_id(paraPr ID 또는 None).
        출력 데이터: 일치하는 paraPr 원본 dict를 반환하고, 없으면 None을 반환한다.
        """
        if para_pr_id is None:
            return None

        return self.para_properties.get(para_pr_id)

    def get_char_pr_raw(self, char_pr_id: Optional[str]) -> Optional[dict[str, Any]]:
        """
        역할: HeaderData에 저장된 charPr 원본 데이터를 ID로 조회한다.
        입력 데이터: char_pr_id(charPr ID 또는 None).
        출력 데이터: 일치하는 charPr 원본 dict를 반환하고, 없으면 None을 반환한다.
        """
        if char_pr_id is None:
            return None

        return self.char_properties.get(char_pr_id)

    def get_style_raw(self, style_id: Optional[str]) -> Optional[dict[str, Any]]:
        """
        역할: HeaderData에 저장된 style 원본 데이터를 ID로 조회한다.
        입력 데이터: style_id(style ID 또는 None).
        출력 데이터: 일치하는 style 원본 dict를 반환하고, 없으면 None을 반환한다.
        """
        if style_id is None:
            return None

        return self.styles.get(style_id)

    def resolve_para_pr_id(
        self,
        para_pr_id: Optional[str] = None,
        style_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        역할: 문단에 적용할 최종 paraPr ID를 직접 참조와 style 참조 우선순위로 결정한다.
        입력 데이터: para_pr_id(직접 hp:p@paraPrIDRef), style_id(hp:p@styleIDRef).
        출력 데이터: 직접 paraPr ID, style에 연결된 paraPr ID, 또는 None을 반환한다.
        """
        """
        문단 스타일 id를 결정한다.

        우선순위:
        1. hp:p@paraPrIDRef
        2. hp:p@styleIDRef → hh:style@paraPrIDRef
        """

        if para_pr_id is not None:
            return para_pr_id

        if style_id is not None:
            return self.style_to_para_pr.get(style_id)

        return None

    def resolve_char_pr_id_from_style(
        self,
        style_id: Optional[str],
    ) -> Optional[str]:
        """
        역할: styleIDRef에 연결된 charPrIDRef를 조회한다.
        입력 데이터: style_id(style ID 또는 None).
        출력 데이터: 연결된 charPr ID를 반환하고, 없으면 None을 반환한다.
        """
        """
        styleIDRef를 통해 charPrIDRef를 찾는다.
        """

        if style_id is None:
            return None

        return self.style_to_char_pr.get(style_id)
