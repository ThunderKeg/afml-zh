# AFML Static Web Book Browser Layout Review

- Generated: `2026-06-26T04:21:58+08:00`
- Status: **PASS**
- Tool: Codex in-app browser runtime with read-only computed-style and DOM checks.
- Viewports: desktop `1280x900`, mobile `390x844`.
- Pages: `book/index.html`, `chapter-13.html`, `chapter-15.html`, `chapter-18.html`, `chapter-20.html`, `chapter-22.html`.

## Checks

| Area | Evidence | Result |
| --- | --- | --- |
| Contents page | `book/index.html` has `.book-toc-panel`, no `.toc-card`, `24` entries, `24` chapter rows, `249` section links, and `22` collapsible section groups at both tested viewports. | PASS |
| Page overflow | All `12` page/viewport combinations had `documentElement.scrollWidth <= clientWidth + 2`. | PASS |
| MathJax rendering | Formula-heavy chapters rendered MathJax containers: Chapter 13 `170`, Chapter 15 `160`, Chapter 18 `205`, Chapter 20 `70`, Chapter 22 `4`. | PASS |
| Images | All tested images loaded: Chapter 13 `25/25`, Chapter 15 `3/3`, Chapter 18 `3/3`, Chapter 20 `2/2`, Chapter 22 `12/12`. | PASS |
| Figure/table captions | Tested figure/table captions rendered at `13.12px` versus body `16px`, muted color `rgb(102,102,102)` versus body `rgb(87,87,87)`, left aligned, width constrained, and with a `1px` top separator. | PASS |
| Code frame width | Tested code listings matched representative prose width: ratio `1.000` on desktop and mobile samples. | PASS |
| Code captions | Tested code-listing captions retained stronger caption styling than ordinary figure/table captions. | PASS |

## Sample Measurements

- Desktop contents page: `scrollWidth=1280`, `clientWidth=1280`, panel width `880`, section links `249`.
- Mobile contents page: `scrollWidth=390`, `clientWidth=390`, panel width `358`, section links `249`.
- Desktop Chapter 20: body paragraph width `1088`, code/prose width ratio `1.000`, figure caption width `832`, images `2/2`, MathJax containers `70`.
- Mobile Chapter 20: body paragraph width `358`, code/prose width ratio `1.000`, figure caption width `326`, images `2/2`, MathJax containers `70`.
