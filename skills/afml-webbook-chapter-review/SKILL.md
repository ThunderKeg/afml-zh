---
name: afml-webbook-chapter-review
description: Review and repair one chapter at a time in the AFML static HTML web book generated from afml.pdf. Use when Codex is asked to continue chapter-by-chapter conversion, fix formulas, code blocks, figures, tables, references, or visual layout in book/chapter-XX.html while preserving semantic HTML and MathJax rather than PDF-page images.
---

# AFML Webbook Chapter Review

## Scope

Work on exactly one chapter per iteration unless the user explicitly asks otherwise. Prefer the chapter in the current browser URL; otherwise continue from the last completed chapter.

The goal is a web-native chapter page: selectable text, MathJax formulas, semantic code/table/list markup, real figure media, and no PDF page-layout imitation.

## Required Workflow

1. Identify the chapter and source PDF page range from `scripts/build_web_book.py`.
2. Read `references/chapter-loop.md` before editing a chapter.
3. Collect three independent reviews before or during implementation:
   - math notation and formula integrity
   - financial/economic meaning
   - frontend layout and responsive behavior
4. Compare the current HTML against `pdftotext -layout` and rendered PDF page images. Use extraction only as a locator; trust visual PDF render and domain reasoning for damaged formulas.
5. Implement chapter-scoped fixes in `scripts/build_web_book.py` unless a generic parser defect is proven across chapters.
6. Rebuild with `python3 scripts/build_web_book.py`.
7. Run global audit: `python3 scripts/audit_web_book.py`.
8. For whole-book QA, or after touching source extraction/rendering, run source and media audits: `python3 scripts/audit_source_alignment.py`, `python3 scripts/audit_heading_alignment.py`, `python3 scripts/audit_text_coverage.py`, and `python3 scripts/audit_media_assets.py`.
9. Run chapter audit: `python3 skills/afml-webbook-chapter-review/scripts/check_chapter.py --chapter chapter-XX`.
10. Verify in browser at desktop and mobile viewports after MathJax renders.
11. For final whole-book acceptance, run `python3 scripts/full_book_review.py --write-report`; this rebuilds the site, runs all global audits, runs every chapter checker, and writes `docs/full-book-review.md`.
12. Update `docs/webbook-conversion-notes.md` when a reusable pattern is learned.

## Implementation Rules

- Keep exercises filtered out unless the user reverses that requirement.
- Do not render text, formulas, or code as page screenshots. Figure images are allowed for actual charts/plots.
- Use chapter-level overrides for damaged inline formulas, display formulas, algorithm lists, code snippets, and figure binding.
- Render inline formulas containing `<` or `>` through `math_inline(...)` so HTML escapes them.
- Do not leave raw TeX delimiters in ordinary text. Formula delimiters belong inside `.math.inline` or `.math.display`, and empty math nodes must fail global audit.
- Use `\pi_+` and `\pi_-` when the source PDF uses payout labels, not `\pi^+` and `\pi^-`.
- Clean PDF-induced code blank lines with code overrides when figures or page breaks split snippets.
- Code listings must stay as the web component, not loose text: `figure.code-listing` with a non-empty caption, one copy button, a `.sourceCode` frame, a `pre.sourceCode`, a `code.sourceCode`, tokenizable Python when marked as Python, and no long extraction blank runs.
- Table figures must stay semantic: `figure.table-figure` with a non-empty caption, `.table-wrap`, a real `<table>` with `thead` and `tbody`, consistent row widths, header cells, and no PDF bullet artifacts such as lone `r`, `•`, or `◦` cells.
- Non-code figures must contain real media (`img`, `svg`, `canvas`, or a semantic table). Never leave caption-only figures in a reviewed chapter.
- Figure and table captions must not look like body text: use smaller, muted, book-style left-aligned caption typography, a constrained caption-block width, and a visible separator from the image/table content; ensure MathJax inside captions inherits the caption size.
- Treat caption typography as a generated-site contract. `scripts/audit_web_book.py` checks the compiled CSS for the separate figure/table caption style and for stronger code-listing captions.
- Keep visible figcaptions and image `alt` text separate. Captions should remain selectable HTML; alt text should describe the visual in plain prose, especially when the caption contains formulas.
- Compare figure/table captions against representative body prose in browser QA. The check should verify font size, color, line height, alignment, and that code-listing captions remain visually stronger than book figure captions.
- Treat referenced image files as first-class deliverables. `scripts/audit_media_assets.py` must be clean for whole-book QA, verifying that all referenced local images are readable, non-trivial in size, and not nearly blank.
- Treat `scripts/audit_text_coverage.py` as a broad leak detector, not a proof of exact transcription. It is intended to catch serious missing pages or paragraphs after extraction/rendering changes; formula, code, and economic correctness still require chapter review.
- References and bibliography sections must render as `.references-list` items with compact hanging-indent CSS. Do not allow reference entries to fall back to large body paragraphs, except for documented chapter-scoped introductory prose.
- PDF float placement is not web reading order. If a figure, table, heading, or footnote splits a sentence, move the web element after the completed sentence or paragraph and add a chapter checker artifact for the broken form.
- Keep page-level horizontal overflow absent. Long code and wide formulas may scroll inside their own containers.

## Done Criteria

A chapter is complete only when:

- the math, finance, and layout reviews have no open blocking findings
- global and chapter audits pass
- source-label, heading-alignment, text-coverage, and media-asset audits pass for whole-book QA or any cross-chapter extraction/rendering change
- browser checks show MathJax containers, loaded figures, no page-level horizontal overflow, and no console errors
- browser checks compare figure/table captions against representative body prose, including caption MathJax sizing when captions contain formulas
- known OCR artifacts for that chapter are absent
- code blocks tokenize when marked as Python, keep the standard web component structure, and have no extraction blank runs
