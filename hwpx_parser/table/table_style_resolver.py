#================================================
# table/table_style_resolver.py
#================================================

from __future__ import annotations

from typing import Any, Optional

from hwpx_document.table import Table
from hwpx_document.table.table_data.table_style import BorderFill, BorderSide, FillInfo
from hwpx_parser.parser_context import ParserContext


class TableStyleResolver:
    """
    Table / TableCell의 borderFillIDRef를
    header.xml의 hh:borderFill 정보와 연결한다.
    """

    @classmethod
    def resolve(
        cls,
        table: Table,
        context: ParserContext,
    ) -> None:
        """
        역할: 표와 셀의 borderFillIDRef를 실제 BorderFill 객체로 해석해 연결한다.
        입력 데이터: table(파싱된 Table), context(header 원본 데이터를 조회할 ParserContext).
        출력 데이터: 반환값은 없고, table.border_fill 및 각 cell.border_fill 속성이 갱신된다.
        """
        """
        표 전체와 셀 단위 borderFillIDRef를 실제 BorderFill 객체로 연결한다.
        """

        table.border_fill = cls._resolve_border_fill(
            border_fill_id=table.border_fill_id_ref,
            context=context,
        )

        for cell in table.cells:
            cell.border_fill = cls._resolve_border_fill(
                border_fill_id=cell.border_fill_id_ref,
                context=context,
            )

            for nested_table in getattr(cell, "nested_tables", []):
                cls.resolve(
                    table=nested_table,
                    context=context,
                )

    @classmethod
    def _resolve_border_fill(
        cls,
        border_fill_id: Optional[str],
        context: ParserContext,
    ) -> Optional[BorderFill]:
        """
        역할: 하나의 borderFillIDRef를 header 원본 데이터에서 찾아 BorderFill 객체로 변환한다.
        입력 데이터: border_fill_id(borderFillIDRef 또는 None), context(header 조회용 ParserContext).
        출력 데이터: BorderFill 객체를 반환하고, ID가 없거나 원본을 찾지 못하면 None을 반환한다.
        """
        if border_fill_id is None:
            return None

        raw = context.get_border_fill_raw(border_fill_id)

        if raw is None:
            return None

        return cls._raw_to_border_fill(
            border_fill_id=border_fill_id,
            raw=raw,
        )

    @classmethod
    def _raw_to_border_fill(
        cls,
        border_fill_id: str,
        raw: dict[str, Any],
    ) -> BorderFill:
        """
        역할: HeaderData에 저장된 borderFill 원본 dict를 타입이 있는 BorderFill 객체로 바꾼다.
        입력 데이터: border_fill_id(borderFill ID), raw(tag/attrs/children 구조의 원본 dict).
        출력 데이터: 좌/우/상/하/대각선/채우기 정보가 담긴 BorderFill 객체를 반환한다.
        """
        children = raw.get("children", [])

        return BorderFill(
            id=border_fill_id,
            left=cls._find_border_side(children, "leftBorder"),
            right=cls._find_border_side(children, "rightBorder"),
            top=cls._find_border_side(children, "topBorder"),
            bottom=cls._find_border_side(children, "bottomBorder"),
            diagonal=cls._find_border_side(children, "diagonal"),
            slash=cls._find_border_side(children, "slash"),
            back_slash=cls._find_border_side(children, "backSlash"),
            fill=cls._find_fill(children),
        )

    @classmethod
    def _find_border_side(
        cls,
        children: list[dict[str, Any]],
        tag_name: str,
    ) -> Optional[BorderSide]:
        """
        역할: borderFill 하위 children에서 특정 테두리 방향 요소를 찾아 BorderSide로 변환한다.
        입력 데이터: children(borderFill 하위 원본 dict 리스트), tag_name(찾을 테두리 태그명).
        출력 데이터: BorderSide 객체를 반환하고, 해당 태그가 없으면 None을 반환한다.
        """
        for child in children:
            if child.get("tag") != tag_name:
                continue

            attrs = child.get("attrs", {})

            return BorderSide(
                type=attrs.get("type"),
                width=attrs.get("width"),
                color=attrs.get("color"),
            )

        return None

    @classmethod
    def _find_fill(
        cls,
        children: list[dict[str, Any]],
    ) -> Optional[FillInfo]:
        """
        역할: borderFill 하위 fillBrush/winBrush에서 배경 채우기 정보를 추출한다.
        입력 데이터: children(borderFill 하위 원본 dict 리스트).
        출력 데이터: FillInfo 객체를 반환하고, 채우기 정보가 없으면 None을 반환한다.
        """
        """
        hh:fillBrush 내부의 winBrush 정보를 우선 추출한다.
        """

        fill_brush = None

        for child in children:
            if child.get("tag") == "fillBrush":
                fill_brush = child
                break

        if fill_brush is None:
            return None

        for child in fill_brush.get("children", []):
            if child.get("tag") != "winBrush":
                continue

            attrs = child.get("attrs", {})

            return FillInfo(
                face_color=attrs.get("faceColor"),
                hatch_color=attrs.get("hatchColor"),
                pattern_type=attrs.get("patternType"),
            )

        return None
