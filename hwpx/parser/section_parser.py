#================================================
# section_parser.py
#================================================

from __future__ import annotations

import re
from pathlib import Path
import xml.etree.ElementTree as ET

from .parser_context import ParserContext
from .table.table_parser import TableParser
from .table.parsers.table_analyzer import TableAnalyzer

import logging

# 라이브러리는 조용한 것이 기본이다. 단계 보고를 보려면 쓰는 쪽에서
# logging 을 켠다. tools 는 그렇게 하고 있다.
log = logging.getLogger(__name__)


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

            log.info(
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

                # 머리말/꼬리말/각주 안에 표를 짜 넣은 경우, 조상에 tbl이 없어
                # 최상위 표로 수집된다. 표시해 두지 않으면 본문 데이터 표와
                # 구분할 수 없다. (셀 안쪽은 TableParser가 같은 표시를 붙인다)
                table.owner_control_type = cls._owner_control_type(
                    tbl_element, parent_map,
                )

                table = TableAnalyzer.analyze(table, context)

                cls._fill_candidates(table, tbl_element, parent_map, root)

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

    # hp:ctrl 하위에서 독립 엔티티로 승격되는 요소 (SectionStreamParser와 동일 집합)
    _CTRL_OWNER_TAGS = {
        "header": "header",
        "footer": "footer",
        "footNote": "footnote",
        "endNote": "endnote",
    }

    @classmethod
    def _owner_control_type(cls, element, parent_map) -> str | None:
        """
        역할: 표의 조상 중 머리말/꼬리말/각주/미주가 있으면 그 종류를 반환한다.
        입력 데이터: element(hp:tbl 요소), parent_map(자식→부모 맵).
        출력 데이터: control 종류 문자열. 본문 표면 None.
        """
        parent = parent_map.get(element)

        while parent is not None:
            owner = cls._CTRL_OWNER_TAGS.get(cls._local_name(parent.tag))
            if owner is not None:
                return owner
            parent = parent_map.get(parent)

        return None

    @classmethod
    def _has_ancestor_tbl(cls, element, parent_map) -> bool:
        parent = parent_map.get(element)

        while parent is not None:
            if cls._local_name(parent.tag) == "tbl":
                return True

            parent = parent_map.get(parent)

        return False

    #────────────────────────────────────────────────
    # caption / note / source candidate 추출
    #────────────────────────────────────────────────

    _RE_CAPTION = re.compile(r"^(표|그림|Figure|Table)\s*[\d\.\-]|^【.+】$|^\[.+\]$")
    _RE_NOTE    = re.compile(r"^(주[):\s]|주석|※|\*\s)")
    _RE_SOURCE  = re.compile(r"^(자료|출처|자료원)\s*[:：]")
    _RE_IGNORE  = re.compile(r"^그림입니다\.|^원본 그림의|^묶음 개체")

    @classmethod
    def _fill_candidates(cls, table, tbl_element, parent_map, root) -> None:
        """tbl을 감싼 hp:p의 앞뒤 형제 p에서 caption/note/source 후보를 추출한다."""
        # tbl → run → p 순으로 sec 직계 p를 찾는다
        container_p = cls._find_container_p(tbl_element, parent_map, root)
        if container_p is None:
            return

        sec = parent_map.get(container_p)
        if sec is None:
            return

        siblings = list(sec)
        idx = siblings.index(container_p)

        prev_text = cls._p_text(siblings[idx - 1]) if idx > 0 else ""
        next_text = cls._p_text(siblings[idx + 1]) if idx + 1 < len(siblings) else ""

        # 이미지 설명문 등 무의미한 텍스트 제거
        if cls._RE_IGNORE.match(prev_text):
            prev_text = ""
        if cls._RE_IGNORE.match(next_text):
            next_text = ""

        if prev_text and cls._RE_CAPTION.match(prev_text):
            table.caption_candidate = prev_text

        if next_text and cls._RE_NOTE.match(next_text):
            table.note_candidate = next_text
        elif next_text and cls._RE_SOURCE.match(next_text):
            table.source_candidate = next_text

        # 뒤쪽 두 번째 줄까지 확인 (note 다음에 source가 올 수 있음)
        if idx + 2 < len(siblings):
            next2_text = cls._p_text(siblings[idx + 2])
            if next2_text and cls._RE_SOURCE.match(next2_text) and table.source_candidate is None:
                table.source_candidate = next2_text

    @classmethod
    def _find_container_p(cls, tbl_element, parent_map, root):
        """tbl의 조상 중 sec 직계 자식인 p를 반환한다."""
        sec_children = set(root)
        cur = tbl_element
        while cur is not None:
            if cur in sec_children and cls._local_name(cur.tag) == "p":
                return cur
            cur = parent_map.get(cur)
        return None

    @classmethod
    def _p_text(cls, elem) -> str:
        """hp:p 요소의 텍스트를 하나의 문자열로 합친다."""
        parts = [t.strip() for e in elem.iter() if (t := e.text or "")]
        return " ".join(p for p in parts if p)
