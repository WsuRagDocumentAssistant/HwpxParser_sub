#================================================
# tools/regression_check.py
#
# HWPX 파싱 파이프라인 회귀 검증 하네스.
#
# 파서/분석 코드를 수정할 때 "의도한 변화만 일어났는지"를 기계적으로 확인한다.
# 이 스크립트는 산출물을 읽기만 하며 파이프라인을 실행하지 않는다.
#
# 사용 순서:
#   1) python -m tools.regression_check freeze     # 수정 전 상태를 baseline으로 동결
#   2) (파서/분석 코드 수정)
#   3) python -m tools.run_model --debug                      # 산출물 재생성 (--debug 가 있어야
#                                                  #   final_debug.json 이 나온다)
#   4) python -m tools.regression_check check      # 불변식 + baseline diff 검증
#
# 산출물 파일 없이 검사하기:
#   python -m tools.regression_check check-pipeline
#
#   문서를 직접 파싱해 파이프라인을 돌리고, 결과 객체(PipelineResult)를 그대로
#   검사한다. final_debug.json / llm_context.txt 를 읽지 않는다. JSON 산출물을
#   나중에 없애도 회귀 검증이 계속 돌아가게 하려는 것이다.
#
#   두 경로는 같은 검사 함수(run_invariants)를 공유한다. 검사들이 보는 것은
#   구조뿐이라 '파일에서 읽은 dict' 든 'PipelineResult 를 가리키는 view' 든
#   결과가 같다. 실제로 11개 불변식과 baseline diff가 양쪽에서 동일했다.
#
# 불변식 (I1~I6):
#   I1 텍스트 커버리지 : section*.xml의 모든 hp:t / composeText가 최종 JSON에 존재
#   I2 표 구조 총량    : XML에서 유도한 표/셀/텍스트셀 개수와 산출물이 일치
#   I3 표 내부 불변    : table_internal_blocks 해시가 baseline과 동일
#   I4 표-블록 연결    : 표 블록과 최상위 표가 일대일. 참조를 직접 다시 세며
#                       ref 없음/없는 표 가리킴/중복 참조/블록 없는 표가 모두 0
#   I5 내부 블록 무결성: internal_block_id 중복 0, 부모 참조 미아 0
#   I6 depth 해소     : depth 미해소 블록 0
#   I7 텍스트 소실 0   : baseline에서 텍스트가 있던 블록이 비어버린 경우 0
#   I8 블록 참조 무결성: internal_blocks.source_block_id가 실제 block_id를 가리킴
#   I9 캡션 보존       : hp:caption이 전부 table_caption 엔티티로 남고 개체와 연결됨
#   I10 LLM 산출물 완전성: llm_context.txt에 문서의 모든 텍스트가 존재
#   I11 ctrl 승격 보존  : 머리말/꼬리말/각주/미주가 독립 엔티티로 남고 셀 본문을 오염시키지 않음
#
# I10은 depth_text_preview를 검사하지 않는다. 그 산출물은 표 내부를 빼고
# 120자에서 자르는 사람용 디버그 뷰이며, 그렇게 하도록 만들어진 것이다.
#
# I2는 hp:caption을 셀 본문 집계에서 제외한다. 캡션은 셀 데이터 값이 아니라
# 개체 설명문이기 때문이다. 이 완화가 캡션 유실을 가리지 않도록 I9를 짝으로 둔다.
#
# 주의: 블록 수가 바뀌면 block_id(s{sec}_b{counter:05d})가 전면 재부여되므로
# internal_blocks의 source_block_id도 함께 바뀐다. 이때 I3의 전체 해시는
# 달라지지만 internal_text_hash(셀 텍스트)는 동일해야 하며, 참조가 깨지지
# 않았음은 I8이 보증한다.
#
# I1은 "문자열이 JSON 어딘가에 존재하는가"만 본다. 위치가 바뀌거나 다른 곳에
# 같은 문자열이 있으면 통과하므로 단독으로는 약한 검사다. 블록 단위 소실은
# I7이, 표 셀 단위 소실은 I2/I3가 잡는다. 세 검사를 함께 봐야 한다.
#
# I1/I2/I5/I6은 baseline 없이도 단독 판정이 가능하다.
# I3/I7과 텍스트 diff는 baseline이 있어야 한다.
#================================================

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


#------------------------------------------------
# 기본 경로
#------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

# check-pipeline 은 파이프라인을 직접 돌리므로 저장소 루트를 import 경로에 둔다.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from .defaults import DEFAULT_SOURCE  # noqa: E402
except ImportError as exc:            # noqa: E402
    # tools 가 패키지가 된 뒤로 이 파일은 모듈로 실행해야 한다.
    # 직접 실행하면 부모 패키지를 몰라 상대 import 가 풀리지 않는다.
    raise SystemExit(
        "이 파일은 모듈로 실행하세요.\n"
        "  python -m tools.regression_check ..."
    ) from exc

DEFAULT_CONTENTS_DIR = (REPO_ROOT / "output" / "unpacked"
                        / DEFAULT_SOURCE.stem / "Contents")
DEFAULT_CURRENT = (REPO_ROOT / "output" / "results" / DEFAULT_SOURCE.stem
                   / "final_debug.json")
DEFAULT_BASELINE = (REPO_ROOT / "tools" / "baseline"
                    / (DEFAULT_SOURCE.stem + ".baseline.json"))

# 블록 텍스트 diff의 조인 키.
# block_id는 블록 수가 바뀌면 전면 재부여되므로 키로 쓸 수 없다.
JOIN_KEY_FIELDS = ("source_xml_path", "source_occurrence_index")

# hp:ctrl 하위에서 독립 엔티티로 승격되는 요소.
# 최상위 문단이면 blocks의 header/footer/... 블록, 표 셀 안이면
# table_internal_blocks의 table_control이 된다.
CTRL_PROMOTION_TAGS = {
    "header": "header",
    "footer": "footer",
    "footNote": "footnote",
    "endNote": "endnote",
}


#------------------------------------------------
# XML 유틸
#------------------------------------------------

def local_name(tag: str) -> str:
    """
    역할: XML 태그에서 네임스페이스를 제거한다.
    입력 데이터: tag(네임스페이스 포함 또는 미포함 태그명).
    출력 데이터: local name 문자열.
    """
    return tag.split("}", 1)[1] if "}" in tag else tag


