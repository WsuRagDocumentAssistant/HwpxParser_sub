#================================================
# parser/parser_context.py
#================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any

from hwpx_document.header_data import HeaderData


@dataclass
class ParserContext:
    """
    section.xml, table.xml 등을 파싱할 때 필요한 공통 참조 정보.

    이 Context는 paraPr/charPr/style 같은 참조 ID를 기준으로 header.xml 정보를 조회하는 역할만 한다.
    """

    # header.xml 파싱 결과
    header: HeaderData

    # 이미지 폴더 경로
    image_dir_path: Optional[Path] = None

    #------------------------------------------------
    # paraPr 참조 조회
    #------------------------------------------------

    def get_para_pr_raw(
        self,
        para_pr_id: Optional[str] = None,
        style_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        역할: 직접 paraPrIDRef 또는 styleIDRef를 기준으로 문단 속성 원본 데이터를 조회한다.
        입력 데이터: para_pr_id(직접 문단 속성 ID), style_id(스타일 ID).
        출력 데이터: 해석된 paraPr 원본 dict를 반환하고, 찾지 못하면 None을 반환한다.
        """
        """
        hp:p@paraPrIDRef 또는 hp:p@styleIDRef를 기준으로
        header.xml의 hh:paraPr raw 정보를 조회한다.

        style_id가 들어오면 HeaderData에서 style → paraPrIDRef를 먼저 해석한다.
        """

        resolved_para_pr_id = self.header.resolve_para_pr_id(
            para_pr_id=para_pr_id,
            style_id=style_id,
        )

        return self.header.get_para_pr_raw(resolved_para_pr_id)

    #------------------------------------------------
    # charPr 참조 조회
    #------------------------------------------------

    def get_char_pr_raw(
        self,
        char_pr_id: Optional[str],
    ) -> Optional[dict[str, Any]]:
        """
        역할: run의 charPrIDRef로 header.xml의 글자 속성 원본 데이터를 조회한다.
        입력 데이터: char_pr_id(글자 속성 ID 또는 None).
        출력 데이터: 일치하는 charPr 원본 dict를 반환하고, 없으면 None을 반환한다.
        """
        """
        hp:run@charPrIDRef가 가리키는
        header.xml의 hh:charPr raw 정보를 조회한다.
        """

        if char_pr_id is None:
            return None

        return self.header.get_char_pr_raw(str(char_pr_id))

    #------------------------------------------------
    # style 참조 조회
    #------------------------------------------------

    def get_style_raw(
        self,
        style_id: Optional[str],
    ) -> Optional[dict[str, Any]]:
        """
        역할: 문단의 styleIDRef로 header.xml의 style 원본 데이터를 조회한다.
        입력 데이터: style_id(스타일 ID 또는 None).
        출력 데이터: 일치하는 style 원본 dict를 반환하고, 없으면 None을 반환한다.
        """
        """
        hp:p@styleIDRef가 가리키는
        header.xml의 hh:style raw 정보를 조회한다.
        """

        if style_id is None:
            return None

        return self.header.get_style_raw(str(style_id))
