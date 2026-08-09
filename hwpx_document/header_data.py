#================================================
# document/header_data.py
#================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any


# 유니코드 사설 사용 영역(Private Use Area).
# Wingdings 계열 불릿(U+F09E 등)이 이 범위에 들어오며 해당 폰트 없이는
# 렌더링되지 않으므로, 계층 신호로 글리프 자체를 쓰면 안 된다.
_PRIVATE_USE_START = ""
_PRIVATE_USE_END = ""


def _is_private_use(char: str) -> bool:
    """
    역할: 문자가 유니코드 사설 사용 영역(PUA)에 속하는지 판별한다.
    입력 데이터: char(문자열).
    출력 데이터: PUA 문자가 하나라도 있으면 True.
    """
    return any(_PRIVATE_USE_START <= ch <= _PRIVATE_USE_END for ch in char)


@dataclass
class HeaderData:
    """
    header.xml에서 추출한 참조 정보를 저장하는 객체.

    여기서는 ParagraphStyle, CharacterStyle 같은
    table_style 객체로 변환하지 않는다.

    단순히 header.xml의 id 기반 정보를 dict로 보관한다.
    """

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

    # paraPr id → {"type": OUTLINE|NUMBER|BULLET|NONE, "level": int|None, "id_ref": str|None}
    para_pr_to_heading: dict[str, dict[str, Any]] = field(default_factory=dict)

    # hh:bullet@id → @char (문단 앞에 자동 렌더링되는 불릿 문자)
    bullet_chars: dict[str, str] = field(default_factory=dict)

    # hh:numbering@id → level(str) → {"text", "num_format", "start"}
    numbering_para_heads: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)

    # header.xml 최상위 속성
    raw_attrs: dict[str, Any] = field(default_factory=dict)

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

    def resolve_auto_label(
        self,
        para_pr_id: Optional[str] = None,
        style_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        역할: 문단 앞에 자동 렌더링되지만 hp:t에는 저장되지 않는 마커
              (불릿 문자 / 개요·문단 번호 형식)을 header.xml 정의에서 복원한다.
        입력 데이터: para_pr_id(hp:p@paraPrIDRef), style_id(hp:p@styleIDRef).
        출력 데이터: 마커 정보 dict. 자동 마커가 없는 문단(type=NONE 등)이면 None.

        주의: 반환값은 원문 텍스트가 아니라 '렌더링 시 덧붙는 마커'다.
              text에 직접 접합하면 원문 무손실성이 깨지므로 별도 필드로 다뤄야 한다.
        """
        resolved_id = self.resolve_para_pr_id(para_pr_id=para_pr_id, style_id=style_id)

        if resolved_id is None:
            return None

        heading = self.para_pr_to_heading.get(str(resolved_id))

        if not heading:
            return None

        heading_type = heading.get("type")
        id_ref = heading.get("id_ref")
        level = heading.get("level")

        if heading_type == "BULLET":
            char = self.bullet_chars.get(str(id_ref)) if id_ref is not None else None

            if char is None:
                return None

            return {
                "label_kind": "bullet",
                "bullet_id": str(id_ref),
                "text": char,
                # 사설 사용 영역(Wingdings 등) 문자는 폰트가 없으면 렌더링되지 않는다.
                # 계층 판정은 글리프가 아니라 bullet_id를 기준으로 하는 것이 안전하다.
                "is_private_use": _is_private_use(char),
                "level": level,
            }

        if heading_type in ("OUTLINE", "NUMBER"):
            heads = self.numbering_para_heads.get(str(id_ref)) if id_ref is not None else None

            if not heads:
                return None

            head = heads.get(str(level))

            if head is None:
                return None

            return {
                "label_kind": "number",
                "numbering_id": str(id_ref),
                # "^1." 같은 형식 문자열. 실제 순번 치환은 문서 순회 상태가 필요하므로
                # 여기서는 형식만 보존한다.
                "text": head.get("text"),
                "num_format": head.get("num_format"),
                "start": head.get("start"),
                "is_private_use": False,
                "level": level,
            }

        return None