def normalize(text: str | None) -> str:
    """
    역할: 공백을 모두 제거해 비교용 정규화 문자열을 만든다.
          (파서가 공백/줄바꿈을 어떻게 합치든 텍스트 존재 여부만 보기 위함)
    입력 데이터: text(원본 문자열 또는 None).
    출력 데이터: 공백이 제거된 문자열.
    """
    return "".join((text or "").split())


def section_paths(contents_dir: Path) -> list[Path]:
    """
    역할: Contents 폴더에서 section*.xml을 번호 순으로 수집한다.
    입력 데이터: contents_dir(Contents 폴더 경로).
    출력 데이터: 정렬된 section XML 경로 리스트.
    """
    def sort_key(path: Path) -> tuple[int, str]:
        digits = "".join(ch for ch in path.stem if ch.isdigit())
        return (int(digits) if digits else 10**9, path.stem)

    return sorted(contents_dir.glob("section*.xml"), key=sort_key)


def iter_text_nodes(root) -> list[tuple[str, str, str]]:
    """
    역할: 섹션 XML에서 문서 텍스트를 담고 있는 노드를 모두 수집한다.
          hp:t는 하위 인라인 마커(fwSpace/tab/lineBreak)의 tail까지 포함해야 하므로
          itertext()를 쓰고, hp:compose는 텍스트가 composeText 속성에 있다.
    입력 데이터: root(섹션 XML 루트 Element).
    출력 데이터: (종류, 텍스트, 조상 체인) 튜플 리스트.
    """
    parent_map = {child: parent for parent in root.iter() for child in parent}

    def ancestor_chain(element, limit: int = 7) -> str:
        chain: list[str] = []
        cursor = parent_map.get(element)
        while cursor is not None and len(chain) < limit:
            chain.append(local_name(cursor.tag))
            cursor = parent_map.get(cursor)
        return "/".join(chain)

    nodes: list[tuple[str, str, str]] = []

    for element in root.iter():
        name = local_name(element.tag)

        if name == "t":
            text = "".join(element.itertext())
        elif name == "compose":
            text = element.attrib.get("composeText") or ""
        else:
            continue

        if not normalize(text):
            continue

        nodes.append((name, text, ancestor_chain(element)))

    return nodes


def derive_table_ground_truth(paths: list[Path]) -> dict[str, int]:
    """
    역할: 산출물을 신뢰하지 않고 XML에서 직접 표 구조 총량을 유도한다.
          "텍스트 있는 셀"은 중첩 tbl 내부를 제외하고 자기 소속 텍스트가
          하나라도 있는 hp:tc로 정의한다 (파서 구현과 독립적인 정의).
    입력 데이터: paths(section XML 경로 리스트).
    출력 데이터: {"table_count", "cell_count", "non_empty_cell_count"}.
    """
    table_count = 0
    cell_count = 0
    non_empty_cell_count = 0

    def has_own_text(cell_element) -> bool:
        stack = list(cell_element)
        while stack:
            node = stack.pop()
            name = local_name(node.tag)

            if name == "tbl":
                # 중첩 표의 텍스트는 그 표의 셀 소속이다
                continue

            if name == "caption":
                # 개체 설명문은 셀 본문이 아니라 별도 엔티티다.
                # 캡션이 유실되지 않았는지는 I9가 따로 보증한다.
                continue

            if name in CTRL_PROMOTION_TAGS:
                # 머리말/꼬리말/각주/미주는 페이지 장식이지 셀 값이 아니다.
                # 유실되지 않았는지는 I11이 따로 보증한다.
                continue

            if name == "t":
                if "".join(node.itertext()).strip():
                    return True
                continue

            if name == "compose":
                if (node.attrib.get("composeText") or "").strip():
                    return True
                continue

            stack.extend(list(node))

        return False

    for path in paths:
        root = ET.parse(path).getroot()

        for element in root.iter():
            name = local_name(element.tag)

            if name == "tbl":
                table_count += 1
            elif name == "tc":
                cell_count += 1
                if has_own_text(element):
                    non_empty_cell_count += 1

    return {
        "table_count": table_count,
        "cell_count": cell_count,
        "non_empty_cell_count": non_empty_cell_count,
    }


#------------------------------------------------
# 산출물 요약
#------------------------------------------------

def canonical_hash(value: Any) -> str:
    """
    역할: JSON 직렬화 가능한 값의 안정적인 해시를 만든다.
    입력 데이터: value(dict/list 등).
    출력 데이터: sha256 hex 문자열.
    """
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def paragraph_scope(key: str) -> str:
    """
    역할: 블록 조인 키에서 소속 문단 범위를 뽑는다.
          "Contents/section0.xml#hp:p[83]/hp:compose|0" -> "Contents/section0.xml#hp:p[83]"
          같은 문단 안에서 텍스트가 다른 블록으로 옮겨간 경우를 판정하는 데 쓴다.
    입력 데이터: key(join_key 결과).
    출력 데이터: 문단 범위 문자열.
    """
    path = key.split("|", 1)[0]
    return path.split("/hp:", 1)[0]


def join_key(block: dict[str, Any]) -> str:
    """
    역할: 블록 수가 바뀌어도 안정적인 블록 조인 키를 만든다.
    입력 데이터: block(blocks_document.blocks의 원소).
    출력 데이터: "source_xml_path#occurrence" 형식 문자열.
    """
    return "|".join(str(block.get(field)) for field in JOIN_KEY_FIELDS)


