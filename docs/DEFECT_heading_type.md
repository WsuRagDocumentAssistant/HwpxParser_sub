# heading_type / numbering_level 추출 결함

`hp:paraPr` 의 `heading` 선언을 문단 인라인에서만 찾고 header.xml 의 스타일
정의를 따라가지 않아, 개요·불릿 수준이 전부 소실된다.

발견 경위는 컬럼 판정 감사다. `heading_type` 이 251개 인스턴스 전부 `NONE`
이라 상수로 잡혔고, 원본을 대조하다 실제로는 `BULLET` 을 선언한 문단이
있다는 것이 드러났다.

## 증상

| | 값 |
|---|---|
| `blocks[].style_features.heading_type` | 251개 전부 `NONE` |
| `blocks[].style_features.heading_level_native` | 411개 전부 `null` |
| `blocks[].style_features.numbering_level` | 411개 전부 `null` |

원본에는 `NONE` 이 아닌 선언이 있다.

```
header.xml  paraPr/heading@type   412개  {NONE 393, BULLET 13, OUTLINE 6}
```

## 원인

`hwpx_analysis/add_document_blocks_to_json.py:88`

```python
heading = _find_child_raw(raw, "heading")
if heading is not None:
    h_attrs = heading.get("attrs", {})
    h_type = h_attrs.get("type")
    ...
    features["heading_type"] = h_type
    if h_type == "OUTLINE":
        features["heading_level_native"] = level
    elif h_type in ("NUMBER", "BULLET"):
        features["numbering_level"] = level
```

`raw` 는 본문 문단(`hp:p`)이다. section*.xml 의 문단에는 `heading` 자식이
하나도 없다(측정: 0개). 실제 선언은 header.xml 의 스타일 정의에 있고,
문단은 `@paraPrIDRef` 로 그것을 가리킨다.

```
header.xml  head/refList/paraProperties/paraPr/heading
```

참조를 따라가지 않으므로 `heading` 을 찾지 못하고, 값이 채워지는 경로는
기본값 `NONE` 뿐이다.

## 영향 범위

본문 문단 **57개**가 `BULLET` 을 선언한 paraPr 를 참조한다.

| paraPr id | 선언 | 참조 문단 수 |
|---|---|---|
| 241 | BULLET | 31 |
| 245 | BULLET | 10 |
| 243 | BULLET | 6 |
| 336 | BULLET | 3 |
| 85 | BULLET | 3 |
| 99 | BULLET | 2 |
| 71 | BULLET | 1 |
| 246 | BULLET | 1 |

(OUTLINE 을 선언한 paraPr 6종은 이 문서 본문에서 참조되지 않는다.)

## 회귀 범위

`numbering_level` 을 읽는 곳은 두 군데다. 실행 중 읽기 추적으로 확인했다.

- `hwpx_analysis/correct_title_box_depths.py`
- `hwpx_analysis/validate_blocks.py`

둘 다 depth 판정 경로다. 지금은 값이 전부 `null` 이라 이 분기가 돌지
않는다. 고치면 depth 가 움직일 수 있으므로 `tools/refactor_guard.py` 와
`tools/regression_check.py` 를 반드시 함께 돌려야 한다. 계층 정확도는
`tools/audit/hierarchy_score.py` 로 전후를 비교한다.

## 확인 방법

```bash
python -m tools.audit.column_verdict prov.json
```

`KNOWN_NOT_VALID` fixture 가 이 두 컬럼이 `valid` 로 올라오는 것을 막는다.
고치기 전에 fixture 를 먼저 손봐야 한다.

## 이 기록이 결함이 아니라고 확인한 것

`para_pr_id_ref` 와 `resolved_para_pr_id` 가 251개 인스턴스 전부 값이 같다.
`hwpx_document/header_data.py` 의 해소 함수가 `para_pr_id` 가 있으면 그대로
돌려주고, 이 문서는 모든 `hp:p` 에 `@paraPrIDRef` 가 있어 해소가 no-op 인
것이다. 설계대로이며 위 결함과 무관하다.
