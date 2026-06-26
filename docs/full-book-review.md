# AFML Static Web Book Full Review

- Generated: `2026-06-26T04:23:05+08:00`
- Status: **PASS**
- Scope: full generated static website in `book/` plus generator and review tooling.

## Requirement Coverage

| Requirement | Evidence | Result |
| --- | --- | --- |
| Text correctness | `audit_text_coverage.py --min-coverage 0.85`; lowest chapter `chapter-13` at `0.859`; per-chapter expert checks. | PASS |
| Formula correctness | `audit_web_book.py` rejects empty math, raw TeX delimiters, legacy formula fallbacks, and known bad TeX artifacts; per-chapter checker locks reconstructed formulas. `2098` inline and `212` display MathJax nodes are present. | PASS |
| Images and captions | `audit_web_book.py` validates figure/table/caption structure, distinct caption typography, caption MathJax sizing, and stronger code-listing captions; `audit_media_assets.py` opens every referenced image. `90` book figures, `10` table figures, `200` captions. | PASS |
| Original source comparison | Source label and heading audits compare `pdftotext -layout` against HTML; `200` labels and `276` section headings matched. | PASS |
| Book-style contents | `book/index.html` uses a book-toc list, not card grid; `24` entries, `24` chapter rows, `249` section links, `22` collapsible section groups. | PASS |
| Browser layout QA | `docs/browser-layout-review.md` records desktop and mobile browser checks for contents, formulas, figures, captions, code width, image loading, MathJax rendering, and page-level overflow. | PASS |

## Site Inventory

- HTML pages: `25`
- Chapter pages: `22`
- Code listings: `98`
- Reference items: `357`
- Media summary: `summary, referenced=97, unique_referenced=97, media_files=142, unreferenced=45`

## Automated Gates

| Check | Command | Result |
| --- | --- | --- |
| Static site rebuild | `/opt/homebrew/opt/python@3.14/bin/python3.14 scripts/build_web_book.py` | PASS |
| Generated site contract audit | `/opt/homebrew/opt/python@3.14/bin/python3.14 scripts/audit_web_book.py` | PASS |
| Source label alignment | `/opt/homebrew/opt/python@3.14/bin/python3.14 scripts/audit_source_alignment.py` | PASS |
| Source heading alignment | `/opt/homebrew/opt/python@3.14/bin/python3.14 scripts/audit_heading_alignment.py` | PASS |
| Text coverage against source PDF | `/opt/homebrew/opt/python@3.14/bin/python3.14 scripts/audit_text_coverage.py --min-coverage 0.85` | PASS |
| Media asset integrity | `/opt/homebrew/opt/python@3.14/bin/python3.14 scripts/audit_media_assets.py` | PASS |
| Python syntax compile | `/opt/homebrew/opt/python@3.14/bin/python3.14 -m py_compile scripts/build_web_book.py scripts/audit_web_book.py scripts/audit_source_alignment.py scripts/audit_text_coverage.py scripts/audit_heading_alignment.py scripts/audit_media_assets.py scripts/full_book_review.py skills/afml-webbook-chapter-review/scripts/check_chapter.py` | PASS |
| Per-chapter expert workflow checks | `/opt/homebrew/opt/python@3.14/bin/python3.14 skills/afml-webbook-chapter-review/scripts/check_chapter.py --chapter chapter-XX` | PASS |
| Browser visual layout review | `manual-browser-qa docs/browser-layout-review.md` | PASS |

## Notes

- Text coverage is a smoke test for serious omissions, not proof of character-for-character transcription. Formula, code, table, figure, and finance-specific correctness are additionally covered by chapter-specific checker assertions.
- Source alignment uses `pdftotext -layout` as locator evidence; deliberate source errata and reconstructed formulas are documented in `docs/webbook-conversion-notes.md`.
- The website remains static HTML/CSS/JS. Figures are image assets only when they represent actual charts/plots; text, formulas, code, tables, and captions remain selectable semantic HTML.
- Ordinary figure/table captions are intentionally styled differently from body prose; code-listing captions intentionally remain visually stronger than figure/table captions.

## Command Output Samples

### Static site rebuild

```text
-
```

### Generated site contract audit