def build_snapshot(final_debug: dict[str, Any]) -> dict[str, Any]:
    """
    역할: final_debug.json(18MB+)에서 회귀 비교에 필요한 필드만 추출해
          가벼운 baseline 스냅샷을 만든다.
    입력 데이터: final_debug(최종 산출물 dict).
    출력 데이터: 스냅샷 dict.
    """
    blocks_document = final_debug.get("blocks_document") or {}
    blocks = blocks_document.get("blocks") or []
    quality = blocks_document.get("quality") or {}

    table_internal = final_debug.get("table_internal_blocks") or {}
    internal_blocks = table_internal.get("internal_blocks") or []

    block_records: dict[str, dict[str, Any]] = {}
    for block in blocks:
        block_records[join_key(block)] = {
            "block_type": block.get("block_type"),
            "semantic_role": block.get("semantic_role"),
            "depth": block.get("depth"),
            "reading_order_index": block.get("reading_order_index"),
            "text_content": block.get("text_content"),
        }

    block_type_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    for block in blocks:
        block_type = str(block.get("block_type"))
        role = str(block.get("semantic_role"))
        block_type_counts[block_type] = block_type_counts.get(block_type, 0) + 1
        role_counts[role] = role_counts.get(role, 0) + 1

    return {
        "schema_version": 1,
        "block_count": len(blocks),
        "block_type_counts": block_type_counts,
        "semantic_role_counts": role_counts,
        "blocks": block_records,
        "internal_block_count": len(internal_blocks),
        # I3: 표 경로를 건드리지 않는 수정이라면 이 해시는 절대 변하면 안 된다
        "internal_blocks_hash": canonical_hash(internal_blocks),
        "internal_text_hash": canonical_hash([
            [b.get("internal_block_id"), b.get("text_content")]
            for b in internal_blocks
        ]),
        "table_hierarchy_link": quality.get("table_hierarchy_link"),
    }


#------------------------------------------------
# 불변식 검사
#------------------------------------------------

class Report:
    """검사 결과 누적기."""

    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def add(self, check_id: str, passed: bool, detail: str) -> None:
        self.rows.append((check_id, passed, detail))

    @property
    def failed(self) -> bool:
        return any(not passed for _, passed, _ in self.rows)

    def render(self) -> str:
        lines = []
        for check_id, passed, detail in self.rows:
            mark = "PASS" if passed else "FAIL"
            lines.append(f"  [{mark}] {check_id:32s} {detail}")
        return "\n".join(lines)


def check_i1_text_coverage(
    paths: list[Path],
    final_debug: dict[str, Any],
    report: Report,
    sample_limit: int = 8,
) -> None:
    """
    역할: I1 — section*.xml의 모든 텍스트 노드가 최종 JSON에 존재하는지 검사한다.
    입력 데이터: paths(section XML), final_debug(최종 산출물), report(결과 누적기).
    출력 데이터: 반환값 없음. report에 결과를 추가한다.
    """
    blob = normalize(json.dumps(final_debug, ensure_ascii=False))

    total = 0
    missing: list[tuple[str, str, str]] = []

    for path in paths:
        root = ET.parse(path).getroot()
        for kind, text, chain in iter_text_nodes(root):
            total += 1
            if normalize(text) not in blob:
                missing.append((kind, text, chain))

    passed = not missing
    detail = f"텍스트 노드 {total}개 중 누락 {len(missing)}개"

    if missing:
        grouped: dict[tuple[str, str], int] = {}
        for kind, _, chain in missing:
            grouped[(kind, chain)] = grouped.get((kind, chain), 0) + 1
        top = sorted(grouped.items(), key=lambda kv: -kv[1])[:sample_limit]
        detail += " | " + "; ".join(f"{count}x {kind}@{chain}" for (kind, chain), count in top)

    report.add("I1 text_coverage", passed, detail)


def check_i2_table_totals(
    paths: list[Path],
    final_debug: dict[str, Any],
    report: Report,
) -> None:
    """
    역할: I2 — XML에서 유도한 표/셀/텍스트셀 총량이 산출물과 일치하는지 검사한다.
    입력 데이터: paths, final_debug, report.
    출력 데이터: 반환값 없음.
    """
    expected = derive_table_ground_truth(paths)

    analyzed = ((final_debug.get("tables") or {}).get("analyzed")) or []

    actual_tables = 0
    actual_cells = 0
    actual_cell_texts = 0

    def walk(table: dict[str, Any]) -> None:
        nonlocal actual_tables, actual_cells, actual_cell_texts
        actual_tables += 1
        for cell in ((table.get("preprocess") or {}).get("cells")) or []:
            actual_cells += 1
            if ((cell.get("text") or {}).get("text") or "").strip():
                actual_cell_texts += 1
        for child in table.get("children") or []:
            walk(child)

    for table in analyzed:
        walk(table)

    internal_blocks = ((final_debug.get("table_internal_blocks") or {}).get("internal_blocks")) or []
    internal_cell_texts = sum(
        1 for b in internal_blocks if b.get("internal_block_type") == "table_cell_text"
    )

    mismatches = []
    if actual_tables != expected["table_count"]:
        mismatches.append(f"표 {actual_tables}!={expected['table_count']}")
    if actual_cells != expected["cell_count"]:
        mismatches.append(f"셀 {actual_cells}!={expected['cell_count']}")
    if actual_cell_texts != expected["non_empty_cell_count"]:
        mismatches.append(f"텍스트셀 {actual_cell_texts}!={expected['non_empty_cell_count']}")
    if internal_cell_texts != expected["non_empty_cell_count"]:
        mismatches.append(
            f"internal cell_text {internal_cell_texts}!={expected['non_empty_cell_count']}"
        )

    detail = (
        f"표 {actual_tables} / 셀 {actual_cells} / 텍스트셀 {actual_cell_texts} "
        f"(XML 기대: {expected['table_count']} / {expected['cell_count']} "
        f"/ {expected['non_empty_cell_count']})"
    )
    if mismatches:
        detail += " | 불일치: " + ", ".join(mismatches)

    report.add("I2 table_totals", not mismatches, detail)


