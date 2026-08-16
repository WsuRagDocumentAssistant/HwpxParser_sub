# TABLE_VALUE_FLOW

## 1. 전체 흐름 한 줄 요약

```text
TableParser.parse()에서 Table 기본 속성 생성
-> TableParser._parse_rows() / _parse_cells() / _parse_paragraphs() / _parse_runs()에서 Row/Cell/Paragraph/Run 추가
-> TableParser._parse_nested_tables()에서 셀 내부 Table을 cell.nested_tables에 재귀 추가
-> TableStyleResolver.resolve()에서 Table과 TableCell의 border_fill 추가/갱신
-> TableAnalyzer.analyze()에서 validation 추가
-> table_to_dict()에서 최종 dict로 변환
```

---

## 2. Table 값 추가 흐름

| 순서 | 파일 | 함수/메서드 | 대상 객체 | 추가/갱신되는 필드 | 값의 출처 | 설명 |
| -: | -- | ------ | ----- | ---------- | ----- | -- |
| 1 | `hwpx_parser/table/table_parser.py` | `TableParser.parse()` | `Table` | `table_id` | `_make_table_id(section_index, table_index, attrs.get("id"))` | 내부 표 식별자 생성 |
| 2 | `hwpx_parser/table/table_parser.py` | `TableParser.parse()` | `Table` | `section_index`, `table_index` | `SectionParser.parse()`의 enumerate 값 | section 내 표 위치 저장 |
| 3 | `hwpx_parser/table/table_parser.py` | `TableParser.parse()` | `Table` | `xml_table_id`, `row_count`, `col_count`, `cell_spacing`, `border_fill_id_ref`, `repeat_header`, `page_break`, `text_wrap`, `text_flow`, `raw_attrs` | `hp:tbl` XML attrs | 표 XML 속성 저장 |
| 4 | `hwpx_parser/table/table_parser.py` | `TableParser.parse()` | `Table` | `rows` | `_parse_rows()` 반환값 | 표 하위 행 목록 연결 |
| 5 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_rows()` | `TableRow` | `row_id`, `table_id`, `row_index`, `xml_order_index`, `raw_attrs` | `table_id`, `enumerate(tr_elements)`, `hp:tr` attrs | 행 객체 생성 |
| 6 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_rows()` | `TableRow` | `cells` | `_parse_cells()` 반환값 | 행 하위 셀 목록 연결 |
| 7 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_rows()` | `TableRow` | `declared_row_addr` | 첫 번째 `row.cells[0].row_addr` | 첫 셀의 `rowAddr`가 있으면 행 선언 좌표로 저장 |
| 8 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_cells()` | `TableCell` | `cell_id`, `table_id`, `row_id`, `cell_index` | `_make_cell_id()`, 부모 ID, `enumerate(tc_elements)` | 셀 식별자와 위치 정보 저장 |
| 9 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_cells()` | `TableCell` | `name`, `header`, `has_margin`, `protect`, `editable`, `dirty`, `border_fill_id_ref`, `raw_attrs` | `hp:tc` attrs | 셀 XML 속성 저장 |
| 10 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_cells()` | `TableCell` | `row_addr`, `col_addr` | `hp:cellAddr@rowAddr`, `hp:cellAddr@colAddr` | 셀 시작 좌표 저장 |
| 11 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_cells()` | `TableCell` | `row_span`, `col_span` | `hp:cellSpan@rowSpan`, `hp:cellSpan@colSpan` | 병합 크기 저장, 없으면 기본값 1 |
| 12 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_cells()` | `TableCell` | `width`, `height` | `hp:cellSz@width`, `hp:cellSz@height` | 셀 크기 저장 |
| 13 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_cells()` | `TableCell` | `margin_left`, `margin_right`, `margin_top`, `margin_bottom` | `hp:cellMargin` attrs | 셀 여백 저장 |
| 14 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_cells()` | `TableCell` | `sublist_raw_attrs`, `sublist_id`, `sublist_text_direction`, `sublist_line_wrap`, `sublist_vert_align`, `sublist_link_list_id_ref`, `sublist_link_list_next_id_ref`, `sublist_text_width`, `sublist_text_height`, `sublist_has_text_ref`, `sublist_has_num_ref` | `hp:subList` attrs | 셀 내부 subList 속성 저장 |
| 15 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_cells()` | `TableCell` | `paragraphs` | `_parse_paragraphs()` 반환값 | 셀 하위 문단 목록 연결 |
| 16 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_cells()` | `TableCell` | `text` | `paragraph.text` join | 셀 전체 텍스트 구성 |
| 17 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_cells()` | `TableCell` | `is_empty`, `has_image`, `has_field`, `has_shape` | `cell.text`, 하위 `run` 플래그 | 셀 내용 상태 플래그 계산 |
| 18 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_paragraphs()` | `TableParagraph` | `paragraph_id`, `cell_id`, `xml_para_id`, `paragraph_index`, `style_id_ref`, `para_pr_id_ref`, `raw_attrs` | 부모 셀 ID, `hp:p` attrs | 문단 객체 생성 |
| 19 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_paragraphs()` | `TableParagraph` | `runs` | `_parse_runs()` 반환값 | 문단 하위 run 목록 연결 |
| 20 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_paragraphs()` | `TableParagraph` | `text` | `run.text` join | 문단 전체 텍스트 구성 |
| 21 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_runs()` | `TableRun` | `run_id`, `paragraph_id`, `run_index`, `char_pr_id_ref`, `raw_attrs` | 부모 문단 ID, `hp:run` attrs | run 객체 생성 |
| 22 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_runs()` | `TableRun` | `text` | `_extract_run_text()` | run 하위 `t`, `lineBreak`, `tab`, `fwSpace`를 문자열로 변환 |
| 23 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_runs()` | `TableRun` | `has_image`, `has_field`, `has_shape`, `has_line_break`, `has_tab`, `has_fw_space` | `_has_descendant()` | run 하위 요소 존재 여부 저장 |
| 24 | `hwpx_parser/table/table_parser.py` | `TableParser._parse_nested_tables()` | `TableCell` | `nested_tables` | 셀 내부 `hp:tbl` 요소 | 부모 셀 안의 하위 표를 `Table` 객체로 재귀 저장 |
| 25 | `hwpx_parser/table/table_parser.py` | `TableParser.parse()` | 중첩 `Table` | `is_nested`, `parent_table_id`, `parent_cell_id` | 부모 표 ID, 부모 셀 ID | 중첩 표의 부모 추적 정보 저장 |
| 26 | `hwpx_parser/table/table_style_resolver.py` | `TableStyleResolver.resolve()` | `Table` | `border_fill` | `context.get_border_fill_raw(table.border_fill_id_ref)` | 표의 `border_fill_id_ref`를 실제 `BorderFill` 객체로 연결, 중첩 표도 재귀 처리 |
| 27 | `hwpx_parser/table/table_style_resolver.py` | `TableStyleResolver.resolve()` | `TableCell` | `border_fill` | `context.get_border_fill_raw(cell.border_fill_id_ref)` | 셀의 `border_fill_id_ref`를 실제 `BorderFill` 객체로 연결 |
| 28 | `hwpx_parser/table/table_analyzer.py` | `TableAnalyzer.analyze()` | `Table` | `validation` | `TableValidation(...)` 및 검증 함수 결과 | 표 검증 결과 객체 연결, 중첩 표도 재귀 처리 |
| 29 | `tools/run_model.py` | `table_to_dict()` | `Table`, `TableRow`, `TableCell`, `TableParagraph`, `TableRun` | dict 키 구조 | 객체 속성 및 `to_jsonable()` | `tables.json` 저장용 dict로 변환 |

---

## 3. 단계별 객체 상태 변화

### Step 1. Table 생성 직후

생성 위치: `hwpx_parser/table/table_parser.py`의 `TableParser.parse()`

`Table(...)` 생성자에 직접 전달되는 값은 아래와 같다. `rows`, `validation`, `semantic`, `border_fill` 등은 생성자에 전달되지 않으며 dataclass 기본값으로 시작한다.

```python
Table(
    table_id=table_id,
    section_index=section_index,
    table_index=table_index,
    xml_table_id=attrs.get("id"),
    row_count=cls._to_int(attrs.get("rowCnt"), default=0),
    col_count=cls._to_int(attrs.get("colCnt"), default=0),
    cell_spacing=cls._to_int_or_none(attrs.get("cellSpacing")),
    border_fill_id_ref=attrs.get("borderFillIDRef"),
    repeat_header=cls._to_bool(attrs.get("repeatHeader")),
    page_break=attrs.get("pageBreak") not in (None, "0", "NONE", "None"),
    text_wrap=attrs.get("textWrap"),
    text_flow=attrs.get("textFlow"),
    raw_attrs=attrs,
)

