# 계층화 알고리즘 — 적용 순서와 우선순위

HWPX 문서에서 표 계층과 문서 depth를 결정하는 알고리즘의 실행 순서를 정리한다.
코드 주석에 흩어져 있는 스테이지 번호(4-B, 7.5-A, 8-A …)가 실제 실행 순서와
일치하지 않으므로, 이 문서는 **실행 순서**를 기준으로 기술한다.

측정 수치는 문서 3종(sample.zip + 실제 보고서 2건, 표 728개 / 블록 2,126개)
기준이며 `output/results/<문서명>/final_debug.json`에서 산출했다.

---

## 0. 진입점

```
tools/run_model.py
  └ HwpxParser.parse()                    hwpx_parser/parser.py
      ├ HeaderParser.parse(header.xml)    스타일·불릿·번호 정의
      └ SectionParser.parse(section*.xml) 표 파싱 (조상에 tbl 없는 hp:tbl)
  └ table_to_dict()                       hwpx_analysis/table_json_serializer.py
  └ run_analysis_pipeline()               hwpx_analysis/pipeline.py:54
```

`run_analysis_pipeline`이 아래 17단계를 순서대로 실행한다.

---

## 1. 표 계층화 (1~4단계)

| # | 단계 | 모듈 |
|---|---|---|
| 1 | preprocess | `add_table_preprocess_to_json` |
| 2 | grid | `add_table_grid_to_json` (+ `grid_normalizer`) |
| 3 | **hierarchy** | `table_hierarchy/orchestrator` |
| 4 | body linking | `make_body_linking_table_json` |

### 3단계 내부 — 분류 체인

`classify_table()` (`table_hierarchy/classify.py:25`)은 **순서 의존 체인**이다.
먼저 참이 되는 조건이 이기며, 앞 조건이 뒤 조건의 게이트 역할을 한다.

```
① _is_priority_title_box      번호형 제목 우선 (caption 검사보다 먼저)
② is_caption_or_note_table    ← 게이트. 참이면 ③④가 실행되지 않음
③ is_title_box
④ _is_title_box_condition1 / _is_title_box_condition2
⑤ _is_data_table_priority
⑥ is_key_value_table
⑦ 기본값 data_table
```

> **주의**: 한 조각만 제거해도 뒤 판정이 바뀐다. ②는 728개 표에서 한 번도
> 참이 되지 않았지만(발동 0회), 제거하면 title_box 판정 결과가 달라진다.

### 3단계 내부 — 분기별 빌더

| table_type | 산출 |
|---|---|
| `title_box` | `title_cells` 만 (records 생략) |
| `caption_or_note_table` | caption 셀 목록만 |
| `key_value_table` | `build_key_value_records` → orientation 분기 (`row_pairs` / `form_kv` → `_build_form_sections`) |
| `data_table` | `build_data_table_hierarchy` |

중첩 표는 `rows → direct cells → children` 순으로 시도해 재귀한다
(`table_hierarchy/nested.py`).

### 3단계 내부 — data_table 전용 후속 체인

```
build_raw_rows
  → detect_header_rows        ★ build_data_table_hierarchy의 header_rows를 덮어씀
  → detect_header_cols
  → build_columns             header_rows가 있을 때만
  → build_structured_records
  → apply_record_stability_filter
  → normalize_hierarchy_warnings
```

`build_data_table_hierarchy`가 반환한 `header_rows`는 data_table에서 폐기되지만,
같은 호출의 `body_cells`는 사용된다. 반쪽만 죽은 코드다.

**헤더 판정 점수제** (`header_row_detector.score_header_row_candidate`)
임계 4점, 주요 가점은 `label_ratio >= 0.5` (+2)와 후행 데이터 행 (+2).
`is_label_like_cell`은 **숫자가 포함된 셀을 라벨에서 제외**하므로
`2022학년도`, `1차년도 (2022)` 같은 연도형 헤더가 탈락한다.

---

## 2. 문서 계층화 (5~17단계)

| # | 스테이지 | 모듈 | depth 관여 |
|---|---|---|---|
| 5 | — | `add_document_blocks_to_json` | **1차 depth 부여** |
| 6 | 4-B | `resolve_floating_anchors` | 앵커 기록만, depth 불변 |
| 7 | 7.5-A | `add_table_hierarchy_ref_to_blocks` | `title_text` 등 연결 |
| 8 | 8-A | `resolve_block_depth_candidates` | 후보 top-k 생성, depth 불변 |
| 9 | 8-A′ | `add_toc_depth0_anchors` | **목차 매칭 → depth 확정 (최우선)** |
| 10 | 8-B | `apply_depth_constraints` | 완화 후보 채택 + flow 전파 |
| 11 | — | `assign_block_visibility` | 노출 여부만 |
| 12 | — | `correct_title_box_depths` | **최종 보정 (5단계)** |
| 13 | 7.5-B | `flatten_table_internal_blocks` | 확정 depth 사용 |
| 14 | 9-A/B | `validate_blocks` | 검증 |
| 15 | 9-C | `validate_table_internal_blocks` | 검증 |
| 16 | 10-C | `generate_depth_text_preview` | 산출물 |
| 17 | 10-D | `generate_llm_context` | 산출물 |

### 5단계 — 1차 depth 규칙

