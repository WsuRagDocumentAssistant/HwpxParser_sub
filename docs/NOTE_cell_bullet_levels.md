# 표 셀 안 불릿 수준의 보존 위치

컬럼 판정 감사 중 `heading_type` 이 251개 전부 `NONE` 인 것을 결함으로
오진했다가 정정하는 과정에서 확인한 내용이다. 결함 기록이 아니라 관찰
기록이다.

## 확인된 사실 (측정)

`BULLET` 을 선언한 paraPr 를 참조하는 문단은 **57개이고 전부 표 셀(`tc`)
안에 있다.** 본문 직속 0개, 도형 안 0개.

```
header.xml  paraPr/heading@type   412개  {NONE 393, BULLET 13, OUTLINE 6}
   비NONE paraPr 를 참조하는 문단  57개  ->  tc 안 57 / 본문직속 0 / 도형안 0
   OUTLINE paraPr 6종은 참조하는 문단이 0개
```

따라서 `blocks[].style_features.heading_type` 이 251개 전부 `NONE` 인 것과
`numbering_level` 이 전부 null 인 것은 **정상이다.** `blocks_document.blocks`
는 본문 블록만 담고, 본문 문단이 참조하는 paraPr 에는 실제로 `NONE` 만
있다.

추출 코드도 header 를 이미 따라간다.

```python
# add_document_blocks_to_json.py:65
resolved_id = header.resolve_para_pr_id(para_pr_id=..., style_id=...)
raw = header.get_para_pr_raw(resolved_id)      # header.xml 의 paraPr 정의
heading = _find_child_raw(raw, "heading")
```

`paraPr 241` 을 직접 해소하면 `{"type": "BULLET", "level": "0"}` 이 나온다.

## 확인된 사실 (측정) - 보존 위치

셀 문단의 불릿은 `style_features` 가 아니라 `paragraph_auto_labels` 에
남는다.

```
{"label_kind": "bullet", "bullet_id": "9", "text": "-",
 "is_private_use": false, "level": 0}
```

개수가 맞는다.

```
BULLET paraPr 참조 문단          57개
bullet 라벨                      57개  (internal_blocks 34개에 분산)
```

한 셀 블록이 여러 문단을 담으므로 블록 수(34)와 문단 수(57)가 다른 것은
정상이다. `level` 은 57개 전부 0 이다.

`table_internal_blocks.internal_blocks[]` 와
`tables.analyzed[].preprocess.cells[].text` 가 같은 라벨 dict 객체를 공유한다
(참조 동일성 관측에서 확인된 57개 공유 객체가 이것이다).

## 판단이 필요한 설계 질문

셀 내부 불릿 수준을 계층 판정이 소비해야 하는가.

지금 `correct_title_box_depths` 는 본문 블록의 `numbering_level` 만 본다.
셀 안 불릿은 `paragraph_auto_labels.level` 로 남아 있지만 depth 판정에
쓰이지 않는다. 쓸 값인지, 쓴다면 어느 단계에서 읽을지는 측정으로 답할 수
없고 결정해야 하는 사항이다.

## 오진 경위 (같은 실수를 막기 위해)

`paraPrIDRef` 로 참조 문단 57개를 세고, 그 문단이 본문에 있다고 전제했다.
부모가 `tc` 인지 확인하지 않았다. 같은 세션에서 `subList/@vertAlign` 이
2374 대 2150 으로 어긋나 보이던 것도 부모 컨텍스트(`tc` 직속인지)를 봐야
풀렸는데, 그 교훈을 이 리드에는 적용하지 않았다.