def check_i4_table_link(final_debug: dict[str, Any], report: Report) -> None:
    """
    역할: I4 — 표 블록과 표 계층 분석 결과의 연결이 모두 성립하는지 검사한다.
          기록된 통계를 믿지 않고 참조를 데이터에서 다시 센다 (I5와 같은 방식).
    입력 데이터: final_debug, report.
    출력 데이터: 반환값 없음.

    기록된 matched/missing 만 보던 때는 참조가 실제로 끊겨도 통과했다.
    그 숫자는 7.5단계가 실행 중에 세어 적어둔 값이라, 적은 뒤에 누가
    table_hierarchy_ref 를 지워도 움직이지 않기 때문이다. 실제로 프리뷰에서
    목차가 사라진 사고가 이 필드를 지워서 났는데 I4는 조용히 통과했다.

    tables.analyzed 는 최상위 표만 담고 중첩표는 children 안에 있다.
    표 블록은 최상위 표에만 생기므로(중첩표는 셀 안에 산다) 최상위 표와
    표 블록은 일대일이어야 한다.
    """
    blocks_document = final_debug.get("blocks_document") or {}
    blocks = blocks_document.get("blocks") or []
    link = ((blocks_document.get("quality") or {}).get("table_hierarchy_link") or {})
    stats = link.get("top_level_block_stats") or {}

    table_blocks = [b for b in blocks if b.get("block_type") == "table"]
    table_block_count = len(table_blocks)
    matched = stats.get("matched")
    missing = stats.get("missing")

    top_ids = {
        t.get("table_id")
        for t in ((final_debug.get("tables") or {}).get("analyzed") or [])
        if t.get("table_id")
    }

    no_ref = 0
    dangling = 0
    ref_ids: list[str] = []
    for block in table_blocks:
        ref = block.get("table_hierarchy_ref") or {}
        table_id = ref.get("table_id")
        if not table_id:
            no_ref += 1
            continue
        ref_ids.append(table_id)
        if table_id not in top_ids:
            dangling += 1

    seen: dict[str, int] = {}
    for table_id in ref_ids:
        seen[table_id] = seen.get(table_id, 0) + 1
    duplicate = sum(n - 1 for n in seen.values() if n > 1)

    unreferenced = len(top_ids - set(ref_ids))

    passed = (
        missing == 0
        and matched == table_block_count
        and no_ref == 0
        and dangling == 0
        and duplicate == 0
        and unreferenced == 0
    )
    detail = (
        f"table 블록 {table_block_count}, matched {matched}, missing {missing}, "
        f"최상위 표 {len(top_ids)}개 / ref 없음 {no_ref}, 없는 표 가리킴 {dangling}, "
        f"중복 참조 {duplicate}, 블록 없는 표 {unreferenced}"
    )

    report.add("I4 table_hierarchy_link", passed, detail)


def check_i5_internal_integrity(final_debug: dict[str, Any], report: Report) -> None:
    """
    역할: I5 — table_internal_blocks의 id 중복과 부모 참조 미아를 직접 재계산한다.
          산출물에 기록된 통계를 믿지 않고 데이터에서 다시 센다.
    입력 데이터: final_debug, report.
    출력 데이터: 반환값 없음.
    """
    internal_blocks = ((final_debug.get("table_internal_blocks") or {}).get("internal_blocks")) or []

    ids = [b.get("internal_block_id") for b in internal_blocks]
    duplicate_count = len(ids) - len(set(ids))

    id_set = set(ids)
    orphan_count = sum(
        1 for b in internal_blocks
        if b.get("parent_internal_block_id") is not None
        and b.get("parent_internal_block_id") not in id_set
    )

    passed = duplicate_count == 0 and orphan_count == 0
    detail = (
        f"internal_block {len(internal_blocks)}개, "
        f"id 중복 {duplicate_count}, 부모 미아 {orphan_count}"
    )

    report.add("I5 internal_integrity", passed, detail)


def check_i6_depth_resolved(final_debug: dict[str, Any], report: Report) -> None:
    """
    역할: I6 — depth가 부여되지 않은 블록이 없는지 검사한다.
    입력 데이터: final_debug, report.
    출력 데이터: 반환값 없음.
    """
    blocks = ((final_debug.get("blocks_document") or {}).get("blocks")) or []
    unresolved = [b.get("block_id") for b in blocks if b.get("depth") is None]

    detail = f"depth 미해소 블록 {len(unresolved)}개"
    if unresolved:
        detail += " | " + ", ".join(str(x) for x in unresolved[:5])

    report.add("I6 depth_resolved", not unresolved, detail)


def check_i3_and_diff(
    current_snapshot: dict[str, Any],
    baseline_snapshot: dict[str, Any] | None,
    report: Report,
    diff_limit: int = 20,
) -> dict[str, Any]:
    """
    역할: I3(표 내부 불변) 검사와 baseline 대비 블록 텍스트 diff를 수행한다.
    입력 데이터: current_snapshot, baseline_snapshot(없으면 skip), report, diff_limit.
    출력 데이터: diff 상세 dict (없으면 빈 dict).
    """
    if baseline_snapshot is None:
        report.add("I3 internal_unchanged", True, "baseline 없음 - 건너뜀 (freeze 먼저 실행)")
        return {}

    same_internal = (
        current_snapshot["internal_blocks_hash"] == baseline_snapshot["internal_blocks_hash"]
    )
    same_internal_text = (
        current_snapshot["internal_text_hash"] == baseline_snapshot["internal_text_hash"]
    )

    if same_internal:
        detail = "table_internal_blocks 완전 동일"
    elif same_internal_text:
        detail = "text_content는 동일하나 다른 필드가 변경됨 (Task C에서는 정상)"
    else:
        detail = (
            f"셀 텍스트가 변경됨 "
            f"({baseline_snapshot['internal_block_count']} -> "
            f"{current_snapshot['internal_block_count']} 블록)"
        )

    report.add("I3 internal_unchanged", same_internal or same_internal_text, detail)

    #--- 블록 텍스트 diff ---
    base_blocks = baseline_snapshot["blocks"]
    curr_blocks = current_snapshot["blocks"]

    added = sorted(set(curr_blocks) - set(base_blocks))
    removed = sorted(set(base_blocks) - set(curr_blocks))

    text_changed: list[tuple[str, str | None, str | None]] = []
    text_lost: list[tuple[str, str | None, str | None]] = []
    meta_changed: list[str] = []

    for key in sorted(set(curr_blocks) & set(base_blocks)):
        before = base_blocks[key]
        after = curr_blocks[key]

        before_text = before.get("text_content")
        after_text = after.get("text_content")

        if before_text != after_text:
            # 텍스트가 있던 블록이 비어버린 경우는 '변경'이 아니라 '소실'로 분류한다
            if normalize(before_text) and not normalize(after_text):
                text_lost.append((key, before_text, after_text))
            else:
                text_changed.append((key, before_text, after_text))

        for field in ("block_type", "semantic_role", "depth"):
            if before.get(field) != after.get(field):
                meta_changed.append(f"{key} {field}: {before.get(field)} -> {after.get(field)}")

    # 삭제된 블록 중 텍스트를 가지고 있던 것은 '소실'과 '이동'을 구분한다.
    # 같은 문단 범위(hp:p[i]) 안의 다른 블록이 그 텍스트를 흡수했다면 이동이다.
    # (예: Task A에서 compose 블록이 사라지고 그 문자가 문단 텍스트로 합쳐지는 경우)
    texts_by_scope: dict[str, str] = {}
    for key, record in curr_blocks.items():
        scope = paragraph_scope(key)
        texts_by_scope[scope] = texts_by_scope.get(scope, "") + normalize(record.get("text_content"))

    removed_with_text: list[str] = []
    relocated: list[str] = []

    for key in removed:
        text = normalize(base_blocks[key].get("text_content"))
        if not text:
            continue
        if text in texts_by_scope.get(paragraph_scope(key), ""):
            relocated.append(key)
        else:
            removed_with_text.append(key)

    return {
        "block_count_before": baseline_snapshot["block_count"],
        "block_count_after": current_snapshot["block_count"],
        "added": added,
        "removed": removed,
        "removed_with_text": removed_with_text,
        "relocated": relocated,
        "text_changed": text_changed,
        "text_lost": text_lost,
        "meta_changed": meta_changed,
        "diff_limit": diff_limit,
        "type_counts_before": baseline_snapshot["block_type_counts"],
        "type_counts_after": current_snapshot["block_type_counts"],
    }


