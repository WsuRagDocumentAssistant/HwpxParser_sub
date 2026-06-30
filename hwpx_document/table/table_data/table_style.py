#================================================
# document/table/table_style.py
#================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class BorderSide:
    """
    hh:borderFill 안의 한쪽 테두리 정보.
    """

    type: Optional[str] = None
    width: Optional[str] = None
    color: Optional[str] = None


@dataclass
class FillInfo:
    """
    셀 또는 표 배경 채우기 정보.
    """

    face_color: Optional[str] = None
    hatch_color: Optional[str] = None
    pattern_type: Optional[str] = None


@dataclass
class BorderFill:
    """
    header.xml의 hh:borderFill 정보.
    """

    id: str

    left: Optional[BorderSide] = None
    right: Optional[BorderSide] = None
    top: Optional[BorderSide] = None
    bottom: Optional[BorderSide] = None

    diagonal: Optional[BorderSide] = None
    slash: Optional[BorderSide] = None
    back_slash: Optional[BorderSide] = None

    fill: Optional[FillInfo] = None


@dataclass
class ParagraphStyle:
    """
    header.xml의 hh:paraPr / hh:style 기반 문단 스타일.
    """

    id: str

    style_id: Optional[str] = None
    style_name: Optional[str] = None

    para_pr_id_ref: Optional[str] = None
    char_pr_id_ref: Optional[str] = None

    align: Optional[str] = None
    vertical_align: Optional[str] = None

    margin_left: Optional[int] = None
    margin_right: Optional[int] = None
    indent: Optional[int] = None

    heading_level: Optional[int] = None


@dataclass
class CharacterStyle:
    """
    header.xml의 hh:charPr 기반 글자 스타일.
    """

    id: str

    height: Optional[int] = None
    text_color: Optional[str] = None
    font_face: Optional[str] = None

    bold: bool = False
    italic: bool = False
    underline: bool = False