"""원본 XML 을 대조 가능한 색인으로 만든다.

원본 범위
    section*.xml 과 header.xml 만 센다. masterpage*.xml 은 빼는데, 머리말/
    바닥글 배경 정의라 본문 추출 대상이 아니면서 같은 속성을 또 갖고 있어
    개수 대조를 흐린다. 포함하면 subList 가 8개(TOP), pos 가 12개 늘어난다.
    범위에 따라 근거 수치가 달라지므로 여기에 명시해 둔다.

색인 키에 부모를 넣는 이유
    (요소, 속성)만으로는 부족하다. subList/@vertAlign 은 2374개인데 그중
    표 셀(tc) 직속은 2150개고 나머지는 도형 텍스트·바닥글·캡션에 붙어 있다.
    산출물의 cells[].sublist 는 셀 것만 담으므로 2150 이 정상인데, 요소까지만
    좁히면 '224개 누락'으로 보여 정상인 컬럼을 결함으로 몰게 된다.
    그래서 (부모 요소, 요소, 속성) 으로 잡는다.

    같은 이유로 @textFlow 는 8개 요소에 걸쳐 890개지만 tbl 로 좁히면 200개고,
    산출물 layout.text_flow 200개와 정확히 맞는다.
"""

from __future__ import annotations

import glob
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

# 원본으로 셀 파일. 바꾸면 근거 수치가 바뀐다.
SOURCE_GLOBS = ('section*.xml', 'header.xml')
EXCLUDED_NOTE = 'masterpage*.xml 은 본문 추출 대상이 아니라 제외'


def local(tag: str) -> str:
    return tag.split('}', 1)[1] if '}' in tag else tag


def norm_text(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def _text_of(node) -> str:
    parts = [node.text or '']
    for child in node:
        parts.append(_text_of(child))
        parts.append(child.tail or '')
    return ''.join(parts)


class SourceIndex:
    """원본 XML 의 속성 분포와 텍스트."""

    def __init__(self, contents_dir: Path, globs=SOURCE_GLOBS):
        self.contents_dir = contents_dir
        self.globs = tuple(globs)
        self.attrs: dict[tuple[str, str, str], Counter] = defaultdict(Counter)
        self.files: list[str] = []
        paragraphs: list[str] = []

        for pattern in self.globs:
            for f in sorted(glob.glob(str(contents_dir / pattern))):
                self.files.append(Path(f).name)
                root = ET.parse(f).getroot()
                parent = {c: p for p in root.iter() for c in p}
                for node in root.iter():
                    tag = local(node.tag)
                    up = parent.get(node)
                    up_tag = local(up.tag) if up is not None else '(root)'
                    for key, value in node.attrib.items():
                        self.attrs[(up_tag, tag, local(key))][value] += 1
                    if tag in ('p', 't'):
                        s = norm_text(_text_of(node))
                        if s:
                            paragraphs.append(s)
                    for value in node.attrib.values():
                        if value:
                            paragraphs.append(norm_text(value))
        self.text = '\n'.join(paragraphs)

    def candidates(self, values: set[str]):
        """값 집합을 모두 받아주는 (부모, 요소, 속성) 키들."""
        if not values:
            return []
        return [k for k, dist in self.attrs.items() if values <= set(dist)]

    def occurrences(self, key) -> int:
        return sum(self.attrs[key].values())

    def describe(self, key) -> str:
        up, tag, attr = key
        return f"{up}/{tag}@{attr}"
