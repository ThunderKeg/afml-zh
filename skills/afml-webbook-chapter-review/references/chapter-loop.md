# Chapter Loop Reference

## Review Inputs

- Source PDF: `afml.pdf`
- Generator: `scripts/build_web_book.py`
- Generated chapter: `book/chapter-XX.html`
- Existing notes: `docs/webbook-conversion-notes.md`

Find page range:

```bash
rg -n 'Chapter\\("chapter-XX"' scripts/build_web_book.py
```

Extract source text:

```bash
pdftotext -f START -l END -layout afml.pdf - | sed -n '1,420p'
```

Render source pages when layout or formulas matter:

```bash
pdftoppm -f START -l END -png afml.pdf tmp/chapter-XX-page
```

## Reviewer Prompts

Use these as separate review tracks.

Math:
Review only chapter XX. Compare `afml.pdf` pages START-END with `book/chapter-XX.html` and the chapter-specific code in `scripts/build_web_book.py`. Find formula, symbol, subscript/superscript, fraction, integral, matrix, and inline MathJax errors. Do not modify files; return exact issues and suggested TeX.

Finance:
Review only chapter XX. Check whether the generated HTML preserves the chapter's financial/economic meaning, variables, assumptions, examples, and interpretations. Compare against `afml.pdf` pages START-END. Do not modify files; return issues and corrected wording/TeX.

Layout:
Review only chapter XX in desktop and mobile browser viewports. Check formulas, code, figures, tables, references, paragraph flow, and overflow. Do not modify files; return DOM/CSS/generator issues and suggested fixes.

## Common Fix Patterns