def check_i9_caption_coverage(
    paths: list[Path],
    final_debug: dict[str, Any],
    report: Report,
) -> None:
    """
    역할: I9 — section*.xml의 hp:caption이 전부 별도 caption 엔티티로 보존됐는지 검사한다.
          I2가 캡션을 셀 본문 집계에서 제외하므로, 캡션이 조용히 사라지지 않았음을
          여기서 반드시 보증해야 한다. (I2 완화와 짝을 이루는 검사)
    입력 데이터: paths(section XML), final_debug, report.
    출력 데이터: 반환값 없음.
    """
    expected_texts: list[str] = []

    for path in paths:
        root = ET.parse(path).getroot()
        for element in root.iter():
            if local_name(element.tag) != "caption":
                continue
            text = "".join(
                "".join(t.itertext())
                for t in element.iter()
                if local_name(t.tag) == "t"
            )
            if normalize(text):
                expected_texts.append(text)

    internal_blocks = ((final_debug.get("table_internal_blocks") or {}).get("internal_blocks")) or []
    caption_blocks = [
        b for b in internal_blocks if b.get("internal_block_type") == "table_caption"
    ]
    caption_index = {normalize(b.get("text_content")) for b in caption_blocks}

    missing = [t for t in expected_texts if normalize(t) not in caption_index]

    # 캡션이 대상 개체와 연결돼 있어야 데이터로서 의미가 있다
    unlinked = [
        b.get("internal_block_id")
        for b in caption_blocks
        if not b.get("binary_item_id_ref")
    ]

    passed = not missing and not unlinked and len(caption_blocks) == len(expected_texts)
    detail = (
        f"XML hp:caption {len(expected_texts)}개 / caption 블록 {len(caption_blocks)}개, "
        f"누락 {len(missing)}개, 대상 개체 미연결 {len(unlinked)}개"
    )
    if missing:
        detail += f" | 예: {missing[0][:30]!r}"

    report.add("I9 caption_coverage", passed, detail)


def check_i11_ctrl_promotion_coverage(
    paths: list[Path],
    final_debug: dict[str, Any],
    report: Report,
) -> None:
    """
    역할: I11 — 머리말/꼬리말/각주/미주가 전부 독립 엔티티로 보존됐는지 검사한다.
          최상위 문단이면 blocks의 header/footer/footnote/endnote 블록,
          표 셀 안이면 table_internal_blocks의 table_control이어야 한다.
          어느 쪽에도 없으면 셀 본문 텍스트에 섞였거나 사라진 것이다.
          I2가 이들을 셀 본문 집계에서 제외하므로 이 검사가 짝을 이룬다.
    입력 데이터: paths(section XML), final_debug, report.
    출력 데이터: 반환값 없음.
    """
    expected: list[tuple[str, str]] = []

    for path in paths:
        root = ET.parse(path).getroot()
        for element in root.iter():
            control_type = CTRL_PROMOTION_TAGS.get(local_name(element.tag))
            if control_type is None:
                continue
            text = "".join(
                "".join(t.itertext())
                for t in element.iter()
                if local_name(t.tag) == "t"
            )
            if normalize(text):
                expected.append((control_type, text))

    blocks = ((final_debug.get("blocks_document") or {}).get("blocks")) or []
    internal_blocks = ((final_debug.get("table_internal_blocks") or {}).get("internal_blocks")) or []

    block_texts = {
        normalize(b.get("text_content"))
        for b in blocks
        if b.get("block_type") in set(CTRL_PROMOTION_TAGS.values())
    }
    control_blocks = [
        b for b in internal_blocks if b.get("internal_block_type") == "table_control"
    ]
    control_texts = {normalize(b.get("text_content")) for b in control_blocks}

    # HWPX는 머리말 내용을 표로 짜기도 한다. 그 표의 셀 텍스트도
    # "머리말로 식별 가능한 위치"로 인정한다. 소유자 표시는 아래에서 따로 검사한다.
    owned_table_ids = _owned_table_ids(final_debug)
    owned_cell_texts = {
        normalize(b.get("text_content"))
        for b in internal_blocks
        if b.get("internal_block_type") == "table_cell_text"
        and b.get("source_table_id") in owned_table_ids
    }

    def is_preserved(text: str) -> bool:
        key = normalize(text)
        return key in block_texts or key in control_texts or key in owned_cell_texts

    missing = [(kind, text) for kind, text in expected if not is_preserved(text)]

    # 일반(소유자 없는) 표의 셀 값과 구분되지 않는 상태로 남아 있는지 확인한다.
    # 부분 일치는 '●' 같은 한 글자 마커에서 오탐이 나므로 완전 일치만 본다.
    plain_cell_texts = {
        normalize(b.get("text_content"))
        for b in internal_blocks
        if b.get("internal_block_type") == "table_cell_text"
        and b.get("source_table_id") not in owned_table_ids
    }
    contaminated = [
        (kind, text) for kind, text in expected
        if normalize(text) in plain_cell_texts
    ]

    passed = not missing and not contaminated
    detail = (
        f"승격 대상 텍스트 {len(expected)}개 / "
        f"blocks {len(block_texts)}종 + table_control {len(control_blocks)}개 "
        f"+ 소유표 {len(owned_table_ids)}개, "
        f"미보존 {len(missing)}개, 일반 셀과 구분불가 {len(contaminated)}개"
    )
    if missing:
        detail += f" | 미보존 예: {missing[0][1][:30]!r}"
    elif contaminated:
        detail += f" | 구분불가 예: {contaminated[0][1][:30]!r}"

    report.add("I11 ctrl_promotion", passed, detail)