```text
file	code	ref_lists	ref_items	figures	images	ref_p	dup_ids	table_pre	ex_head	formula_fallback
book-index.html	0	0	0	0	0	0	0	0	0	0
chapter-01.html	0	2	21	2	0	0	0	0	0	0
chapter-02.html	4	1	10	4	3	0	0	0	0	0
chapter-03.html	8	1	39	2	3	0	0	0	0	0
chapter-04.html	11	2	13	3	3	0	0	0	0	0
chapter-05.html	4	2	11	6	5	0	0	0	0	0
chapter-06.html	2	2	8	3	3	0	0	0	0	0
chapter-07.html	4	1	7	3	3	0	0	0	0	0
chapter-08.html	10	1	7	4	4	0	0	0	0	0
chapter-09.html	4	2	10	2	2	0	0	0	0	0
chapter-10.html	4	2	5	3	3	0	0	0	0	0
chapter-11.html	0	2	34	2	2	0	0	0	0	0
chapter-12.html	0	1	4	2	0	0	0	0	0	0
chapter-13.html	2	1	6	26	25	0	0	0	0	0
chapter-14.html	4	2	35	4	3	0	0	0	0	0
chapter-15.html	5	1	4	3	3	0	0	0	0	0
chapter-16.html	5	1	20	9	10	0	0	0	0	0
chapter-17.html	4	1	11	4	3	0	0	0	0	0
chapter-18.html	4	2	23	2	3	0	0	0	0	0
chapter-19.html	2	1	40	3	3	0	0	0	0	0
chapter-20.html	14	2	7	2	2	0	0	0	0	0
chapter-21.html	7	1	5	1	1	0	0	0	0	0
chapter-22.html	0	1	37	10	12	0	0	0	0	0
front-matter.html	0	0	0	1	1	0	0	0	0	0
index.html	0	0	0	0	0	0	0	0	0	0
```

### Source label alignment

```text
chapter	source_labels	html_labels	missing_in_html	extra_in_html
chapter-01	2	2	-	-
chapter-02	8	8	-	-
chapter-03	10	10	-	-
chapter-04	14	14	-	-
chapter-05	10	10	-	-
chapter-06	5	5	-	-
chapter-07	7	7	-	-
chapter-08	14	14	-	-
chapter-09	6	6	-	-
chapter-10	7	7	-	-
chapter-11	3	3	-	-
chapter-12	2	2	-	-
chapter-13	28	28	-	-
chapter-14	9	9	-	-
chapter-15	8	8	-	-
chapter-16	14	14	-	-
chapter-17	8	8	-	-
chapter-18	6	6	-	-
chapter-19	5	5	-	-
chapter-20	16	16	-	-
chapter-21	8	8	-	-
chapter-22	10	10	-	-
```

### Source heading alignment

```text
chapter	source_sections	html_sections	missing_in_html	extra_in_html
chapter-01	24	24	-	-
chapter-02	25	25	-	-
chapter-03	9	9	-	-
chapter-04	12	12	-	-
chapter-05	12	12	-	-
chapter-06	10	10	-	-
chapter-07	8	8	-	-
chapter-08	10	10	-	-
chapter-09	5	5	-	-
chapter-10	6	6	-	-
chapter-11	6	6	-	-
chapter-12	9	9	-	-
chapter-13	12	12	-	-
chapter-14	17	17	-	-
chapter-15	6	6	-	-
chapter-16	11	11	-	-
chapter-17	15	15	-	-
chapter-18	15	15	-	-
chapter-19	21	21	-	-
chapter-20	13	13	-	-
chapter-21	12	12	-	-
chapter-22	18	18	-	-
```

### Text coverage against source PDF

```text
chapter	coverage	source_vocab	html_vocab	top_missing_candidates
chapter-01	0.998	1801	1880	-
chapter-02	0.992	1355	1410	-
chapter-03	0.990	903	1118	rti:7, pti:2, stoploss:2, metalabeling:2
chapter-04	0.914	790	813	blood:7, cholesterol:4, patients:3, tube:3, patient:3, subject:2, your:2, contains:2, chronological:2
chapter-05	0.995	741	816	converges:2
chapter-06	0.992	618	696	-
chapter-07	0.992	514	596	scikitlearn:2
chapter-08	0.986	980	1036	nxn:2
chapter-09	0.990	494	603	logc:2
chapter-10	0.984	445	510	maxi:3, pti:2
chapter-11	0.978	786	908	prob:2
chapter-12	0.986	560	616	datapoints:2, nth:2, combining:2
chapter-13	0.859	813	787	again:4, srr:3, conjunction:3, increased:3, context:2, were:2, mtm:2, questions:2, generated:2, appreciate:2, effect:2, arises:2
chapter-14	0.991	844	1070	plots:2
chapter-15	0.991	450	504	xi2:4
chapter-16	0.985	1217	1339	nxn:2
chapter-17	0.969	748	830	sadft:20, smtt:5, limt:3, adft0:3
chapter-18	0.974	901	1018	lin:7, limq:6, count:4, std:4, x1n:2, ceil:2, top:2, bottom:2
chapter-19	0.982	1099	1245	pint:2
chapter-20	0.987	765	813	txn:2
chapter-21	0.978	497	559	continuous:2
chapter-22	0.983	1653	1770	servers:5, anl:3, qdr:2, continued:2
```