- Add `CHAPTER_XX_CODE_OVERRIDES` when snippets are split by PDF figures or page breaks.
- Add `chapter_XX_figure_html(...)` when image extraction page ordering is wrong or a vector figure must be cropped from a rendered PDF page.
- Add paragraph overrides when inline math has been split into plain text, especially `x 2`, `T1`, `Sec- tion`, or `pθ*` artifacts.
- Add list overrides for algorithms and coefficient lists; use nested `<ol>` for `(a)/(b)` steps.
- Add list overrides when PDF secondary bullets (`◦`) or indented bullets are flattened. API argument lists and model-configuration categories often need nested `<ul>` to preserve meaning.
- Suppress low-information formula fragments instead of rendering misleading MathJax.
- For chapters where all trustworthy display formulas are reconstructed in paragraph overrides, suppress the chapter's raw extracted formula blocks broadly. Otherwise a late source block can leak as a broken MathJax fragment after the correct formula has already been inserted.
- Suppress leftover formula-sentence fragments when a paragraph override has already reconstructed the same notation.
- For matrix-heavy examples, insert one clean MathJax matrix and suppress all adjacent raw PDF rows, including raw Greek symbols, combining accents, and box-drawing characters.
- Check code blocks for swallowed section headings such as `16.A.4 REPRODUCING ...`; fix with chapter code overrides or parser termination rules.
- If extracted chart media is black-background, reversed, detached from labels, or missing panels, crop white-background figures from rendered PDF pages and suppress the old extracted assets.
- When adding cropped figure assets, add an `ensure_chapter_XX_media()` build hook. `scripts/build_web_book.py` rebuilds `book/media` from scratch, so manually saved crops disappear on the next full build unless the generator recreates them.
- Multi-panel figures should usually be one semantic `<figure>` with multiple images or panels, one caption, and visible panel labels such as `(a)`/`(b)`. Suppress the extracted standalone `(a)`/`(b)` paragraphs.
- Figure captions should not look like body text. Keep `.book-figure figcaption` smaller, muted, book-style left-aligned, width-constrained, and visibly separated from the image; keep code-listing captions visually stronger.
- Table-figure captions should follow the same smaller, muted, book-style left-aligned, constrained caption treatment as image captions. If a chapter has `figure.table-figure`, include it in both static and browser caption QA.
- Matrix-like figures whose row/column assignments carry meaning should become semantic HTML tables instead of images when the table structure can be reconstructed reliably. Add table-specific checker assertions for headers, row labels, marker counts, and sentinel cells.
- Check References/Bibliography for continuation rows such as `Available at ...`; URLs with four-digit path segments must not become standalone list entries.
- Check References/Bibliography for author continuations that look like a new entry, for example a list item beginning with `D., Rubel ...`; attach those fragments to the previous author entry.
- Check References/Bibliography for new author entries prefixed by combining marks. Strip the mark and split the reference, for example `̇Zbikowski, K.` after a previous entry.
- If inline TeX includes `<` or `>`, build it with `math_inline(...)`.
- For formula-dense prose sections, verify both display equations and the surrounding sentence. Common bad leftovers include page-break continuations like `[1980] derives ...`, axis offsets like `1e-3`, bare case-brace glyphs, and duplicate reconstructed formulas.
- When the printed PDF or extracted source appears to contradict the surrounding math, finance logic, or executable code, do not blindly preserve the glyph-level extraction. Compare all three tracks, make the web version semantically consistent, and record the deliberate correction in `docs/webbook-conversion-notes.md`.
- For derivation-heavy chapters, reconstruct the entire mathematical argument as paragraph-level HTML plus MathJax. Fractional-differencing style derivations can require rebuilding the prose, display equations, recurrence, convergence conditions, and follow-on interpretation together; isolated formula overrides leave orphaned OCR rows behind.
- When a code listing crosses a page break, compare the copied code text itself. It is not enough for the code block to tokenize; it must contain the full snippet and not leave the rest of the snippet as a prose paragraph.
- Code listings can swallow the prose immediately after a snippet even when syntax highlighting still succeeds. Search code text for natural-language phrases such as `Snippet X.Y lists`, `which implements`, or sentence continuations, and use a chapter code override plus paragraph reconstruction when needed.
- When a code listing is interrupted by a footnote, check that the footnote did not enter the snippet's docstring or comments. Move the footnote to a semantic `.footnote` paragraph and use a chapter code override for the listing.
- When a snippet continuation after a page break starts at low indentation, it can be misclassified as prose. Check for paragraphs that look like Python (`return`, assignments, `pd.concat`, `out.to_csv`, etc.) immediately before or after code listings, and use a chapter code override when needed.
- If an extracted snippet has a variable-name mismatch caused by OCR or page-break reconstruction, compare the function signature, surrounding prose, and later calls before preserving the raw text. Prefer the version that matches the chapter's stated API.
- When `pdftohtml` extracts chart media, inspect the actual image. A file can load successfully but still be unusable because it has a black background or missing labels; crop a white-background PDF render when needed.
- Caption-only chart figures should be treated as missing media even if the figcaption is present. Crop or reconstruct the visual and keep the figcaption as selectable HTML.
- After adding a cropped figure asset, browser QA must check image load state (`img.complete` and `naturalWidth`), not only static HTML. Missing local assets can pass structural checks until the browser tries to load them.
- Formula-dense performance chapters often need paragraph-level reconstruction for work-count and matrix-partition formulas. Rebuild the surrounding prose plus display equations together, then suppress raw fragments such as bare roots, `condition 12`, or accent/subscript leftovers.
- Browser `textContent` from MathJax can collapse fractions such as `\frac{1}{2}` into `12`. Confirm suspicious math artifacts against static HTML and visual MathJax output before adding a checker failure.
- Footnote URLs should be rendered as `.footnote` paragraphs with breakable text; mobile QA should verify `scrollWidth` for footnotes, not only the full page.
- Ordinary article links can also overflow mobile layouts, especially repaired Stack Overflow or documentation URLs. Apply reusable link wrapping in the CSS template and verify `article a` elements do not exceed their container.
- Put reusable CSS changes in the `write_css()` template inside `scripts/build_web_book.py`, not directly in `assets/afml-book.css`, because the asset is regenerated.
- Bump `ASSET_VERSION` after CSS changes, otherwise the browser can keep old cached styles and make visual QA misleading.
- For mobile formula QA, page overflow is `document.documentElement.scrollWidth`; when `body.scrollWidth` is larger, confirm the wide descendants are contained by `.sourceCode`, `.table-wrap`, or MathJax containers with `overflow-x:auto`.
- For combinatorial-optimization chapters, formulas are often misclassified as bullet lists. Rebuild expected-return, transaction-cost, partition, and feasible-set definitions as display MathJax, then suppress fragments such as `pK,N`, `K1 pi`, raw underbrace glyphs, and standalone axis labels around figures.
- In browser QA, MathJax accessibility text may flatten `p^{K,N}` to `pK,N` or `\binom{K+N-1}{N-1}` to plain text. Treat these as possible false positives unless the static HTML source or visible page still contains the damaged OCR string.
- Code listing frames should match the prose column width. Verify `figure.code-listing.getBoundingClientRect().width` equals a representative paragraph width; long source lines should overflow only inside `.sourceCode`.
- Figure captions should be part of browser QA. Compare `.book-figure figcaption` against body text: it should be smaller, muted, book-style left-aligned, and separate from code-listing captions.
- Figure captions should also be part of static QA when a chapter has `figure.book-figure`: the generated CSS must keep `.book-figure figcaption` at a smaller size, muted color, book-style left alignment, constrained caption-block width, and a visible separator. A chapter should not rely on body-like caption typography.
- If a figure caption contains MathJax, verify that MathJax inherits the caption size. Caption formulas should not visually jump back to body text size.
- Keep visible figcaptions and `alt` text separate in QA: figcaptions should be selectable HTML with proper typography, while `alt` text should describe the visual in plain prose.
- Compare figure captions against a representative body paragraph, not the chapter-header kicker or other muted metadata. A false body sample can make caption QA look better or worse than the real reading experience.
- Do not use global `html, body { overflow-x:hidden; }` to pass visual QA. Fix the offending element or contain overflow inside `.sourceCode`, `.table-wrap`, or explicit MathJax display containers, then measure page-level `documentElement.scrollWidth` again.
- For mobile formula QA, prefer semantic line breaks (`aligned`, cases, or separate displays) when a display equation can be split cleanly. Horizontal formula scrolling is acceptable for inherently wide matrices/tables, but not for simple chained equalities.
- Long inline formulas can visually overflow mobile text without increasing `documentElement.scrollWidth`. Browser QA should scan for visible MathJax nodes outside the article column and convert long inline tuple/list expressions to display MathJax when they cannot wrap naturally.
- Bad-pattern rules should be no broader than the OCR artifact. Avoid raw substring checks that also appear in corrected TeX, such as `e-1` inside `e^{-1}` or `\varphi-1` inside `(\varphi-1)`.
- In generator Python, TeX strings containing backslashes should be raw strings (`r"..."`) or double-escaped. A plain string such as `"20\times20"` silently inserts a tab and damages MathJax output.
- When a formula-dense chapter has been rebuilt through paragraph-level MathJax, consider suppressing the chapter's remaining raw formula blocks by default. OCR matrix rows often leak later as ordinary paragraphs or low-quality formula fragments after the correct display has already been inserted.
- Heat maps and charts should be inspected visually, not only checked for image presence. If extracted images omit axes, titles, ticks, or colorbar labels, crop complete figures from rendered PDF pages and bind those crops while keeping the web figcaption as selectable text.
- Source tables can contain obvious cross-chapter numbering errors. If the surrounding chapter text, captions, and figure sequence prove the source table is wrong, correct the web semantic table and document the deliberate correction in `docs/webbook-conversion-notes.md`.
- Check DOM order around figures when section meaning depends on it. Figures associated with one financial regime should not drift under the next section heading because of PDF float placement.
- Hidden PDF page anchors are not a success metric for the web version. Preserve visible semantic reading order and figure proximity to explanatory text; only inspect page anchors when a user-facing link or navigation target depends on them.
- Quote/callout snippets should not be forced into code listings. If a PDF `SNIPPET` is a quote, maxim, or boxed prose rather than executable/source text, render it as a semantic quote block and exclude it from media-required figure checks.
- Extracted chart images can be technically present but visually unusable, especially black-background plots with missing labels. Inspect chart assets in the browser or as images; crop white-background PDF renders when the extracted asset loses labels or contrast.
- Reference URLs should be cleaned before linkification. Remove PDF wrap spaces in domains and paths (`ssrn .com`, `ssrn. com`, `/ abstract`), repair obvious missing leading `h` in `ttps://`, and ensure `Available at` URLs become anchors that wrap on mobile.
- When reconstructing statistical algorithms, validate the financial/statistical semantics as well as the glyphs. For strategy-selection ranks, distinguish IS performance `R_{n^*}` from OOS performance `\bar R_{n^*}`.
- HPC case-study chapters often have chart text extracted as prose and multi-panel figures split across pages. Crop the actual panels from rendered PDF pages, suppress axis/legend leftovers, and keep a single semantic caption for the whole figure.
- Footnotes in prose should be semantic `.footnote` paragraphs with `<sup>` markers at the call site. Remove extracted footnote continuation lines from ordinary paragraphs and verify long footnote URLs wrap on mobile.
- Reference lists can split venue/publisher continuations into fake entries. Count the source entries and merge continuations such as `IEEE. Choi`, `ACM. Fox`, or `... Redmond, WA. Hirschman` before considering the chapter done.
- Multi-line PDF headings can leave an all-caps continuation paragraph after a web heading, especially when a title ends with `Vs.` or another connector. Merge the continuation into the heading text and add a checker rule for the broken structure.
- Sparse overview tables can shift marker columns leftward or turn wrapped cells into fake rows. Rebuild high-value tables semantically when column placement changes meaning, and add table-specific checks for sentinel rows.
- Wide data tables with an implicit first column should receive an explicit semantic header, such as `Contract`, and row labels should be rendered as `th scope="row"` rather than ordinary `td` cells.
- FAQ or Q&A sections should preserve question boundaries as web-native blocks, not one long paragraph. Suppress PDF running headers such as `FAQs 15` and render questions with a stable class for QA.
- PDF floating tables can be extracted between two halves of a sentence. For a web-native chapter, move the table to the nearest semantic anchor, usually after the paragraph that introduces it, and reconstruct/suppress the split prose around the original table position.
- When a clean display formula is inserted, search nearby paragraphs for duplicate OCR fragments of the same formula, such as `\Lambda ∕2`, raw primes, or mixed MathJax/plain-text symbols. Suppress those fragments in the same chapter pass.
- Reviewer requests to restore Exercises should be treated as intentional suppression unless the project rule changes; keep exercise headings filtered out.
- If generator code is newer than `book/chapter-XX.html`, rebuild before reviewing. A passing checker against stale HTML is not meaningful.
- If a figure is extracted in the middle of a sentence, complete the sentence before the figure and resume explanation after the figure; do not preserve the PDF page break as web reading order.
- If the source PDF pushes figures to a later page, place the web figure next to the paragraph that explains it when that improves reading order. Suppress the later extracted duplicate figure block.
- Footnote QA should inspect HTML and visible rendering. A correct `<sup>` marker can still appear adjacent in `innerText`; the failure is a literal prose `predictions.1`, not a semantic footnote marker.
- Cross-page ordered lists should be reassembled when the PDF page break restarts numbering. This is common for conceptual lists, algorithm steps, and model-configuration remedies; add checker assertions for expected item counts when a split changes meaning.
- Chapter-specific paragraph overrides are often safer than widening global math regexes for dense inline notation such as `Z_{t,n}`, `\lambda_{i,j,k}`, `\widetilde X_i`, and matrix products. Add checker fragments for the corrected TeX and bad-pattern checks for the original glyph-level extraction.
- Distribution definitions and scoring formulas often need grouped reconstruction. For cases-style CDF/PDF formulas or nested sums, rebuild the surrounding definition, display equations, and variable bullets together, then suppress fragments like `[ ] for ...`, `n=0 k=0`, or flattened `pn,k`.
- Backtest-statistics chapters need formula groups validated as financial/statistical definitions, not isolated glyphs. Rebuild TWRR, HHI, PSR/DSR, and classification metrics together with their prose and variable definitions, then add chapter-specific checker fragments for the full corrected TeX.
- If the printed PDF/extraction gives a financially inconsistent formula, compare the surrounding definition before preserving it. For example, an annualized return from total wealth over `y_i` years should render as `(\varphi_{i,T})^{1/y_i}-1`; document the deliberate correction when source glyphs suggest otherwise.
- Boxed laws, aphorisms, or maxims labeled as snippets should be quote snippets, not code listings. Assert that they render as `.quote-snippet` and that no `figure.code-listing` carries the same snippet caption.
- MathJax SVG internals can cause page-level mobile overflow even when `.math.display` has `overflow-x:auto`. Inspect SVG descendants when `documentElement.scrollWidth` is larger than expected, and fix the MathJax container/SVG overflow rather than adding global `overflow-x:hidden`.
- Ordinary inline `code` in prose and list items should wrap on mobile. Keep source listings scrollable with `code.sourceCode { white-space: pre; }`, but allow non-source inline code to use `overflow-wrap:anywhere`.
- Reference cleanup should include mid-URL spaces after schemes and path underscores, not only broken `.com`/`.org` domains. Also merge DOI-only continuation entries into the previous bibliography item.

## Mechanical QA

Run:

```bash
python3 -m py_compile scripts/build_web_book.py scripts/audit_web_book.py
python3 scripts/build_web_book.py
python3 scripts/audit_web_book.py
python3 skills/afml-webbook-chapter-review/scripts/check_chapter.py --chapter chapter-XX
```

Browser assertions should include:

- `document.documentElement.scrollWidth <= document.documentElement.clientWidth + 2`
- all `figure:not(.code-listing)` have loaded media
- `document.querySelectorAll('mjx-container').length > 0` for formula-heavy chapters
- no old OCR artifacts identified by the reviewers
- code blocks have no long runs of blank lines
- long code, tables, and display math scroll inside their own containers on mobile
- figure/table captions are visually distinct from representative body prose: smaller font size, muted color, left alignment, constrained width, visible separation from the media/table, and caption-sized MathJax when formulas appear
- code-listing captions remain stronger than ordinary figure/table captions
