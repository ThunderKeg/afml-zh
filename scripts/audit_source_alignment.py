#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

from build_web_book import BOOK, CHAPTERS, PDF, Chapter


LABEL_RE = re.compile(r"\b(?P<kind>SNIPPET|FIGURE|TABLE)\s+(?P<number>\d+\.\d+)\b", re.I)
KIND_ORDER = {"Table": 0, "Figure": 1, "Snippet": 2}


@dataclass(frozen=True)
class Label:
    kind: str
    number: str

    @property
    def key(self) -> str:
        return f"{self.kind} {self.number}"


def chapter_no(chapter: Chapter) -> str | None:
    match = re.fullmatch(r"chapter-(\d+)", chapter.slug)
    return str(int(match.group(1))) if match else None


def normalize_kind(kind: str) -> str:
    return kind[:1].upper() + kind[1:].lower()


def sort_key(label: Label) -> tuple[int, list[int]]:
    parts = [int(part) for part in label.number.split(".")]
    return KIND_ORDER.get(label.kind, 9), parts


def extract_source_labels(chapter: Chapter) -> set[Label]:
    number_prefix = chapter_no(chapter)
    if number_prefix is None:
        return set()
    text = subprocess.check_output(
        ["pdftotext", "-layout", "-f", str(chapter.start), "-l", str(chapter.end), str(PDF), "-"],
        cwd=PDF.parent,
        text=True,
    )
    labels: set[Label] = set()
    for match in LABEL_RE.finditer(text):
        number = match.group("number")
        if not number.startswith(f"{number_prefix}."):
            continue
        labels.add(Label(normalize_kind(match.group("kind")), number))
    return labels


def extract_html_labels(chapter: Chapter) -> set[Label]:
    path = BOOK / chapter.file
    if not path.exists():
        return set()
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    labels: set[Label] = set()
    for caption in soup.select("figure figcaption"):
        text = caption.get_text(" ", strip=True)
        match = LABEL_RE.search(text)
        if match:
            labels.add(Label(normalize_kind(match.group("kind")), match.group("number")))
    return labels


def fmt(labels: set[Label]) -> str:
    return ", ".join(label.key for label in sorted(labels, key=sort_key)) or "-"


def main() -> int:
    failures: list[str] = []
    print("chapter\tsource_labels\thtml_labels\tmissing_in_html\textra_in_html")
    for chapter in CHAPTERS:
        if chapter.slug in {"front-matter", "index-back"}:
            continue
        source_labels = extract_source_labels(chapter)
        html_labels = extract_html_labels(chapter)
        missing = source_labels - html_labels
        extra = html_labels - source_labels
        print(
            "\t".join(
                [
                    chapter.slug,
                    str(len(source_labels)),
                    str(len(html_labels)),
                    fmt(missing),
                    fmt(extra),
                ]
            )
        )
        if missing:
            failures.append(f"{chapter.slug}: source labels missing in HTML: {fmt(missing)}")
        if extra:
            failures.append(f"{chapter.slug}: HTML labels not found in source extraction: {fmt(extra)}")

    if failures:
        print("\nFailures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
