# DocumentModel — 전체 구조와 의미

문서 하나를 조립한 결과. `hwpx_analysis/document_model.py` 에 정의돼 있고
`build_document_model(PipelineResult)` 가 만든다. JSON 을 읽지 않는다.

수치는 전부 sample.zip 실측이다.

```
DocumentModel
├─ file    : FileInfo              문서 자체
├─ images  : {ref: ImageFile}      BinData 실제 파일 81개
└─ blocks  : [Block]               읽기 순서대로 411개
```

`blocks` 는 `order` 오름차순으로 담긴다. 0~410 연속이고 빈 자리가 없다.
**순서를 담는 별도 객체가 필요 없다.**

---

## FileInfo — 문서 자체

| 필드 | 의미 | 실측 |
|---|---|---|
| `title` | 문서 제목. 원본 `content.hpf` 의 title 이 비는 문서가 있어 파일명을 쓴다 | `sample` |
| `filename` | 파일명 | `sample` |
| `creator` | 만든 사람 | `Administrator` |
| `last_saved_by` | 마지막 저장자 | `aaa` |
| `created_at` / `modified_at` | 만든·수정 시각 | `2024-03-28` / `2026-06-24` |
| `language` | 문서 언어 | `ko` |
| `application` / `app_version` | 작성 프로그램 | `Hancom Office Hangul` / `12, 0, 0, 535` |
| `section_count` | 섹션 수 | 5 |
| `table_count` | 모델에 남은 표 수 | 140 |

`creator` 부터 `app_version` 까지는 파이프라인이 읽지 않는 `content.hpf` /
`version.xml` 에서 빌더가 직접 가져온다.

---

## ImageFile — 실제 그림 파일

| 필드 | 의미 |
|---|---|
| `ref` | `image9` 같은 참조 id |
| `path` | `BinData/image9.jpg` |
| `media_type` | `image/jpg` |
| `size_bytes` | 16,036 |

`content.hpf` 의 manifest 에서 온다. **그림을 실제 파일과 잇는 유일한 통로**다.
81개 전부 경로가 있다.

---

## Block — 문서의 기본 단위 (411개)

### 모든 블록이 갖는 것

| 필드 | 의미 | 실측 |
|---|---|---|
| `id` | 블록 유일 id (`s3_b00365`) | 411 |
| `order` | 읽기 순서. 문서 순서의 유일한 근거 | 0~410 연속 |
| `section` | 섹션 경계 | 0~4 |
| `depth` | 문서 계층 | 0~8 |
| `area` | `본문` / `주변부`. 머리말·바닥글을 가른다 | 본문 375 / 주변부 36 |
| `kind` | **형태**. 문단 251 / 표 85 / 컨트롤 27 / 도형묶음 19 / 이미지 14 / 도형 6 / 섹션컨트롤 5 / 바닥글 4 | 411 |
| `role` | **의미**. 빈문단 135 / 표 85 / 제목 58 / 본문 58 / 그림 39 / 문서컨트롤 32 / 바닥글 4 | 411 |
| `searchable` | 검색·임베딩 대상인지 | true 240 |

`kind` 와 `role` 은 축이 다르다. 그림 39개가 이미지 14 / 도형묶음 19 / 도형 6 으로
갈리는 건 `kind` 에서만 보이고, 그 셋이 다 "그림" 이라는 건 `role` 에서만 보인다.

### 있을 때만 채워지는 것

| 필드 | 의미 | 실측 |
|---|---|---|
| `text` | 본문 텍스트 | 143 |
| `heading_path` | 조상 제목 id 목록 | 401 |
| `heading_path_text` | 같은 경로의 제목 글자 | 401 |
| `child_headings` | 이 제목의 하위 제목 id | 13 |
| `toc` | 목차 노드일 때 `{title, numbering}` | 23 |
| `toc_entries` | 목차 표 자리. `{text, depth}` 29항목 | 1 |
| `excluded_table` | 빠진 표 자리. `{table_id, reason}` | 14 |
| `figure` | 그림 | 39 |
| `table` | 표 | 70 |

`heading_path` 예시:

```
□ 대학 교육혁신 전략 추진 관련 > ○ 문제점 > □ 추진 세부내용 > 가. 세부내용 1. 역량중심 교육
```

`excluded_table` 은 구조를 믿을 수 없어 뺀 표의 자리다. 텍스트는 비어 있고 표 id 와
사유만 남는다. **OCR 결과가 들어올 자리**다.

`table` 이 70개인 이유는 최상위 표만 블록에 붙기 때문이다. 나머지 70개는 `children`
으로 중첩돼 있다(합 140).

---

## Figure — 그림 (39개)

| 필드 | 의미 | 실측 |
|---|---|---|
| `shape` | 이미지 14 / 도형묶음 19 / 도형 6 | 39 |
| `z_order` | 겹쳤을 때 앞뒤 | 39 |
| `placement` | `글자처럼` 35 / `떠있음` 4 | 39 |
| `paragraph_index` | 몇 번째 문단에 붙었는지 | 39 |
| `image` | `ImageRef{ref, path, media_type}` | 14 |
| `shape_type` | 도형 종류(polygon 등) | 6 |
| `width` / `height` | 크기 | 20 |
| `contains` | 묶음이 품은 것 `{"rect": 2}` | 19 |

