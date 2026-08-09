#================================================
# pipeline_models.py
#
# 파이프라인 단계 간에 주고받는 인메모리 데이터 클래스 모음.
#
# 기존에는 각 단계가 JSON 파일(tables.json, tables_preprocessed.json,
# blocks.json 등)을 읽고 쓰는 방식으로 연결되어 있었다.
# 이제 각 단계는 아래 데이터 클래스를 직접 주고받으며,
# 파일 저장은 파이프라인 마지막의 디버깅용 최종 JSON과
# 계층 시각화용 txt 두 종류만 수행한다.
#================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


#------------------------------------------------
# 표 분석 상태
#------------------------------------------------

@dataclass
class TableAnalysis:
    """
    역할: 표 분석 파이프라인의 상태를 단계 순서대로 담는다.
    - raw: 파서 직렬화 원본 (구 tables.json)
    - analyzed: preprocess + grid + hierarchy가 반영된 표 리스트
      (구 tables_preprocessed.json → tables_hierarchical.json)
    - body_linking: 본문-표 연결용 경량 프로젝션
      (구 tables_hierarchical_for_body_linking.json)
    """
    raw: list[dict[str, Any]]
    analyzed: list[dict[str, Any]] = field(default_factory=list)
    body_linking: list[dict[str, Any]] = field(default_factory=list)


#------------------------------------------------
# 문서 블록 레지스트리
#------------------------------------------------

@dataclass
class BlocksDocument:
    """
    역할: 문서 전역 블록 레지스트리 (구 blocks.json).
    - document: 문서 메타데이터 (source_type, section_count, style_summary 등)
    - blocks: block dict 리스트 (각 단계가 필드를 추가하며 갱신)
    - quality: 단계별 품질/통계 정보
    """
    document: dict[str, Any]
    blocks: list[dict[str, Any]]
    quality: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document": self.document,
            "blocks": self.blocks,
            "quality": self.quality,
        }

#------------------------------------------------
# 표 내부 평탄화 결과
#------------------------------------------------

@dataclass
class TableInternalBlocks:
    """
    역할: 표 내부(row/cell/nested table) 평탄화 결과
          (구 table_internal_blocks.json).
    """
    document: dict[str, Any]
    tables: list[dict[str, Any]]
    internal_blocks: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "document": self.document,
            "tables": self.tables,
            "internal_blocks": self.internal_blocks,
        }

#------------------------------------------------
# 검증 결과
#------------------------------------------------

@dataclass
class ValidationReport:
    """
    역할: 블록/표 내부 검증 결과 (구 warnings.json / quality_report.json).
    validate_blocks가 생성하고 validate_table_internal_blocks가 병합한다.
    """
    warnings: list[dict[str, Any]] = field(default_factory=list)
    quality_report: dict[str, Any] = field(default_factory=dict)


#------------------------------------------------
# 계층 시각화 프리뷰
#------------------------------------------------

@dataclass
class DepthTextPreview:
    """
    역할: depth 들여쓰기 기반 사람용 계층 프리뷰 텍스트.
    raw_text = 전체 block, clean_text = preview 비노출 block 제외.
    """
    raw_text: str
    clean_text: str
    line_counts: dict[str, int] = field(default_factory=dict)
    max_depth: int = 0


#------------------------------------------------
# LLM 입력용 텍스트
#------------------------------------------------

@dataclass
class LlmContextText:
    """
    역할: 텍스트 손실이 없는 LLM 입력용 계층 텍스트.
    DepthTextPreview와 목적이 다르다. preview는 사람용 디버그 산출물이라
    표 내부 텍스트를 빼고 120자에서 자르지만, 이쪽은 자르지 않고
    표 내부 cell text/caption까지 포함한다.
    """
    text: str
    stats: dict[str, Any] = field(default_factory=dict)


#------------------------------------------------
# 파이프라인 최종 결과
#------------------------------------------------

@dataclass
class PipelineResult:
    """
    역할: 파이프라인 전체의 최종 상태.
    to_debug_dict()가 디버깅용 최종 JSON의 내용을 만든다.
    """
    summary: dict[str, Any]
    tables: TableAnalysis
    blocks: BlocksDocument
    table_internal: TableInternalBlocks | None = None
    validation: ValidationReport | None = None
    preview: DepthTextPreview | None = None
    llm_context: LlmContextText | None = None

    def to_debug_dict(self) -> dict[str, Any]:
        """
        디버깅용 최종 JSON 내용을 구성한다.
        raw 표(파서 직렬화 원본)는 크기가 커서 제외하고,
        분석이 끝난 최종 상태만 담는다.
        """
        return {
            "summary": self.summary,
            "tables": {
                "analyzed": self.tables.analyzed,
                "body_linking": self.tables.body_linking,
            },
            "blocks_document": self.blocks.to_dict(),
            "table_internal_blocks": (
                self.table_internal.to_dict()
                if self.table_internal is not None else None
            ),
            "warnings": (
                self.validation.warnings
                if self.validation is not None else []
            ),
            "quality_report": (
                self.validation.quality_report
                if self.validation is not None else {}
            ),
        }