def _owned_table_ids(final_debug: dict[str, Any]) -> set[str]:
    """
    역할: 머리말/꼬리말/각주/미주에 소속된 표의 id를 모은다.
          HWPX는 머리말 내용을 표로 짜기도 하는데, 소유자 표시가 없으면
          본문 데이터 표와 구분할 수 없다.
    입력 데이터: final_debug.
    출력 데이터: owner_control_type이 붙은 표 id 집합.
    """
    owned: set[str] = set()

    def walk(table: dict[str, Any], inherited: str | None) -> None:
        nesting = (table.get("preprocess") or {}).get("nesting") or {}
        owner = nesting.get("owner_control_type") or inherited
        if owner:
            owned.add(table.get("table_id"))
        for child in table.get("children") or []:
            walk(child, owner)

    for table in ((final_debug.get("tables") or {}).get("analyzed")) or []:
        walk(table, None)

    return owned


def check_i10_llm_context_coverage(
    paths: list[Path],
    llm_context: Path | str,
    report: Report,
    sample_limit: int = 6,
) -> None:
    """
    역할: I10 — LLM 입력용 산출물(llm_context.txt)에 문서의 모든 텍스트가 있는지 검사한다.
          depth_text_preview는 표 내부 텍스트를 빼고 120자에서 자르는 사람용
          디버그 산출물이라 이 검사의 대상이 아니다.
    입력 데이터: paths(section XML), llm_context(파일 경로 또는 텍스트), report.
    출력 데이터: 반환값 없음.

    파일이 아니라 텍스트도 받는다. 파이프라인 결과를 메모리로 검사할 때
    llm_context.txt를 굳이 저장할 이유가 없기 때문이다.
    """
    if isinstance(llm_context, Path):
        if not llm_context.exists():
            report.add("I10 llm_context_coverage", False, f"산출물 없음: {llm_context}")
            return
        blob = normalize(llm_context.read_text(encoding="utf-8"))
    else:
        blob = normalize(llm_context)

    total = 0
    missing: list[tuple[str, str, str]] = []

    for path in paths:
        root = ET.parse(path).getroot()
        for kind, text, chain in iter_text_nodes(root):
            total += 1
            if normalize(text) not in blob:
                missing.append((kind, text, chain))

    passed = not missing
    detail = f"텍스트 노드 {total}개 중 누락 {len(missing)}개"

    if missing:
        grouped: dict[tuple[str, str], int] = {}
        for kind, _, chain in missing:
            grouped[(kind, chain)] = grouped.get((kind, chain), 0) + 1
        top = sorted(grouped.items(), key=lambda kv: -kv[1])[:sample_limit]
        detail += " | " + "; ".join(f"{count}x {kind}@{chain}" for (kind, chain), count in top)

    report.add("I10 llm_context_coverage", passed, detail)


def check_i8_source_block_refs(final_debug: dict[str, Any], report: Report) -> None:
    """
    역할: I8 — internal_blocks의 source_block_id가 실제 존재하는 block_id를 가리키는지,
          모든 table 블록이 table_internal_ref를 갖는지 검사한다.
          블록 수가 바뀌면 block_id가 재부여되므로(예: Task A) 이 참조가
          깨지지 않았음을 기계적으로 확인해야 한다.
    입력 데이터: final_debug, report.
    출력 데이터: 반환값 없음.
    """
    blocks = ((final_debug.get("blocks_document") or {}).get("blocks")) or []
    internal_blocks = ((final_debug.get("table_internal_blocks") or {}).get("internal_blocks")) or []

    block_ids = {b.get("block_id") for b in blocks}

    dangling = {
        b.get("source_block_id")
        for b in internal_blocks
        if b.get("source_block_id") is not None
        and b.get("source_block_id") not in block_ids
    }

    table_blocks = [b for b in blocks if b.get("block_type") == "table"]
    without_ref = [
        b.get("block_id") for b in table_blocks if not b.get("table_internal_ref")
    ]

    passed = not dangling and not without_ref
    detail = (
        f"source_block_id 미아 {len(dangling)}개, "
        f"table_internal_ref 없는 table 블록 {len(without_ref)}개"
    )
    if dangling:
        detail += " | 예: " + ", ".join(str(x) for x in sorted(dangling)[:3])

    report.add("I8 source_block_refs", passed, detail)


def check_i7_text_regression(diff: dict[str, Any], report: Report) -> None:
    """
    역할: I7 — baseline에서 텍스트를 가지고 있던 블록이 비어버렸거나
          텍스트를 가진 채 사라졌는지 검사한다.
          I1(존재 여부)이 놓치는 '블록 단위 소실'을 잡는 게이트다.
    입력 데이터: diff(check_i3_and_diff 반환값), report.
    출력 데이터: 반환값 없음.
    """
    if not diff:
        report.add("I7 no_text_regression", True, "baseline 없음 - 건너뜀")
        return

    lost = diff["text_lost"]
    removed_with_text = diff["removed_with_text"]
    total = len(lost) + len(removed_with_text)

    detail = (
        f"텍스트 소실 블록 {len(lost)}개, 텍스트 보유 삭제 블록 {len(removed_with_text)}개"
        f" (같은 문단 내 이동 {len(diff['relocated'])}개는 소실로 세지 않음)"
    )
    if lost:
        key, before, _ = lost[0]
        detail += f" | 예: {key} <- {before!r:.40}"
    elif removed_with_text:
        detail += f" | 예: {removed_with_text[0]}"

    report.add("I7 no_text_regression", total == 0, detail)


#------------------------------------------------
# diff 출력
#------------------------------------------------

