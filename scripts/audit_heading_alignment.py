#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass

from bs4 import BeautifulSoup

from build_web_book import BOOK, CHAPTERS, PDF, Chapter


SECTION_RE = re.compile(r"^(?P<number>\d+\.\d+(?:\.\d+){0,3})\s+(?P<title>.+)$")
SOURCE_TAIL_RE = re.compile(r"(?im)^\s*(EXERCISES|REFERENCES)\s*$")


@dataclass(frozen=True)
class Section:
    number: str
    title: str

    @property
    def section_id(self) -> str:
        return "sec-" + self.number.replace(".", "-")

    @property
    def level(self) -> str:
        return f"h{2 + min(self.number.count('.') - 1, 2)}"


def chapter_prefix(chapter: Chapter) -> str | None:
    match = re.fullmatch(r"chapter-(\d+)", chapter.slug)
    if not match:
        return None
    return f"{int(match.group(1))}."


def sort_key(number: str) -> list[int]:
    return [int(part) for part in number.split(".")]


def looks_like_heading_title(title: str) -> bool:
    match = re.search(r"[A-Za-z]", title)
    return bool(match and title[match.start()].isupper())


def source_sections(chapter: Chapter) -> dict[str, Section]:
    prefix = chapter_prefix(chapter)
    if prefix is None:
        return {}
    text = subprocess.check_output(
        ["pdftotext", "-layout", "-f", str(chapter.start), "-l", str(chapter.end), str(PDF), "-"],
        cwd=PDF.parent,
        text=True,
    )
    tail = SOURCE_TAIL_RE.search(text)
    if tail:
        text = text[: tail.start()]
    sections: dict[str, Section] = {}
    for line in text.splitlines():
        line = " ".join(line.strip().split())
        match = SECTION_RE.match(line)
        if not match:
            continue
        number = match.group("number")
        title = match.group("title").strip()
        if number.startswith(prefix) and looks_like_heading_title(title):
            sections[number] = Section(number, title)
    return sections


def html_sections(chapter: Chapter) -> dict[str, Section]:
    soup = BeautifulSoup((BOOK / chapter.file).read_text(encoding="utf-8"), "html.parser")
    sections: dict[str, Section] = {}
    for heading in soup.select("h2,h3,h4"):
        text = heading.get_text(" ", strip=True)
        match = SECTION_RE.match(text)
        if not match:
            continue
        number = match.group("number")
        sections[number] = Section(number, match.group("title").strip())
    return sections


def fmt(numbers: set[str]) -> str:
    return ", ".join(sorted(numbers, key=sort_key)) or "-"


def main() -> int:
    failures: list[str] = []
    print("chapter\tsource_sections\thtml_sections\tmissing_in_html\textra_in_html")
    for chapter in CHAPTERS:
        if not chapter.slug.startswith("chapter-"):
            continue
        src = source_sections(chapter)
        html = html_sections(chapter)
        missing = set(src) - set(html)
        extra = set(html) - set(src)
        print("\t".join([chapter.slug, str(len(src)), str(len(html)), fmt(missing), fmt(extra)]))
        if missing:
            failures.append(f"{chapter.slug}: source section headings missing in HTML: {fmt(missing)}")
        if extra:
            failures.append(f"{chapter.slug}: HTML section headings not found in source: {fmt(extra)}")

        soup = BeautifulSoup((BOOK / chapter.file).read_text(encoding="utf-8"), "html.parser")
        for section in html.values():
            heading = soup.select_one(f"#{section.section_id}")
            if heading is None:
                failures.append(f"{chapter.slug}: section heading id missing: {section.section_id}")
                continue
            if heading.name != section.level:
                failures.append(f"{chapter.slug}: {section.number} should render as {section.level}, found {heading.name}")

    if failures:
        print("\nFailures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
