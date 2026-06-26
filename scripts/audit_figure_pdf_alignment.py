#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

from audit_zh_quality import has_dark_crop_strip, image_dimensions
from build_web_book import BOOK, CHAPTERS, PDF, Chapter


ROOT = Path(__file__).resolve().parents[1]
ZH = ROOT / "zh"
FIGURE_LABEL_RE = re.compile(r"\bFIGURE\s+(?P<number>\d+\.\d+)\b", re.I)
EN_CAPTION_RE = re.compile(r"^Figure\s+(?P<number>\d+\.\d+):\s+\S")
ZH_CAPTION_RE = re.compile(r"^图\s+(?P<number>\d+\.\d+)：\s*\S")
VERTICAL_SUBFIGURE_RE = re.compile(
    r"\btop\b.*\bbottom\b|\bbottom\b.*\btop\b|上.*下|下.*上",
    re.I,
)
VERTICAL_SUBFIGURE_MAX_ASPECT = 0.85
ZH_CAPTION_BAD_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"\.\.\.",
        r"TuW，TuW",
        r"ADF统计量",
        r"关于d的函数",
        r"\d+折CV",
        r"Markowitz诅咒",
        r"IVP的",
        r"\d+个原子任务",
        r"HPC计算机",
        r"HPC系统",
        r"非均匀FFT",
        r"具有强烈存在",
        r"^图 13\.\d+：参数",
        r"LTAP\.\(a\)",
        r"结果\.\(b\)",
        r"梯度树提升（GTB）似乎",
    )
]
EXPECTED_EN_CAPTION_SUBSTRINGS = {
    "14.1": "time under water + (TuW)",
    "14.2": "Figure 14.2: PSR as a function of skewness and sample length",
    "16.5": "Figure 16.5: Dendogram of cluster formation",
    "22.6": "Gradient tree boosting (GBT)",
}


@dataclass(frozen=True)
class FigureInfo:
    number: str
    caption: str
    image_srcs: tuple[str, ...]
    classes: tuple[str, ...]


def chapter_no(chapter: Chapter) -> str | None:
    match = re.fullmatch(r"chapter-(\d+)", chapter.slug)
    return str(int(match.group(1))) if match else None


def source_figure_labels(chapter: Chapter) -> set[str]:
    number_prefix = chapter_no(chapter)
    if number_prefix is None:
        return set()
    text = subprocess.check_output(
        ["pdftotext", "-layout", "-f", str(chapter.start), "-l", str(chapter.end), str(PDF), "-"],
        cwd=ROOT,
        text=True,
    )
    return {
        match.group("number")
        for match in FIGURE_LABEL_RE.finditer(text)
        if match.group("number").startswith(f"{number_prefix}.")
    }


def figure_number(caption: str, lang: str) -> str | None:
    pattern = EN_CAPTION_RE if lang == "en" else ZH_CAPTION_RE
    match = pattern.match(caption)
    return match.group("number") if match else None


def html_figures(root: Path, page_name: str, lang: str) -> list[FigureInfo]:
    soup = BeautifulSoup((root / page_name).read_text(encoding="utf-8"), "html.parser")
    figures: list[FigureInfo] = []
    for figure in soup.select("figure.book-figure, figure.cpcv-figure"):
        caption_node = figure.select_one("figcaption")
        caption = caption_node.get_text(" ", strip=True) if caption_node else ""
        number = figure_number(caption, lang) or ""
        images = tuple(image.get("src", "") for image in figure.select("img[src]"))
        figures.append(FigureInfo(number, caption, images, tuple(figure.get("class") or [])))
    return figures


def sort_numbers(values: set[str]) -> list[str]:
    return sorted(values, key=lambda value: [int(part) for part in value.split(".")])


def format_numbers(values: set[str]) -> str:
    return ", ".join(sort_numbers(values)) or "-"


def check_image(root: Path, page_name: str, figure: FigureInfo, src: str, failures: list[str]) -> None:
    if not src.startswith("media/"):
        failures.append(f"{page_name}: Figure {figure.number} uses non-local image src {src}")
        return
    path = root / src
    if not path.exists():
        failures.append(f"{page_name}: Figure {figure.number} missing image asset {src}")
        return
    dimensions = image_dimensions(path)
    if dimensions is None:
        failures.append(f"{page_name}: Figure {figure.number} has unreadable image dimensions {src}")
        return
    width, height = dimensions
    if width < 80 or height < 60:
        failures.append(f"{page_name}: Figure {figure.number} image too small {src} {width}x{height}")
    if has_dark_crop_strip(path):
        failures.append(f"{page_name}: Figure {figure.number} image appears to contain a dark crop strip {src}")
    if VERTICAL_SUBFIGURE_RE.search(figure.caption) and height and width / height > VERTICAL_SUBFIGURE_MAX_ASPECT:
        failures.append(f"{page_name}: Figure {figure.number} caption says top/bottom but image is not vertical {src}")


def main() -> int:
    failures: list[str] = []
    print("chapter\tpdf_figures\tbook_figures\tzh_figures\tbook_images\tzh_images")
    for chapter in CHAPTERS:
        if not chapter.slug.startswith("chapter-"):
            continue
        pdf_numbers = source_figure_labels(chapter)
        book = html_figures(BOOK, chapter.file, "en")
        zh = html_figures(ZH, chapter.file, "zh")
        book_by_number = {figure.number: figure for figure in book if figure.number}
        zh_by_number = {figure.number: figure for figure in zh if figure.number}
        book_numbers = set(book_by_number)
        zh_numbers = set(zh_by_number)

        print(
            "\t".join(
                [
                    chapter.slug,
                    str(len(pdf_numbers)),
                    str(len(book_numbers)),
                    str(len(zh_numbers)),
                    str(sum(len(figure.image_srcs) for figure in book)),
                    str(sum(len(figure.image_srcs) for figure in zh)),
                ]
            )
        )

        if pdf_numbers != book_numbers:
            failures.append(
                f"{chapter.slug}: PDF/book figure numbers differ; missing={format_numbers(pdf_numbers - book_numbers)} extra={format_numbers(book_numbers - pdf_numbers)}"
            )
        if book_numbers != zh_numbers:
            failures.append(
                f"{chapter.slug}: book/zh figure numbers differ; missing_zh={format_numbers(book_numbers - zh_numbers)} extra_zh={format_numbers(zh_numbers - book_numbers)}"
            )

        for figure in book:
            if not figure.number:
                failures.append(f"{chapter.file}: English figure caption is not normalized: {figure.caption[:120]}")
            expected = EXPECTED_EN_CAPTION_SUBSTRINGS.get(figure.number)
            if expected and expected not in figure.caption:
                failures.append(f"{chapter.file}: Figure {figure.number} English caption does not match PDF wording: {figure.caption[:120]}")
            for src in figure.image_srcs:
                check_image(BOOK, chapter.file, figure, src, failures)

        for figure in zh:
            if not figure.number:
                failures.append(f"{chapter.file}: Chinese figure caption is not normalized: {figure.caption[:120]}")
            for pattern in ZH_CAPTION_BAD_PATTERNS:
                if pattern.search(figure.caption):
                    failures.append(f"{chapter.file}: Chinese figure caption has bad pattern {pattern.pattern}: {figure.caption[:120]}")
                    break
            for src in figure.image_srcs:
                check_image(ZH, chapter.file, figure, src, failures)
            if figure.number and figure.number in book_by_number:
                if figure.image_srcs != book_by_number[figure.number].image_srcs:
                    failures.append(f"{chapter.file}: Figure {figure.number} image srcs differ between book and zh")

    if failures:
        print("\nFailures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
