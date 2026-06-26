#!/usr/bin/env python3
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image, ImageStat, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "book"
MEDIA = BOOK / "media"


@dataclass(frozen=True)
class ImageRef:
    page: Path
    src: str
    alt: str

    @property
    def path(self) -> Path:
        return self.page.parent / self.src


def local_image_refs() -> list[ImageRef]:
    refs: list[ImageRef] = []
    for page in sorted(BOOK.glob("*.html")):
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
        for image in soup.select("img"):
            src = image.get("src", "")
            if not src or src.startswith(("http://", "https://", "data:")):
                continue
            refs.append(ImageRef(page, src, image.get("alt", "")))
    return refs


def image_stats(path: Path) -> tuple[str, int, int, float, float]:
    with Image.open(path) as image:
        image.load()
        fmt = image.format or path.suffix.lstrip(".").upper()
        width, height = image.size
        sample = image.convert("L")
        sample.thumbnail((160, 160))
        stat = ImageStat.Stat(sample)
        mean = float(stat.mean[0])
        stddev = float(stat.stddev[0])
    return fmt, width, height, mean, stddev


def main() -> int:
    failures: list[str] = []
    refs = local_image_refs()
    referenced = {ref.path.resolve() for ref in refs}
    media_files = {path.resolve() for path in MEDIA.glob("*") if path.is_file()} if MEDIA.exists() else set()

    print("page\tsrc\tformat\twidth\theight\tbytes\tmean_luma\tstddev_luma")
    for ref in refs:
        path = ref.path
        if not path.exists():
            failures.append(f"{ref.page.name}: missing image asset: {ref.src}")
            continue
        try:
            fmt, width, height, mean, stddev = image_stats(path)
        except (OSError, UnidentifiedImageError) as exc:
            failures.append(f"{ref.page.name}: unreadable image asset {ref.src}: {type(exc).__name__}")
            continue
        size = path.stat().st_size
        print("\t".join([ref.page.name, ref.src, fmt, str(width), str(height), str(size), f"{mean:.1f}", f"{stddev:.1f}"]))
        if fmt.upper() not in {"JPEG", "JPG", "PNG", "WEBP"}:
            failures.append(f"{ref.page.name}: unsupported image format {fmt}: {ref.src}")
        if width < 80 or height < 60:
            failures.append(f"{ref.page.name}: image dimensions too small {width}x{height}: {ref.src}")
        if size < 1_000:
            failures.append(f"{ref.page.name}: image file unexpectedly small ({size} bytes): {ref.src}")
        if stddev < 1.0:
            failures.append(f"{ref.page.name}: image appears nearly blank (stddev={stddev:.2f}): {ref.src}")

    unreferenced = sorted(media_files - referenced)
    print(f"summary\treferenced={len(refs)}\tunique_referenced={len(referenced)}\tmedia_files={len(media_files)}\tunreferenced={len(unreferenced)}")

    if failures:
        print("\nFailures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