**도형묶음 19개는 `width`/`height` 가 비어 있다.** 원본이 자기 크기를 선언하지 않기
때문이고, 대신 `contains` 가 무엇을 품었는지 알려준다.

---

## Table — 표 (중첩 포함 140개)

같은 표를 세 가지 형태로 갖는다. **격자**는 원본 복원용, **레코드**는 행 단위 소비용,
**마크다운**은 사람·LLM 이 읽는 용도다.

### 식별과 성격

| 필드 | 의미 | 실측 |
|---|---|---|
| `id` | 표 유일 id | 140 |
| `kind` | 데이터표 113 / 제목상자 25 / 키값표 2 | 140 |
| `numeric` | 수치표인지 | true 18 |
| `numeric_verdict` | `수치표` 18 / `아님` 11 / `판정불가` 86 / `대상아님` 25 | 140 |
| `row_records_available` | 행 레코드로 읽을 수 있는지 | true 28 |
| `title` | 표 제목. `제목상자` 만 갖는다 | 25 |

`판정불가` 는 "숫자가 없다" 가 아니라 **헤더가 없어 열의 성격을 가릴 수 없다**는 뜻이다.
`아님` 으로 뭉개면 헤더 검출이 좋아졌을 때 재판정 대상을 놓친다.

### 헤더

```json
"header": {
  "header_rows": [0],
  "header_cols": [],
  "columns": [{"index": 0, "name": "혁신전략", "is_row_header": false}, …]
}
```

| 필드 | 의미 |
|---|---|
| `header_rows` / `header_cols` | 어느 행·열이 머리글인지 |
| `columns[].index` | 열 번호 |
| `columns[].name` | 열 이름. **값에 의미를 붙이는 것** |
| `columns[].is_row_header` | 그 열이 값이 아니라 라벨인지 |

**140개 중 28개만 있다.** 나머지는 헤더 검출이 안 된 표이고, 그건 의도된 결과다.

### 격자 — `cells` (1,088개)

```json
{"row": 0, "col": 1, "row_span": 3, "col_span": 1, "text": "역량 중심 교육 혁신",
 "paragraphs": [], "images": [], "child_tables": []}
```

| 필드 | 의미 | 실측 |
|---|---|---|
| `row` / `col` | 격자 좌표 | 1,088 |
| `row_span` / `col_span` | 병합 | span>1 인 칸 117 |
| `text` | 칸 내용 | 1,088 |
| `paragraphs` | 한 칸에 문단이 둘 이상일 때만 | 144 |
| `images` | 칸 안 그림 `ImageRef` | 83 |
| `child_tables` | 이 칸에 든 하위표 id | 31 |

`paragraphs` 는 `text` 로는 문단 경계를 되찾을 수 없어 따로 둔다.
`child_tables` 는 "어느 칸에" 를, `children` 은 "어떤 표" 를 말한다. 둘 다 있어야
하위표를 제자리에 꽂는다.

### 행 레코드 — `records` (147개)

```json
{"index": 1,
 "values": {"혁신전략": "역량 중심 교육 혁신", "개선방안": "우수 교수학습 사례…"},
 "inherited": ["혁신전략"]}
```

| 필드 | 의미 | 실측 |
|---|---|---|
| `index` | 행 번호 | 147 |
| `values` | `{열이름: 값}`. 행 하나가 자립한다 | 147 |
| `inherited` | **병합으로 위칸에서 물려받은 열** | 48 |

`inherited` 가 없으면 같은 값이 여러 행에 나올 때 진짜 반복인지 병합인지 구분할 수 없다.

### 읽기용과 중첩

| 필드 | 의미 | 실측 |
|---|---|---|
| `markdown` | 격자를 Markdown 표로. 병합 값은 덮이는 칸에 채운다 | 140 |
| `rows` / `cols` | 선언 크기 | 140 |
| `raw_row_count` | 레코드를 못 만든 표의 행 수 | 85 |
| `parent` | 중첩일 때 `{table_id, cell_id}` | 70 |
| `children` | 하위표. 재귀 | 29 |

---

## 모델에 없는 것

조립에만 쓰고 결과에는 두지 않는다.

```
source_block_id / internal_block_id / parent_internal_block_id
internal_block_type / local_order_index / root_table_id / source_table_id
xml_table_id(블록 쪽) / toc_source_table_ids
```

쓰는 사람이 봐야 하는 것은 계층·종류·표 구조이지 조립 흔적이 아니다.
매 실행 `M8` 검사가 이 키들이 남지 않았는지 확인한다.

---

## 쓰는 법

```python
from hwpx_analysis.build_document_model import build_document_model

model = build_document_model(result)      # result = run_analysis_pipeline(...)

model.file.creator                        # 'Administrator'
model.blocks[364].table.records[0].values
list(model.tables())                      # 중첩 포함 140개
model.numeric_tables()                    # 18개
model.searchable_blocks()                 # 240개
```

```bash
python tools/build_document_model.py      # 문서 -> 파이프라인 -> 모델 -> 저장
```

매 실행 M2~M10 을 검증하고 하나라도 깨지면 저장하지 않는다.
