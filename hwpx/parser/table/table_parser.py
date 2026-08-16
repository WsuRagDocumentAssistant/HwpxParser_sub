#================================================
# table/table_parser.py
#================================================

from __future__ import annotations

from typing import Any

from ...document.table import Table
from ...document.table.elements.table_row import TableRow
from ...document.table.elements.table_cell import ImageInfo, TableCell, TableParagraph, TableRun


class TableParser:
    """
    hp:tbl XML element를 Table 객체로 변환하는 파서.
    """

    @classmethod
    def parse(
        cls,
        tbl_element,
        section_index: int,
        table_index: int,
        is_nested: bool = False,
        parent_table_id: str | None = None,
        parent_cell_id: str | None = None,
    ) -> Table:
        """
        역할: 하나의 hp:tbl XML 요소를 내부 Table 객체로 변환한다.
        입력 데이터: tbl_element(hp:tbl XML 요소), section_index(섹션 번호), table_index(섹션 내 표 번호).
        출력 데이터: 행/셀/문단/run과 원본 속성이 채워진 Table 객체를 반환한다.
        """
        attrs = dict(tbl_element.attrib)

        table_id = cls._make_table_id(
            section_index=section_index,
            table_index=table_index,
            xml_id=attrs.get("id"),
        )

        if is_nested and parent_cell_id is not None:
            table_id = cls._make_nested_table_id(
                parent_cell_id=parent_cell_id,
                table_index=table_index,
                xml_id=attrs.get("id"),
            )

        # ------------------------------------------------------------
        # hp:tbl의 직접 자식 태그에서 표 레벨 layout 정보 추출
        # ------------------------------------------------------------
        size_attrs = cls._get_child_attrs(tbl_element, "sz")
        pos_attrs = cls._get_child_attrs(tbl_element, "pos")
        in_margin_attrs = cls._get_child_attrs(tbl_element, "inMargin")
        out_margin_attrs = cls._get_child_attrs(tbl_element, "outMargin")

        table = Table(
            table_id=table_id,
            section_index=section_index,
            table_index=table_index,

            xml_table_id=attrs.get("id"),

            row_count=cls._to_int(attrs.get("rowCnt"), default=0),
            col_count=cls._to_int(attrs.get("colCnt"), default=0),

            cell_spacing=cls._to_int_or_none(attrs.get("cellSpacing")),

            repeat_header=cls._to_bool(attrs.get("repeatHeader")),
            page_break=attrs.get("pageBreak") not in (None, "0", "NONE", "None"),

            text_wrap=attrs.get("textWrap"),
            text_flow=attrs.get("textFlow"),

            # --------------------------------------------------------
            # hp:tbl/hp:sz
            # --------------------------------------------------------
            width=cls._to_int_or_none(size_attrs.get("width")),
            height=cls._to_int_or_none(size_attrs.get("height")),

            # --------------------------------------------------------
            # hp:tbl/hp:pos
            # --------------------------------------------------------
            pos_x=cls._to_int_or_none(pos_attrs.get("horzOffset")),
            pos_y=cls._to_int_or_none(pos_attrs.get("vertOffset")),

            treat_as_char=(
                cls._to_bool(pos_attrs.get("treatAsChar"))
                if pos_attrs.get("treatAsChar") is not None
                else None
            ),
            flow_with_text=(
                cls._to_bool(pos_attrs.get("flowWithText"))
                if pos_attrs.get("flowWithText") is not None
                else None
            ),

            # --------------------------------------------------------
            # hp:tbl/hp:inMargin
            # --------------------------------------------------------
            in_margin_left=cls._to_int_or_none(in_margin_attrs.get("left")),
            in_margin_right=cls._to_int_or_none(in_margin_attrs.get("right")),
            in_margin_top=cls._to_int_or_none(in_margin_attrs.get("top")),
            in_margin_bottom=cls._to_int_or_none(in_margin_attrs.get("bottom")),

            # --------------------------------------------------------
            # hp:tbl/hp:outMargin
            # --------------------------------------------------------
            out_margin_left=cls._to_int_or_none(out_margin_attrs.get("left")),
            out_margin_right=cls._to_int_or_none(out_margin_attrs.get("right")),
            out_margin_top=cls._to_int_or_none(out_margin_attrs.get("top")),
            out_margin_bottom=cls._to_int_or_none(out_margin_attrs.get("bottom")),

            raw_attrs=attrs,
            is_nested=is_nested,
            parent_table_id=parent_table_id,
            parent_cell_id=parent_cell_id,
        )

        table.rows = cls._parse_rows(
            tbl_element=tbl_element,
            table_id=table.table_id,
            section_index=section_index,
        )

        return table


    @classmethod
    def _parse_rows(
        cls,
        tbl_element,
        table_id: str,
        section_index: int,
    ) -> list[TableRow]:
        """
        역할: hp:tbl의 직접 자식 hp:tr 요소들을 TableRow 리스트로 변환한다.
        입력 데이터: tbl_element(hp:tbl XML 요소), table_id(부모 표 내부 ID).
        출력 데이터: XML 순서대로 정렬된 TableRow 리스트를 반환한다.
        """
        rows: list[TableRow] = []

        tr_elements = [
            child for child in list(tbl_element)
            if cls._local_name(child.tag) == "tr"
        ]

        for row_index, tr_element in enumerate(tr_elements):
            row_id = f"{table_id}_row{row_index}"

            row = TableRow(
                row_id=row_id,
                table_id=table_id,
                row_index=row_index,
                xml_order_index=row_index,
                raw_attrs=dict(tr_element.attrib),
            )

            row.cells = cls._parse_cells(
                tr_element=tr_element,
                table_id=table_id,
                row_id=row_id,
                section_index=section_index,
            )

            # row 내부 cellAddr@rowAddr 대표값 저장
            if row.cells and row.cells[0].row_addr is not None:
                row.declared_row_addr = row.cells[0].row_addr

            rows.append(row)

        return rows

    @classmethod
    def _parse_cells(
        cls,
        tr_element,
        table_id: str,
        row_id: str,
        section_index: int,
    ) -> list[TableCell]:
        """
        역할: hp:tr의 직접 자식 hp:tc 요소들을 TableCell 리스트로 변환한다.
        입력 데이터: tr_element(hp:tr XML 요소), table_id(부모 표 ID), row_id(부모 행 ID).
        출력 데이터: 좌표/병합/크기/문단/run 정보가 채워진 TableCell 리스트를 반환한다.
        """
        cells: list[TableCell] = []

        tc_elements = [
            child for child in list(tr_element)
            if cls._local_name(child.tag) == "tc"
        ]

        for cell_index, tc_element in enumerate(tc_elements):
            attrs = dict(tc_element.attrib)

            cell_addr = cls._find_first_child(tc_element, "cellAddr")
            cell_span = cls._find_first_child(tc_element, "cellSpan")
            cell_sz = cls._find_first_child(tc_element, "cellSz")
            cell_margin = cls._find_first_child(tc_element, "cellMargin")
            sub_list = cls._find_first_child(tc_element, "subList")

            row_addr = None
            col_addr = None

            if cell_addr is not None:
                row_addr = cls._to_int_or_none(cell_addr.attrib.get("rowAddr"))
                col_addr = cls._to_int_or_none(cell_addr.attrib.get("colAddr"))

            row_span = 1
            col_span = 1

            if cell_span is not None:
                row_span = cls._to_int(cell_span.attrib.get("rowSpan"), default=1)
                col_span = cls._to_int(cell_span.attrib.get("colSpan"), default=1)

            width = None
            height = None

            if cell_sz is not None:
                width = cls._to_int_or_none(cell_sz.attrib.get("width"))
                height = cls._to_int_or_none(cell_sz.attrib.get("height"))

            margin_left = None
            margin_right = None
            margin_top = None
            margin_bottom = None

            if cell_margin is not None:
                margin_left = cls._to_int_or_none(cell_margin.attrib.get("left"))
                margin_right = cls._to_int_or_none(cell_margin.attrib.get("right"))
                margin_top = cls._to_int_or_none(cell_margin.attrib.get("top"))
                margin_bottom = cls._to_int_or_none(cell_margin.attrib.get("bottom"))

            sublist_attrs: dict[str, Any] = {}

            if sub_list is not None:
                sublist_attrs = dict(sub_list.attrib)

            cell_id = cls._make_cell_id(
                table_id=table_id,
                cell_index=cell_index,
                row_addr=row_addr,
                col_addr=col_addr,
            )

            cell = TableCell(
                cell_id=cell_id,
                table_id=table_id,
                row_id=row_id,
                cell_index=cell_index,

                name=attrs.get("name"),
                header=cls._to_bool(attrs.get("header")),
                has_margin=cls._to_bool(attrs.get("hasMargin")),
                protect=cls._to_bool(attrs.get("protect")),
                editable=cls._to_bool(attrs.get("editable")),
                dirty=cls._to_bool(attrs.get("dirty")),

                row_addr=row_addr,
                col_addr=col_addr,
                row_span=row_span,
                col_span=col_span,

                width=width,
                height=height,

                margin_left=margin_left,
                margin_right=margin_right,
                margin_top=margin_top,
                margin_bottom=margin_bottom,

                sublist_raw_attrs=sublist_attrs,
                sublist_id=sublist_attrs.get("id"),
                sublist_text_direction=sublist_attrs.get("textDirection"),
                sublist_line_wrap=sublist_attrs.get("lineWrap"),
                sublist_vert_align=sublist_attrs.get("vertAlign"),
                sublist_link_list_id_ref=sublist_attrs.get("linkListIDRef"),
                sublist_link_list_next_id_ref=sublist_attrs.get("linkListNextIDRef"),
                sublist_text_width=cls._to_int_or_none(sublist_attrs.get("textWidth")),
                sublist_text_height=cls._to_int_or_none(sublist_attrs.get("textHeight")),
                sublist_has_text_ref=cls._to_bool(sublist_attrs.get("hasTextRef")),
                sublist_has_num_ref=cls._to_bool(sublist_attrs.get("hasNumRef")),

                raw_attrs=attrs,
            )

            cell.paragraphs = cls._parse_paragraphs(
                tc_element=tc_element,
                cell_id=cell.cell_id,
            )

            cell.images = cls._parse_images(
                tc_element=tc_element,
                table_id=table_id,
                cell_id=cell.cell_id,
            )

            cell.draw_objects = cls._parse_draw_objects(
                tc_element=tc_element,
                cell_id=cell.cell_id,
            )

            cell.captions = cls._parse_captions(
                tc_element=tc_element,
                cell_id=cell.cell_id,
            )

            cell.controls = cls._parse_cell_controls(
                tc_element=tc_element,
                cell_id=cell.cell_id,
            )

            cell.nested_tables = cls._parse_nested_tables(
                tc_element=tc_element,
                section_index=section_index,
                parent_table_id=table_id,
                parent_cell_id=cell.cell_id,
            )

            cell.text = "\n".join(
                paragraph.text
                for paragraph in cell.paragraphs
                if paragraph.text
            )

            cell.is_empty = not bool(cell.text.strip())

            cell.has_image = len(cell.images) > 0

            cell.has_caption = len(cell.captions) > 0

            cell.has_field = any(
                run.has_field
                for paragraph in cell.paragraphs
                for run in paragraph.runs
            )

            cell.has_shape = any(
                run.has_shape
                for paragraph in cell.paragraphs
                for run in paragraph.runs
            )

            cells.append(cell)

        return cells

    @classmethod
    def _parse_images(
        cls,
        tc_element,
        table_id: str,
        cell_id: str,
    ) -> list[ImageInfo]:
        images: list[ImageInfo] = []
        seen_refs: set[tuple[Any, ...]] = set()

        for image_element in cls._find_image_elements(tc_element):
            attrs = cls._extract_image_attrs(image_element)
            image_key = cls._make_image_key(attrs)

            if image_key in seen_refs:
                continue

            seen_refs.add(image_key)

            images.append(
                ImageInfo(
                    image_id=f"{cell_id}_img{len(images)}",
                    parent_table_id=table_id,
                    parent_cell_id=cell_id,
                    binary_item_id_ref=attrs.get("binaryItemIDRef"),
                    href=attrs.get("href") or attrs.get("xlink:href"),
                    ref_id=attrs.get("refID"),
                    width=cls._to_int_or_none(attrs.get("width")),
                    height=cls._to_int_or_none(attrs.get("height")),
                    raw_attrs=attrs,
                )
            )

        return images

    # 셀 내부 그리기 개체로 수집하는 요소 local name (이미지 pic은 별도 수집)
    _DRAW_OBJECT_TAGS = frozenset({
        "container", "rect", "ellipse", "polygon", "line", "arc", "curve",
        "connectLine", "textart", "ole", "equation", "chart", "video",
    })

    @classmethod
    def _parse_draw_objects(
        cls,
        tc_element,
        cell_id: str,
    ) -> list[dict[str, Any]]:
        """
        역할: 셀 직속(중첩 tbl 내부 제외) 최상위 그리기 개체를 수집한다.
              개체 내부 텍스트(drawText)는 셀 paragraphs가 원본이므로
              여기서는 개체 정체성과 참고용 텍스트만 기록한다.
        출력 데이터: {object_id, object_type, draw_text, child_pic_count} dict 리스트.
        """
        draw_objects: list[dict[str, Any]] = []

        def inner_text(elem) -> str:
            parts: list[str] = []

            def walk_text(e) -> None:
                for child in e:
                    name = cls._local_name(child.tag)
                    if name == "tbl":
                        continue
                    if name == "t":
                        parts.append("".join(child.itertext()))
                    else:
                        walk_text(child)

            walk_text(elem)
            return " ".join(p.strip() for p in parts if p.strip())

        def count_pics(elem) -> int:
            count = 0
            for child in elem:
                name = cls._local_name(child.tag)
                if name == "tbl":
                    continue
                if name == "pic":
                    count += 1
                    continue
                count += count_pics(child)
            return count

        def visit(element) -> None:
            for child in list(element):
                name = cls._local_name(child.tag)
                if name == "tbl":
                    continue
                if name in cls._DRAW_OBJECT_TAGS:
                    # 최상위 개체만 1개로 수집한다 (내부 개체는 하위 요약으로만)
                    draw_objects.append({
                        "object_id": f"{cell_id}_obj{len(draw_objects)}",
                        "object_type": name,
                        "draw_text": inner_text(child) or None,
                        "child_pic_count": count_pics(child),
                    })
                    continue
                visit(child)

        visit(tc_element)
        return draw_objects

    # hp:ctrl 하위에서 셀 본문이 아닌 것으로 분리하는 요소.
    # SectionStreamParser._CTRL_BLOCK_TAGS와 같은 집합이며,
    # 본문 경로에서 독립 블록으로 승격되는 것들과 일치시킨다.
    _CELL_CONTROL_TAGS = {
        "header": "header",
        "footer": "footer",
        "footNote": "footnote",
        "endNote": "endnote",
    }

    @classmethod
    def _parse_cell_controls(
        cls,
        tc_element,
        cell_id: str,
    ) -> list[dict[str, Any]]:
        """
        역할: 셀 내부 hp:ctrl 하위의 머리말/꼬리말/각주/미주를 별도 엔티티로 수집한다.
              중첩 표 내부는 그 표의 셀 소관이므로 내려가지 않는다.
        입력 데이터: tc_element(hp:tc XML 요소), cell_id(부모 셀 ID).
        출력 데이터: {control_id, control_type, text, source_element} 리스트.

        배경: 이들은 페이지 장식이라 셀 본문 텍스트에 섞이면 표 데이터 값과
              구분할 수 없다. 본문 경로(SectionStreamParser)는 최상위 문단의
              hp:ctrl만 블록으로 승격하므로, 셀 안에 있는 것은 어느 레지스트리에도
              남지 않고 셀 텍스트만 오염시키고 있었다.
        """
        controls: list[dict[str, Any]] = []

        def visit(element) -> None:
            for child in list(element):
                name = cls._local_name(child.tag)

                if name == "tbl":
                    continue

                control_type = cls._CELL_CONTROL_TAGS.get(name)

                if control_type is not None:
                    parts: list[str] = []

                    # 자기 자신을 넘기면 _collect_element_text가 즉시 반환하므로
                    # 자식부터 수집한다.
                    for control_child in list(child):
                        cls._collect_element_text(control_child, parts)

                    controls.append({
                        "control_id": f"{cell_id}_ctrl{len(controls)}",
                        "control_type": control_type,
                        "text": "".join(parts).strip(),
                        "source_element": f"hp:{name}",
                    })
                    continue

                visit(child)

        visit(tc_element)

        return controls

    @classmethod
    def _parse_captions(
        cls,
        tc_element,
        cell_id: str,
    ) -> list[dict[str, Any]]:
        """
        역할: 셀 내부 개체(hp:pic 등)에 붙은 hp:caption을 별도 엔티티로 수집한다.
              중첩 표 내부는 그 표의 셀 소관이므로 내려가지 않는다.
        입력 데이터: tc_element(hp:tc XML 요소), cell_id(부모 셀 ID).
        출력 데이터: {caption_id, text, parent_object_type, binary_item_id_ref, raw_attrs} 리스트.

        주의: 부모 개체와의 연결은 생성 id가 아니라 binaryItemIDRef로 건다.
              _parse_images가 중복 이미지를 dedup하기 때문에 image_id 순번과
              pic 등장 순번이 어긋날 수 있다.
        """
        captions: list[dict[str, Any]] = []

        def visit(element) -> None:
            for child in list(element):
                name = cls._local_name(child.tag)

                if name == "tbl":
                    continue

                if name == "caption":
                    parent_name = cls._local_name(element.tag)
                    parts: list[str] = []

                    # caption 자신을 넘기면 _collect_element_text가 즉시 반환하므로
                    # 자식부터 수집한다.
                    for caption_child in list(child):
                        cls._collect_element_text(caption_child, parts)

                    captions.append({
                        "caption_id": f"{cell_id}_cap{len(captions)}",
                        "text": "".join(parts).strip(),
                        "parent_object_type": parent_name,
                        "binary_item_id_ref": cls._find_direct_binary_item_ref(element),
                        "raw_attrs": cls._normalize_attrs(child.attrib),
                    })
                    continue

                visit(child)

        visit(tc_element)

        return captions

    @classmethod
    def _find_direct_binary_item_ref(cls, element) -> str | None:
        """
        역할: 개체(hp:pic 등) 하위 hc:img의 binaryItemIDRef를 찾는다.
              caption을 어느 이미지의 설명인지 연결하는 안정적인 키다.
        입력 데이터: element(개체 XML 요소).
        출력 데이터: binaryItemIDRef 문자열 또는 None.
        """
        for descendant in element.iter():
            if cls._local_name(descendant.tag) != "img":
                continue

            value = cls._normalize_attrs(descendant.attrib).get("binaryItemIDRef")

            if value not in (None, ""):
                return str(value)

        return None

    @classmethod
    def _make_image_key(cls, attrs: dict[str, Any]) -> tuple[Any, ...]:
        binary_item_id_ref = attrs.get("binaryItemIDRef")
        if binary_item_id_ref not in (None, ""):
            return ("binaryItemIDRef", binary_item_id_ref)

        href = attrs.get("href") or attrs.get("xlink:href")
        if href not in (None, ""):
            return ("href", href)

        ref_id = attrs.get("refID")
        if ref_id not in (None, ""):
            return ("refID", ref_id)

        image_id = attrs.get("id")
        if image_id not in (None, ""):
            return ("id", image_id)

        instid = attrs.get("instid")
        if instid not in (None, ""):
            return ("instid", instid)

        return (
            "size",
            attrs.get("width"),
            attrs.get("height"),
        )

    @classmethod
    def _find_image_elements(cls, tc_element) -> list:
        image_elements = []

        def visit(element) -> None:
            for child in list(element):
                name = cls._local_name(child.tag)

                if name == "tbl":
                    continue

                if name == "pic":
                    image_elements.append(child)
                    continue

                visit(child)

        visit(tc_element)

        return image_elements

    @classmethod
    def _extract_image_attrs(cls, image_element) -> dict[str, Any]:
        """
        hp:pic 이미지 객체에서 속성을 추출한다.

        주의:
        - binaryItemIDRef, href 등은 hp:pic attribute에 있음
        - width, height는 보통 hp:pic/hp:sz 자식 태그에 있음
        """

        normalized_attrs = cls._normalize_attrs(image_element.attrib)

        # hp:pic 하위 hp:sz에서 이미지 크기 추출
        size_element = cls._find_direct_child_by_local_name(image_element, "sz")

        if size_element is not None:
            size_attrs = cls._normalize_attrs(size_element.attrib)

            for key in ("width", "height", "widthRelTo", "heightRelTo", "protect"):
                if size_attrs.get(key) not in (None, ""):
                    normalized_attrs[key] = size_attrs.get(key)

            # 원본 size attribute도 보존하고 싶으면 추가
            normalized_attrs["size_raw_attrs"] = size_attrs

        for child in image_element.iter():
            if child is image_element:
                continue

            child_attrs = cls._normalize_attrs(child.attrib)

            for key in ("binaryItemIDRef", "href", "xlink:href", "refID"):
                if normalized_attrs.get(key) in (None, "") and child_attrs.get(key) not in (None, ""):
                    normalized_attrs[key] = child_attrs.get(key)

        return normalized_attrs

    @classmethod
    def _parse_nested_tables(
        cls,
        tc_element,
        section_index: int,
        parent_table_id: str,
        parent_cell_id: str,
    ) -> list[Table]:
        # 머리말/꼬리말/각주 안에 들어 있는 표를 표시하기 위한 소유자 맵.
        # HWPX는 머리말 내용을 표로 짜는 경우가 있고, 그 표는 본문 데이터 표와
        # 구조가 같아서 표시하지 않으면 구분할 수 없다.
        owner_by_element = cls._map_control_owned_tables(tc_element)

        nested_tables: list[Table] = []

        for nested_index, tbl_element in enumerate(
            cls._find_direct_nested_tables(tc_element)
        ):
            nested_table = cls.parse(
                tbl_element=tbl_element,
                section_index=section_index,
                table_index=nested_index,
                is_nested=True,
                parent_table_id=parent_table_id,
                parent_cell_id=parent_cell_id,
            )
            nested_table.owner_control_type = owner_by_element.get(id(tbl_element))
            nested_tables.append(nested_table)

        return nested_tables

    @classmethod
    def _map_control_owned_tables(cls, tc_element) -> dict[int, str]:
        """
        역할: 셀 안에서 머리말/꼬리말/각주/미주에 소속된 tbl 요소를 찾아
              {id(tbl element): control_type} 맵을 만든다.
        입력 데이터: tc_element(hp:tc XML 요소).
        출력 데이터: 소유자가 있는 표만 담은 dict (없으면 빈 dict).
        """
        owner_by_element: dict[int, str] = {}

        def visit(element, owner: str | None) -> None:
            for child in list(element):
                name = cls._local_name(child.tag)
                control_type = cls._CELL_CONTROL_TAGS.get(name)
                next_owner = control_type if control_type is not None else owner

                if name == "tbl":
                    if next_owner is not None:
                        owner_by_element[id(child)] = next_owner
                    # 표 내부는 그 표의 셀 소관이므로 더 내려가지 않는다
                    continue

                visit(child, next_owner)

        visit(tc_element, None)

        return owner_by_element

    @classmethod
    def _find_direct_nested_tables(cls, tc_element) -> list:
        parent_map = {
            child: parent
            for parent in tc_element.iter()
            for child in list(parent)
        }

        return [
            elem for elem in tc_element.iter()
            if cls._local_name(elem.tag) == "tbl"
            and not cls._has_ancestor_tbl_before(elem, tc_element, parent_map)
        ]

    @classmethod
    def _has_ancestor_tbl_before(cls, element, stop_element, parent_map) -> bool:
        parent = parent_map.get(element)

        while parent is not None and parent is not stop_element:
            if cls._local_name(parent.tag) == "tbl":
                return True

            parent = parent_map.get(parent)

        return False

    @classmethod
    def _parse_paragraphs(
        cls,
        tc_element,
        cell_id: str,
    ) -> list[TableParagraph]:
        """
        역할: 셀 내부 subList의 hp:p 요소들을 TableParagraph 리스트로 변환한다.
        입력 데이터: tc_element(hp:tc XML 요소), cell_id(부모 셀 ID).
        출력 데이터: 문단 속성, run 목록, 문단 텍스트가 채워진 TableParagraph 리스트를 반환한다.
        """
        paragraphs: list[TableParagraph] = []

        sub_list = cls._find_first_child(tc_element, "subList")

        if sub_list is None:
            return paragraphs

        p_elements = [
            child for child in list(sub_list)
            if cls._local_name(child.tag) == "p"
        ]

        for paragraph_index, p_element in enumerate(p_elements):
            attrs = dict(p_element.attrib)

            paragraph_id = f"{cell_id}_p{paragraph_index}"

            paragraph = TableParagraph(
                paragraph_id=paragraph_id,
                cell_id=cell_id,
                xml_para_id=attrs.get("id"),
                paragraph_index=paragraph_index,
                style_id_ref=attrs.get("styleIDRef"),
                para_pr_id_ref=attrs.get("paraPrIDRef"),
                raw_attrs=attrs,
            )

            paragraph.runs = cls._parse_runs(
                p_element=p_element,
                paragraph_id=paragraph.paragraph_id,
            )

            paragraph.text = "".join(run.text for run in paragraph.runs)

            paragraphs.append(paragraph)

        return paragraphs

    @classmethod
    def _parse_runs(
        cls,
        p_element,
        paragraph_id: str,
    ) -> list[TableRun]:
        """
        역할: 문단 내부 hp:run 요소들을 TableRun 리스트로 변환한다.
        입력 데이터: p_element(hp:p XML 요소), paragraph_id(부모 문단 ID).
        출력 데이터: 텍스트, charPr 참조, 이미지/필드/도형 여부가 채워진 TableRun 리스트를 반환한다.
        """
        runs: list[TableRun] = []

        run_elements = [
            child for child in list(p_element)
            if cls._local_name(child.tag) == "run"
        ]

        for run_index, run_element in enumerate(run_elements):
            attrs = dict(run_element.attrib)

            run_id = f"{paragraph_id}_run{run_index}"

            run = TableRun(
                run_id=run_id,
                paragraph_id=paragraph_id,
                run_index=run_index,
                char_pr_id_ref=attrs.get("charPrIDRef"),
                raw_attrs=attrs,
            )

            run.text = cls._extract_run_text(run_element)

            run.has_image = cls._has_descendant(run_element, "pic")
            run.has_field = (
                cls._has_descendant(run_element, "fieldBegin")
                or cls._has_descendant(run_element, "fieldEnd")
            )
            run.has_shape = (
                cls._has_descendant(run_element, "rect")
                or cls._has_descendant(run_element, "ellipse")
                or cls._has_descendant(run_element, "container")
            )

            run.has_line_break = cls._has_descendant(run_element, "lineBreak")
            run.has_tab = cls._has_descendant(run_element, "tab")
            run.has_fw_space = cls._has_descendant(run_element, "fwSpace")

            runs.append(run)

        return runs

    @classmethod
    def _extract_run_text(cls, run_element) -> str:
        """
        역할: hp:run 하위의 텍스트 관련 요소를 하나의 문자열로 평탄화한다.
        입력 데이터: run_element(hp:run XML 요소).
        출력 데이터: t/lineBreak/tab/fwSpace를 반영한 문자열을 반환한다.
        """
        parts: list[str] = []
        cls._collect_element_text(run_element, parts)
        return "".join(parts)

    @classmethod
    def _collect_element_text(cls, element, parts: list) -> None:
        name = cls._local_name(element.tag)

        if name == "tbl":
            return

        if name == "caption":
            # hp:caption은 개체(그림/표)의 설명문이지 셀 본문이 아니다.
            # 셀 텍스트에 섞으면 표 데이터 값과 구분할 수 없게 되므로
            # 여기서 끊고 _parse_captions가 별도 엔티티로 수집한다.
            return

        if name in cls._CELL_CONTROL_TAGS:
            # 머리말/꼬리말/각주/미주는 페이지 장식이지 셀 본문이 아니다.
            # 셀 텍스트에 섞이면 표 데이터 값과 구분할 수 없다.
            # _parse_cell_controls가 별도 엔티티로 수집한다.
            return

        if name == "t":
            parts.append(element.text or "")
        elif name == "lineBreak":
            parts.append("\n")
        elif name == "tab":
            parts.append("\t")
        elif name == "fwSpace":
            parts.append(" ")
        elif name == "compose":
            # hp:compose(글자 겹치기, 원문자/사각문자 마커)는 텍스트가
            # <hp:t> 자식이 아니라 composeText 속성에 들어있다.
            # 자식은 hp:charPr뿐이라 재귀해도 텍스트가 없으므로 여기서 종료한다.
            compose_text = dict(element.attrib).get("composeText")
            if compose_text:
                parts.append(compose_text)
            return

        children = list(element)
        draw_children = [
            child for child in children
            if cls._local_name(child.tag) in cls._DRAW_OBJECT_TAGS
        ]

        # 형제 그리기 개체가 2개 이상이면 XML 문서 순서가 시각적 배치 순서와
        # 다를 수 있으므로(hp:offset 기준 정렬 필요) 개체별 텍스트를 따로 모아
        # 시각적 위치(y, x) 순으로 공백 구분하여 합친다.
        if len(draw_children) < 2:
            for child in children:
                cls._collect_element_text(child, parts)
                if child.tail:
                    parts.append(child.tail)
            return

        draw_ids = {id(child) for child in draw_children}
        ordered = sorted(
            enumerate(draw_children),
            key=lambda item: cls._draw_object_sort_key(item[1]) + (item[0],),
        )

        draw_texts: list[str] = []
        for _, child in ordered:
            sub_parts: list[str] = []
            cls._collect_element_text(child, sub_parts)
            text = "".join(sub_parts).strip()
            if text:
                draw_texts.append(text)

        inserted = False
        for child in children:
            if id(child) in draw_ids:
                if not inserted and draw_texts:
                    cls._append_text_with_boundary(parts, " ".join(draw_texts))
                    inserted = True
            else:
                cls._collect_element_text(child, parts)
            if child.tail:
                parts.append(child.tail)

    @classmethod
    def _draw_object_sort_key(cls, element) -> tuple[int, int]:
        """
        역할: 그리기 개체의 시각적 정렬 키 (y, x)를 hp:offset에서 추출한다.
        출력 데이터: (y, x) 튜플. offset이 없으면 (0, 0).
        """
        offset = cls._find_first_child(element, "offset")
        if offset is None:
            return (0, 0)
        attrs = dict(offset.attrib)
        return (
            cls._to_signed_int32(attrs.get("y")),
            cls._to_signed_int32(attrs.get("x")),
        )

    @staticmethod
    def _to_signed_int32(value) -> int:
        """
        역할: HWPX 좌표 문자열을 signed int로 변환한다.
              음수 좌표가 uint32(예: 4294967253 = -43)로 저장되는 경우를 보정한다.
        """
        try:
            v = int(value)
        except (TypeError, ValueError):
            return 0
        if v >= 2**31:
            v -= 2**32
        return v

    @staticmethod
    def _append_text_with_boundary(parts: list, text: str) -> None:
        """
        역할: 앞선 텍스트와 경계가 붙지 않도록 필요 시 공백을 넣어 추가한다.
        """
        if parts:
            prev = parts[-1]
            if prev and not prev[-1].isspace():
                parts.append(" ")
        parts.append(text)

    @classmethod
    def _iter_without_nested_tables(cls, element):
        yield element

        for child in list(element):
            if cls._local_name(child.tag) == "tbl":
                continue

            yield from cls._iter_without_nested_tables(child)

    @classmethod
    def _find_first_child(cls, element, local_name: str):
        """
        역할: XML 요소의 직접 자식 중 local name이 일치하는 첫 요소를 찾는다.
        입력 데이터: element(부모 XML 요소), local_name(찾을 태그의 local name).
        출력 데이터: 찾은 자식 Element를 반환하고, 없으면 None을 반환한다.
        """
        for child in list(element):
            if cls._local_name(child.tag) == local_name:
                return child

        return None

    @classmethod
    def _has_descendant(cls, element, local_name: str) -> bool:
        """
        역할: XML 요소 자신과 모든 하위 요소 중 특정 local name 태그가 있는지 검사한다.
        입력 데이터: element(검사할 XML 요소), local_name(찾을 태그의 local name).
        출력 데이터: 하나라도 존재하면 True, 없으면 False를 반환한다.
        """
        for elem in element.iter():
            if cls._local_name(elem.tag) == local_name:
                return True

        return False

    @classmethod
    def _make_table_id(
        cls,
        section_index: int,
        table_index: int,
        xml_id: str | None,
    ) -> str:
        """
        역할: 섹션 번호, 표 번호, XML id를 조합해 내부 표 ID를 생성한다.
        입력 데이터: section_index, table_index, xml_id(선택적 hp:tbl@id).
        출력 데이터: section{n}_tbl{m} 형식의 표 ID 문자열을 반환한다.
        """
        if xml_id:
            return f"section{section_index}_tbl{table_index}_{xml_id}"

        return f"section{section_index}_tbl{table_index}"

    @classmethod
    def _make_nested_table_id(
        cls,
        parent_cell_id: str,
        table_index: int,
        xml_id: str | None,
    ) -> str:
        if xml_id:
            return f"{parent_cell_id}_nested_tbl{table_index}_{xml_id}"

        return f"{parent_cell_id}_nested_tbl{table_index}"

    @classmethod
    def _make_cell_id(
        cls,
        table_id: str,
        cell_index: int,
        row_addr: int | None,
        col_addr: int | None,
    ) -> str:
        """
        역할: 표 ID와 셀 순서/좌표를 조합해 내부 셀 ID를 생성한다.
        입력 데이터: table_id, cell_index, row_addr(선택), col_addr(선택).
        출력 데이터: 좌표가 있으면 r{row}_c{col}, 없으면 cell{index}가 포함된 셀 ID 문자열을 반환한다.
        """
        if row_addr is not None and col_addr is not None:
            return f"{table_id}_r{row_addr}_c{col_addr}"

        return f"{table_id}_cell{cell_index}"

    @classmethod
    def _local_name(cls, tag: str) -> str:
        """
        역할: XML 태그 문자열에서 네임스페이스를 제거한다.
        입력 데이터: tag(네임스페이스 포함 또는 미포함 XML 태그명).
        출력 데이터: local tag name 문자열을 반환한다.
        """
        if "}" in tag:
            return tag.rsplit("}", 1)[-1]

        if ":" in tag:
            return tag.rsplit(":", 1)[-1]

        return tag

    @classmethod
    def _normalize_attrs(cls, attrs: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}

        for key, value in dict(attrs).items():
            result[cls._local_name(str(key))] = value

        return result

    @classmethod
    def _to_int(cls, value: Any, default: int = 0) -> int:
        """
        역할: XML 속성값을 정수로 변환하고 실패 시 기본값을 사용한다.
        입력 데이터: value(원본 속성값), default(변환 실패 또는 None일 때 사용할 정수).
        출력 데이터: 변환된 int 또는 default를 반환한다.
        """
        try:
            if value is None:
                return default
            return int(value)
        except ValueError:
            return default

    @classmethod
    def _to_int_or_none(cls, value: Any) -> int | None:
        """
        역할: 선택적 XML 속성값을 정수로 변환한다.
        입력 데이터: value(원본 속성값).
        출력 데이터: 변환된 int를 반환하고, None이거나 변환 실패 시 None을 반환한다.
        """
        try:
            if value is None:
                return None
            return int(value)
        except ValueError:
            return None

    @classmethod
    def _to_bool(cls, value: Any) -> bool:
        """
        역할: HWPX XML의 boolean 계열 속성값을 bool로 해석한다.
        입력 데이터: value(원본 속성값).
        출력 데이터: "1", "true", "True", "TRUE"이면 True, 그 외에는 False를 반환한다.
        """
        return str(value) in ("1", "true", "True", "TRUE")
    



    @classmethod
    def _get_child_attrs(cls, element, child_local_name: str) -> dict[str, str]:
        """
        역할: 현재 XML 요소의 직접 자식 중 특정 local_name을 가진 태그의 속성을 반환한다.

        예:
        hp:tbl
        ├─ hp:sz
        ├─ hp:pos
        ├─ hp:inMargin
        └─ hp:outMargin

        child_local_name에 "sz"를 넣으면 hp:sz의 attribute dict를 반환한다.
        """
        child = cls._find_direct_child_by_local_name(element, child_local_name)

        if child is None:
            return {}

        return {
            cls._local_name(key): value
            for key, value in child.attrib.items()
        }


    @classmethod
    def _find_direct_child_by_local_name(cls, element, local_name: str):
        """
        현재 element의 직접 자식 중 local name이 일치하는 첫 번째 요소를 반환한다.
        """

        for child in list(element):
            if cls._local_name(child.tag) == local_name:
                return child

        return None