def render_diff(diff: dict[str, Any]) -> str:
    """
    역할: baseline 대비 변화를 사람이 읽을 수 있게 정리한다.
    입력 데이터: diff(check_i3_and_diff 반환값).
    출력 데이터: 출력 문자열.
    """
    if not diff:
        return "  (baseline 없음 - diff 생략)"

    limit = diff["diff_limit"]
    lines: list[str] = []

    lines.append(
        f"  block_count : {diff['block_count_before']} -> {diff['block_count_after']}"
    )

    before_types = diff["type_counts_before"]
    after_types = diff["type_counts_after"]
    changed_types = sorted(set(before_types) | set(after_types))
    type_deltas = [
        f"{name} {before_types.get(name, 0)}->{after_types.get(name, 0)}"
        for name in changed_types
        if before_types.get(name, 0) != after_types.get(name, 0)
    ]
    lines.append(f"  block_type 변화 : {', '.join(type_deltas) if type_deltas else '없음'}")

    lines.append(f"  신규 블록 : {len(diff['added'])}개")
    for key in diff["added"][:limit]:
        lines.append(f"      + {key}")

    lines.append(
        f"  삭제 블록 : {len(diff['removed'])}개 "
        f"(텍스트 소실 {len(diff['removed_with_text'])}개, "
        f"같은 문단 내 이동 {len(diff['relocated'])}개)"
    )
    for key in diff["removed"][:limit]:
        lines.append(f"      - {key}")

    lines.append(f"  텍스트 소실 블록 : {len(diff['text_lost'])}개")
    for key, before, after in diff["text_lost"][:limit]:
        lines.append(f"      ! {key}")
        lines.append(f"          before: {before!r}")
        lines.append(f"          after : {after!r}")

    lines.append(f"  텍스트 변경 블록 : {len(diff['text_changed'])}개")
    for key, before, after in diff["text_changed"][:limit]:
        lines.append(f"      ~ {key}")
        lines.append(f"          before: {before!r}")
        lines.append(f"          after : {after!r}")
    if len(diff["text_changed"]) > limit:
        lines.append(f"      ... 외 {len(diff['text_changed']) - limit}개")

    lines.append(f"  메타(타입/역할/depth) 변경 : {len(diff['meta_changed'])}개")
    for entry in diff["meta_changed"][:limit]:
        lines.append(f"      ~ {entry}")
    if len(diff["meta_changed"]) > limit:
        lines.append(f"      ... 외 {len(diff['meta_changed']) - limit}개")

    return "\n".join(lines)


#------------------------------------------------
# 기대 프로파일
#------------------------------------------------

# 각 Task 완료 시 기대되는 변화. 실제 diff와 대조해 사람이 판단한다.
EXPECTED_PROFILES: dict[str, str] = {
    "none": (
        "변화 없음. block_count 동일, 텍스트 변경 0, I3 완전 동일."
    ),
    "A": (
        "compose 인라인화. unknown_object 15->0, block_count 426->411, "
        "텍스트 변경 정확히 15건(모두 숫자 삽입), "
        "삭제 15건은 전부 '같은 문단 내 이동'으로 분류되어야 함(소실 0), "
        "I3 완전 동일."
    ),
    "B": (
        "본문 텍스트 재귀화. 텍스트 변경 24건(fwSpace 위치 공백 추가), "
        "block_count 동일, I3 완전 동일. "
        "주의: 이 문서의 hp:lineBreak 8개는 전부 표 셀 안이라 "
        "line_features 변화는 관측되지 않는 것이 정상."
    ),
    "C": (
        "불릿 라벨 부여. 기존 필드 전부 불변(텍스트 변경 0, block_count 동일), "
        "I3는 internal_text_hash 동일. 신규 auto_label 필드만 추가."
    ),
}


#------------------------------------------------
# 진입점
#------------------------------------------------

def load_json(path: Path) -> dict[str, Any]:
    """
    역할: JSON 파일을 읽어 dict로 반환한다.
    입력 데이터: path(파일 경로).
    출력 데이터: 파싱된 dict.
    """
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def command_freeze(args: argparse.Namespace) -> int:
    """
    역할: 현재 산출물에서 baseline 스냅샷을 생성한다.
    입력 데이터: args(current/baseline 경로).
    출력 데이터: 종료 코드.
    """
    current_path = Path(args.current)
    baseline_path = Path(args.baseline)

    if not current_path.exists():
        print(f"[ERROR] 산출물이 없습니다: {current_path}")
        print("        final_debug.json 은 --debug 를 줄 때만 저장됩니다.")
        print("        python -m tools.run_model --debug              파일을 만든 뒤 다시 실행")
        print("        python -m tools.regression_check check-pipeline")
        print("                                            파일 없이 바로 검증")
        return 1

    if baseline_path.exists() and not args.force:
        print(f"[ERROR] baseline이 이미 있습니다: {baseline_path}")
        print("        덮어쓰려면 --force 를 사용하세요.")
        print("        (수정 작업 중이라면 덮어쓰면 안 됩니다)")
        return 1

    final_debug = load_json(current_path)
    snapshot = build_snapshot(final_debug)

    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    with baseline_path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    size_kb = baseline_path.stat().st_size / 1024
    print("===========================================")
    print("[BASELINE 동결 완료]")
    print(f"  source        : {current_path}")
    print(f"  baseline      : {baseline_path}  ({size_kb:.0f} KB)")
    print(f"  block_count   : {snapshot['block_count']}")
    print(f"  internal_block: {snapshot['internal_block_count']}")
    print(f"  internal_hash : {snapshot['internal_blocks_hash'][:16]}...")
    print("===========================================")
    return 0


