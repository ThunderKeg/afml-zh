#!/usr/bin/env python3
from __future__ import annotations

import html
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "afml.pdf"
TMP = ROOT / "tmp" / "pdf2xml"
XML = TMP / "afml.xml"
BOOK = ROOT / "book"
MEDIA = BOOK / "media"


def run_pdftohtml() -> None:
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    subprocess.run(
        ["pdftohtml", "-q", "-xml", str(PDF), str(XML)],
        cwd=ROOT,
        check=True,
    )


def inner_html(node: ET.Element) -> str:
    parts: list[str] = []
    if node.text:
        parts.append(html.escape(node.text))
    for child in node:
        tag = child.tag.lower()
        if tag in {"b", "i"}:
            parts.append(f"<{tag}>{inner_html(child)}</{tag}>")
        else:
            parts.append(inner_html(child))
        if child.tail:
            parts.append(html.escape(child.tail))
    return "".join(parts)


def font_family(name: str) -> str:
    lower = name.lower()
    if "courier" in lower or "mono" in lower:
        return '"Courier New", Courier, monospace'
    if "stix" in lower or "math" in lower:
        return '"STIX Two Math", "STIXGeneral", "Cambria Math", "Times New Roman", serif'
    return '"Times New Roman", Times, serif'


def build_css(root: ET.Element) -> str:
    rules: list[str] = []
    for font in root.findall("page/fontspec"):
        font_id = font.attrib["id"]
        size = font.attrib.get("size", "12")
        family = font_family(font.attrib.get("family", ""))
        color = font.attrib.get("color", "#000000")
        rules.append(
            f".f{font_id}{{font-size:{size}px;font-family:{family};color:{color};}}"
        )
    return "\n".join(rules)


def copy_image(src_attr: str) -> str:
    source = (ROOT / src_attr).resolve()
    if not source.exists():
        source = (TMP / Path(src_attr).name).resolve()
    MEDIA.mkdir(parents=True, exist_ok=True)
    target = MEDIA / source.name
    if source.exists() and not target.exists():
        shutil.copy2(source, target)
    return f"media/{target.name}"


def page_html(page: ET.Element) -> str:
    number = page.attrib["number"]
    width = page.attrib["width"]
    height = page.attrib["height"]
    parts = [
        f'<a class="page-anchor" name="{number}" id="p{number}"></a>',
        (
            f'<section class="pdf-page" aria-label="PDF page {number}" '
            f'style="width:{width}px;height:{height}px">'
        ),
    ]

    for image in page.findall("image"):
        src = copy_image(image.attrib["src"])
        top = image.attrib["top"]
        left = image.attrib["left"]
        img_width = image.attrib["width"]
        img_height = image.attrib["height"]
        parts.append(
            '<img class="pdf-image" '
            f'src="{html.escape(src)}" alt="" '
            f'style="top:{top}px;left:{left}px;width:{img_width}px;height:{img_height}px">'
        )

    for text in page.findall("text"):
        content = inner_html(text)
        if not content.strip():
            continue
        top = text.attrib["top"]
        left = text.attrib["left"]
        width = text.attrib.get("width", "auto")
        height = text.attrib.get("height", "auto")
        font = text.attrib.get("font", "0")
        parts.append(
            '<span class="pdf-text '
            f'f{font}" style="top:{top}px;left:{left}px;width:{width}px;height:{height}px">'
            f"{content}</span>"
        )

    parts.append("</section>")
    return "\n".join(parts)


def build_html() -> None:
    tree = ET.parse(XML)
    root = tree.getroot()
    if BOOK.exists():
        shutil.rmtree(BOOK)
    MEDIA.mkdir(parents=True)

    pages = root.findall("page")
    body = "\n".join(page_html(page) for page in pages)
    css = build_css(root)
    output = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Advances in Financial Machine Learning</title>
    <link rel="stylesheet" href="../assets/afml-pages.css">
    <style>
{css}
    </style>
  </head>
  <body>
    <main class="pdf-book">
{body}
    </main>
  </body>
</html>
"""
    (BOOK / "afml.html").write_text(output, encoding="utf-8")


def main() -> None:
    run_pdftohtml()
    build_html()
    if TMP.exists():
        shutil.rmtree(TMP)
    try:
        TMP.parent.rmdir()
    except OSError:
        pass


if __name__ == "__main__":
    main()
