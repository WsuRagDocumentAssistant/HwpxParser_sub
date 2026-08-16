#================================================
# pipeline.py
#
# HWPX 표/블록 분석 파이프라인 오케스트레이터.
#
# 각 단계는 데이터 클래스(pipeline_models)를 인메모리로 주고받는다.
# 파일 저장은 save_pipeline_outputs에서만 수행하며,
# 산출물은 디버깅용 최종 JSON(final_debug.json)과
# 계층 시각화용 txt(depth_text_preview_raw/clean.txt)뿐이다.
#================================================

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .pipeline_models import (
    BlocksDocument,
    PipelineResult,
    TableAnalysis,
)
from .add_table_preprocess_to_json import preprocess_tables
from .add_table_grid_to_json import add_table_grid
from .add_table_hierarchy_to_json import add_table_hierarchy
from .make_body_linking_table_json import build_body_linking_tables
from .add_document_blocks_to_json import build_document_blocks
from .resolve_floating_anchors import resolve_floating_anchors
from .add_table_hierarchy_ref_to_blocks import (
    add_table_hierarchy_ref_to_blocks,
)
from .resolve_block_depth_candidates import (
    resolve_block_depth_candidates,
)
from .add_toc_depth0_anchors import add_toc_depth0_anchors
from .apply_depth_constraints import apply_depth_constraints
from .assign_block_visibility import assign_block_visibility
from .correct_title_box_depths import correct_title_box_depths
from .propagate_toc_anchor_depth import propagate_toc_anchor_depth
from .flatten_table_internal_blocks import (
    flatten_table_internal_blocks,
)
from .validate_blocks import validate_blocks
from .validate_table_internal_blocks import (
    validate_table_internal_blocks,
)
from .generate_depth_text_preview import generate_depth_text_preview
from .generate_llm_context import generate_llm_context
from ..document.header_data import HeaderData

import logging

# 라이브러리는 조용한 것이 기본이다. 단계 보고를 보려면 쓰는 쪽에서
# logging 을 켠다. tools 는 그렇게 하고 있다.
log = logging.getLogger(__name__)


#------------------------------------------------
# 파이프라인 실행
#------------------------------------------------

def run_analysis_pipeline(
    raw_tables: list[dict[str, Any]],
    section_paths: list[str | Path],
    header: HeaderData,
    summary: dict[str, Any],
) -> PipelineResult:
    """
    역할: 표 분석 → 블록 레지스트리 → depth 판정 → 검증 → 계층 프리뷰까지
          전체 분석 파이프라인을 인메모리로 실행한다.
    입력 데이터: raw_tables(파서 직렬화 표 리스트), section_paths(section*.xml 경로),
                 header(HeaderData), summary(파싱 요약 dict).
    출력 데이터: PipelineResult(모든 단계의 최종 상태).
    """
    #--- 표 분석: preprocess → grid → hierarchy → body linking -------
    tables = TableAnalysis(raw=raw_tables)
    tables.analyzed = preprocess_tables(tables.raw)
    add_table_grid(tables.analyzed)
    add_table_hierarchy(tables.analyzed)
    tables.body_linking = build_body_linking_tables(tables.analyzed)

    #--- 문서 전역 블록 레지스트리 생성 -------------------------------
    blocks_doc: BlocksDocument = build_document_blocks(
        section_paths=section_paths,
        header=header,
    )

    # Stage 4-B: floating object anchor를 paragraph_index 기준으로 구조적 확인
    resolve_floating_anchors(blocks_doc)

    # Stage 7.5-A: table block에 표 hierarchy 요약 메타데이터 연결
    add_table_hierarchy_ref_to_blocks(blocks_doc, tables.analyzed)

    # Stage 8-A: depth 후보 top-k 재생성
    resolve_block_depth_candidates(blocks_doc)

    # Stage 8-A': 목차 기반 depth 0 anchor 생성.
    # 매칭 성공 시 해당 block을 depth 0 anchor로 확정하고(기존 depth 0 추정보다
    # 우선), 실패 시 block을 바꾸지 않아 기존 로직이 fallback으로 동작한다.
    add_toc_depth0_anchors(blocks_doc, tables.raw)

    # Stage 8-B: 복수 후보 heading의 보수적 제약 판정 + 채택 시 flow 전파
    apply_depth_constraints(blocks_doc)

    # v3.1 보완: visibility 부여 (preview/LLM 노출 여부만 결정, depth는 불변)
    assign_block_visibility(blocks_doc)

    # v3.1 보완: title_box outline depth 보정 + scope 내부 paragraph heading
    # 재앵커링 + flow shift/clamp. 8-B의 flow 전파가 보정을 덮어쓰지 않도록
    # 반드시 8-B 이후, flatten(7.5-B) 이전에 실행한다.
    correct_title_box_depths(blocks_doc, tables.analyzed)

    # Stage 8-C: 목차 anchor 하위 flow 전파 + 잔여 구간 clamp.
    # anchor는 자기 depth만 확정하고 뒤 블록은 옛 좌표에 남아 단절되므로
    # 모든 depth 보정이 끝난 뒤 마지막으로 연결한다.
    propagate_toc_anchor_depth(blocks_doc)

    # Stage 7.5-B: 표 내부(row/cell/nested table) 평탄화.
    # base_depth로 최종 확정 depth를 쓰기 위해 depth 보정 뒤에 둔다.
    table_internal = flatten_table_internal_blocks(blocks_doc, tables.analyzed)

    # Stage 9-A/9-B: blocks + table_internal 검증 → ValidationReport 생성
    validation = validate_blocks(blocks_doc, table_internal)

    # Stage 9-C: table internal 구조 무결성 검증.
    # validate_blocks가 만든 report에 stage9c warning append +
    # table_internal_validation 키를 merge한다.
    validate_table_internal_blocks(
        blocks_doc, tables.analyzed, table_internal, validation,
    )

    # Stage 10-C: depth 들여쓰기 기반 사람용 계층 프리뷰 생성 (인메모리)
    preview = generate_depth_text_preview(blocks_doc, table_internal)

    # Stage 10-D: LLM 입력용 텍스트 (자르지 않고 표 내부까지 포함)
    llm_context = generate_llm_context(blocks_doc, table_internal)

    return PipelineResult(
        summary=summary,
        tables=tables,
        blocks=blocks_doc,
        table_internal=table_internal,
        validation=validation,
        preview=preview,
        llm_context=llm_context,
    )


