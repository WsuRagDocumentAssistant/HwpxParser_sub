#================================================
# section_parser.py
#================================================

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from hwpx_parser.parser_context import ParserContext
from hwpx_parser.table.table_parser import TableParser

from .table.table_analyzer import TableAnalyzer
from hwpx_parser.table.table_style_resolver import TableStyleResolver


class SectionParser:
    """
    section*.xml에서 hp:tbl을 찾아 Table 객체로 변환한다.
    """

    @classmethod
    def parse(
        cls,
        section_sources: list[str | Path],
        context: ParserContext,
    ):
        """
        역할: 각 section*.xml에서 hp:tbl 요소를 찾아 Table 객체로 파싱하고 분석까지 수행한다.
        입력 데이터: section_sources(섹션 XML 경로 리스트), context(header/이미지 경로를 담은 ParserContext).
        출력 데이터: 스타일 해석과 구조 검증이 끝난 Table 객체 리스트를 반환한다.
        """
        tables = []

        for section_index, section_source in enumerate(section_sources):
            section_path = Path(section_source)
            root = ET.parse(section_path).getroot()
            parent_map = cls._build_parent_map(root)

            tbl_elements = [
                elem for elem in root.iter()
                if cls._local_name(elem.tag) == "tbl"
                and not cls._has_ancestor_tbl(elem, parent_map)
            ]

            print(
                f"[SectionParser] section_index={section_index}, "
                f"file={section_path.name}, "
                f"table_count={len(tbl_elements)}"
            )

            for table_index, tbl_element in enumerate(tbl_elements):
                table = TableParser.parse(
                    tbl_element=tbl_element,
                    section_index=section_index,
                    table_index=table_index,
                )

                TableStyleResolver.resolve(
                    table=table,
                    context=context,
                )

                table = TableAnalyzer.analyze(table, context)


                tables.append(table)

        return tables

    @classmethod
    def _local_name(cls, tag: str) -> str:
        """
        역할: XML 태그 문자열에서 네임스페이스를 제거한다.
        입력 데이터: tag(네임스페이스 포함 또는 미포함 XML 태그명).
        출력 데이터: local tag name 문자열을 반환한다.
        """
        if "}" in tag:
            return tag.split("}", 1)[1]

        return tag

    @classmethod
    def _build_parent_map(cls, root):
        return {
            child: parent
            for parent in root.iter()
            for child in list(parent)
        }

    @classmethod
    def _has_ancestor_tbl(cls, element, parent_map) -> bool:
        parent = parent_map.get(element)

        while parent is not None:
            if cls._local_name(parent.tag) == "tbl":
                return True

            parent = parent_map.get(parent)

        return False
