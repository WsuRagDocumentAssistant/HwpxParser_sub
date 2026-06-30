#================================================
# header_parser.py
#================================================

from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from hwpx_document.header_data import HeaderData


class HeaderParser:
    """
    Contents/header.xml에서 문서 파싱에 필요한 공통 참조 정보를 추출한다.

    저장 대상:
    - hh:borderFill@id  -> HeaderData.border_fills
    - hh:paraPr@id      -> HeaderData.para_properties
    - hh:charPr@id      -> HeaderData.char_properties
    - hh:style@id       -> HeaderData.styles
    - hh:style@id       -> style_names / style_to_para_pr / style_to_char_pr
    - hh:paraPr heading -> para_pr_to_heading_level

    주의:
    - Table / TableCell에 BorderFill 객체를 직접 저장하지 않는다.
    - header.xml의 borderFill은 HeaderData.border_fills에 raw dict로 보관한다.
    - 이후 ParserContext.get_border_fill_raw(border_fill_id)로 필요할 때 조회한다.
    """

    @classmethod
    def parse(cls, source: str | Path) -> HeaderData:
        """
        역할: Contents/header.xml을 읽어 공통 참조 정보가 담긴 HeaderData 객체로 변환한다.
        입력 데이터: source(header.xml 파일 경로 문자열 또는 Path).
        출력 데이터: borderFill/paraPr/charPr/style 원본 맵을 가진 HeaderData 객체를 반환한다.
        """
        source = Path(source)

        if not source.exists():
            raise FileNotFoundError(f"header.xml을 찾을 수 없습니다: {source}")

        root = ET.parse(source).getroot()

        header = HeaderData(
            raw_attrs=cls._normalize_attrs(root.attrib),
        )

        cls._parse_border_fills(root, header)
        cls._parse_para_properties(root, header)
        cls._parse_char_properties(root, header)
        cls._parse_styles(root, header)

        return header

    #------------------------------------------------
    # borderFill 파싱
    #------------------------------------------------

    @classmethod
    def _parse_border_fills(cls, root, header: HeaderData) -> None:
        """
        역할: header.xml 전체에서 hh:borderFill 요소를 찾아 ID별 원본 데이터로 저장한다.
        입력 데이터: root(header XML 루트), header(수정할 HeaderData).
        출력 데이터: 반환값은 없고, header.border_fills 딕셔너리가 갱신된다.
        """
        """
        header.xml의 hh:borderFill 목록을 추출한다.

        예:
        <hh:borderFill id="3">
            <hh:leftBorder ... />
            <hh:rightBorder ... />
            <hh:fillBrush>...</hh:fillBrush>
        </hh:borderFill>

        저장 형태:
        header.border_fills["3"] = {
            "tag": "borderFill",
            "attrs": {"id": "3", ...},
            "children": [...]
        }

        Table / TableCell에는 이 객체를 직접 넣지 않고,
        border_fill_id_ref만 저장한 뒤 필요할 때 ID로 조회한다.
        """

        for elem in root.iter():
            if cls._local_name(elem.tag) != "borderFill":
                continue

            attrs = cls._normalize_attrs(elem.attrib)

            border_fill_id = attrs.get("id")
            if border_fill_id is None:
                continue

            border_fill_id = str(border_fill_id)

            header.border_fills[border_fill_id] = cls._element_to_raw(elem)

    #------------------------------------------------
    # paraPr 파싱
    #------------------------------------------------

    @classmethod
    def _parse_para_properties(cls, root, header: HeaderData) -> None:
        """
        역할: header.xml의 hh:paraPr 요소와 heading level 정보를 추출한다.
        입력 데이터: root(header XML 루트), header(수정할 HeaderData).
        출력 데이터: 반환값은 없고, header.para_properties와 header.para_pr_to_heading_level이 갱신된다.
        """
        """
        header.xml의 hh:paraPr 목록을 추출한다.
        문단 속성, 개요/heading level 분석에 사용된다.
        """

        for elem in root.iter():
            if cls._local_name(elem.tag) != "paraPr":
                continue

            attrs = cls._normalize_attrs(elem.attrib)

            para_pr_id = attrs.get("id")
            if para_pr_id is None:
                continue

            para_pr_id = str(para_pr_id)

            raw = cls._element_to_raw(elem)
            header.para_properties[para_pr_id] = raw

            heading_level = cls._extract_heading_level(elem)
            if heading_level is not None:
                header.para_pr_to_heading_level[para_pr_id] = heading_level

    #------------------------------------------------
    # charPr 파싱
    #------------------------------------------------

    @classmethod
    def _parse_char_properties(cls, root, header: HeaderData) -> None:
        """
        역할: header.xml의 hh:charPr 요소를 찾아 ID별 글자 속성 원본 데이터로 저장한다.
        입력 데이터: root(header XML 루트), header(수정할 HeaderData).
        출력 데이터: 반환값은 없고, header.char_properties 딕셔너리가 갱신된다.
        """
        """
        header.xml의 hh:charPr 목록을 추출한다.
        글자 크기, 색상, 굵게, 밑줄 등의 참조 분석에 사용된다.
        """

        for elem in root.iter():
            if cls._local_name(elem.tag) != "charPr":
                continue

            attrs = cls._normalize_attrs(elem.attrib)

            char_pr_id = attrs.get("id")
            if char_pr_id is None:
                continue

            char_pr_id = str(char_pr_id)

            header.char_properties[char_pr_id] = cls._element_to_raw(elem)

    #------------------------------------------------
    # style 파싱
    #------------------------------------------------

    @classmethod
    def _parse_styles(cls, root, header: HeaderData) -> None:
        """
        역할: header.xml의 hh:style 요소와 연결된 paraPrIDRef/charPrIDRef 정보를 추출한다.
        입력 데이터: root(header XML 루트), header(수정할 HeaderData).
        출력 데이터: 반환값은 없고, styles/style_names/style_to_para_pr/style_to_char_pr 맵이 갱신된다.
        """
        """
        header.xml의 hh:style 목록을 추출한다.

        styleIDRef를 통해 paraPrIDRef / charPrIDRef까지 이어질 수 있으므로
        style_to_para_pr, style_to_char_pr도 같이 구성한다.
        """

        for elem in root.iter():
            if cls._local_name(elem.tag) != "style":
                continue

            attrs = cls._normalize_attrs(elem.attrib)

            style_id = attrs.get("id")
            if style_id is None:
                continue

            style_id = str(style_id)

            header.styles[style_id] = cls._element_to_raw(elem)

            style_name = attrs.get("name") or attrs.get("engName")
            if style_name is not None:
                header.style_names[style_id] = style_name

            para_pr_id_ref = attrs.get("paraPrIDRef")
            if para_pr_id_ref is not None:
                header.style_to_para_pr[style_id] = str(para_pr_id_ref)

            char_pr_id_ref = attrs.get("charPrIDRef")
            if char_pr_id_ref is not None:
                header.style_to_char_pr[style_id] = str(char_pr_id_ref)

    #------------------------------------------------
    # heading level 추출
    #------------------------------------------------

    @classmethod
    def _extract_heading_level(cls, para_pr_element) -> int | None:
        """
        역할: 하나의 paraPr 요소 하위에서 heading/outline 계층 레벨을 찾아낸다.
        입력 데이터: para_pr_element(paraPr XML 요소).
        출력 데이터: level 속성을 정수로 변환해 반환하고, 없거나 변환 실패 시 None을 반환한다.
        """
        """
        HWPX header.xml의 paraPr 아래 heading 정보를 가능한 범위에서 추출한다.

        문서마다 heading 표현이 조금씩 다를 수 있어서 다음 이름을 모두 허용한다.
        - heading
        - headingInfo
        - outline

        그리고 level 속성이 있으면 int로 변환한다.
        """

        candidate_names = {"heading", "headingInfo", "outline"}

        for child in para_pr_element.iter():
            if child is para_pr_element:
                continue

            if cls._local_name(child.tag) not in candidate_names:
                continue

            attrs = cls._normalize_attrs(child.attrib)

            level = attrs.get("level")
            if level is None:
                continue

            try:
                return int(level)
            except ValueError:
                return None

        return None

    #------------------------------------------------
    # XML element raw 변환
    #------------------------------------------------

    @classmethod
    def _element_to_raw(cls, element) -> dict[str, Any]:
        """
        역할: XML 요소와 하위 요소를 JSON 직렬화 가능한 원본 dict 구조로 변환한다.
        입력 데이터: element(XML Element 객체).
        출력 데이터: tag/attrs/text/children 키를 가진 dict를 반환한다.
        """
        """
        XML element를 dict로 보존한다.

        검증 단계에서는 주로 attrs를 쓰지만,
        추후 스타일 상세 분석을 위해 children도 같이 저장한다.

        반환 예:
        {
            "tag": "borderFill",
            "attrs": {"id": "3"},
            "text": "",
            "children": [...]
        }
        """

        return {
            "tag": cls._local_name(element.tag),
            "attrs": cls._normalize_attrs(element.attrib),
            "text": element.text or "",
            "children": [
                cls._element_to_raw(child)
                for child in list(element)
            ],
        }

    #------------------------------------------------
    # 유틸
    #------------------------------------------------

    @staticmethod
    def _normalize_attrs(attrs: dict[str, Any]) -> dict[str, Any]:
        """
        역할: XML 네임스페이스가 포함된 속성명을 local name 기준으로 정리한다.
        입력 데이터: attrs(XML 속성 dict).
        출력 데이터: 네임스페이스가 제거된 속성명과 원래 값을 담은 dict를 반환한다.
        """
        """
        XML namespace가 붙은 속성명을 local name으로 정리한다.
        """

        return {
            str(key).split("}", 1)[-1] if "}" in str(key) else str(key): value
            for key, value in dict(attrs).items()
        }

    @staticmethod
    def _local_name(tag: str) -> str:
        """
        역할: XML 태그 문자열에서 네임스페이스를 제거한다.
        입력 데이터: tag(네임스페이스 포함 또는 미포함 XML 태그명).
        출력 데이터: local tag name 문자열을 반환한다.
        """
        """
        {namespace}tag 형태에서 tag만 추출한다.
        """

        if "}" in tag:
            return tag.split("}", 1)[1]

        return tag
