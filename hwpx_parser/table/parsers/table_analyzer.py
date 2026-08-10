#================================================
# parser/table/parsers/table_analyzer.py
#================================================

from __future__ import annotations

from typing import Any

from hwpx_document.table import Table
from hwpx_document.table.elements.table_analysis import TableValidation
from hwpx_document.table.utils import get_table_cells
from hwpx_parser.parser_context import ParserContext


class TableAnalyzer:
    """
    TableParser가 생성한 Table 객체를 받아
    rowCnt, colCnt, cellAddr, cellSpan 기준으로
    실제 표 grid 구조를 검증한다.

    context가 전달되면 header.xml 참조 기반 스타일 검증도 수행한다.
    """

    @classmethod
    def analyze(
        cls,
        table: Table,
        context: ParserContext | None = None,
    ) -> Table:
        """
        역할: 파싱된 Table 객체의 구조와 header 참조를 검증하고 validation 결과를 붙인다.
        입력 데이터: table(검증할 Table), context(header 참조 검증용 ParserContext 또는 None).
        출력 데이터: validation 속성이 채워진 동일 Table 객체를 반환한다.
        """
        validation = TableValidation(
            table_id=table.table_id,
            declared_row_count=table.row_count,
            declared_col_count=table.col_count,
            actual_tr_count=len(table.rows),
            actual_cell_count=len(get_table_cells(table)),
        )

        cls._validate_row_count(table, validation)
        cls._validate_row_order(table, validation)
        cls._validate_cell_addr_and_span(table, validation)
        cls._calculate_actual_max_size(table, validation)
        cls._build_grid(table, validation)

        if context is not None:
            cls._validate_paragraph_style_refs(table, validation, context)
            cls._validate_character_style_refs(table, validation, context)

        table.validation = validation

        for cell in get_table_cells(table):
            for nested_table in getattr(cell, "nested_tables", []):
                cls.analyze(nested_table, context)

        return table

    @staticmethod
    def _add_issue(
        validation: TableValidation,
        code: str,
        message: str,
        severity: str = "ERROR",
        row_id: str | None = None,
        cell_id: str | None = None,
        row_index: int | None = None,
        col_index: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        역할: 검증 오류/경고 정보를 표준 dict 형태로 validation.issues에 추가한다.
        입력 데이터: validation, code, message, severity, row/cell 위치 정보, details.
        출력 데이터: 반환값은 없고, issues가 갱신되며 severity가 ERROR이면 is_valid가 False로 변경된다.
        """
        validation.issues.append(
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
        )

        if severity == "ERROR":
            validation.is_valid = False

    @classmethod
    def _validate_row_count(
        cls,
        table: Table,
        validation: TableValidation,
    ) -> None:
        """
        역할: hp:tbl@rowCnt 선언값과 실제 hp:tr 개수를 비교한다.
        입력 데이터: table(검증 대상 Table), validation(갱신할 TableValidation).
        출력 데이터: 반환값은 없고, 불일치 시 row count 플래그와 이슈가 추가된다.
        """
        if table.row_count != len(table.rows):
            validation.has_row_count_mismatch = True

            cls._add_issue(
                validation,
                code="ROW_COUNT_MISMATCH",
                message="rowCnt와 실제 hp:tr 개수가 다릅니다.",
                severity="ERROR",
                details={
                    "declared_row_count": table.row_count,
                    "actual_tr_count": len(table.rows),
                },
            )

    @classmethod
    def _validate_row_order(
        cls,
        table: Table,
        validation: TableValidation,
    ) -> None:
        """
        역할: hp:tr XML 등장 순서(xml_order_index)와 셀이 선언한 rowAddr(declared_row_addr)을 비교한다.
        입력 데이터: table(검증 대상 Table), validation(갱신할 TableValidation).
        출력 데이터: 반환값은 없고, 순서 불일치 시 has_row_order_mismatch 플래그와 이슈가 추가된다.
        """
        for row in table.rows:
            if row.declared_row_addr is None or row.xml_order_index is None:
                continue

            if row.xml_order_index != row.declared_row_addr:
                validation.has_row_order_mismatch = True

                cls._add_issue(
                    validation,
                    code="ROW_ORDER_MISMATCH",
                    message="hp:tr XML 등장 순서와 cellAddr@rowAddr 선언값이 다릅니다.",
                    severity="WARNING",
                    row_id=row.row_id,
                    details={
                        "xml_order_index": row.xml_order_index,
                        "declared_row_addr": row.declared_row_addr,
                    },
                )

    @classmethod
    def _validate_cell_addr_and_span(
        cls,
        table: Table,
        validation: TableValidation,
    ) -> None:
        """
        역할: 각 셀의 cellAddr 좌표, cellSpan 값, 선언된 행/열 범위 초과 여부를 검증한다.
        입력 데이터: table(검증 대상 Table), validation(갱신할 TableValidation).
        출력 데이터: 반환값은 없고, 좌표/병합/범위 관련 플래그와 이슈가 갱신된다.
        """
        for cell in get_table_cells(table):
            if cell.row_addr is None or cell.col_addr is None:
                validation.has_missing_cell_addr = True

                cls._add_issue(
                    validation,
                    code="MISSING_CELL_ADDR",
                    message="cellAddr의 rowAddr 또는 colAddr이 없습니다.",
                    severity="ERROR",
                    cell_id=cell.cell_id,
                    details={
                        "row_addr": cell.row_addr,
                        "col_addr": cell.col_addr,
                    },
                )
                continue

            if cell.row_addr < 0 or cell.col_addr < 0:
                validation.has_invalid_cell_addr = True

                cls._add_issue(
                    validation,
                    code="INVALID_CELL_ADDR",
                    message="cellAddr의 rowAddr 또는 colAddr이 음수입니다.",
                    severity="ERROR",
                    cell_id=cell.cell_id,
                    row_index=cell.row_addr,
                    col_index=cell.col_addr,
                    details={
                        "row_addr": cell.row_addr,
                        "col_addr": cell.col_addr,
                    },
                )

            if cell.row_span < 1 or cell.col_span < 1:
                validation.has_invalid_cell_span = True

                cls._add_issue(
                    validation,
                    code="INVALID_CELL_SPAN",
                    message="cellSpan의 rowSpan 또는 colSpan이 1보다 작습니다.",
                    severity="ERROR",
                    cell_id=cell.cell_id,
                    row_index=cell.row_addr,
                    col_index=cell.col_addr,
                    details={
                        "row_span": cell.row_span,
                        "col_span": cell.col_span,
                    },
                )

            if cell.row_addr + cell.row_span > table.row_count:
                validation.has_out_of_range_cell = True

                cls._add_issue(
                    validation,
                    code="ROW_OUT_OF_RANGE",
                    message="셀이 선언된 rowCnt 범위를 벗어납니다.",
                    severity="ERROR",
                    cell_id=cell.cell_id,
                    row_index=cell.row_addr,
                    col_index=cell.col_addr,
                    details={
                        "row_addr": cell.row_addr,
                        "row_span": cell.row_span,
                        "declared_row_count": table.row_count,
                        "end_row": cell.row_addr + cell.row_span,
                    },
                )

            if cell.col_addr + cell.col_span > table.col_count:
                validation.has_out_of_range_cell = True

                cls._add_issue(
                    validation,
                    code="COL_OUT_OF_RANGE",
                    message="셀이 선언된 colCnt 범위를 벗어납니다.",
                    severity="ERROR",
                    cell_id=cell.cell_id,
                    row_index=cell.row_addr,
                    col_index=cell.col_addr,
                    details={
                        "col_addr": cell.col_addr,
                        "col_span": cell.col_span,
                        "declared_col_count": table.col_count,
                        "end_col": cell.col_addr + cell.col_span,
                    },
                )

    @staticmethod
    def _calculate_actual_max_size(
        table: Table,
        validation: TableValidation,
    ) -> None:
        """
        역할: 셀 좌표와 병합 크기를 기준으로 실제 표가 차지하는 최대 행/열 크기를 계산한다.
        입력 데이터: table(검증 대상 Table), validation(갱신할 TableValidation).
        출력 데이터: 반환값은 없고, actual_max_row_count/actual_max_col_count 및 불일치 플래그가 갱신된다.
        """
        max_row = 0
        max_col = 0

        for cell in get_table_cells(table):
            if cell.row_addr is None or cell.col_addr is None:
                continue

            if cell.row_span < 1 or cell.col_span < 1:
                continue

            max_row = max(max_row, cell.row_addr + cell.row_span)
            max_col = max(max_col, cell.col_addr + cell.col_span)

        validation.actual_max_row_count = max_row
        validation.actual_max_col_count = max_col

        if max_row != table.row_count:
            validation.has_row_count_mismatch = True
            validation.is_valid = False

        if max_col != table.col_count:
            validation.has_col_count_mismatch = True
            validation.is_valid = False

    @classmethod
    def _build_grid(
        cls,
        table: Table,
        validation: TableValidation,
    ) -> None:
        """
        역할: 선언된 rowCnt/colCnt 크기의 grid를 만들고 각 셀을 좌표와 span에 따라 배치한다.
        입력 데이터: table(검증 대상 Table), validation(갱신할 TableValidation).
        출력 데이터: 반환값은 없고, validation.grid와 중복/빈 슬롯 관련 플래그 및 이슈가 갱신된다.
        """
        row_count = table.row_count
        col_count = table.col_count

        if row_count <= 0 or col_count <= 0:
            return

        grid: list[list[dict[str, Any]]] = [
            [
                {
                    "row_index": r,
                    "col_index": c,
                    "table_id": table.table_id,
                    "row_id": None,
                    "cell_id": None,
                    "is_origin": False,
                    "is_covered": False,
                    "is_empty": True,
                }
                for c in range(col_count)
            ]
            for r in range(row_count)
        ]

        for cell in get_table_cells(table):
            if cell.row_addr is None or cell.col_addr is None:
                continue

            if cell.row_span < 1 or cell.col_span < 1:
                continue

            start_row = cell.row_addr
            start_col = cell.col_addr
            end_row = start_row + cell.row_span
            end_col = start_col + cell.col_span

            if end_row > row_count or end_col > col_count:
                continue

            for r in range(start_row, end_row):
                for c in range(start_col, end_col):
                    slot = grid[r][c]

                    if slot["cell_id"] is not None:
                        validation.has_duplicated_slot = True

                        cls._add_issue(
                            validation,
                            code="DUPLICATED_GRID_SLOT",
                            message="하나의 grid slot에 둘 이상의 셀이 배치되었습니다.",
                            severity="ERROR",
                            cell_id=cell.cell_id,
                            row_index=r,
                            col_index=c,
                            details={
                                "existing_cell_id": slot["cell_id"],
                                "new_cell_id": cell.cell_id,
                            },
                        )
                        continue

                    slot["row_id"] = getattr(cell, "row_id", None)
                    slot["cell_id"] = cell.cell_id
                    slot["is_empty"] = False

                    if r == start_row and c == start_col:
                        slot["is_origin"] = True
                    else:
                        slot["is_covered"] = True

        for r in range(row_count):
            for c in range(col_count):
                if grid[r][c]["cell_id"] is None:
                    validation.has_empty_slot = True
                    validation.is_irregular = True

                    cls._add_issue(
                        validation,
                        code="EMPTY_GRID_SLOT",
                        message="채워지지 않은 grid slot이 있습니다.",
                        severity="WARNING",
                        row_index=r,
                        col_index=c,
                        details={
                            "row_index": r,
                            "col_index": c,
                        },
                    )

        validation.grid = grid

    @classmethod
    def _validate_paragraph_style_refs(
        cls,
        table: Table,
        validation: TableValidation,
        context: ParserContext,
    ) -> None:
        """
        역할: 셀 문단의 styleIDRef와 paraPrIDRef가 header.xml에 존재하는지 검증한다.
        입력 데이터: table(검증 대상 Table), validation(갱신할 TableValidation), context(header 조회용 ParserContext).
        출력 데이터: 반환값은 없고, 누락된 style/paraPr 참조 플래그와 이슈가 갱신된다.
        """
        for cell in get_table_cells(table):
            for paragraph in cell.paragraphs:
                style_id = paragraph.style_id_ref
                para_pr_id = paragraph.para_pr_id_ref

                if style_id is not None and context.get_style_raw(style_id) is None:
                    validation.has_missing_style_ref = True

                    cls._add_issue(
                        validation,
                        code="MISSING_STYLE_REF",
                        message="문단의 styleIDRef가 header.xml의 hh:style에 존재하지 않습니다.",
                        severity="ERROR",
                        cell_id=cell.cell_id,
                        row_index=cell.row_addr,
                        col_index=cell.col_addr,
                        details={
                            "paragraph_id": paragraph.paragraph_id,
                            "style_id_ref": style_id,
                        },
                    )

                if para_pr_id is not None and context.get_para_pr_raw(
                    para_pr_id=para_pr_id
                ) is None:
                    validation.has_missing_para_pr_ref = True

                    cls._add_issue(
                        validation,
                        code="MISSING_PARA_PR_REF",
                        message="문단의 paraPrIDRef가 header.xml의 hh:paraPr에 존재하지 않습니다.",
                        severity="ERROR",
                        cell_id=cell.cell_id,
                        row_index=cell.row_addr,
                        col_index=cell.col_addr,
                        details={
                            "paragraph_id": paragraph.paragraph_id,
                            "para_pr_id_ref": para_pr_id,
                        },
                    )

                if para_pr_id is None and style_id is not None:
                    resolved = context.header.resolve_para_pr_id(
                        para_pr_id=None,
                        style_id=style_id,
                    )

                    if resolved is not None and context.get_para_pr_raw(
                        para_pr_id=resolved
                    ) is None:
                        validation.has_missing_para_pr_ref = True

                        cls._add_issue(
                            validation,
                            code="MISSING_RESOLVED_PARA_PR_REF",
                            message="styleIDRef로 연결된 paraPrIDRef가 header.xml의 hh:paraPr에 존재하지 않습니다.",
                            severity="ERROR",
                            cell_id=cell.cell_id,
                            row_index=cell.row_addr,
                            col_index=cell.col_addr,
                            details={
                                "paragraph_id": paragraph.paragraph_id,
                                "style_id_ref": style_id,
                                "resolved_para_pr_id": resolved,
                            },
                        )

    @classmethod
    def _validate_character_style_refs(
        cls,
        table: Table,
        validation: TableValidation,
        context: ParserContext,
    ) -> None:
        """
        역할: 각 run의 charPrIDRef가 header.xml의 charPr 목록에 존재하는지 검증한다.
        입력 데이터: table(검증 대상 Table), validation(갱신할 TableValidation), context(header 조회용 ParserContext).
        출력 데이터: 반환값은 없고, 누락된 charPr 참조 플래그와 이슈가 갱신된다.
        """
        for cell in get_table_cells(table):
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    char_pr_id = run.char_pr_id_ref

                    if char_pr_id is None:
                        continue

                    if context.get_char_pr_raw(char_pr_id) is not None:
                        continue

                    validation.has_missing_char_pr_ref = True

                    cls._add_issue(
                        validation,
                        code="MISSING_CHAR_PR_REF",
                        message="run의 charPrIDRef가 header.xml의 hh:charPr에 존재하지 않습니다.",
                        severity="ERROR",
                        cell_id=cell.cell_id,
                        row_index=cell.row_addr,
                        col_index=cell.col_addr,
                        details={
                            "paragraph_id": paragraph.paragraph_id,
                            "run_id": run.run_id,
                            "char_pr_id_ref": char_pr_id,
                        },
                    )
