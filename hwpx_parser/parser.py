#================================================
# hwpx_parser.py
#================================================

from __future__ import annotations

from pathlib import Path
import zipfile

from hwpx_parser.header_parser import HeaderParser
from hwpx_parser.parser_context import ParserContext
from hwpx_parser.section_parser import SectionParser


class HwpxParser:
    """
    HWPX 표 계층화 파서 진입점.

    역할:
    1. .hwpx/.zip 압축 해제
    2. Contents/header.xml 찾기
    3. Contents/section*.xml 찾기
    4. HeaderParser로 HeaderData 생성
    5. ParserContext 생성
    6. SectionParser로 section 내부 표 파싱
    """

    def __init__(self, doc_save_path: str, source: str):
        """
        역할: HWPX 파서 인스턴스의 경로와 내부 상태를 초기화한다.
        입력 데이터: doc_save_path(결과/압축해제 저장 루트), source(HWPX 또는 ZIP 원본 파일 경로).
        출력 데이터: 반환값은 없고, source_path/contents_dir_path/header_file_path 등 인스턴스 속성이 설정된다.
        """
        self.source_path = Path(source)
        self.filename = self.source_path.stem

        self.doc_save_path = Path(doc_save_path)

        self.unpacked_dir_path = (
            self.doc_save_path / "unpacked" / self.filename
        )

        self.contents_dir_path = self.unpacked_dir_path / "Contents"
        self.header_file_path = self.contents_dir_path / "header.xml"
        self.metadata_file_path = self.contents_dir_path / "content.hpf"
        self.image_dir_path = self.unpacked_dir_path / "BinData"

        self.section_file_paths: list[Path] = []

        self.header = None
        self.context: ParserContext | None = None
        self.tables = []

    def parse(self):
        """
        역할: 압축 해제, 경로 확인, header.xml 파싱, section*.xml 표 파싱까지 전체 파이프라인을 실행한다.
        입력 데이터: 초기화된 HwpxParser 인스턴스의 source_path/doc_save_path 상태.
        출력 데이터: 파싱된 Table 객체 리스트를 반환하고 self.tables에도 저장한다.
        """
        """
        전체 파싱 실행 진입점.
        """

        self._ensure_unpacked()
        self._resolve_hwpx_paths()
        self._load_section_files()

        self.header = HeaderParser.parse(self.header_file_path)

        self.context = ParserContext(
            header=self.header,
            image_dir_path=self.image_dir_path,
        )

        self.tables = SectionParser.parse(
            section_sources=self.section_file_paths,
            context=self.context,
        )

        return self.tables

    def _ensure_unpacked(self) -> None:
        """
        역할: 이미 압축 해제된 파일이 있는지 확인하고, 없으면 원본 HWPX/ZIP을 해제한다.
        입력 데이터: self.source_path, self.unpacked_dir_path, self.contents_dir_path.
        출력 데이터: 반환값은 없고, 필요한 경우 unpacked_dir_path 아래에 문서 파일을 생성한다.
        """
        """
        압축 해제 여부 확인 후 필요하면 압축 해제.
        """

        if self._is_already_unpacked():
            return

        self._unpack_hwpx()

    def _is_already_unpacked(self) -> bool:
        """
        역할: 기존 압축 해제 결과가 재사용 가능한 HWPX 구조인지 검사한다.
        입력 데이터: self.contents_dir_path, self.header_file_path, section*.xml 존재 여부.
        출력 데이터: 재사용 가능하면 True, 아니면 False를 반환한다.
        """
        """
        이미 압축 해제되어 있는지 확인.
        """

        return (
            self.contents_dir_path.exists()
            and self.header_file_path.exists()
            and bool(list(self.contents_dir_path.glob("section*.xml")))
        )

    def _unpack_hwpx(self) -> None:
        """
        역할: 원본 HWPX/ZIP 파일을 unpacked_dir_path로 압축 해제한다.
        입력 데이터: self.source_path에 있는 ZIP 구조의 문서 파일.
        출력 데이터: 반환값은 없고, 압축 해제된 파일/폴더가 self.unpacked_dir_path에 생성된다.
        """
        """
        HWPX 파일 압축 해제.
        HWPX는 내부적으로 zip 구조다.
        """

        if not self.source_path.exists():
            raise FileNotFoundError(f"원본 파일을 찾을 수 없습니다: {self.source_path}")

        self.unpacked_dir_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(self.source_path, "r") as zip_ref:
            zip_ref.extractall(self.unpacked_dir_path)

    def _resolve_hwpx_paths(self) -> None:
        """
        역할: 압축 해제 결과에서 실제 Contents, header.xml, content.hpf, BinData 경로를 확정한다.
        입력 데이터: self.unpacked_dir_path 아래의 HWPX 디렉터리 구조.
        출력 데이터: 반환값은 없고, contents_dir_path/header_file_path/metadata_file_path/image_dir_path가 갱신된다.
        """
        """
        기본 Contents 위치에 파일이 없을 경우,
        압축 해제 폴더 전체에서 content.hpf를 찾아 Contents 경로를 다시 잡는다.

        zip 안에 문서 폴더가 한 겹 더 들어간 경우를 처리하기 위한 코드.
        """

        if self.header_file_path.exists() and self.metadata_file_path.exists():
            return

        found_metadata_files = list(self.unpacked_dir_path.rglob("content.hpf"))

        if not found_metadata_files:
            raise FileNotFoundError(
                f"content.hpf를 찾을 수 없습니다: {self.unpacked_dir_path}"
            )

        self.metadata_file_path = found_metadata_files[0]
        self.contents_dir_path = self.metadata_file_path.parent
        self.header_file_path = self.contents_dir_path / "header.xml"
        self.image_dir_path = self.contents_dir_path.parent / "BinData"

        if not self.header_file_path.exists():
            raise FileNotFoundError(
                f"header.xml을 찾을 수 없습니다: {self.header_file_path}"
            )

    def _load_section_files(self) -> None:
        """
        역할: Contents 폴더의 section*.xml 파일을 문서 순서대로 수집한다.
        입력 데이터: self.contents_dir_path.
        출력 데이터: 반환값은 없고, 정렬된 Path 리스트가 self.section_file_paths에 저장된다.
        """
        """
        Contents 폴더에서 section*.xml 파일을 숫자 기준으로 정렬해서 저장.
        """

        self.section_file_paths = sorted(
            self.contents_dir_path.glob("section*.xml"),
            key=self._section_sort_key,
        )

        if not self.section_file_paths:
            raise FileNotFoundError(
                f"section*.xml 파일을 찾을 수 없습니다: {self.contents_dir_path}"
            )

    def file_info(self) -> None:
        """
        역할: 현재 파서가 사용하는 원본/압축해제/헤더/이미지 경로와 개수를 콘솔에 출력한다.
        입력 데이터: self.source_path, self.section_file_paths, self.tables 등 파서 상태.
        출력 데이터: 반환값은 없고, 표준 출력(stdout)에 요약 정보를 출력한다.
        """
        """
        현재 파서가 잡은 파일 경로 정보 출력.
        """

        print("===========================================")
        print(f"source          : {self.source_path}")
        print(f"filename        : {self.filename}")
        print(f"unpacked        : {self.unpacked_dir_path}")
        print(f"contents        : {self.contents_dir_path}")
        print(f"header          : {self.header_file_path}")
        print(f"image_dir       : {self.image_dir_path}")
        print(f"section_count   : {len(self.section_file_paths)}")
        print(f"table_count     : {len(self.tables)}")
        print("===========================================")

    @classmethod
    def _section_sort_key(cls, source: Path) -> tuple[int, str]:
        """
        역할: section0.xml, section10.xml 같은 파일명을 숫자 기준으로 정렬할 키를 만든다.
        입력 데이터: source(section XML 파일 Path).
        출력 데이터: sorted()에서 사용할 (섹션번호, 파일명) 튜플을 반환한다.
        """
        """
        section0.xml, section1.xml, section10.xml을 숫자 기준으로 정렬하기 위한 key.
        """

        stem = source.stem
        suffix = "".join(ch for ch in stem if ch.isdigit())

        if not suffix:
            return (10**9, stem)

        return (int(suffix), stem)
