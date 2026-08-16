# DocumentModel 사용 안내

> 이 문서가 왜 있나 — HWPX 문서를 파싱한 결과를 **조립까지 끝낸 객체**로 쓰는 법을 적는다. 어떤 값이 어디 있고, 어떤 경우에 그 값이 비는지를 알면 나머지는 따라온다.

숫자는 모두 실측이다. 기준 문서 둘을 나란히 적는다.

- **본 문서** — `3주기(2025년) 대학혁신지원사업 1차년도 수정 자율혁신계획_260122 1133.hwpx`
- **sample** — `sample.zip` (중첩표·떠있는 도형이 있어 본 문서에 없는 경우를 덮는다)

---

## 0. 이게 뭔지

> 한 줄 — 파싱 결과가 id로 흩어져 있던 걸 **한 번에 붙여 놓은 최종 객체**다.

파이프라인은 `blocks`, `tables.analyzed`, `table_internal_blocks`를 따로 들고 서로를 id로 가리킨다. 표 하나를 꺼내려면 세 군데를 조인해야 한다. `DocumentModel`은 그 조인을 끝내 놓은 것이다.

```python
from hwpx.analysis.build_document_model import build_document_model

model = build_document_model(result)      # result = run_analysis_pipeline(...)
model.blocks[341].table.records[0].values
```

만들 때 정한 것 세 가지다. 이걸 알고 봐야 값이 비어 있는 이유가 납득된다.

1. **표는 구조를 믿을 수 있는 것만 남겼다.** 나머지는 버린 게 아니라 OCR 경로로 보낸다. 자리에는 표시가 남는다.
2. **문서 순서와 계층은 그대로다.** 블록 수·읽는 순서·depth는 파이프라인 최종값과 하나도 다르지 않다(매 실행 M2·M9가 확인).
3. **조립용 중간 키는 남기지 않았다.** 내부 식별자를 들고 다니지 않는다(M8이 확인).

JSON을 읽지 않는다. `document_model.json`은 눈으로 보라고 떨어뜨리는 사본이고, 정본은 객체다.

---

## 1. 30초 — 전체 모양

> 한 줄 — 값을 찾기 전에 **어디에 무엇이 담기는지** 지도를 먼저 본다.

```
DocumentModel
├─ file        문서 메타 11개          (제목·생성자·작성프로그램·섹션수·표수)
├─ images      파일 카탈로그           본 38개 / sample 81개
└─ blocks      읽는 순서대로           본 409개 / sample 411개
   ├─ 공통    id · order · section · depth · area · kind · role · searchable · text
   ├─ 계층    heading_path · heading_path_text · child_headings
   ├─ 목차    toc · toc_entries
   └─ 실림    table │ figure │ excluded_table      ← 셋 중 최대 하나
```

| | 본 문서 | sample |
|---|---|---|
| 블록 | 409 | 411 |
| 검색 대상 블록 | 217 | 240 |
| 표 (중첩 포함) | 26 | 140 |
| 이미지 파일 / 실제 쓰인 것 | 38 / 12 | 81 / 13 |
| 목차 노드 / 목차 항목 | 21 / 38 | 23 / 29 |

---

## 2. 가장 먼저 — 블록은 6갈래다

> 한 줄 — 여기서 안 갈라 놓으면 **뒤의 모든 코드가 어딘가에서 죽는다.** 가장 먼저 읽어야 할 절이다.

`table` / `figure` / `excluded_table`은 **셋 중 최대 하나만** 채워진다(둘 다인 경우 0건 확인). `block.table.markdown`을 무심코 쓰면 본 문서 409개 중 383개에서 터진다.

```python
for b in model.blocks:
    if b.table:            ...   # 본 26  / sample 70
    elif b.excluded_table: ...   # 본 63  / sample 14   내용 없음, 사유만
    elif b.toc_entries:    ...   # 본 1   / sample 1    목차 표가 있던 자리
    elif b.figure:         ...   # 본 23  / sample 39
    elif b.text:           ...   # 본 104 / sample 118
    else:                  continue   # 본 192 / sample 169  빈 블록
```

순서가 중요하다. 표 블록도 `toc`를 가질 수 있고 도형 블록도 `text`를 가질 수 있어서, 겹치는 축을 뒤에 두어야 한다.