# dataclass 기본값
table.border_fill = None
table.width = None
table.height = None
table.pos_x = None
table.pos_y = None
table.treat_as_char = None
table.flow_with_text = None
table.in_margin_left = None
table.in_margin_right = None
table.in_margin_top = None
table.in_margin_bottom = None
table.out_margin_left = None
table.out_margin_right = None
table.out_margin_top = None
table.out_margin_bottom = None
table.rows = []
table.validation = None
table.semantic = None
table.caption_candidate = None
table.note_candidate = None
table.source_candidate = None
```

### Step 2. rows 추가 후

추가 위치: `hwpx_parser/table/table_parser.py`의 `TableParser.parse()`와 `TableParser._parse_rows()`

```python
table.rows = [
    TableRow(
        row_id=f"{table_id}_row{row_index}",
        table_id=table_id,
        row_index=row_index,
        xml_order_index=row_index,
        raw_attrs=dict(tr_element.attrib),
    )
]

# TableParser._parse_rows() 내부에서 이후 갱신
row.cells = cls._parse_cells(...)

if row.cells and row.cells[0].row_addr is not None:
    row.declared_row_addr = row.cells[0].row_addr
```

### Step 3. cells 추가 후

추가 위치: `hwpx_parser/table/table_parser.py`의 `TableParser._parse_cells()`

```python
row.cells = [
    TableCell(
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
        border_fill_id_ref=attrs.get("borderFillIDRef"),
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
]

# 생성 후 추가/갱신
cell.paragraphs = cls._parse_paragraphs(...)
cell.text = "\n".join(paragraph.text for paragraph in cell.paragraphs if paragraph.text)
cell.is_empty = not bool(cell.text.strip())
cell.has_image = any(run.has_image for paragraph in cell.paragraphs for run in paragraph.runs)
cell.has_field = any(run.has_field for paragraph in cell.paragraphs for run in paragraph.runs)
cell.has_shape = any(run.has_shape for paragraph in cell.paragraphs for run in paragraph.runs)

# dataclass 기본값
cell.border_fill = None
cell.is_column_header = False
cell.is_row_header = False
cell.is_group_header = False
cell.is_data_cell = False
```

### Step 4. paragraphs/runs 추가 후

추가 위치: `hwpx_parser/table/table_parser.py`의 `TableParser._parse_paragraphs()`와 `TableParser._parse_runs()`

```python
cell.paragraphs = [
    TableParagraph(
        paragraph_id=f"{cell_id}_p{paragraph_index}",
        cell_id=cell_id,
        xml_para_id=attrs.get("id"),
        paragraph_index=paragraph_index,
        style_id_ref=attrs.get("styleIDRef"),
        para_pr_id_ref=attrs.get("paraPrIDRef"),
        raw_attrs=attrs,
    )
]

paragraph.runs = [
    TableRun(
        run_id=f"{paragraph_id}_run{run_index}",
        paragraph_id=paragraph_id,
        run_index=run_index,
        char_pr_id_ref=attrs.get("charPrIDRef"),
        raw_attrs=attrs,
    )
]

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

paragraph.text = "".join(run.text for run in paragraph.runs)
```

### Step 5. validation 추가 후

추가 위치: `hwpx_parser/table/table_analyzer.py`의 `TableAnalyzer.analyze()`

```python
table.validation = TableValidation(
    table_id=table.table_id,
    declared_row_count=table.row_count,
    declared_col_count=table.col_count,
    actual_tr_count=len(table.rows),
    actual_cell_count=len(table.cells),
)
```

검증 과정에서 아래 값이 추가 또는 갱신된다.

```python
table.validation.is_valid
table.validation.actual_max_row_count
table.validation.actual_max_col_count
table.validation.grid
table.validation.issues

table.validation.has_row_count_mismatch
table.validation.has_col_count_mismatch
table.validation.has_missing_cell_addr
table.validation.has_invalid_cell_addr
table.validation.has_out_of_range_cell
table.validation.has_row_order_mismatch
table.validation.has_invalid_cell_span
table.validation.has_duplicated_slot
table.validation.has_empty_slot
table.validation.has_missing_border_fill_ref
table.validation.has_missing_style_ref
table.validation.has_missing_para_pr_ref
table.validation.has_missing_char_pr_ref
table.validation.has_size_mismatch
table.validation.has_margin_difference
table.validation.has_empty_cell
table.validation.has_nested_object
table.validation.is_irregular
```

`grid`는 `row_count > 0`이고 `col_count > 0`일 때 `_build_grid()`에서 아래 형태의 2차원 리스트로 채워진다.

```python
grid[row][col] = {
    "row_index": r,
    "col_index": c,
    "table_id": table.table_id,
    "row_id": None 또는 cell.row_id,
    "cell_id": None 또는 cell.cell_id,
    "is_origin": False 또는 True,
    "is_covered": False 또는 True,
    "is_empty": True 또는 False,
}
```

`issues`는 `_add_issue()`를 통해 아래 형태의 dict로 추가된다.

```python
{
    "code": code,
    "message": message,
    "severity": severity,
    "table_id": validation.table_id,
    "row_id": row_id,
    "cell_id": cell_id,
    "row_index": row_index,
    "col_index": col_index,
    "details": details or {},
}
```

### Step 6. border_fill 추가 후

실행 위치: `hwpx_parser/section_parser.py`의 `SectionParser.parse()`

실제 실행 함수: `hwpx_parser/table/table_style_resolver.py`의 `TableStyleResolver.resolve()`

현재 코드에는 `BorderFillResolver` 클래스가 없고, 실제 클래스명은 `TableStyleResolver`이다.

```python
table.border_fill_id_ref = attrs.get("borderFillIDRef")
table.border_fill = BorderFill(id=table.border_fill_id_ref, ...)

cell.border_fill_id_ref = attrs.get("borderFillIDRef")
cell.border_fill = BorderFill(id=cell.border_fill_id_ref, ...)
```

구분:

```python
# XML 원본 참조값
table.border_fill_id_ref
cell.border_fill_id_ref

# header.xml의 borderFill 원본 dict를 변환해 연결한 실제 객체
table.border_fill
cell.border_fill
```

`border_fill_id_ref`가 `None`이거나 `context.get_border_fill_raw()` 결과가 `None`이면 `border_fill`은 `None`으로 남는다.

---

## 4. 최종 table_to_dict 결과

`tools/run_model.py`의 현재 `table_to_dict(table)`는 `parser`를 인자로 받지 않고, 객체에 이미 들어 있는 `border_fill`을 `to_jsonable()`로 변환한다. 최종 구조는 아래처럼 축약할 수 있다.

```json
{
  "table_id": "...",
  "section_index": 0,
  "table_index": 0,
  "xml_table_id": "...",
  "row_count": 1,
  "col_count": 2,
  "cell_spacing": 0,
  "border_fill_id_ref": "3",
  "border_fill": {
    "id": "3",
    "left": {},
    "right": {},
    "top": {},
    "bottom": {},
    "diagonal": null,
    "slash": null,
    "back_slash": null,
    "fill": {}
  },
  "repeat_header": false,
  "page_break": false,
  "text_wrap": "...",
  "text_flow": "...",
  "width": null,
  "height": null,
  "pos_x": null,
  "pos_y": null,
  "treat_as_char": null,
  "flow_with_text": null,
  "in_margin_left": null,
  "in_margin_right": null,
  "in_margin_top": null,
  "in_margin_bottom": null,
  "out_margin_left": null,
  "out_margin_right": null,
  "out_margin_top": null,
  "out_margin_bottom": null,
  "caption_candidate": null,
  "note_candidate": null,
  "source_candidate": null,
  "validation": {
    "table_id": "...",
    "is_valid": true,
    "declared_row_count": 1,
    "declared_col_count": 2,
    "actual_tr_count": 1,
    "actual_cell_count": 2,
    "actual_max_row_count": 1,
    "actual_max_col_count": 2,
    "grid": [],
    "issues": []
  },
  "semantic": null,
  "raw_attrs": {},
  "is_nested": false,
  "parent_table_id": null,
  "parent_cell_id": null,
  "rows": [
    {
      "row_id": "...",
      "table_id": "...",
      "row_index": 0,
      "raw_attrs": {},
      "cells": [
        {
          "cell_id": "...",
          "table_id": "...",
          "row_id": "...",
          "cell_index": 0,
          "name": null,
          "header": false,
          "has_margin": false,
          "protect": false,
          "editable": false,
          "dirty": false,
          "border_fill_id_ref": "216",
          "border_fill": {
            "id": "216"
          },
          "row_addr": 0,
          "col_addr": 0,
          "row_span": 1,
          "col_span": 1,
          "end_row": 0,
          "end_col": 0,
          "width": 1000,
          "height": 500,
          "margin_left": null,
          "margin_right": null,
          "margin_top": null,
          "margin_bottom": null,
          "sublist_raw_attrs": {},
          "sublist_id": null,
          "sublist_text_direction": null,
          "sublist_line_wrap": null,
          "sublist_vert_align": null,
          "sublist_link_list_id_ref": null,
          "sublist_link_list_next_id_ref": null,
          "sublist_text_width": null,
          "sublist_text_height": null,
          "sublist_has_text_ref": false,
          "sublist_has_num_ref": false,
          "nested_tables": [
            {
              "table_id": "..._nested_tbl0",
              "is_nested": true,
              "parent_table_id": "...",
              "parent_cell_id": "...",
              "rows": []
            }
          ],
          "paragraphs": [
            {
              "paragraph_id": "...",
              "cell_id": "...",
              "paragraph_index": 0,
              "text": "...",
              "para_pr_id_ref": "...",
              "style_id_ref": "...",
              "raw_attrs": {},
              "runs": [
                {
                  "run_id": "...",
                  "paragraph_id": "...",
                  "run_index": 0,
                  "text": "...",
                  "char_pr_id_ref": "...",
                  "has_line_break": false,
                  "has_tab": false,
                  "has_fw_space": false,
                  "raw_attrs": {}
                }
              ]
            }
          ],
          "text": "...",
          "is_empty": false,
          "has_image": false,
          "has_field": false,
          "has_shape": false,
          "is_column_header": false,
          "is_row_header": false,
          "is_group_header": false,
          "is_data_cell": false,
          "raw_attrs": {}
        }
      ]
    }
  ]
}
```

현재 `table_to_dict()` 최종 출력에는 `border_fill_raw`가 없다. `border_fill_raw`를 만드는 별도 `cell_to_dict()` 함수는 파일에 남아 있지만, 현재 `save_results()`는 `tables_data = [table_to_dict(table) for table in tables]`를 사용한다.

---

## 5. 필드별 추가 위치 정리

| 필드 | 대상 객체 | 처음 추가되는 파일/함수 | 이후 갱신 여부 | 최종 출력 여부 |
| -- | ----- | ------------- | -------- | -------- |
| `table_id` | `Table` | `hwpx_parser/table/table_parser.py` / `TableParser.parse()` | 갱신 없음 | 예 |
| `section_index` | `Table` | `hwpx_parser/table/table_parser.py` / `TableParser.parse()` | 갱신 없음 | 예 |
| `table_index` | `Table` | `hwpx_parser/table/table_parser.py` / `TableParser.parse()` | 갱신 없음 | 예 |
| `xml_table_id` | `Table` | `hwpx_parser/table/table_parser.py` / `TableParser.parse()` | 갱신 없음 | 예 |
| `row_count` | `Table` | `hwpx_parser/table/table_parser.py` / `TableParser.parse()` | 갱신 없음 | 예 |
| `col_count` | `Table` | `hwpx_parser/table/table_parser.py` / `TableParser.parse()` | 갱신 없음 | 예 |
| `cell_spacing` | `Table` | `hwpx_parser/table/table_parser.py` / `TableParser.parse()` | 갱신 없음 | 예 |
| `border_fill_id_ref` | `Table` | `hwpx_parser/table/table_parser.py` / `TableParser.parse()` | 갱신 없음 | 예 |
| `border_fill` | `Table` | dataclass 기본값 `None` / `hwpx_document/table/table_data.py` | `TableStyleResolver.resolve()`에서 `BorderFill` 또는 `None`으로 갱신 | 예 |
| `rows` | `Table` | dataclass 기본값 `[]` / `hwpx_document/table/table_data.py` | `TableParser.parse()`에서 `_parse_rows()` 결과로 갱신 | 예 |
| `validation` | `Table` | dataclass 기본값 `None` / `hwpx_document/table/table_data.py` | `TableAnalyzer.analyze()`에서 `TableValidation`으로 갱신 | 예 |
| `semantic` | `Table` | dataclass 기본값 `None` / `hwpx_document/table/table_data.py` | 현재 코드에서는 추가되지 않음 | 예 |
| `raw_attrs` | `Table` | `hwpx_parser/table/table_parser.py` / `TableParser.parse()` | 갱신 없음 | 예 |
| `is_nested` | `Table` | dataclass 기본값 `False` / `hwpx_document/table/table_data.py` | 중첩 표일 때 `TableParser.parse()`에서 `True`로 설정 | 예 |
| `parent_table_id` | `Table` | dataclass 기본값 `None` / `hwpx_document/table/table_data.py` | 중첩 표일 때 `TableParser.parse()`에서 부모 표 ID로 설정 | 예 |
| `parent_cell_id` | `Table` | dataclass 기본값 `None` / `hwpx_document/table/table_data.py` | 중첩 표일 때 `TableParser.parse()`에서 부모 셀 ID로 설정 | 예 |
| `row_id` | `TableRow` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_rows()` | 갱신 없음 | 예 |
| `row_index` | `TableRow` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_rows()` | 갱신 없음 | 예 |
| `cells` | `TableRow` | dataclass 기본값 `[]` / `hwpx_document/table/table_data.py` | `TableParser._parse_rows()`에서 `_parse_cells()` 결과로 갱신 | 예 |
| `cell_id` | `TableCell` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_cells()` | 갱신 없음 | 예 |
| `cell_index` | `TableCell` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_cells()` | 갱신 없음 | 예 |
| `row_addr` | `TableCell` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_cells()` | 갱신 없음 | 예 |
| `col_addr` | `TableCell` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_cells()` | 갱신 없음 | 예 |
| `row_span` | `TableCell` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_cells()` | 갱신 없음 | 예 |
| `col_span` | `TableCell` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_cells()` | 갱신 없음 | 예 |
| `width` | `TableCell` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_cells()` | 갱신 없음 | 예 |
| `height` | `TableCell` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_cells()` | 갱신 없음 | 예 |
| `paragraphs` | `TableCell` | dataclass 기본값 `[]` / `hwpx_document/table/table_cell.py` | `TableParser._parse_cells()`에서 `_parse_paragraphs()` 결과로 갱신 | 예 |
| `nested_tables` | `TableCell` | dataclass 기본값 `[]` / `hwpx_document/table/table_cell.py` | `TableParser._parse_cells()`에서 `_parse_nested_tables()` 결과로 갱신 | 예 |
| `text` | `TableCell` | dataclass 기본값 `""` / `hwpx_document/table/table_cell.py` | `TableParser._parse_cells()`에서 문단 텍스트 join 결과로 갱신 | 예 |
| `paragraph_id` | `TableParagraph` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_paragraphs()` | 갱신 없음 | 예 |
| `para_pr_id_ref` | `TableParagraph` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_paragraphs()` | 갱신 없음 | 예 |
| `style_id_ref` | `TableParagraph` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_paragraphs()` | 갱신 없음 | 예 |
| `run_id` | `TableRun` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_runs()` | 갱신 없음 | 예 |
| `char_pr_id_ref` | `TableRun` | `hwpx_parser/table/table_parser.py` / `TableParser._parse_runs()` | 갱신 없음 | 예 |

---

## 6. 현재 코드에서 값이 비어 있는 필드

코드 기준으로 기본값이 `None`, 빈 리스트, 빈 문자열, 또는 `False`로 남을 수 있는 필드는 아래와 같다.

* `Table.semantic`: dataclass 기본값은 `None`이고, 현재 실행 흐름에서 `TableSemantic` 객체를 할당하는 코드가 없다.
* `Table.caption_candidate`, `Table.note_candidate`, `Table.source_candidate`: dataclass 기본값은 `None`이고, 현재 코드에서는 추가되지 않음.
* `Table.width`, `Table.height`, `Table.pos_x`, `Table.pos_y`: dataclass 기본값은 `None`이고, `TableParser.parse()`에서 `hp:tbl` 위치/크기 값을 읽어 넣지 않는다.
* `Table.treat_as_char`, `Table.flow_with_text`: dataclass 기본값은 `None`이고, 현재 코드에서는 추가되지 않음.
* `Table.in_margin_left`, `Table.in_margin_right`, `Table.in_margin_top`, `Table.in_margin_bottom`: dataclass 기본값은 `None`이고, 현재 코드에서는 추가되지 않음.
* `Table.out_margin_left`, `Table.out_margin_right`, `Table.out_margin_top`, `Table.out_margin_bottom`: dataclass 기본값은 `None`이고, 현재 코드에서는 추가되지 않음.
* `Table.border_fill`: 기본값은 `None`이다. `TableStyleResolver.resolve()`에서 `border_fill_id_ref`가 없거나 header.xml에서 원본을 찾지 못하면 `None`으로 남는다.
* `TableRow.declared_row_addr`: 기본값은 `None`이다. `row.cells`가 없거나 첫 셀의 `row_addr`가 `None`이면 `None`으로 남는다.
* `TableCell.border_fill`: 기본값은 `None`이다. `TableStyleResolver.resolve()`에서 `border_fill_id_ref`가 없거나 header.xml에서 원본을 찾지 못하면 `None`으로 남는다.
* `TableCell.row_addr`, `TableCell.col_addr`: `hp:cellAddr`가 없거나 값 변환에 실패하면 `None`으로 남는다.
* `TableCell.width`, `TableCell.height`: `hp:cellSz`가 없거나 값 변환에 실패하면 `None`으로 남는다.
* `TableCell.margin_left`, `TableCell.margin_right`, `TableCell.margin_top`, `TableCell.margin_bottom`: `hp:cellMargin`이 없거나 값 변환에 실패하면 `None`으로 남는다.
* `TableCell.sublist_id`, `sublist_text_direction`, `sublist_line_wrap`, `sublist_vert_align`, `sublist_link_list_id_ref`, `sublist_link_list_next_id_ref`, `sublist_text_width`, `sublist_text_height`: `hp:subList` 속성이 없으면 `None`으로 남는다.
* `TableCell.paragraphs`: `hp:subList`가 없거나 하위 `hp:p`가 없으면 빈 리스트로 남는다.
* `TableCell.text`: 문단 텍스트가 없으면 빈 문자열로 남는다.
* `TableCell.is_column_header`, `TableCell.is_row_header`, `TableCell.is_group_header`, `TableCell.is_data_cell`: dataclass 기본값은 `False`이고, 현재 코드에서는 추가/갱신되지 않는다.
* `TableParagraph.xml_para_id`, `TableParagraph.style_id_ref`, `TableParagraph.para_pr_id_ref`: `hp:p` attrs에 해당 값이 없으면 `None`으로 남는다.
* `TableParagraph.runs`: 문단 하위에 직접 자식 `hp:run`이 없으면 빈 리스트로 남는다.
* `TableParagraph.text`: run 텍스트가 없으면 빈 문자열로 남는다.
* `TableRun.char_pr_id_ref`: `hp:run` attrs에 `charPrIDRef`가 없으면 `None`으로 남는다.
* `TableRun.text`: `_extract_run_text()`에서 텍스트 관련 하위 요소를 찾지 못하면 빈 문자열로 남는다.
* `TableValidation.grid`: `row_count <= 0` 또는 `col_count <= 0`이면 `_build_grid()`가 바로 반환하므로 빈 리스트로 남는다.
* `TableValidation.issues`: 검증 중 오류/경고가 없으면 빈 리스트로 남는다.
* `TableValidation.has_row_order_mismatch`: 필드는 있지만 현재 `TableAnalyzer` 안에서 갱신하는 코드가 없다.
* `TableValidation.has_size_mismatch`, `TableValidation.has_margin_difference`, `TableValidation.has_empty_cell`, `TableValidation.has_nested_object`: 필드는 있지만 현재 `TableAnalyzer` 안에서 갱신하는 코드가 없다.

---

## 7. 최종 요약

```text
최종적으로 Table은 다음 정보를 가진다.

1. 표 자체 정보
   - table_id
   - row_count
   - col_count
   - border_fill_id_ref
   - border_fill

2. 행/셀 구조
   - rows
   - cells
   - row_addr / col_addr
   - row_span / col_span

3. 셀 내부 텍스트 구조
   - paragraphs
   - runs
   - text

4. 검증 결과
   - validation
   - grid
   - issues

5. 최종 출력
   - table_to_dict()
   - tables.json
```
