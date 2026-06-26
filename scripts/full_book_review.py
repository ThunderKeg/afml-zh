#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "book"
DOCS = ROOT / "docs"
REPORT = DOCS / "full-book-review.md"
BROWSER_REPORT = DOCS / "browser-layout-review.md"


@dataclass(frozen=True)
class CheckResult:
    name: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


def run_command(name: str, command: list[str]) -> CheckResult:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    return CheckResult(name, command, result.returncode, result.stdout, result.stderr)


def run_chapter_checks() -> CheckResult:
    lines: list[str] = []
    failures: list[str] = []
    for path in sorted(BOOK.glob("chapter-*.html")):
        slug = path.stem
        result = subprocess.run(
            [sys.executable, "skills/afml-webbook-chapter-review/scripts/check_chapter.py", "--chapter", slug],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            failures.append(f"{slug}: {result.stdout}{result.stderr}".strip())
            lines.append(f"FAILED {slug}")
        else:
            lines.append(f"OK {slug}")
    return CheckResult(
        "Per-chapter expert workflow checks",
        [sys.executable, "skills/afml-webbook-chapter-review/scripts/check_chapter.py", "--chapter", "chapter-XX"],
        1 if failures else 0,
        "\n".join(lines) + "\n",
        "\n\n".join(failures),
    )


def run_browser_layout_review_gate() -> CheckResult:
    if not BROWSER_REPORT.exists():
        return CheckResult(
            "Browser visual layout review",
            ["manual-browser-qa", str(BROWSER_REPORT.relative_to(ROOT))],
            1,
            "",
            f"{BROWSER_REPORT.relative_to(ROOT)} is missing",
        )
    text = BROWSER_REPORT.read_text(encoding="utf-8")
    passed = "- Status: **PASS**" in text
    return CheckResult(
        "Browser visual layout review",
        ["manual-browser-qa", str(BROWSER_REPORT.relative_to(ROOT))],
        0 if passed else 1,
        "\n".join(text.splitlines()[:40]) + "\n",
        "" if passed else f"{BROWSER_REPORT.relative_to(ROOT)} does not record PASS status",
    )


def parse_tabular(output: str) -> list[dict[str, str]]:
    rows = [line.split("\t") for line in output.splitlines() if line.strip()]
    if not rows:
        return []
    headers = rows[0]
    return [dict(zip(headers, row, strict=False)) for row in rows[1:]]


def collect_site_stats() -> dict[str, object]:
    pages = sorted(BOOK.glob("*.html"))
    chapter_pages = sorted(BOOK.glob("chapter-*.html"))
    contents = BeautifulSoup((BOOK / "index.html").read_text(encoding="utf-8"), "html.parser")

    math_inline = 0
    math_display = 0
    code_listings = 0
    table_figures = 0
    book_figures = 0
    captions = 0
    reference_items = 0
    for page in pages:
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
        math_inline += len(soup.select(".math.inline"))
        math_display += len(soup.select(".math.display"))
        code_listings += len(soup.select("figure.code-listing"))
        table_figures += len(soup.select("figure.table-figure"))
        book_figures += len(soup.select("figure.book-figure"))
        captions += len(soup.select("figcaption"))
        reference_items += len(soup.select(".references-list li"))

    return {
        "html_pages": len(pages),
        "chapter_pages": len(chapter_pages),
        "contents_entries": len(contents.select("[data-toc-entry]")),
        "toc_chapters": len(contents.select(".toc-chapter")),
        "toc_section_links": len(contents.select(".toc-sections a[href*='#sec-']")),
        "toc_details": len(contents.select(".toc-chapter details.toc-details")),
        "math_inline": math_inline,
        "math_display": math_display,
        "code_listings": code_listings,
        "table_figures": table_figures,
        "book_figures": book_figures,
        "captions": captions,
        "reference_items": reference_items,
    }


def summarize_text_coverage(output: str) -> tuple[str, float]:
    rows = parse_tabular(output)
    if not rows:
        return "-", 0.0
    values = [(row.get("chapter", "-"), float(row.get("coverage", "0") or 0)) for row in rows]
    chapter, ratio = min(values, key=lambda item: item[1])
    return chapter, ratio


def summarize_label_count(output: str) -> int:
    rows = parse_tabular(output)
    total = 0
    for row in rows:
        total += int(row.get("source_labels", row.get("source_sections", "0")) or 0)
    return total


def media_summary(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("summary\t"):
            return line.replace("\t", ", ")
    return "-"


def command_line(command: list[str]) -> str:
    return " ".join(command)


def fenced(text: str, limit: int = 2200) -> str:
    text = text.strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + "\n..."
    return f"```text\n{text or '-'}\n```"


def write_report(results: list[CheckResult]) -> None:
    stats = collect_site_stats()
    by_name = {result.name: result for result in results}
    text_chapter, text_ratio = summarize_text_coverage(by_name["Text coverage against source PDF"].stdout)
    source_label_total = summarize_label_count(by_name["Source label alignment"].stdout)
    source_section_total = summarize_label_count(by_name["Source heading alignment"].stdout)
    media = media_summary(by_name["Media asset integrity"].stdout)
    all_passed = all(result.passed for result in results)

    status = "PASS" if all_passed else "FAIL"
    generated = dt.datetime.now().astimezone().replace(microsecond=0).isoformat()

    lines = [
        "# AFML Static Web Book Full Review",
        "",
        f"- Generated: `{generated}`",
        f"- Status: **{status}**",
        f"- Scope: full generated static website in `book/` plus generator and review tooling.",
        "",
        "## Requirement Coverage",
        "",
        "| Requirement | Evidence | Result |",
        "| --- | --- | --- |",
        f"| Text correctness | `audit_text_coverage.py --min-coverage 0.85`; lowest chapter `{text_chapter}` at `{text_ratio:.3f}`; per-chapter expert checks. | {'PASS' if by_name['Text coverage against source PDF'].passed and by_name['Per-chapter expert workflow checks'].passed else 'FAIL'} |",
        f"| Formula correctness | `audit_web_book.py` rejects empty math, raw TeX delimiters, legacy formula fallbacks, and known bad TeX artifacts; per-chapter checker locks reconstructed formulas. `{stats['math_inline']}` inline and `{stats['math_display']}` display MathJax nodes are present. | {'PASS' if by_name['Generated site contract audit'].passed and by_name['Per-chapter expert workflow checks'].passed else 'FAIL'} |",
        f"| Images and captions | `audit_web_book.py` validates figure/table/caption structure, distinct caption typography, caption MathJax sizing, and stronger code-listing captions; `audit_media_assets.py` opens every referenced image. `{stats['book_figures']}` book figures, `{stats['table_figures']}` table figures, `{stats['captions']}` captions. | {'PASS' if by_name['Generated site contract audit'].passed and by_name['Media asset integrity'].passed else 'FAIL'} |",
        f"| Original source comparison | Source label and heading audits compare `pdftotext -layout` against HTML; `{source_label_total}` labels and `{source_section_total}` section headings matched. | {'PASS' if by_name['Source label alignment'].passed and by_name['Source heading alignment'].passed else 'FAIL'} |",
        f"| Book-style contents | `book/index.html` uses a book-toc list, not card grid; `{stats['contents_entries']}` entries, `{stats['toc_chapters']}` chapter rows, `{stats['toc_section_links']}` section links, `{stats['toc_details']}` collapsible section groups. | {'PASS' if by_name['Generated site contract audit'].passed else 'FAIL'} |",
        f"| Browser layout QA | `docs/browser-layout-review.md` records desktop and mobile browser checks for contents, formulas, figures, captions, code width, image loading, MathJax rendering, and page-level overflow. | {'PASS' if by_name['Browser visual layout review'].passed else 'FAIL'} |",
        "",
        "## Site Inventory",
        "",
        f"- HTML pages: `{stats['html_pages']}`",
        f"- Chapter pages: `{stats['chapter_pages']}`",
        f"- Code listings: `{stats['code_listings']}`",
        f"- Reference items: `{stats['reference_items']}`",
        f"- Media summary: `{media}`",
        "",
        "## Automated Gates",
        "",
        "| Check | Command | Result |",
        "| --- | --- | --- |",
    ]

    for result in results:
        lines.append(f"| {result.name} | `{command_line(result.command)}` | {'PASS' if result.passed else 'FAIL'} |")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Text coverage is a smoke test for serious omissions, not proof of character-for-character transcription. Formula, code, table, figure, and finance-specific correctness are additionally covered by chapter-specific checker assertions.",
            "- Source alignment uses `pdftotext -layout` as locator evidence; deliberate source errata and reconstructed formulas are documented in `docs/webbook-conversion-notes.md`.",
            "- The website remains static HTML/CSS/JS. Figures are image assets only when they represent actual charts/plots; text, formulas, code, tables, and captions remain selectable semantic HTML.",
            "- Ordinary figure/table captions are intentionally styled differently from body prose; code-listing captions intentionally remain visually stronger than figure/table captions.",
            "",
            "## Command Output Samples",
            "",
        ]
    )

    for result in results:
        lines.extend(
            [
                f"### {result.name}",
                "",
                fenced(result.stdout),
            ]
        )
        if result.stderr.strip():
            lines.extend(["", "stderr:", fenced(result.stderr)])
        lines.append("")

    REPORT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full final review suite for the AFML static web book.")
    parser.add_argument("--skip-build", action="store_true", help="Review the current generated book without rebuilding first.")
    parser.add_argument("--write-report", action="store_true", help=f"Write {REPORT.relative_to(ROOT)}.")
    args = parser.parse_args()

    checks: list[tuple[str, list[str]]] = []
    if not args.skip_build:
        checks.append(("Static site rebuild", [sys.executable, "scripts/build_web_book.py"]))
    checks.extend(
        [
            ("Generated site contract audit", [sys.executable, "scripts/audit_web_book.py"]),
            ("Source label alignment", [sys.executable, "scripts/audit_source_alignment.py"]),
            ("Source heading alignment", [sys.executable, "scripts/audit_heading_alignment.py"]),
            ("Text coverage against source PDF", [sys.executable, "scripts/audit_text_coverage.py", "--min-coverage", "0.85"]),
            ("Media asset integrity", [sys.executable, "scripts/audit_media_assets.py"]),
            (
                "Python syntax compile",
                [
                    sys.executable,
                    "-m",
                    "py_compile",
                    "scripts/build_web_book.py",
                    "scripts/audit_web_book.py",
                    "scripts/audit_source_alignment.py",
                    "scripts/audit_text_coverage.py",
                    "scripts/audit_heading_alignment.py",
                    "scripts/audit_media_assets.py",
                    "scripts/full_book_review.py",
                    "skills/afml-webbook-chapter-review/scripts/check_chapter.py",
                ],
            ),
        ]
    )

    results = [run_command(name, command) for name, command in checks]
    results.append(run_chapter_checks())
    results.append(run_browser_layout_review_gate())

    for result in results:
        marker = "PASS" if result.passed else "FAIL"
        print(f"[{marker}] {result.name}: {command_line(result.command)}")
        if not result.passed:
            if result.stdout.strip():
                print(result.stdout)
            if result.stderr.strip():
                print(result.stderr, file=sys.stderr)

    if args.write_report:
        write_report(results)
        print(f"report: {REPORT.relative_to(ROOT)}")

    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