`_resolve_depth_first_pass` (`add_document_blocks_to_json.py:549`). 위에서부터 우선.

```
peripheral (header/footer/control/section_control) → depth 0, band=peripheral
annotation (caption/footnote/endnote)             → 직전 개체 depth + 1
section_heading                                   → native OUTLINE level + 1
                                                     없으면 style cluster depth_rank
list_item                                         → body_depth + (numbering level - 1)
그 외 (body_text / table / image / shape)         → 직전 heading depth + 1
```

heading 판정은 키워드 없이 **문서 내부 스타일 통계**만 사용한다
(`_build_style_clusters`: 글자 크기·굵기·길이·빈도·후행 다양성 점수제, 임계 3.0).

### 12단계 — 최종 보정 순서

`correct_title_box_depths` (`correct_title_box_depths.py:480`)

```
1. title_box outline depth 보정 (numeric / roman-dash family + anchor 학습)
2. roman-dash family root depth 통일
3. title_box scope 생성 (다음 title_box까지, section 경계 carry-over 포함)
4. scope 내부 paragraph heading 재앵커링 (marker 상대 레벨)
5. heading 하위 flow block: shift 먼저 → 그 다음 clamp
   + _align_ordinal_siblings (서수 형제 정렬)
   + _nest_marker_flow (indent 기반 marker 중첩)
```

marker 상대 레벨 테이블 (`_MARKER_RELATIVE_LEVELS`):
`□ ■` → 1, `○ ◦ ●` → 2, `- · ㆍ` → 3

### depth 우선순위 (최종)

```
목차 anchor  >  title_box outline 보정  >  marker 재앵커링  >  cluster/OUTLINE 1차값
```

`_is_toc_depth0_anchor`인 블록은 이후 보정에서 변경하지 않는다.

---

## 3. 규칙별 실제 발동 횟수 (문서 3종)

| 보정 규칙 | 발동 |
|---|---|
| `flow_shift_from_paragraph_heading` | 1,055 |
| `paragraph_heading_reanchor_in_title_scope` | 222 |
| `flow_depth_clamp_under_paragraph_heading` | 72 |
| `toc_depth0~3_anchor` | 89 |
| `marker_indent_nesting` | 14 |
| `title_box_outline_correction` | 7 |
| `annotation_depth_under_marker` | 3 |
| `ordinal_sibling_alignment` | 1 |

**Stage 8-B 완화 채택**: 후보 14건 중 채택 1건(문서 A만, flow 21블록 전파).
sample과 문서 B는 0건.

`depth_band` 분포: body 2,024 / peripheral 101 / annotation 1.

> 저빈도 규칙(1~7회)은 "안 쓰이는 코드"가 아니라 **드물게 쓰이는 코드**다.
> 제거하면 그만큼 depth가 바뀐다.

---

## 4. 표 분류 / 구조화 산출 현황

| 항목 | 값 |
|---|---|
| 전체 표 | 728 (최상위 419 + 중첩 309) |
| `data_table` | 550 (structured 83 / raw_only 95 / not_applicable 372) |
| `key_value_table` | 52 (전부 산출 있음) |
| `title_box` | 126 |
| `caption_or_note_table` | 0 |

**헤더 검출이 구조화의 단일 병목이다.** 상관관계가 예외 0건으로 성립한다.

```
헤더 검출됨 → structured 또는 raw_only
헤더 없음   → not_applicable (100%)
```

XML의 `hp:tc@header="1"`(저자 선언 헤더)은 `TableParser`가 파싱해
`flags.header`에 넣지만 **헤더 판정에서 소비되지 않는다**. 선언된 26개 표 기준
정확 16 / 미검출 8 / 과대 2.

`hp:tbl@repeatHeader`는 728개 표 전부 `"1"`이라 변별력이 없다.

---

## 5. 산출물

`save_pipeline_outputs` (`pipeline.py:141`) → `output/results/<문서명>/`

| 파일 | 내용 |
|---|---|
| `final_debug.json` | 최종 전체 상태. 키: `summary` / `tables` / `blocks_document` / `table_internal_blocks` / `warnings` / `quality_report` |
| `llm_context.txt` | 텍스트 손실 없는 LLM 입력용 (표 셀·캡션 포함, 절단 없음) |
| `depth_text_preview_raw.txt` | 사람용 계층 프리뷰 (전체 블록) |
| `depth_text_preview_clean.txt` | 〃 (`include_in_preview=false` 제외) |

`depth_text_preview_*`는 디버그용이라 표 내부 텍스트를 넣지 않고
(`INCLUDE_TABLE_INTERNAL_PREVIEW = False`) 120자에서 자른다.
텍스트 완전성이 필요하면 `llm_context.txt`를 쓸 것.

---

## 6. 검증 도구

| 도구 | 용도 |
|---|---|
| `tools/regression_check.py` | 불변식 I1~I11 (텍스트 커버리지, 표 총량, 캡션·ctrl 보존 등) |
| `tools/refactor_guard.py` | 리팩토링용. 산출물 sha256 동일성만 판정 |
| `tools/run_document.py` | 임의 문서로 파이프라인 실행 |

리팩토링 시에는 `refactor_guard`가 기준이다. 불변식 통과만으로는
동작 불변을 보장하지 못한다.
