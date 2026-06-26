#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

from build_web_book import BOOK, CHAPTERS, PDF, Chapter


WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9']{2,}")
SOURCE_TAIL_RE = re.compile(r"(?im)^\s*(REFERENCES|EXERCISES)\s*$")
STOP_WORDS = {
    "the",
    "of",
    "and",
    "to",
    "in",
    "a",
    "is",
    "for",
    "that",
    "with",
    "as",
    "are",
    "by",
    "on",
    "be",
    "or",
    "this",
    "from",
    "it",
    "an",
    "at",
    "not",
    "can",
    "if",
    "we",
    "will",
    "have",
    "has",
    "into",
    "such",
    "which",
    "when",
    "where",
    "these",
    "those",
    "than",
    "then",
    "their",
    "our",
    "its",
    "using",
    "use",
    "used",
    "also",
    "each",
    "may",
    "more",
    "all",
    "one",
    "two",
    "three",
    "figure",
    "table",
    "snippet",
    "chapter",
    "section",
    "part",
    "references",
    "exercise",
    "exercises",
}


def source_text(chapter: Chapter) -> str:
    text = subprocess.check_output(
        ["pdftotext", "-layout", "-f", str(chapter.start), "-l", str(chapter.end), str(PDF), "-"],
        cwd=PDF.parent,
        text=True,
    )
    tail = SOURCE_TAIL_RE.search(text)
    if tail:
        text = text[: tail.start()]
    return text


def html_text(chapter: Chapter) -> str:
    path = BOOK / chapter.file
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for node in soup.select("script, style, header.book-topbar, .chapter-pager"):
        node.decompose()
    return soup.get_text(" ", strip=True)


def normalize(text: str) -> list[str]:
    text = text.lower()
    text = text.replace("lópez", "lopez").replace("lópez", "lopez")
    text = re.sub(r"([a-z])-\s+([a-z])", r"\1\2", text)
    text = re.sub(r"\s+", " ", text)
    tokens: list[str] = []
    for match in WORD_RE.finditer(text):
        token = match.group(0).strip("'")
        if token and token not in STOP_WORDS:
            tokens.append(token)
    return tokens


def coverage(chapter: Chapter) -> tuple[float, int, int, list[tuple[str, int]]]:
    source_tokens = normalize(source_text(chapter))
    html_tokens = set(normalize(html_text(chapter)))
    source_vocab = set(source_tokens)
    if not source_vocab:
        return 1.0, 0, len(html_tokens), []
    present = source_vocab & html_tokens
    missing_counter = Counter(token for token in source_tokens if token not in html_tokens)
    top_missing = [(token, count) for token, count in missing_counter.most_common(12) if count >= 2]
    return len(present) / len(source_vocab), len(source_vocab), len(html_tokens), top_missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit broad source-text vocabulary coverage in generated chapter HTML.")
    parser.add_argument("--min-coverage", type=float, default=0.80)
    args = parser.parse_args()

    failures: list[str] = []
    print("chapter\tcoverage\tsource_vocab\thtml_vocab\ttop_missing_candidates")
    for chapter in CHAPTERS:
        if not chapter.slug.startswith("chapter-"):
            continue
        ratio, source_vocab, html_vocab, top_missing = coverage(chapter)
        print(
            "\t".join(
                [
                    chapter.slug,
                    f"{ratio:.3f}",
                    str(source_vocab),
                    str(html_vocab),
                    ", ".join(f"{token}:{count}" for token, count in top_missing) or "-",
                ]
            )
        )
        if ratio < args.min_coverage:
            failures.append(f"{chapter.slug}: source vocabulary coverage {ratio:.3f} is below {args.min_coverage:.3f}")

    if failures:
        print("\nFailures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
