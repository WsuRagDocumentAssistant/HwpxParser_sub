#================================================
# header_parser.py
#================================================

from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from ..document.header_data import HeaderData


class HeaderParser:
    """
    Contents/header.xml에서 문서 파싱에 필요한 공통 참조 정보를 추출한다.

    저장 대상:
    - hh:paraPr@id      -> HeaderData.para_properties
    - hh:charPr@id      -> HeaderData.char_properties
    - hh:style@id       -> HeaderData.styles
    - hh:style@id       -> style_names / style_to_para_pr / style_to_char_pr
    - hh:paraPr heading -> para_pr_to_heading_level

    """

    @classmethod
    def parse(cls, source: str | Path) -> HeaderData:
        """
        역할: Contents/header.xml을 읽어 공통 참조 정보가 담긴 HeaderData 객체로 변환한다.
        입력 데이터: source(header.xml 파일 경로 문자열 또는 Path).
        출력 데이터: paraPr/charPr/style 원본 맵을 가진 HeaderData 객체를 반환한다.
        """
        source = Path(source)

        if not source.exists():
            raise FileNotFoundError(f"header.xml을 찾을 수 없습니다: {source}")

        root = ET.parse(source).getroot()

        header = HeaderData(
            raw_attrs=cls._normalize_attrs(root.attrib),
        )

        cls._parse_para_properties(root, header)
        cls._parse_char_properties(root, header)
        cls._parse_styles(root, header)
        cls._parse_auto_label_definitions(root, header)

        return header

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

            heading_info = cls._extract_heading_info(elem)
            if heading_info is not None:
                header.para_pr_to_heading[para_pr_id] = heading_info

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
    # heading 상세 정보 / 자동 마커 정의 추출
    #------------------------------------------------

    @classmethod
    def _extract_heading_info(cls, para_pr_element) -> dict[str, Any] | None:
        """
        역할: paraPr 하위 heading에서 type/level/idRef를 함께 추출한다.
              _extract_heading_level은 level만 반환하므로,
              불릿/번호 정의(hh:bullet, hh:numbering)를 찾아가려면 idRef가 필요하다.
        입력 데이터: para_pr_element(paraPr XML 요소).
        출력 데이터: {"type", "level", "id_ref"} dict. heading이 없으면 None.
        """
        candidate_names = {"heading", "headingInfo", "outline"}

        for child in para_pr_element.iter():
            if child is para_pr_element:
                continue

            if cls._local_name(child.tag) not in candidate_names:
                continue

            attrs = cls._normalize_attrs(child.attrib)

            level = attrs.get("level")
            try:
                level_value = int(level) if level is not None else None
            except ValueError:
                level_value = None

            return {
                "type": attrs.get("type"),
                "level": level_value,
                "id_ref": attrs.get("idRef"),
            }

        return None

    @classmethod
    def _parse_auto_label_definitions(cls, root, header: HeaderData) -> None:
        """
        역할: 문단 앞에 자동 렌더링되지만 section*.xml의 hp:t에는 저장되지 않는
              마커 정의를 추출한다.
              - hh:bullet@id -> @char        (불릿 문자)
              - hh:numbering@id -> paraHead  (개요/문단 번호 형식)
        입력 데이터: root(header XML 루트), header(수정할 HeaderData).
        출력 데이터: 반환값은 없고, bullet_chars / numbering_para_heads가 갱신된다.
        """
        for elem in root.iter():
            name = cls._local_name(elem.tag)

            if name == "bullet":
                attrs = cls._normalize_attrs(elem.attrib)
                bullet_id = attrs.get("id")
                char = attrs.get("char")

                if bullet_id is not None and char:
                    header.bullet_chars[str(bullet_id)] = str(char)

                continue

            if name != "numbering":
                continue

            attrs = cls._normalize_attrs(elem.attrib)
            numbering_id = attrs.get("id")

            if numbering_id is None:
                continue

            heads: dict[str, dict[str, Any]] = {}

            for child in elem:
                if cls._local_name(child.tag) != "paraHead":
                    continue

                head_attrs = cls._normalize_attrs(child.attrib)
                level = head_attrs.get("level")

                if level is None:
                    continue

                heads[str(level)] = {
                    # "^1." 처럼 순번 자리표시자가 들어간 형식 문자열
                    "text": child.text,
                    "num_format": head_attrs.get("numFormat"),
                    "start": head_attrs.get("start"),
                }

            if heads:
                header.numbering_para_heads[str(numbering_id)] = heads

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
