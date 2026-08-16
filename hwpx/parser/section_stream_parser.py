#================================================
# section_stream_parser.py
# section*.xml 전체 요소를 XML 문서 순서대로 RawNode로 수집한다.
#
# SectionParser(표 전용)와 달리 hp:p / hp:tbl / hp:pic / 도형 /
# hp:ctrl(머리말/꼬리말/각주) / hp:caption / secPr을 모두 수집 대상으로 한다.
# 이 단계는 판정을 하지 않는다. 판정(role/depth)은 hwpx.analysis 쪽 책임이다.
#================================================

from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


class SectionStreamParser:
    """
    section*.xml의 최상위 hp:p를 문서 순서대로 순회하면서
    문단/표/이미지/도형/컨트롤을 RawNode(dict)로 방출한다.

    RawNode 공통 필드:
    - node_type          : paragraph | table | image | shape | shape_group |
                           caption | header | footer | footnote | endnote |
                           control | section_control | unknown_object
    - section_index      : 섹션 번호
    - xml_order_index    : 문서 전역 등장 순서 (섹션 간 누적)
    - paragraph_index    : 소속 최상위 hp:p의 섹션 내 순서
    - source_xml_path    : 원본 위치 표기 문자열
    - attrs              : 원본 XML 속성 (local name 정규화)
    """

    # 표를 제외한 개체 요소 local name
    _SHAPE_TAGS = frozenset({
        "rect", "ellipse", "polygon", "line", "arc", "curve",
        "connectLine", "textart",
    })
    _OBJECT_TAGS = frozenset({"tbl", "pic", "container", "ole", "equation", "chart", "video", "compose"})

    # hp:ctrl 하위에서 독립 블록으로 승격할 요소
    _CTRL_BLOCK_TAGS = {
        "header": "header",
        "footer": "footer",
        "footNote": "footnote",
        "endNote": "endnote",
    }

    # 문단 텍스트로 합류시키는 인라인 요소.
    # hp:compose는 _OBJECT_TAGS에도 있지만 개체가 아니라 인라인 문자이므로
    # 여기서 먼저 처리한다.
    _INLINE_TEXT_TAGS = frozenset({"t", "compose", "tab", "lineBreak", "fwSpace"})

    # 텍스트 재귀 탐색을 중단할 개체 경계.
    # 이 개체들은 별도 블록으로 방출되므로 문단 텍스트에 합류시키면 이중 계상된다.
    # (표 경로는 반대로 셀 텍스트에 도형 텍스트를 포함해야 하므로 tbl만 차단한다)
    _OBJECT_BOUNDARY_TAGS = (
        (_OBJECT_TAGS | _SHAPE_TAGS | {"ctrl", "secPr"}) - {"compose"}
    )

    #------------------------------------------------
    # 진입점
    #------------------------------------------------

    @classmethod
    def parse(cls, section_sources: list[str | Path]) -> list[dict[str, Any]]:
        """
        역할: 섹션 XML 목록을 순회하며 모든 주요 요소를 RawNode 리스트로 수집한다.
        입력 데이터: section_sources(section*.xml 경로 리스트, 문서 순서로 정렬된 상태).
        출력 데이터: xml_order_index 순서의 RawNode dict 리스트.
        """
        nodes: list[dict[str, Any]] = []
        order = 0

        for section_index, section_source in enumerate(section_sources):
            section_path = Path(section_source)
            root = ET.parse(section_path).getroot()

            # SectionParser와 동일한 규칙으로 최상위 표 순번을 매겨
            # 기존 table pipeline의 table_id와 연결 가능하게 한다.
            table_index_map = cls._build_top_level_table_index_map(root)

            paragraph_index = -1

            for child in root:
                if cls._local_name(child.tag) != "p":
                    # 스펙상 sec 직계는 p 뿐이지만, 방어적으로 unknown 처리
                    nodes.append(cls._make_node(
                        node_type="unknown_object",
                        element=child,
                        section_index=section_index,
                        section_file=section_path.name,
                        xml_order_index=order,
                        paragraph_index=None,
                    ))
                    order += 1
                    continue

                paragraph_index += 1

                para_node, object_elements = cls._collect_paragraph(
                    p_element=child,
                    section_index=section_index,
                    section_file=section_path.name,
                    paragraph_index=paragraph_index,
                    xml_order_index=order,
                )
                nodes.append(para_node)
                order += 1

                for obj_element in object_elements:
                    obj_nodes = cls._emit_object_nodes(
                        element=obj_element,
                        section_index=section_index,
                        section_file=section_path.name,
                        paragraph_index=paragraph_index,
                        parent_node_id_hint=para_node["source_xml_path"],
                        table_index_map=table_index_map,
                        start_order=order,
                    )
                    nodes.extend(obj_nodes)
                    order += len(obj_nodes)

        return nodes

    #------------------------------------------------
    # 문단 수집
    #------------------------------------------------

    @classmethod
    def _collect_paragraph(
        cls,
        p_element,
        section_index: int,
        section_file: str,
        paragraph_index: int,
        xml_order_index: int,
    ) -> tuple[dict[str, Any], list]:
        """
        역할: 최상위 hp:p 하나에서 텍스트/run 스타일 참조를 모으고,
              run 직계 자식으로 등장하는 개체 요소를 따로 반환한다.
        출력 데이터: (paragraph RawNode, 개체 element 리스트).
        """
        attrs = cls._normalize_attrs(p_element.attrib)

        text_parts: list[str] = []
        run_char_infos: list[dict[str, Any]] = []
        object_elements: list = []
        has_sec_pr = False
        line_break_count = 0

        # hp:lineBreak 기준 줄 세그먼트 (표 셀 내부 계층화에서 재사용되는 구조)
        line_segments: list[dict[str, Any]] = [{"parts": [], "char_pr_refs": []}]

        for run in p_element:
            if cls._local_name(run.tag) != "run":
                continue

            run_char_pr = cls._normalize_attrs(run.attrib).get("charPrIDRef")
            run_text_len = 0

            for run_child in run:
                child_name = cls._local_name(run_child.tag)

                if child_name in cls._INLINE_TEXT_TAGS:
                    # hp:t 하위에 fwSpace/tab/lineBreak가 들어오는 경우가 있으므로
                    # 1단계 whitelist가 아니라 재귀 토큰 스트림으로 처리한다.
                    for token_kind, token_value in cls._iter_inline_tokens(run_child):
                        if token_kind == "break":
                            text_parts.append("\n")
                            line_break_count += 1
                            line_segments.append({"parts": [], "char_pr_refs": []})
                            continue

                        text_parts.append(token_value)
                        run_text_len += len(token_value)
                        line_segments[-1]["parts"].append(token_value)
                        if run_char_pr is not None and token_value.strip():
                            line_segments[-1]["char_pr_refs"].append(str(run_char_pr))
                    continue

                if child_name in cls._OBJECT_BOUNDARY_TAGS:
                    if child_name == "secPr":
                        has_sec_pr = True
                    object_elements.append(run_child)

            if run_char_pr is not None:
                run_char_infos.append({
                    "char_pr_id_ref": str(run_char_pr),
                    "text_length": run_text_len,
                })

        text_content = "".join(text_parts)
        line_features = cls._build_line_features(line_segments, line_break_count)

        node = cls._make_node(
            node_type="paragraph",
            element=p_element,
            section_index=section_index,
            section_file=section_file,
            xml_order_index=xml_order_index,
            paragraph_index=paragraph_index,
        )
        node.update({
            "text_content": text_content,
            "para_pr_id_ref": cls._opt_str(attrs.get("paraPrIDRef")),
            "style_id_ref": cls._opt_str(attrs.get("styleIDRef")),
            "run_char_infos": run_char_infos,
            "page_break": attrs.get("pageBreak"),
            "column_break": attrs.get("columnBreak"),
            "has_sec_pr": has_sec_pr,
            "contained_object_count": len(object_elements),
            "line_features": line_features,
            "nested_control_counts": cls._count_nested_controls(p_element),
        })

        return node, object_elements

    @classmethod
    def _iter_inline_tokens(cls, element):
        """
        역할: 인라인 요소에서 텍스트/줄바꿈 토큰을 문서 순서대로 방출한다.
              hp:t 하위에 중첩되는 fwSpace/tab/lineBreak까지 재귀로 처리하고,
              자식 요소의 tail 텍스트도 빠뜨리지 않는다.
              개체(표/도형/이미지/컨트롤)는 별도 블록으로 방출되므로 내려가지 않는다.
        입력 데이터: element(인라인 요소 XML Element).
        출력 데이터: ("text", 문자열) 또는 ("break", None) 토큰 제너레이터.
        """
        name = cls._local_name(element.tag)

        if name in cls._OBJECT_BOUNDARY_TAGS:
            return

        if name == "compose":
            # 텍스트가 자식 hp:t가 아니라 composeText 속성에 들어있다.
            # 자식은 hp:charPr뿐이라 재귀해도 텍스트가 없으므로 여기서 끝낸다.
            compose_text = cls._normalize_attrs(element.attrib).get("composeText") or ""
            if compose_text:
                yield ("text", compose_text)
            return

        if name == "lineBreak":
            yield ("break", None)
            return

        if name == "tab":
            yield ("text", "\t")
            return

        if name == "fwSpace":
            # 전각 공백. 표 경로(TableParser._collect_element_text)와 동일하게
            # 일반 공백으로 정규화한다.
            yield ("text", " ")
            return

        if element.text:
            yield ("text", element.text)

        for child in element:
            yield from cls._iter_inline_tokens(child)
            if child.tail:
                yield ("text", child.tail)

    @classmethod
    def _count_nested_controls(cls, p_element) -> dict[str, int]:
        """
        역할: 중첩 개체(꼬리말/그리기개체/표 등) 내부에 있어 블록으로
              방출되지 않는 hp:ctrl 하위 control을 컨테이너별로 집계한다.
        출력 데이터: {"<container>/<control tag>": count} dict (없으면 빈 dict).
        """
        container_tags = (
            cls._OBJECT_TAGS
            | cls._SHAPE_TAGS
            | set(cls._CTRL_BLOCK_TAGS)
            | {"drawText"}
        )
        counts: dict[str, int] = {}

        def walk(element, container: str | None) -> None:
            for child in element:
                name = cls._local_name(child.tag)
                if name == "ctrl":
                    for ctrl_child in child:
                        child_name = cls._local_name(ctrl_child.tag)
                        if child_name in cls._CTRL_BLOCK_TAGS:
                            # header/footer 등 승격 대상은 최상위 문단의 run 직계
                            # ctrl일 때만 블록으로 승격된다. 개체 내부에 있으면
                            # blocks 레지스트리에 남지 않으므로 그 사실을 집계한다.
                            # (표 셀 안에 있는 것은 TableParser가 table_control로
                            #  수집하지만, 여기 집계 대상은 blocks 레지스트리다.)
                            if container is not None:
                                key = f"{container}/{child_name}"
                                counts[key] = counts.get(key, 0) + 1
                            walk(ctrl_child, child_name)
                            continue
                        if container is not None:
                            key = f"{container}/{child_name}"
                            counts[key] = counts.get(key, 0) + 1
                    continue
                next_container = name if name in container_tags else container
                walk(child, next_container)

        walk(p_element, None)
        return counts

    @classmethod
    def _build_line_features(
        cls,
        line_segments: list[dict[str, Any]],
        line_break_count: int,
    ) -> dict[str, Any]:
        """
        lineBreak 기준 줄 단위 피처를 만든다.

        줄별 charPr 조합이 서로 다르면(line_style_variation > 0) 한 문단 안에
        제목줄+본문줄이 섞여 있을 가능성이 있으므로 depth 후보 신호로 표시한다.
        """
        segments = []
        for index, seg in enumerate(line_segments):
            text = "".join(seg["parts"]).strip()
            segments.append({
                "line_index": index,
                "text": text,
                "char_pr_refs": sorted(set(seg["char_pr_refs"])),
            })

        line_count = len(segments)
        if line_break_count == 0:
            return {
                "has_line_break": False,
                "line_break_count": 0,
                "line_count": 1,
                "line_segments": None,
                "line_style_variation": 0.0,
                "line_depth_candidate": False,
            }

        # 텍스트가 있는 줄들의 charPr 조합 다양성 (0.0 = 전부 동일)
        styled_lines = [
            tuple(seg["char_pr_refs"]) for seg in segments if seg["text"]
        ]
        distinct = len(set(styled_lines))
        variation = (
            (distinct - 1) / (len(styled_lines) - 1)
            if len(styled_lines) > 1 else 0.0
        )

        return {
            "has_line_break": True,
            "line_break_count": line_break_count,
            "line_count": line_count,
            "line_segments": segments,
            "line_style_variation": round(variation, 2),
            "line_depth_candidate": variation > 0.0,
        }

    #------------------------------------------------
    # 개체 수집
    #------------------------------------------------

    @classmethod
    def _emit_object_nodes(
        cls,
        element,
        section_index: int,
        section_file: str,
        paragraph_index: int,
        parent_node_id_hint: str,
        table_index_map: dict,
        start_order: int,
    ) -> list[dict[str, Any]]:
        """
        역할: run 직계 개체 요소 하나를 RawNode(들)로 변환한다.
              개체에 hp:caption이 붙어 있으면 caption RawNode를 추가로 방출한다.
        """
        name = cls._local_name(element.tag)
        nodes: list[dict[str, Any]] = []
        order = start_order

        def base(node_type: str, elem) -> dict[str, Any]:
            node = cls._make_node(
                node_type=node_type,
                element=elem,
                section_index=section_index,
                section_file=section_file,
                xml_order_index=order,
                paragraph_index=paragraph_index,
            )
            node["anchor_paragraph_path"] = parent_node_id_hint
            node["anchor_info"] = cls._extract_anchor_info(elem)
            return node

        if name == "secPr":
            node = base("section_control", element)
            node["page_pr"] = cls._extract_page_pr(element)
            nodes.append(node)

        elif name == "ctrl":
            for ctrl_child in element:
                child_name = cls._local_name(ctrl_child.tag)
                block_type = cls._CTRL_BLOCK_TAGS.get(child_name)

                if block_type is not None:
                    node = base(block_type, ctrl_child)
                    node["text_content"] = cls._collapse_ws(
                        "".join(ctrl_child.itertext())
                    )
                    nodes.append(node)
                else:
                    node = base("control", ctrl_child)
                    node["control_type"] = child_name
                    nodes.append(node)
                order = start_order + len(nodes)

        elif name == "tbl":
            node = base("table", element)
            node["xml_table_id"] = cls._opt_str(
                cls._normalize_attrs(element.attrib).get("id")
            )
            node["table_index"] = table_index_map.get(id(element))
            nodes.append(node)
            order = start_order + len(nodes)
            nodes.extend(cls._emit_caption_nodes(
                element, base, order_offset=order,
            ))

        elif name == "pic":
            node = base("image", element)
            node["binary_item_id_ref"] = cls._find_descendant_attr(
                element, "img", "binaryItemIDRef", skip_tags={"tbl"},
            )
            node["size"] = cls._extract_size(element)
            nodes.append(node)
            order = start_order + len(nodes)
            nodes.extend(cls._emit_caption_nodes(
                element, base, order_offset=order,
            ))

        elif name == "container":
            node = base("shape_group", element)
            node["child_object_summary"] = cls._summarize_children(element)
            node["text_content"] = cls._collapse_ws(
                cls._object_inner_text(element)
            )
            nodes.append(node)
            order = start_order + len(nodes)
            nodes.extend(cls._emit_caption_nodes(
                element, base, order_offset=order,
            ))

        elif name in cls._SHAPE_TAGS:
            node = base("shape", element)
            node["object_type"] = name
            node["text_content"] = cls._collapse_ws(
                cls._object_inner_text(element)
            )
            node["size"] = cls._extract_size(element)
            nodes.append(node)
            order = start_order + len(nodes)
            nodes.extend(cls._emit_caption_nodes(
                element, base, order_offset=order,
            ))

        elif name in cls._OBJECT_TAGS:
            node = base("unknown_object", element)
            node["object_type"] = name
            node["text_content"] = cls._collapse_ws(
                cls._object_inner_text(element)
            )
            nodes.append(node)

        else:
            node = base("unknown_object", element)
            node["object_type"] = name
            nodes.append(node)

        return nodes

    @classmethod
    def _emit_caption_nodes(cls, element, base_factory, order_offset: int) -> list[dict[str, Any]]:
        """개체 직계 하위 hp:caption을 caption RawNode로 방출한다."""
        nodes = []
        for child in element:
            if cls._local_name(child.tag) != "caption":
                continue
            node = base_factory("caption", child)
            node["xml_order_index"] = order_offset + len(nodes)
            node["text_content"] = cls._collapse_ws("".join(child.itertext()))
            node["caption_attrs"] = cls._normalize_attrs(child.attrib)
            nodes.append(node)
        return nodes

    #------------------------------------------------
    # 최상위 표 순번 매핑 (SectionParser와 동일 규칙)
    #------------------------------------------------

    @classmethod
    def _build_top_level_table_index_map(cls, root) -> dict:
        """조상에 tbl이 없는 hp:tbl들에 문서 순서 기준 table_index를 부여한다."""
        parent_map = {
            child: parent
            for parent in root.iter()
            for child in list(parent)
        }

        def has_ancestor_tbl(elem) -> bool:
            parent = parent_map.get(elem)
            while parent is not None:
                if cls._local_name(parent.tag) == "tbl":
                    return True
                parent = parent_map.get(parent)
            return False

        index_map: dict = {}
        table_index = 0
        for elem in root.iter():
            if cls._local_name(elem.tag) != "tbl":
                continue
            if has_ancestor_tbl(elem):
                continue
            index_map[id(elem)] = table_index
            table_index += 1

        return index_map

    #------------------------------------------------
    # 개체 부가 정보 추출
    #------------------------------------------------

    @classmethod
    def _extract_anchor_info(cls, element) -> dict[str, Any]:
        """hp:pos / 요소 속성에서 인라인·부동 배치 정보를 추출한다."""
        attrs = cls._normalize_attrs(element.attrib)
        info: dict[str, Any] = {
            "z_order": attrs.get("zOrder"),
            "text_wrap": attrs.get("textWrap"),
            "text_flow": attrs.get("textFlow"),
            "treat_as_char": None,
            "anchor_type": None,
            "horz_offset": None,
            "vert_offset": None,
        }

        for child in element:
            if cls._local_name(child.tag) != "pos":
                continue
            pos_attrs = cls._normalize_attrs(child.attrib)
            treat = pos_attrs.get("treatAsChar")
            info["treat_as_char"] = treat
            info["horz_offset"] = pos_attrs.get("horzOffset")
            info["vert_offset"] = pos_attrs.get("vertOffset")
            break

        if info["treat_as_char"] is not None:
            is_inline = str(info["treat_as_char"]).lower() in ("true", "1")
            info["anchor_type"] = "inline" if is_inline else "floating"

        return info

    @classmethod
    def _extract_size(cls, element) -> dict[str, Any] | None:
        """hp:sz 또는 hc:curSz/orgSz에서 크기 정보를 추출한다."""
        for tag in ("sz", "curSz", "orgSz"):
            for child in element:
                if cls._local_name(child.tag) != tag:
                    continue
                attrs = cls._normalize_attrs(child.attrib)
                return {
                    "width": attrs.get("width"),
                    "height": attrs.get("height"),
                    "source_tag": tag,
                    "unit": "hwpunit",
                }
        return None

    @classmethod
    def _extract_page_pr(cls, sec_pr_element) -> dict[str, Any] | None:
        """secPr 하위 pagePr(용지 크기/여백)를 추출한다."""
        for elem in sec_pr_element.iter():
            if cls._local_name(elem.tag) != "pagePr":
                continue
            attrs = cls._normalize_attrs(elem.attrib)
            margin = None
            for child in elem:
                if cls._local_name(child.tag) == "margin":
                    margin = cls._normalize_attrs(child.attrib)
                    break
            return {"attrs": attrs, "margin": margin}
        return None

    @classmethod
    def _summarize_children(cls, container_element) -> dict[str, int]:
        """container(묶음 개체) 내부 개체 종류별 개수를 요약한다."""
        summary: dict[str, int] = {}
        for elem in container_element.iter():
            if elem is container_element:
                continue
            name = cls._local_name(elem.tag)
            if name in cls._OBJECT_TAGS or name in cls._SHAPE_TAGS:
                summary[name] = summary.get(name, 0) + 1
        return summary

    @classmethod
    def _object_inner_text(cls, element) -> str:
        """
        개체 내부 텍스트를 추출한다. 내부 tbl 텍스트는 표 파이프라인 소관이므로 제외한다.
        hp:compose(글자 겹치기, 원문자/사각문자 마커)는 텍스트가 <hp:t> 자식이 아니라
        composeText 속성에 들어있으므로 별도로 읽는다.
        """
        parts: list[str] = []

        def emit_compose(elem) -> bool:
            if cls._local_name(elem.tag) != "compose":
                return False
            compose_text = cls._normalize_attrs(elem.attrib).get("composeText")
            if compose_text:
                parts.append(compose_text)
            return True

        emit_compose(element)

        def walk(elem):
            for child in elem:
                if cls._local_name(child.tag) == "tbl":
                    continue
                if emit_compose(child):
                    continue
                if cls._local_name(child.tag) == "t":
                    # 문단 경로와 동일하게 fwSpace/tab/lineBreak를 문자로 복원한다
                    parts.append("".join(
                        value if kind == "text" else "\n"
                        for kind, value in cls._iter_inline_tokens(child)
                    ))
                else:
                    walk(child)

        walk(element)
        return " ".join(p for p in parts if p)

    #------------------------------------------------
    # RawNode 공통 생성
    #------------------------------------------------

    @classmethod
    def _make_node(
        cls,
        node_type: str,
        element,
        section_index: int,
        section_file: str,
        xml_order_index: int,
        paragraph_index: int | None,
    ) -> dict[str, Any]:
        local = cls._local_name(element.tag)
        if paragraph_index is not None:
            path = f"Contents/{section_file}#hp:p[{paragraph_index}]"
            if local != "p":
                path = f"{path}/hp:{local}"
        else:
            path = f"Contents/{section_file}#hp:{local}"

        return {
            "node_type": node_type,
            "source_element": f"hp:{local}",
            "source_xml_path": path,
            "section_index": section_index,
            "xml_order_index": xml_order_index,
            "paragraph_index": paragraph_index,
            "attrs": cls._normalize_attrs(element.attrib),
        }

    #------------------------------------------------
    # 유틸
    #------------------------------------------------

    @staticmethod
    def _local_name(tag: str) -> str:
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    @staticmethod
    def _normalize_attrs(attrs) -> dict[str, Any]:
        return {
            str(key).split("}", 1)[-1] if "}" in str(key) else str(key): value
            for key, value in dict(attrs).items()
        }

    @staticmethod
    def _opt_str(value) -> str | None:
        return None if value is None else str(value)

    @staticmethod
    def _collapse_ws(text: str) -> str:
        return " ".join(text.split())

    @classmethod
    def _find_descendant_attr(
        cls,
        element,
        target_tag: str,
        target_attr: str,
        skip_tags: set[str] | None = None,
    ):
        """skip_tags 내부로는 내려가지 않으면서 첫 target_tag@target_attr 값을 찾는다."""
        skip = skip_tags or set()

        def walk(elem):
            for child in elem:
                name = cls._local_name(child.tag)
                if name in skip:
                    continue
                if name == target_tag:
                    value = cls._normalize_attrs(child.attrib).get(target_attr)
                    if value is not None:
                        return str(value)
                found = walk(child)
                if found is not None:
                    return found
            return None

        return walk(element)