**`kind == '표'`인 블록이 셋으로 갈린다**는 점이 가장 헷갈린다. 남은 표(`table`), 버려진 표(`excluded_table`), 목차 표(`toc_entries`) 셋 다 `kind`는 `'표'`다. → 자세히는 [4.1](#41-블록-6갈래)

---

## 3. 목적별 사용법

> 한 줄 — **하고 싶은 일**에서 출발해 필요한 필드로 가는 길만 적는다. 막히면 4장에서 그 경우를 확인한다.

### 3.1 임베딩할 텍스트를 뽑고 싶다

`searchable`이 임베딩 대상 여부다. 계층은 `heading_path_text`로 붙인다.

```python
for b in model.searchable_blocks():
    if not b.text:
        continue
    context = ' > '.join(b.heading_path_text)
    yield f'{context}\n{b.text}'
```

본 문서에서 검색 대상 217개 중 **텍스트가 있는 블록은 113개**다. 나머지는 표·도형 블록이라 `text`가 비어 있다. 실제 맥락은 이렇게 나온다.

```
자율혁신계획』 > - 2025년 대학혁신지원사업 수정 사업계획 - > 우송대학교 > 【대학혁신지원사업 개요】
```

> 걸리는 곳 — 첫 제목보다 앞에 있는 블록은 `heading_path`가 비어 있다(본 13개 / sample 10개).

### 3.2 표를 행 단위로 쪼개고 싶다

`kept_as == '레코드'`인 표만 해당한다. 행마다 값이 다 채워져 있어 한 행씩 떼어내도 뜻이 통한다.

```python
for t in model.tables():
    if t.kept_as != '레코드':
        continue
    for rec in t.records:
        yield rec.values          # {'구분': '대학혁신위원회', '구성 인원': '총 15명', ...}
```

본 3개 / sample 28개. 레코드 값에 빈 값은 **두 문서 모두 0건**이다 — 그게 이 갈래의 조건이다.

> 걸리는 곳 — `rec.inherited`에 든 키는 그 행에 실제로 쓰인 값이 아니라 **세로 병합으로 위칸에서 물려받은 값**이다(본 6건 / sample 48건). 같은 값이 여러 행에 나올 때 진짜 반복인지 병합인지 여기서 갈린다.

### 3.3 표를 통째로 넣고 싶다

`kept_as == '산문'`은 격자가 아니라 헤더 개념이 성립하지 않는 표다. 쪼개지 말고 `markdown`을 그대로 쓴다.

```python
for t in model.tables():
    if t.kept_as == '산문':
        yield t.markdown
```

본 4개 / sample 86개. `markdown`은 **모든 표에 항상 있다** — 어느 갈래든 이건 쓸 수 있다.

> 걸리는 곳 — 산문표는 `header`와 `title`이 항상 `None`이다. 없는 게 정상이지 실패가 아니다.

### 3.4 수치표만 다르게 처리하고 싶다

```python
model.numeric_tables()            # numeric == True
t.numeric_verdict                 # 수치표 / 아님 / 판정불가 / 대상아님
```

**판정은 `kept_as == '레코드'`인 표에서만 의미가 있다.** 나머지 갈래는 값이 고정이다.

| `kept_as` | 나오는 판정 | 본 문서 | sample |
|---|---|---|---|
| 레코드 | 수치표 / 아님 | 1 / 2 | 18 / 10 |
| 산문 | 판정불가 (고정) | 4 | 86 |
| 제목 | 대상아님 (고정) | 18 | 25 |
| 키값 | 아님 (고정) | 1 | 1 |

`판정불가`는 "재봤더니 아니다"가 아니라 **"열이 성립하지 않아 재볼 수 없다"**는 뜻이다. `아님`과 섞으면 안 된다.

### 3.5 문서 계층·목차를 재구성하고 싶다

```python
b.depth                # 구조 깊이
b.heading_path         # 상위 제목 블록 id 사슬
b.heading_path_text    # 그 제목들의 텍스트
b.child_headings       # 바로 아래 제목 id
b.toc                  # TocRef(title, numbering) — 이 블록이 목차 노드면
b.toc_entries          # 목차 표에서 뽑아낸 항목들
```

목차 노드는 본 21개 / sample 23개. 예: `numbering='2'`, `title='영역별 혁신전략'`.

목차 표 자체는 표로 남기지 않고 **항목 목록으로 바꿔** 원래 자리에 둔다. 본 문서는 38항목, `depth`가 함께 붙는다.

> 걸리는 곳 — **제목 블록의 `heading_path`는 마지막 칸이 자기 자신이다.** 조상만 필요하면 `[:-1]`. → [4.7](#47-계층)

### 3.6 이미지를 꺼내고 싶다

```python
for b in model.blocks:
    if b.figure and b.figure.image:
        b.figure.image.path                          # 'BinData/image7.bmp'
        model.images[b.figure.image.ref].size_bytes  # 5479718
```

`images`는 문서에 든 **파일 카탈로그**, `figure.image`는 **본문이 그 파일을 가리키는 지점**이다. 한 파일을 여러 곳에서 가리킬 수 있고, 목록에만 있고 쓰이지 않는 파일도 있다(본 38개 중 12개만 쓰임).

> 걸리는 곳 — **`figure.image`가 `None`인 경우가 절반쯤 된다**(본 23개 중 11개). 도형·도형묶음은 파일이 없고 대신 `contains`에 구성이 들어간다: `{'rect': 3, 'ellipse': 2}`.

### 3.7 버려진 표를 OCR로 넘기고 싶다

```python
for b in model.blocks:
    if b.excluded_table:
        b.excluded_table.table_id    # 원본에서 찾을 id
        b.excluded_table.reason      # '제외:OCR'
```

본 63개 / sample 14개. 블록 자체는 **원래 위치에 그대로 남아** 있어서, OCR 결과를 받아 그 자리에 끼워 넣을 수 있다.

> 걸리는 곳 — 이 블록은 `text`도 `table`도 없다. 표 내용은 담지 않는다.

---

## 4. 상황별 전체 표

> 한 줄 — 3장을 따라 쓰다 **값이 비었을 때** 그게 정상인지 확인하는 곳이다. 두 문서 실측이며, 한 문서에만 나오는 경우가 있어 둘을 함께 적는다.

### 4.1 블록 6갈래

| 경우 | 본 문서 | sample | 항상 있음 | 항상 없음 |
|---|---|---|---|---|
| 표 있음 | 26 | 70 | `table` | `text` `figure` `excluded_table` `toc_entries` |
| 표 버려짐 | 63 | 14 | `excluded_table` | `text` `table` `figure` `toc` `toc_entries` |
| 목차 항목 자리 | 1 | 1 | `toc_entries` | `text` `table` `figure` `excluded_table` `toc` |
| 도형·이미지 | 23 | 39 | `figure` | `table` `excluded_table` `toc_entries` |
| 텍스트만 | 104 | 118 | `text` | `table` `figure` `excluded_table` `toc_entries` |
| 빈 블록 | 192 | 169 | — | 전부 |

빈 블록의 정체는 빈 문단 167 · 컨트롤 23 · 섹션컨트롤 1 · 캡션 1이다(본 문서 기준). 문서 구조상 자리는 차지하지만 내용이 없다.

### 4.2 표 4갈래 — `kept_as`

| `kept_as` | 본 | sample | 항상 있음 | 항상 없음 | 있을 수도 |
|---|---|---|---|---|---|
| **레코드** | 3 | 28 | `header` `records` `markdown` | `title` `children` `raw_row_count` | `parent` |
| **산문** | 4 | 86 | `markdown` | `header` `title` | `records` `parent` `children` `raw_row_count` |
| **키값** | 1 | 1 | `header` `records` `markdown` | `title` `raw_row_count` | `parent` `children` |
| **제목** | 18 | 25 | `title` `markdown` | `header` `records` `parent` `children` `raw_row_count` | — |

`kind`(데이터표/키값표/제목상자)만으로는 이 구분이 안 된다. 헤더 없는 데이터표가 **"산문이라 헤더가 필요 없는 표"**인지 **"헤더가 있어야 하는데 못 잡은 표"**인지 가릴 수 없기 때문이다. 후자는 애초에 결과에 안 들어오지만, 그 판단 근거가 객체에 남아 있어야 되물을 수 있다.

중첩 표는 본 문서 0개 / sample 70개다. 본 문서에서 중첩표는 전부 버려졌다.

### 4.3 수치 판정 × `kept_as`

| 조합 | 본 | sample |
|---|---|---|
| 레코드 × 수치표 | 1 | 18 |
| 레코드 × 아님 | 2 | 10 |
| 산문 × 판정불가 | 4 | 86 |
| 제목 × 대상아님 | 18 | 25 |
| 키값 × 아님 | 1 | 1 |

두 축은 독립이 아니다. `레코드` 외에는 판정이 한 값으로 고정된다.

### 4.4 칸

| 경우 | 본 | sample | 뜻 |
|---|---|---|---|
| 전체 | 128 | 1,088 | |
| 병합 원본 칸 | 7 | 117 | `row_span`/`col_span` > 1. 덮이는 칸은 항목이 따로 없다 |
| 빈 칸 | 6 | 153 | `text`가 빈 문자열 |
| 문단 여러 개 | 11 | 144 | `paragraphs`에 원래 문단이 남는다 |
| 이미지 보유 | 1 | 83 | `images` |
| 자식표 보유 | 0 | 31 | `child_tables` — id 목록 |

`cell.text`는 문단을 공백으로 이어 한 줄로 정규화한 값이다. 문단 구분이 필요하면 `paragraphs`를 본다(문단이 하나뿐이면 비어 있다).

### 4.5 레코드

| 경우 | 본 | sample |
|---|---|---|
| 전체 | 27 | 154 |
| 병합값 물려받음 (`inherited`) | 6 | 48 |
| 빈 값 있음 | **0** | **0** |

빈 값이 0인 것은 우연이 아니라 `kept_as == '레코드'`의 성립 조건이다.

### 4.6 도형·이미지

| 경우 | 본 | sample |
|---|---|---|
| 전체 | 23 | 39 |
| `image` 있음 | 12 | 14 |
| `image` 없음 | 11 | 25 |
| `shape` 종류 | 이미지 12 · 도형묶음 11 | 이미지 14 · 도형묶음 19 · 도형 6 |
| `contains` 있음 | 11 | 19 |
| 배치 | 글자처럼 23 | 글자처럼 35 · 떠있음 4 |
| 텍스트 동반 | 10 | 25 |

떠있는 개체는 본 문서에 없다. sample에 4개 있으며, 앵커를 찾아 읽는 순서에 꽂아 넣은 상태다.

### 4.7 계층

| 경우 | 확인 |
|---|---|
| 제목 블록 | `heading_path`의 **마지막 칸이 자기 자신**. 본 16개 |
| 일반 블록 | 조상만 들어간다 |
| 경로 없는 블록 | 첫 제목보다 앞. 본 13개 / sample 10개 |

`depth`와 `heading_path`는 다른 개념이다. `depth`는 구조 깊이고, `heading_path`는 읽는 순서상 속한 제목 사슬이다. **제목이 아닌 블록은 자기 `depth`와 무관한 제목 밑에 놓일 수 있다** — depth 0인 컨트롤 블록이 depth 1 제목 뒤에 나오면 그 제목에 속한다.

---

## 5. 자주 걸리는 곳

> 한 줄 — 증상으로 찾아 원인을 확인하는 색인이다.

| 증상 | 원인 | 자세히 |
|---|---|---|
| `kind == '표'`인데 `table`이 없다 | 버려졌거나 목차 표 | [4.1](#41-블록-6갈래) |
| `header`가 `None`이다 | 산문표·제목상자는 원래 없다 | [4.2](#42-표-4갈래--kept_as) |
| 판정이 전부 `판정불가`다 | 산문표는 고정값 | [4.3](#43-수치-판정--kept_as) |
| `figure.image`가 `None`이다 | 도형묶음. `contains`를 본다 | [4.6](#46-도형이미지) |
| 제목 경로가 한 칸 깊다 | 마지막이 자기 자신 | [4.7](#47-계층) |
| 병합 칸을 못 찾겠다 | 덮이는 칸은 항목이 없다 | [4.4](#44-칸) |
| 레코드 값이 실제 칸에 없다 | 병합에서 물려받았다 | [4.5](#45-레코드) |
| `cell.text`에 문단 구분이 없다 | 한 줄로 정규화된다 | [4.4](#44-칸) |

---

## 6. 없는 것과 그 이유

> 한 줄 — "왜 없나"를 적어 두지 않으면 같은 질문이 반복된다.

| 항목 | 이유 |
|---|---|
| 이미지 캡션 | 빼기로 결정. caption 블록은 남아 있으나 `text`는 비어 있다 |
| 표 원문 XML | 빼기로 결정. `markdown`과 `cells`로 대신한다. `cells`는 좌표·병합·문단을 보존하므로 표를 다시 세울 수 있다 |
| 문서 본래 제목 | 파일명을 쓰기로 결정. `file.title == file.filename` |
| 버려진 표의 내용 | 의도. OCR 경로로 보내며 자리 표시만 남긴다 |

---

## 7. 부록 — 전체 필드

> 한 줄 — 찾아보는 용도. 위에서 설명한 것을 클래스별로 다시 늘어놓은 것뿐이다.

### DocumentModel
| 필드 | 뜻 |
|---|---|
| `file` | `FileInfo` |
| `images` | `{ref: ImageFile}` |
| `blocks` | `[Block]` 읽는 순서 |
| `tables()` | 중첩까지 전부 순회 |
| `numeric_tables()` | `numeric == True` |
| `searchable_blocks()` | `searchable == True` |
| `to_dict()` | 직렬화 |

### FileInfo
`title` · `filename` · `creator` · `last_saved_by` · `created_at` · `modified_at` · `language` · `application` · `app_version` · `section_count` · `table_count`

### Block
| 필드 | 뜻 |
|---|---|
| `id` `order` `section` `depth` | 식별·위치 |
| `area` | 본문 / 주변부 |
| `kind` | 문단·표·이미지·도형·도형묶음·컨트롤·바닥글·섹션컨트롤 |
| `role` | 제목·본문·표·그림·바닥글·빈문단·문서컨트롤 등 |
| `searchable` | 임베딩 대상 |
| `text` | 정규화된 한 줄 |
| `heading_path` `heading_path_text` `child_headings` | 계층 |
| `toc` `toc_entries` | 목차 |
| `table` `figure` `excluded_table` | 실린 것 (셋 중 하나) |

### Table
| 필드 | 뜻 |
|---|---|
| `id` `kind` | 식별·종류 |
| `kept_as` | 레코드 / 키값 / 산문 / 제목 |
| `rows` `cols` | 격자 크기 |
| `numeric` `numeric_verdict` | 수치표 판정 |
| `row_records_available` | 행 레코드 성립 여부 |
| `title` | 제목 텍스트 |
| `header` | `TableHeader` |
| `records` | `[TableRecord]` |
| `cells` | `[Cell]` |
| `markdown` | 항상 있음 |
| `raw_row_count` | 레코드가 없을 때의 행 수 |
| `parent` `children` | 중첩 관계 |

### TableHeader / TableColumn
`header_rows` · `header_cols` · `columns[]` (`index`, `name`, `is_row_header`)

### TableRecord
`index` · `values` · `inherited`

### Cell
`row` · `col` · `row_span` · `col_span` · `text` · `paragraphs` · `images` · `child_tables`

### Figure
`shape` · `z_order` · `placement` · `paragraph_index` · `image` · `shape_type` · `width` · `height` · `contains`

### ImageFile / ImageRef
`ImageFile` = `ref` · `path` · `media_type` · `size_bytes` (카탈로그)
`ImageRef` = `ref` · `path` · `media_type` (참조 지점)

### TocRef / TocEntry / ExcludedTable / TableParent
`TocRef` = `title` · `numbering`
`TocEntry` = `text` · `depth`
`ExcludedTable` = `table_id` · `reason`
`TableParent` = `table_id` · `cell_id`

---

## 검증

이 객체는 매 실행 스스로를 검사하며, 하나라도 깨지면 저장하지 않는다.

| | 내용 |
|---|---|
| M2 · M9 | 블록 수·depth·순서·섹션이 파이프라인 최종값과 같다 |
| M4 | 수치 판정이 네 갈래로 빠짐없이 붙는다 |
| M5 · M13 | 이미지 참조가 전부 실제 파일로 풀린다 |
| M6 | 제목 경로의 depth가 단조 증가한다 |
| M7 | 마크다운 격자가 선언 크기와 맞는다 |
| M8 | 조립용 연결 키가 남지 않는다 |
| M10 · M11 | 중첩 표의 상위표가 있고 id·좌표·순서에 중복이 없다 |
| M12 | 모든 블록에 depth·순서·섹션이 해소되어 있다 |
| M14 | 파이프라인이 만든 헤더·레코드가 유실되지 않았다 |
| M15 | `kept_as`가 필터 판정과 같다 |

```bash
python -m tools.run_model
```