#------------------------------------------------
# 최종 산출물 저장
#------------------------------------------------

def save_pipeline_outputs(
    result: PipelineResult,
    output_dir: str | Path,
    debug: bool = False,
) -> dict[str, Path]:
    """
    역할: 파이프라인 최종 산출물을 저장한다.
          - depth_text_preview_raw.txt / depth_text_preview_clean.txt:
            계층 시각화용 txt
          - llm_context.txt
          - final_debug.json: debug=True 일 때만. 디버깅용 전체 최종 상태.
    입력 데이터: result(PipelineResult), output_dir(저장 폴더),
                debug(final_debug.json 도 쓸지).
    출력 데이터: 산출물 이름 -> 경로 dict. 쓰지 않은 것은 키가 없다.

    final_debug.json 은 조사용이지 제품이 아니다. 200MB 가까이 되는 데다
    파이프라인 단계들은 이미 인메모리로 주고받으므로 평소 실행에는 필요가 없다.
    회귀 검증(regression_check check-pipeline)과 동일성 가드
    (refactor_guard verify-pipeline)는 파일 없이 결과 객체를 직접 본다.
    tools/audit/* 처럼 이 파일을 읽는 조사 도구를 쓸 때만 debug=True 로 켠다.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    debug_json_path = output_dir / "final_debug.json"
    raw_preview_path = output_dir / "depth_text_preview_raw.txt"
    clean_preview_path = output_dir / "depth_text_preview_clean.txt"
    llm_context_path = output_dir / "llm_context.txt"

    if debug:
        with debug_json_path.open("w", encoding="utf-8") as f:
            json.dump(result.to_debug_dict(), f, ensure_ascii=False, indent=2)

    if result.preview is not None:
        with raw_preview_path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(result.preview.raw_text)
        with clean_preview_path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(result.preview.clean_text)

    if result.llm_context is not None:
        with llm_context_path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(result.llm_context.text)

    log.info("===========================================")
    log.info("[RESULT SAVED]")
    if debug:
        log.info(f"final_debug        : {debug_json_path}")
    else:
        # 여기서 em dash 를 쓰면 cp949 콘솔에서 죽는다. 라이브러리 출력은
        # 콘솔 인코딩에 기대지 않는다.
        log.info("final_debug        : (안 씀. 필요하면 --debug)")
    log.info(f"depth_preview_raw  : {raw_preview_path}")
    log.info(f"depth_preview_clean: {clean_preview_path}")
    log.info(f"llm_context        : {llm_context_path}")
    log.info("===========================================")

    saved = {
        "depth_text_preview_raw": raw_preview_path,
        "depth_text_preview_clean": clean_preview_path,
        "llm_context": llm_context_path,
    }
    if debug:
        saved["final_debug"] = debug_json_path
    return saved