### Media asset integrity

```text
page	src	format	width	height	bytes	mean_luma	stddev_luma
chapter-02.html	media/afml-55_1.jpg	JPEG	561	355	37486	243.1	32.2
chapter-02.html	media/afml-62_1.jpg	JPEG	643	426	27951	242.2	35.1
chapter-02.html	media/afml-67_1.jpg	JPEG	678	444	33998	248.9	17.4
chapter-03.html	media/afml-74_1.jpg	JPEG	680	503	60372	248.3	20.3
chapter-03.html	media/afml-74_2.jpg	JPEG	680	503	59483	248.6	19.9
chapter-03.html	media/afml-79_1.jpg	JPEG	629	548	34019	197.3	58.5
chapter-04.html	media/afml-88_1.jpg	JPEG	653	408	21152	233.0	50.3
chapter-04.html	media/afml-95_1.jpg	JPEG	651	475	47233	229.5	36.2
chapter-04.html	media/chapter-04-figure-4-3.png	PNG	685	480	43034	234.9	57.8
chapter-05.html	media/chapter-05-figure-5-1.png	PNG	675	400	27512	250.1	13.8
chapter-05.html	media/chapter-05-figure-5-2.png	PNG	680	370	27629	250.1	14.3
chapter-05.html	media/chapter-05-figure-5-3.png	PNG	674	1035	205457	243.9	29.3
chapter-05.html	media/chapter-05-figure-5-4.png	PNG	692	490	122603	228.4	53.6
chapter-05.html	media/chapter-05-figure-5-5.png	PNG	575	420	19657	249.8	16.4
chapter-06.html	media/afml-122_1.jpg	JPEG	536	411	27894	177.4	73.4
chapter-06.html	media/afml-124_1.jpg	JPEG	553	403	35652	154.9	105.3
chapter-06.html	media/afml-127_1.jpg	JPEG	533	715	44082	220.3	30.2
chapter-07.html	media/afml-131_1.jpg	JPEG	687	394	37020	222.4	49.6
chapter-07.html	media/afml-134_1.jpg	JPEG	635	552	52025	247.2	23.3
chapter-07.html	media/afml-135_1.jpg	JPEG	620	539	50113	246.8	23.7
chapter-08.html	media/afml-147_1.jpg	JPEG	692	509	56473	238.1	38.8
chapter-08.html	media/afml-152_1.jpg	JPEG	672	555	70048	236.3	26.0
chapter-08.html	media/afml-153_1.jpg	JPEG	664	539	49814	243.2	25.7
chapter-08.html	media/afml-153_2.jpg	JPEG	664	557	88733	227.1	26.3
chapter-09.html	media/afml-160_1.jpg	JPEG	611	437	32649	64.9	71.8
chapter-09.html	media/afml-162_1.jpg	JPEG	681	498	63000	184.8	64.9
chapter-10.html	media/afml-170_1.jpg	JPEG	694	424	33923	247.4	22.5
chapter-10.html	media/afml-172_1.jpg	JPEG	675	413	29501	247.5	22.7
chapter-10.html	media/chapter-10-figure-10-3.png	PNG	715	465	15155	251.9	12.3
chapter-11.html	media/chapter-11-figure-11-1.png	PNG	680	470	157096	239.7	32.9
chapter-11.html	media/chapter-11-figure-11-2.png	PNG	71
...
```

### Python syntax compile

```text
-
```

### Per-chapter expert workflow checks

```text
OK chapter-01
OK chapter-02
OK chapter-03
OK chapter-04
OK chapter-05
OK chapter-06
OK chapter-07
OK chapter-08
OK chapter-09
OK chapter-10
OK chapter-11
OK chapter-12
OK chapter-13
OK chapter-14
OK chapter-15
OK chapter-16
OK chapter-17
OK chapter-18
OK chapter-19
OK chapter-20
OK chapter-21
OK chapter-22
```

### Browser visual layout review

```text
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
```