def command_check(args: argparse.Namespace) -> int:
    """
    역할: 불변식 I1~I6과 baseline 대비 diff를 검증한다.
    입력 데이터: args(contents/current/baseline 경로, expect 프로파일).
    출력 데이터: 종료 코드 (0=통과, 1=실패).
    """
    contents_dir = Path(args.contents)
    current_path = Path(args.current)
    baseline_path = Path(args.baseline)

    if not current_path.exists():
        print(f"[ERROR] 산출물이 없습니다: {current_path}")
        print("        final_debug.json 은 --debug 를 줄 때만 저장됩니다.")
        print("        python -m tools.run_model --debug 로 만든 뒤 다시 실행하세요.")
        return 1

    paths = section_paths(contents_dir)
    if not paths:
        print(f"[ERROR] section*.xml을 찾을 수 없습니다: {contents_dir}")
        return 1

    final_debug = load_json(current_path)
    current_snapshot = build_snapshot(final_debug)

    baseline_snapshot = None
    if baseline_path.exists():
        baseline_snapshot = load_json(baseline_path)

    report = Report()
    diff = check_i3_and_diff(current_snapshot, baseline_snapshot, report)
    check_i7_text_regression(diff, report)
    run_invariants(
        paths, final_debug, current_path.parent / "llm_context.txt", report,
    )

    print("===========================================")
    print("[불변식 검사]")
    print(f"  contents : {contents_dir}")
    print(f"  current  : {current_path}")
    print(f"  baseline : {baseline_path if baseline_snapshot else '(없음)'}")
    print("-------------------------------------------")
    print(report.render())
    print("-------------------------------------------")
    print("[baseline 대비 변화]")
    print(render_diff(diff))

    if args.expect:
        print("-------------------------------------------")
        print(f"[기대 프로파일: {args.expect}]")
        print(f"  {EXPECTED_PROFILES[args.expect]}")
        print("  위 diff와 대조해 판단하세요.")

    print("===========================================")

    if report.failed:
        print("결과: FAIL - 불변식 위반이 있습니다.")
        return 1

    print("결과: PASS - 모든 불변식 통과.")
    return 0


def run_invariants(
    paths: list[Path],
    final_debug: dict[str, Any],
    llm_context: Path | str,
    report: Report,
) -> None:
    """
    역할: baseline 없이 단독으로 판정 가능한 불변식을 한 번에 돌린다.
    입력 데이터: paths(section XML), final_debug(파이프라인 출력 구조),
                llm_context(경로 또는 텍스트), report.
    출력 데이터: 반환값 없음.

    final_debug는 '파일에서 읽은 dict'일 수도 있고 'PipelineResult를 가리키는
    view'일 수도 있다. 검사들은 구조만 보므로 어느 쪽이든 같은 결과를 낸다.
    """
    check_i1_text_coverage(paths, final_debug, report)
    check_i2_table_totals(paths, final_debug, report)
    check_i4_table_link(final_debug, report)
    check_i5_internal_integrity(final_debug, report)
    check_i6_depth_resolved(final_debug, report)
    check_i8_source_block_refs(final_debug, report)
    check_i9_caption_coverage(paths, final_debug, report)
    check_i11_ctrl_promotion_coverage(paths, final_debug, report)
    check_i10_llm_context_coverage(paths, llm_context, report)


def check_pipeline_result(result, contents_dir: Path, baseline_path: Path | None = None):
    """
    역할: 파이프라인 결과 객체를 파일 없이 검증한다.
    입력 데이터: result(PipelineResult), contents_dir(section XML 폴더),
                baseline_path(있으면 snapshot diff까지).
    출력 데이터: (Report, diff dict).

    final_debug.json을 읽지 않는다. 단계들이 이미 인메모리로 주고받는 구조를
    그대로 본다.
    """
    from hwpx.analysis.table_filter import state_view

    final_debug = state_view(result)
    paths = section_paths(contents_dir)
    report = Report()
    run_invariants(
        paths, final_debug,
        result.llm_context.text if result.llm_context is not None else "",
        report,
    )
    diff: dict[str, Any] = {}
    if baseline_path is not None and Path(baseline_path).exists():
        snapshot = build_snapshot(final_debug)
        baseline = load_json(Path(baseline_path))
        diff = check_i3_and_diff(snapshot, baseline, report)
        check_i7_text_regression(diff, report)
    return report, diff


def command_check_pipeline(args: argparse.Namespace) -> int:
    """
    역할: 문서를 파싱해 파이프라인을 돌리고, 산출물 파일 없이 불변식을 검증한다.
    입력 데이터: args(source/work/baseline).
    출력 데이터: 종료 코드.
    """
    from .audit.documents import enable_utf8_stdout
    from hwpx import run_pipeline

    enable_utf8_stdout()

    source = Path(args.source)
    if not source.exists():
        print(f"[ERROR] 문서를 찾을 수 없습니다: {source}")
        return 1

    parser, result = run_pipeline(source, Path(args.work))
    baseline = Path(args.baseline) if args.baseline else None
    report, diff = check_pipeline_result(
        result, Path(parser.contents_dir_path), baseline,
    )

    print("===========================================")
    print("[불변식 검사 — 파일 없이 파이프라인 결과로]")
    print(f"  source   : {source}")
    print(f"  contents : {parser.contents_dir_path}")
    print(f"  baseline : {baseline if baseline and baseline.exists() else '(없음)'}")
    print("-------------------------------------------")
    print(report.render())
    if diff:
        print("-------------------------------------------")
        print("[baseline 대비 변화]")
        print(render_diff(diff))
    print("===========================================")
    if report.failed:
        print("결과: FAIL")
        return 1
    print("결과: PASS - 모든 불변식 통과.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """
    역할: CLI 진입점.
    입력 데이터: argv(명령행 인자).
    출력 데이터: 종료 코드.
    """
    parser = argparse.ArgumentParser(
        description="HWPX 파싱 파이프라인 회귀 검증 하네스",
    )
    parser.add_argument(
        "command",
        choices=("freeze", "check", "check-pipeline"),
        help="freeze=현재 산출물을 baseline으로 동결, "
             "check=산출물 파일로 검증, "
             "check-pipeline=파일 없이 파이프라인 결과로 검증",
    )
    parser.add_argument("--source", default=str(DEFAULT_SOURCE),
                        help="check-pipeline 대상 문서")
    parser.add_argument("--work", default=str(REPO_ROOT / "output"),
                        help="check-pipeline 압축 해제 위치")
    parser.add_argument("--contents", default=str(DEFAULT_CONTENTS_DIR))
    parser.add_argument("--current", default=str(DEFAULT_CURRENT))
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument(
        "--expect",
        choices=sorted(EXPECTED_PROFILES),
        help="기대 변화 프로파일을 함께 출력한다",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="freeze 시 기존 baseline을 덮어쓴다",
    )

    args = parser.parse_args(argv)

    if args.command == "freeze":
        return command_freeze(args)
    if args.command == "check-pipeline":
        return command_check_pipeline(args)

    return command_check(args)


if __name__ == "__main__":
    sys.exit(main())
