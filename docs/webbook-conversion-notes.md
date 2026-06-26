# Web Book Conversion Notes

## Target

The static book should be semantic HTML, not a PDF page replica and not image-hosted text. Text, formulas, code, tables, figures, and references should remain inspectable and selectable in the browser.

## Rules From The Chapter 2 Prototype

- Prefer web-native layout over PDF pagination. Do not preserve original page numbers as layout structure.
- Render code as `<figure class="code-listing"><pre><code>...</code></pre></figure>` with copy buttons and syntax highlighting.
- Normalize PDF code extraction before highlighting: remove common left margin, quantize indentation to 4-space levels, expand one-line `if/for ...:` suites, split semicolon statements, and normalize Python glyphs such as smart quotes and Unicode dashes.
- Treat quote-only snippets as text, not Python.
- Render References and Bibliography as semantic lists. Keep continuation lines, including page ranges such as `pp. 594-621`, attached to the previous entry.
- Stop References before the next Part/Chapter opener so table-of-contents text cannot leak into the last reference.
- Section headings must match the current chapter number and begin with a real title word. This prevents chart ticks and table rows from becoming headings.
- Filter visual OCR artifacts such as chart axis ticks outside references and tables.
- Keep exercises out of chapter pages.
- Published pages must not use legacy `.formula > pre` fallback blocks. Display formulas should be MathJax `.math.display`; short formulas in prose should be `.math.inline`.
- Do not blindly show broken PDF two-dimensional formula fragments. If a formula can be reconstructed with high confidence, add a chapter-level MathJax override. If the extracted fragment is low-information, such as a bare `∑`, `√`, `[ ]`, or a damaged `\sqrt{}`, suppress it instead of rendering a misleading formula.
- Keep formula and code overflow local to their own containers. The page itself should not gain horizontal scroll on desktop or mobile.

## Current QA Gates

Run:

```bash
python3 scripts/build_web_book.py
python3 scripts/audit_web_book.py
```

The audit fails on:

- duplicate HTML ids
- exercise headings in chapter pages
- reference paragraphs that were not converted to list entries
- Part/Chapter table-of-contents leakage in references
- truncated page ranges in references
- table fallback `<pre>` blocks
- Python snippets that fail `tokenize`
- obvious prose leaked into code
- smart quotes or Unicode dash glyphs inside Python code
- legacy `.formula` fallback blocks
- suspicious TeX artifacts such as `\sqrt{}`, `\sumN`, `\sumn`, `\hat{}`, `\tilde{}`, `\Deltapt`, or `\varepsilont`

## Chapter-by-Chapter Review Workflow

- Work one chapter at a time. Do not attempt full-book semantic repair in one pass.
- For each chapter, run three independent reviews before editing: mathematical notation, financial/economic meaning, and frontend layout.
- Compare against the source PDF pages for that chapter, but implement a web-native chapter page rather than a PDF layout replica.
- Prefer chapter-scoped overrides for damaged PDF extraction. Use them for formulas, line-broken paragraphs, figure binding, code snippets, and algorithm lists when generic parsing would be misleading.
- Keep symbols consistent within the chapter. For Chapter 15, use `\pi_+`, `\pi_-`, `p_{\theta^*}`, and `2\sqrt{p(1-p)}` in the symmetric Sharpe denominator.
- When inline TeX contains `<` or `>`, render it through `math_inline(...)` so the HTML source is escaped and browsers do not parse the formula as markup.
- A chapter is not done until static checks and browser checks both pass: no known OCR artifacts, no empty non-code figures, all referenced figures have media, MathJax renders, code blocks have no extraction blank runs, and page-level horizontal overflow is absent on desktop and mobile.

## Chapter 1 Fixes Captured

- Mechanical chapter checks can pass while semantic tables are wrong. Chapter 1 rebuilds Tables 1.1 and 1.2 as semantic tables because sparse `X` columns shifted left and wrapped cells became fake rows.
- Multi-line section titles can split into a heading plus all-caps paragraph. Chapter 1 merges `1.2 The Main Reason Financial Machine Learning Projects Usually Fail` and suppresses the continuation paragraph.
- PDF page headers inside FAQ sections should be removed, and question boundaries should be restored as web-native `.faq-question` blocks. Chapter 1 renders eleven FAQ questions separately instead of one long paragraph.
- Footnotes should match the reviewed later chapters: call-site `<sup>` markers plus `.footnote` paragraphs with breakable links.
- Exercises remain filtered out by project rule, even when present in the source PDF.

## Chapter 2 Fixes Captured

- Web reading order should override PDF floating layout. Chapter 2 moves Table 2.1 after the Section 2.2 introduction and before Section 2.2.1, then reconstructs the Fundamental Data paragraphs that were split by the table in the PDF extraction.
- Caption-only chart figures must be bound in the generator. Figure 2.3 now uses the extracted chart image `media/afml-67_1.jpg`, and the checker rejects a bare `<figure><figcaption>`.
- Formula reconstruction needs surrounding prose checks. Chapter 2 restores the TIB probability-normalization sentence, removes a duplicate PCA OCR fragment before the clean display equation, and renders the one-sided CUSUM run-up condition instead of a two-sided absolute-value condition.
- Financial definitions around formulas matter. Chapter 2 restores the `\tau_i` transaction-cost paragraph, the `{c_t}`, `{\tilde c_t}`, `{v_t}`, and `v_{i,t}` explanations, and the PCA examples for stock returns, bond-yield changes, and options-volatility changes.
- Preserve domain acronyms in snippet captions. `CUSUM` is now part of the caption acronym allowlist.
- Exercises remain intentionally filtered out, even though reviewers may flag them as PDF content omissions.

## Chapter 3 Fixes Captured

- Chapter pages can be stale after generator edits. Rebuild `book/*.html` before trusting browser or checker output, especially when chapter-specific overrides were just added.
- Fixed-time-horizon labeling needs paragraph-level reconstruction around the formulas. Chapter 3 rebuilds `\{X_i\}_{i=1,\ldots,I}`, the `y_i` cases formula, the return formula, and inline volatility terms such as `\sigma_{t_{i,0}}`.
- Code snippets should be runnable in the web version when the source PDF contains obvious extraction-era bugs. Chapter 3 overrides Snippets 3.2, 3.6, and 3.8 to restore indentation and consistent parameter names/calls.
- Nested bullet structure matters for API semantics. Chapter 3 renders `events -> t1/trgt`, `ptSl -> ptSl[0]/ptSl[1]`, and the three barrier-configuration categories as nested lists.
- Multi-panel figures should be one semantic figure, not duplicated figure blocks. Chapter 3 combines Figure 3.1's two images with `(a)/(b)` panel labels and one caption.
- Figure captions should be visually distinct from body copy. The CSS template now gives `.book-figure figcaption` a smaller, muted, book-style left-aligned treatment, while code listing captions keep their own stronger style.
- Figures inserted in the middle of a sentence should be moved to a semantic paragraph boundary. Chapter 3 completes the ROC sentence before Figure 3.2 and resumes explanation after the figure.
- Footnotes should use a call-site `<sup>` marker and one `.footnote` paragraph. Browser `innerText` may still flatten `predictions.<sup>1</sup>` to `predictions.1`, so inspect the HTML/visual style before treating that as a failure.
- Reference parsing should split entries even when OCR prefixes a new author with a combining mark. Chapter 3 separates Wei from `Zbikowski, K.` and removes the stray combining dot.

## Chapter 4 Fixes Captured

- Chapter 4 suppresses the raw extracted formula blocks and keeps the reconstructed MathJax inserted from paragraph overrides. The PDF extraction leaves misleading fragments around sequential bootstrap, return attribution, and time decay even after the correct formulas are present.
- Figures 4.1 and 4.2 are bound to extracted media, while Figure 4.3 is cropped from a rendered PDF page into `book/media/chapter-04-figure-4-3.png`; browser QA must verify that bound images actually load, not only that `<img>` tags exist.
- Snippets 4.1 and 4.9 use code overrides because page breaks leave function tails outside their code blocks. Snippet 4.5 prose is corrected to “columns in `indM`,” matching the implementation.
- Bibliography intro paragraphs may legitimately appear after a references-style heading, but only as chapter-scoped exceptions; ordinary reference entries should remain in `.references-list` items.
- Figure captions are now a QA target: `.book-figure figcaption` should render smaller, muted, book-style left-aligned, and visually distinct from body copy.

## Chapter 5 Fixes Captured

- Chapter 5 reconstructs the fractional-differentiation derivation at the paragraph level: backshift notation, binomial expansion, long-memory weights, iterative weights, convergence, relative weight loss, FFD truncation, and the ADF-memory trade-off.
- Raw extracted display formulas are suppressed for Chapter 5 because the PDF splits formulas into standalone fragments such as `k=0 xy = k=0`, `X_t-2`, `X̃ t = lk=0`, and `0 if k > l∗`.
- Figures 5.1-5.5 are generated as white-background crops from rendered PDF pages. Existing extracted Figure 5.3/5.4 assets had black backgrounds or split panels, so reviewed chapters should prefer visually inspected crops over merely present image files.
- Snippet 5.3 uses a code override because the page break dedented `for name in series.columns:` out of the function body.
- Table 5.1 needs a semantic contract column. The generator now adds `Contract` to the header row and renders each first-column contract as `th scope="row"`.

## Chapter 6 Fixes Captured

- Ensemble-method formulas are too dense for generic PDF extraction. Chapter 6 reconstructs the bias-variance-noise decomposition, bagging variance derivation, and binomial majority-vote probability as full paragraph-level HTML plus MathJax, then suppresses raw formula fragments.
- Greek symbols with combining macrons such as `\rhō` and `\sigmā` should be normalized to TeX, e.g. `\bar\rho`, `\bar\sigma`, and `\bar\sigma^2`.
- Cross-page ordered lists can silently restart numbering. Chapter 6 merges bias/variance/noise into one three-item list and Random Forest remedies into one five-item list with nested code examples.
- Figure extraction can split captions into a figcaption plus an ordinary paragraph. Chapter 6 explicitly binds Figures 6.1-6.3 and restores Figure 6.2's full caption with inline MathJax.
- A figure inserted mid-sentence should be moved after the sentence is complete. Chapter 6 reconstructs the Boosting paragraph before Figure 6.3 so the web reading order is natural.
- Figure captions are now both a static and browser QA target: `.book-figure figcaption` must be smaller than body text, muted, book-style left-aligned, and distinct from code-listing captions.

## Chapter 7 Fixes Captured

- Cross-validation chapters rely on inline subscripts and event intervals. Chapter 7 reconstructs leakage prose with MathJax for `X_t`, `Y_t`, `\mathbb{E}[Y_{t+1}\mid X_{t+1}]`, `\Phi_i`, `\Phi_j`, and the purging/embargo time intervals.
- PDF page breaks can flatten nested procedures. Chapter 7 rebuilds the k-fold CV procedure and the leakage-remedy discussion as semantic nested lists instead of preserving extracted paragraph fragments.
- Figure 7.1 can be extracted as caption-only even when the image exists. Chapter 7 explicitly binds Figures 7.1-7.3 and checks browser image load state, not only static HTML.
- Running headers inside formula-dense sections must be suppressed. Chapter 7 removes `A SOLUTION: PURGED K-FOLD CV ...` fragments and adds chapter checks so they do not reappear as body prose.
- When the printed PDF conflicts with the surrounding math and code, record a deliberate semantic correction. Chapter 7 renders the overlap condition as `\Phi_i\cap\Phi_j\ne\emptyset`, matching purging logic and the code paths, even though the extracted source line visually resembles an empty-intersection condition.
- Code-listing frame width and figure-caption typography are now included in browser QA: code frames should match the prose column, while long code lines scroll internally; book figure captions should be smaller, muted, and book-style left-aligned.

## Chapter 8 Fixes Captured

- Feature-importance chapters have code listings that continue after footnotes or page breaks. Chapter 8 uses snippet overrides for Snippets 8.2, 8.3, and 8.7-8.9 so Python continuations stay inside code frames rather than leaking into body paragraphs.
- Nested considerations should not be flattened. Chapter 8 renders the MDI masking-effect subpoints as an `<ol type="a">`, and separates the MDA list from the prose introducing Snippet 8.3.
- Inline matrix algebra in prose needs paragraph-level reconstruction. Chapter 8 repairs `Z_{t,n}=\sigma_n^{-1}(X_{t,n}-\mu_n)`, `Z'ZW=W\Lambda`, `P=ZW`, `P'P=W'Z'ZW=W'W\Lambda W'W=\Lambda`, and the parallelized/stacked notation `\lambda_{i,j,k}`, `\Lambda_{j,k}`, `\widetilde X_i\sim X`.
- Caption-only figures can occur even when the media file exists. Chapter 8 explicitly binds Figures 8.1-8.4 to inspected image assets, including Figure 8.2 at `media/afml-152_1.jpg`.
- Web reading order can be better than PDF page order. Chapter 8 places Figures 8.3 and 8.4 next to their explanatory paragraphs instead of preserving the source page break.
- URLs broken by PDF line wraps need explicit repair. Chapter 8 restores the scikit-learn `make_classification` URL and checker coverage.

## Chapter 9 Fixes Captured

- Hyper-parameter tuning chapters can combine cross-page code, footnotes, dense formulas, and floats in one section. Chapter 9 uses `CHAPTER_09_CODE_OVERRIDES` for Snippets 9.1-9.4 so prose such as “Snippet 9.1 lists ...” does not enter code, and Snippet 9.2's `fit_params[...]`/`return super(...)` lines remain inside the code block.
- Formula-dense distribution definitions should be rebuilt as paragraph-level MathJax. Chapter 9 suppresses raw formula fragments and reconstructs the log-uniform definition, CDF, PDF, base-invariance identity, and the log-loss double sum with clean TeX.
- Inline statistical variables in explanatory bullets need semantic MathJax. Chapter 9 renders `p_{n,k}`, `y_{n,k}`, `Y`, and `K` in the log-loss definitions rather than preserving flattened OCR strings like `pn,k`.
- Footnote call sites and URLs should be semantic. Chapter 9 moves the scikit-learn URLs to `.footnote` paragraphs with `<sup>` markers, fixes the Stack Overflow URL split, and gives all article links `overflow-wrap:anywhere` for mobile.
- Reviewer consensus can justify correcting an extraction/source typo when the chapter's own references identify the correct citation. Chapter 9 renders `Bergstra et al.` to match the reference list rather than preserving `Begstra`.
- Figure captions now render as a stronger caption block: `.book-figure figcaption` is smaller, muted, book-style left-aligned, and max-width constrained. Browser QA checks this separately from code-listing captions.
- Asset version must be bumped when CSS changes. Chapter 9 updates `ASSET_VERSION` so the in-app browser reloads the new caption/link styles instead of serving cached CSS.

## Chapter 10 Fixes Captured

- Bet-sizing chapters mix classification probabilities, concurrency counts, dynamic limit-price formulas, and snippets. Chapter 10 reconstructs those formula groups as paragraph-level MathJax instead of preserving damaged OCR fragments such as flattened `p^2`, broken cases, or denominator rows.
- Long display equations should be split semantically when mobile width allows a clean two-line form. The binary test-statistic formula now uses an `aligned` display so 390px QA has no formula-level horizontal overflow.
- Figure media must be visible, not caption-only. Chapter 10 binds Figures 10.1 and 10.2 to extracted assets and creates a cropped `chapter-10-figure-10-3.png` from a rendered PDF page, while keeping captions as selectable HTML.
- Do not use global `overflow-x:hidden` to hide layout errors. The CSS now leaves page overflow measurable; allowed horizontal scrolling should be contained in `.sourceCode`, `.table-wrap`, or explicit MathJax display containers.
- Figure captions are checked against representative body prose, not the chapter header. Chapter 10 browser QA confirmed `.book-figure figcaption` is smaller, muted, book-style left-aligned, and constrained while code frames still match paragraph width.
- Mathematical figure captions need an explicit MathJax inheritance rule. Caption formulas must remain caption-sized instead of visually returning to body scale.
- Keep accessibility alt text separate from visible captions. When a caption uses formulas, the `alt` should still describe the visual semantically in plain text, as with Figure 10.3.
- Probability-to-bet-size formulas can include explanatory underbraces that carry meaning. Chapter 10 locks `m=x\underbrace{(2Z[z]-1)}_{\in[0,1]}` instead of the plainer `m=x(2Z[z]-1)`.
- When OCR or prose makes a scalar result ambiguous, state the variable explicitly. Chapter 10 renders the limit price as `\bar p=112.3657`, satisfying `p_t<\bar p<f_i`.
- Exercises remain intentionally filtered out under the current product decision; chapter reviews should reject partial exercise leakage, not reintroduce exercise sections unless the user reverses that requirement.
- Hidden PDF page anchors are not a quality target for the web version. Visible semantic order should place figures near the explanatory paragraph, even when the old PDF page break would put a hidden anchor elsewhere.

## Chapter 11 Fixes Captured

- Backtest-overfitting chapters can have dense CSCV notation that is unreadable after OCR. Chapter 11 reconstructs the CSCV combination count, training/testing matrix dimensions, selected strategy ranks, logit definition, and PBO integral as semantic MathJax.
- OOS ranks must be checked semantically, not only glyph-by-glyph. The CSCV relative-rank step uses `\bar R_{n^*}` within `\bar R`, while the IS comparison remains `R_{n^*}` within `R`.
- Quote snippets are not code listings. Snippet 11.1 is rendered as `.quote-snippet` with a blockquote and attribution, and the checker excludes `.quote-snippet` from “figures requiring media.”
- Chart images can load but still be unusable if extracted as black-background images with missing labels. Chapter 11 crops white-background Figures 11.1 and 11.2 from rendered PDF page 184 and suppresses the chart OCR text.
- Reference URLs need PDF-wrap cleanup and linkification. The generator now repairs fragments such as `ssrn .com`, `ssrn. com`, `jpm .2017`, `/ abstract`, and `ttps://` before rendering reference-list anchors.
- Mobile QA should reject unnecessary formula scrolling for simple chained equalities. Chapter 11 splits the CSCV combination formula into an `aligned` display so 390px rendering has no formula overflow.

## Chapter 12 Fixes Captured

- Combinatorial purged CV is better represented as semantic web structure than as cropped images. Chapter 12 renders Figures 12.1 and 12.2 as checked HTML tables, with exact group/split/path assignments validated by the chapter checker.
- Table figures need caption treatment too. The shared CSS now applies the smaller, muted, book-style left-aligned, constrained caption style to both `.book-figure figcaption` and `figure.table-figure figcaption`, while code-listing captions keep their stronger label style.
- Long inline tuple lists can visually overflow mobile text even when the document has no page-level horizontal scroll. Chapter 12 converts the path examples into an `aligned` display equation and browser QA checks for visible oversize MathJax nodes outside allowed scroll containers.
- Checker bad-pattern rules must not be broader than the OCR error they target. Chapter 12 removed false positives such as plain `e-1` and `\varphi-1` because those substrings legitimately occur inside corrected TeX forms like `e^{-1}` and `(\varphi-1)`.
- PDF extraction can misclassify explanatory CV paragraphs as ordered-list items. Chapter 12 suppresses the raw stress-test list fragment and reconstructs the surrounding WF/CV/CPCV comparison as prose.

## Chapter 13 Fixes Captured

- Formula-dense chapters can be safer with broad chapter-level raw-formula suppression after the trusted formulas are reconstructed in paragraph overrides. Chapter 13 rebuilds Definitions 1-2, equations (13.1)-(13.7), the O-U half-life relation, and the algorithm steps as semantic MathJax, then suppresses the leftover OCR matrix rows.
- Heat-map figures extracted by `pdftohtml` lost axes, titles, or colorbar labels. Chapter 13 crops Figures 13.1-13.25 from rendered PDF pages and binds them to semantic HTML figure captions, keeping captions selectable while preserving complete visual context.
- Obvious source-table numbering mistakes can be corrected deliberately in the web version. Table 13.1 prints Figure `16.x` in the source PDF, but the chapter text and figure captions are Figure `13.x`; the web table uses `13.1` through `13.25` and the checker locks that mapping.
- DOM order matters for financial interpretation. Figures 13.9-13.15 belong to the positive long-run-equilibrium discussion and are inserted before Section 13.6.3, while Figure 13.16 begins the negative-equilibrium section.
- TeX strings in generator code must be raw strings when they include backslashes such as `\times`; otherwise Python can turn `\t` into a tab and MathJax renders damaged text.

## Chapter 14 Fixes Captured

- Performance-statistics chapters need grouped semantic reconstruction. Chapter 14 rebuilds the TWRR equations, variable definitions, HHI concentration formulas, Sharpe/PSR/DSR formulas, and classification scores as paragraph-level MathJax, then suppresses the raw extracted formula blocks.
- The annualized return formula is rendered as `R_i=(\varphi_{i,T})^{1/y_i}-1`. The source extraction and printed glyphs appear as a negative `y_i` exponent, but the surrounding definition says `y_i` is elapsed years; the web version records the financially consistent annualization.
- Snippet 14.3 crosses an extraction boundary: the `tHHI` line and `getHHI()` function fell into prose. Chapter 14 uses a code override and checker assertions for `tHHI`, `def getHHI`, and `return hhi`.
- Snippet 14.5 is a boxed maxim, not executable code. Render it as `.quote-snippet`, exclude it from code-listing counts, and check the quote body plus attribution.
- Caption-only figures can still have usable extracted media. Chapter 14 binds Figure 14.1 to `media/afml-229_1.jpg`, keeps Figures 14.2 and 14.3 bound to existing chart images, and repairs captions with selectable MathJax where needed.
- MathJax SVG children can keep `overflow: visible` and inflate mobile `documentElement.scrollWidth` even when the display formula container is scrollable. The CSS template now clips SVG overflow inside MathJax containers while keeping the container scrollable.
- Inline `code` in prose can overflow mobile lists independently from code blocks. The CSS template allows ordinary inline code to break with `overflow-wrap:anywhere`, while `code.sourceCode` keeps `white-space: pre` and scrolls inside `.sourceCode`.
- Reference cleanup must handle mid-URL spaces beyond common domains. Chapter 14 repairs `http://www .alacra...`, `http:// citeseerx...`, split MSCI paths, split SSRN IDs, and DOI continuation rows.

## Chapter 15 Fixes Captured

- Chapter 15 has chapter-scoped code overrides for Snippets 15.1-15.5, because the PDF places Figures 15.2 and 15.3 inside code listings and creates artificial blank lines.
- Figure 15.1 is generated from a cropped local PDF render because it is vector content and not emitted by `pdftohtml` as a standalone image.
- Figures 15.2 and 15.3 are explicitly bound to `media/afml-242_1.jpg` and `media/afml-243_1.jpg`. Their visible captions use selectable HTML plus MathJax spans for `n`, `p`, `\pi_-`, `\pi_+`, and `\theta^*`, while their image `alt` text stays plain prose.
- Formula structure should stay inside MathJax when it carries meaning. Chapter 15 keeps the Sharpe-ratio t-value note as an `\underbrace{...}_{\substack{...}}`, keeps `\frac{2p-1}{2\sqrt{p(1-p)}}=0.1005` as one inline equation, and renders `n=\frac{T}{y}` as a fraction rather than flattened text.
- The Chapter 15 algorithm list is rendered as a nested ordered list with MathJax for `p_i`, `\lfloor nk\rfloor`, `f[p]`, and the final strategy-risk integral. The investor assessment horizon keeps the source example `(e.g., 2 years)`.
- Preserve source-book content unless the project deliberately creates an errata layer. Chapter 15 reviewer comments identified a possible statistical correction to the normal approximation and corresponding code standard deviation; the web version keeps the source formula/code rather than silently changing the book.
- Terminology fixes can be semantic even when small: Chapter 15 renders the trading exit condition as `stop-loss`, matching the source and standard risk-management usage.
- Caption QA should avoid false positives from valid MathJax. Static checks should reject raw `\(...\)` only outside `.math.inline` spans, because semantic captions legitimately contain MathJax delimiters inside the span text.

## Chapter 16 Fixes Captured

- Formula-dense chapters need grouped semantic reconstruction, not one-fragment TeX repair. Chapter 16 rebuilds the tree-clustering matrices, recursive-bisection algorithm, complexity notation, allocation constraints, and appendix proofs from source PDF context.
- PDF matrix fragments can appear as raw Greek symbols, combining accents such as `d̃`, and box-drawing rows. Match those raw forms in chapter overrides and suppress the leftover fragments after inserting the clean MathJax matrix.
- Reconstructed formulas still need symbol-level review. Chapter 16 corrected `\tilde d_{i,j}=\tilde d[D_i,D_j]` after review caught the missing tilde on the function name.
- Example captions can contain mathematical symbols too. Chapter 16 renders Example 16.1's `\rho` and `D` as inline MathJax in `.example-caption` instead of lowering them to plain text.
- Web reading order should repair PDF float splits. Chapter 16 merges the Rokach/Maimon, Brualdi, and scipy-library sentence that was split around Figure 16.3, converts the scipy URLs into a semantic footnote, and completes the `Appendix 16.A.2 for a derivation of IVP` sentence before Figure 16.4.
- Code listings can swallow appendix headings when a page break follows code. Chapter 16 uses code overrides for Snippets 16.4 and 16.5 and the chapter checker now flags section-heading patterns inside Python code blocks.
- Multi-panel figures may need local crops from rendered PDF pages. Chapter 16 crops Figures 16.1, 16.3, 16.5, and 16.7, and binds existing extracted media for Figures 16.4, 16.6, and 16.8.
- Multi-panel figure captions should preserve panel semantics. Chapter 16 renders Figure 16.7 as `(a) IVP; (b) HRP; (c) CLA` and splits the panel explanations into three paragraphs.
- Do not silently apply source-book errata during web conversion. Reviewers flagged possible source-level issues in Chapter 16, including covariance-vs-correlation captions and a nonnegative-correlation proof assumption; those are recorded as possible errata but not changed in the faithful web edition.
- Mobile code and table figures must reset default figure side margins; otherwise the content column can look artificially narrow even when horizontal overflow is contained.
- CSS fixes must be made in `scripts/build_web_book.py`'s asset template. Direct edits to `assets/afml-book.css` are overwritten on the next build.
- Long MathJax displays should scroll inside their `mjx-container`, without increasing page-level `documentElement.scrollWidth`. Chapter 16 tightened the CSS template so wide MathJax SVGs and code tokens are clipped by their scroll containers while remaining locally scrollable.

## Chapter 17 Fixes Captured

- Structural-break chapters mix prose, formulas, figures, and regression tables tightly. Repair the financial meaning at the paragraph/list level first, then suppress the leftover raw fragments; otherwise isolated symbols such as `ft`, `i=2`, or chart ticks can survive as standalone paragraphs.
- Some formulas are easiest to reconstruct in adjacent paragraph overrides rather than `chapter_formula_override_html(...)`, especially when the PDF extraction breaks a multi-line derivation into unrelated text runs.
- Use white-background crops from rendered PDF pages for vector figures when `pdftohtml` emits caption-only or empty image fragments. Chapter 17 crops Figures 17.1-17.3 and suppresses the empty follow-on image for Figure 17.3.
- Math inside table cells should use `math_inline(...)` and semantic table markup. Table 17.1 is rendered as a FLOPs table, not as extracted fallback text.
- Keep raw citation markers such as `[41]` in chapter-specific paragraph overrides and let the shared citation styling wrap them once. Pre-wrapping citations inside overrides can create nested citation spans.
- Dense computational-complexity prose can be lost before a table when PDF extraction splits a float. Chapter 17 restores the E-mini S&P 500 dollar-bar FLOPs/PFLOPs example before Table 17.1 and checks the numerical anchors.
- Chapter 17 deliberately records source-book mathematical errata in the web version: Chow's alternative is `H_1:\delta>0`, the full SADF-series cost uses `\sum_{t=\tau}^{T}g(N,t,\tau)`, CSW's backward window is `n\in[1,t-1]`, QADF uses the same `t_0\in[1,t-\tau]` range as SADF/CADF, and the explosive-state threshold uses `-\alpha/\beta`.
- Code-argument prose must be checked against the rendered code, not only the PDF text. The `constant='nc'` option in Chapter 17 means no constant and no trend; `'c'`, `'ct'`, and `'ctt'` add deterministic terms.
- When a log-linear explosiveness test is introduced, use a multiplicative disturbance before taking logs. Chapter 17 renders SM-Exp and SM-Power with `\eta_t` and `\log[\eta_t]=\xi_t` rather than deriving a log model directly from additive errors.
- Bibliographic fixes can be chapter-scoped. Chapter 17 corrects Brown, Durbin, and Evans (1975) to Journal of the Royal Statistical Society: Series B, Vol. 37, No. 2, pp. 149-192.

## Chapter 18 Fixes Captured

- Information-theory chapters require semantic repair of paragraph text, not only display equations. Chapter 18 fixes entropy prose such as `p[x]=1/\|A\|`, `\log_2(1/p[x])`, plug-in word notation `x_1^n`, `A^w`, `y_1^w`, and market-microstructure variables such as `V_\tau^B`.
- Formula fragments can be emitted as prose by `formula_sentence_html(...)`. If a damaged formula sentence is already reconstructed in a paragraph override, add a chapter formula override to suppress the old fragment.
- Code blocks may swallow prose immediately after a snippet. Chapter 18 uses a `CHAPTER_18_CODE_OVERRIDES` entry for Snippet 18.3 so “Ornstein and Weiss ...” is not copied as Python code.
- Figure extraction can produce black-background chart images and detached axis/table labels. Chapter 18 crops Figures 18.1 and 18.2 from rendered PDF pages and suppresses the old `afml-299_*`, `afml-300_*`, and `afml-301_1` assets.
- Reference continuation lines beginning with `Available at ...` must stay attached to the preceding entry even when the URL contains a four-digit numeric segment such as `1401.`.
- Multi-panel figures should be anchored near their explanatory paragraph when the PDF float placement drifts. Chapter 18 moves Figure 18.1 to the end of Section 18.6, before Section 18.7, and renders panels `(a)-(b)` and `(c)-(d)` as one semantic figure with one selectable caption.
- Figure captions are part of the chapter acceptance bar, not a cosmetic afterthought. Chapter 18's checker now verifies smaller muted left-aligned `.book-figure`/`figure.table-figure` captions, MathJax caption-size inheritance, and separate stronger code-listing captions.
- Long formulas inside list items can pass page-level overflow while still visually exceeding the mobile prose column. Chapter 18 renders the generalized-mean special cases as display MathJax within list items instead of inline MathJax.
- The web edition records source-level information-theory issues without silently changing executable snippets: reviewers flagged possible off-by-one and normalization issues in Snippets 18.1 and 18.4, plus log-base/nats-vs-bits tension in entropy formulas. Keep those as documented source errata unless a later pass deliberately chooses corrected-code behavior.

## Chapter 19 Fixes Captured

- Market-microstructure chapters have many formulas embedded inside prose. Chapter 19 reconstructs the tick rule, Roll model result, high-low volatility constants, Corwin-Schultz alpha/beta/gamma equations, Kyle/Amihud/Hasbrouck lambdas, PIN likelihood, VPIN decomposition, and microstructural information definition with chapter-scoped MathJax and paragraph overrides.
- When a two-dimensional formula is split across a page break, leftover continuations can become duplicate paragraphs, for example `[1980] derives ...` or `alphas to 0 ...`. Add exact paragraph suppressions after reconstructing the complete paragraph.
- Code blocks split by page breaks should be replaced with complete source overrides. Chapter 19 uses `CHAPTER_19_CODE_OVERRIDES` for Snippets 19.1 and 19.2, preserving line breaks and avoiding smart dash glyphs in Python.
- Figures extracted by `pdftohtml` may load but have black backgrounds. Chapter 19 crops Figures 19.1-19.3 from rendered PDF pages to produce white-background PNGs, while keeping the visible figcaptions as selectable HTML and avoiding duplicate PDF-cropped captions.
- Lists can be fragmented when PDF bullets are extracted as separate blocks. Chapter 19 renders the four predatory algorithm categories as one semantic `<ul>` and suppresses continuation paragraphs.
- References can be split across lines in ways that look like a new author. Chapter 19 keeps the Beckers entry separate from Bethel and appends `D., Rubel ...` to the Bethel entry instead of letting it become a standalone reference.
- Page-break prose repair should include inline variables, not only sentence joins. Chapter 19 merges Kyle's `orders from noise / traders` split and renders `y=x+u` and `p` as inline MathJax.
- When source glyphs contradict the chapter's own equations and financial meaning, prefer the mathematically consistent web edition and document the correction. Chapter 19 renders Kyle's equilibrium as `\alpha=-p_0\sqrt{\sigma_u^2/\Sigma_0}` because the surrounding derivation states `\alpha=-\mu/(2\lambda)`, and renders the VPIN expectation expansion so it simplifies to `\alpha\mu(1-2\delta)` when `\delta` is the bad-news probability.
- OCR title and compound-word artifacts should be locked in the chapter checker. Chapter 19 rejects `buyinitiated`, `bidask`, `highfrequency`, `socalled`, `Distibution`, and the raw Unicode math remnants around `S_0`, `\alpha`, `\delta`, and `\phi_\tau`.

## Chapter 20 Fixes Captured

- Multiprocessing chapters can have code listings interrupted by footnotes. Chapter 20 uses a `CHAPTER_20_CODE_OVERRIDES` entry for Snippet 20.7 so the Heisenbugs footnote is not copied into the Python docstring and `jobs=[]` is not merged with the following `for` loop.
- When a book code snippet contains an apparent extraction-era variable mismatch, compare the function signature and surrounding explanation. Chapter 20 renders `mpPandasObj` with `pdObj[1]`, matching the function arguments and making the snippet usable.
- Nested-loop partition formulas need paragraph-level reconstruction. Chapter 20 rebuilds the lower-triangular work count, the `S_m` partition target, and the `r_1`, `r_2`, and `r_m` roots as MathJax, then suppresses OCR fragments such as `condition 12 ... = 2M`.
- MathJax-rendered text can collapse `\frac{1}{2}` to `12` in `textContent`; use static HTML and visual MathJax checks before treating that as an OCR artifact.
- Sparse PCA examples are fragile because accents and subscripts get split. Chapter 20 reconstructs `P=Z\tilde W`, the eigenvalue ratio, `P=Z\tilde W=\sum_b Z_b\tilde W_b`, and the meanings of `Z_b`, `\tilde W_b`, and `N_b` in one paragraph override.
- Footnotes with long URLs should be rendered as `.footnote` paragraphs and allowed to break with `overflow-wrap:anywhere`, otherwise mobile pages can hide URL tails under `overflow-x:hidden`.
- Caption-only chart figures should be replaced with white-background PDF crops and semantic figcaptions. Chapter 20 crops Figures 20.1 and 20.2 from rendered PDF pages and binds them explicitly.
- Multi-line PDF section titles can be misread as a heading followed by an all-caps paragraph. Chapter 20 merges `20.3 Single-Thread Vs. Multithreading Vs. Multiprocessing` into one heading and the chapter checker now flags this broken structure.
- If source code contradicts the chapter's stated dimensions and callback semantics, prefer a documented executable erratum. Chapter 20 corrects Snippet 20.4 to partition `r[:, ...]` along `r.shape[1]`, because the 10,000 simulated Gaussian paths are columns and `barrierTouch` iterates columns.
- Long condition formulas inside prose can overflow mobile even when page-level `scrollWidth` is clean. Chapter 20 renders the `r_1`, `r_2`, and `r_m` partition conditions as display MathJax blocks, then checks that the old inline versions do not return.
- Figure/table captions should be visibly distinct from body prose, not just semantically separate. The shared CSS now uses smaller muted left-aligned caption blocks for `.book-figure` and `.table-figure`, while code-listing captions keep their stronger weight.

## Chapter 21 Fixes Captured

- Combinatorial optimization chapters can have formulas misclassified as bullet lists. Chapter 21 renders the expected-return vector and transaction-cost functions through `chapter_list_html(...)` overrides instead of preserving the extracted `<ul>`.
- When objective functions are split into multiple PDF rows, reconstruct the complete display equation and suppress the leftover rows. Chapter 21 rebuilds `SR[r]` and the constrained `\max_{\omega}` problem with MathJax, removing standalone `N` and `i=1` fragments.
- Pigeonhole and partition notation should be repaired at paragraph level. Chapter 21 reconstructs `x_1+\cdots+x_N=K`, `\binom{K+N-1}{N-1}`, `p^{K,N}`, and the definition of `\Omega` in one semantic pass, then suppresses fragments like `pK,N`, `K1 pi`, and raw underbrace glyphs.
- Figure media must be visually inspected, not only checked for existence. Chapter 21 replaces the black-background `afml-349_1.jpg` with a white-background crop of Figure 21.1 and removes axis/legend labels that were extracted as ordinary paragraphs.
- Code snippets can contain a book-layout indentation bug rather than a converter bug. Chapter 21 keeps the source API but dedents Snippet 21.5's parameter-generation block so it renders as executable top-level setup code in the web version.
- Code listing width is now constrained to the same content column as prose. Desktop and mobile QA should compare `figure.code-listing` width against a representative paragraph, while long code lines remain horizontally scrollable inside `.sourceCode`.
- When source formulas contradict their own indexing and executable code, prefer the mathematically consistent web edition and document the erratum. Chapter 21 renders the feasible-weight vector as `\{(s_j/K)p_j\}_{j=1,\ldots,N}` even though the PDF prints `p_i`, because the vector index is `j` and Snippet 21.2 multiplies signs by the corresponding partition coordinate.
- Optimization snippets should match the general model stated in the formulas. Chapter 21 updates `evalTCosts` to accept optional `w0` for the initial allocation `\omega^*`, while preserving the source example's zero-allocation default.
- Set-builder code should avoid duplicate brute-force candidates. Chapter 21 de-duplicates signed weights in `getAllWeights`, because zero components otherwise produce repeated vectors despite `\Omega` being a set.
- Mathematical wording should be corrected when source prose is imprecise. Chapter 21 describes `\sqrt{|\Delta\omega|}` costs as non-smooth/non-differentiable at zero rather than non-continuous.

## Chapter 22 Fixes Captured

- HPC chapters can have figure OCR extracted as body prose. Chapter 22 suppresses chart labels around Figures 22.1, 22.3, and 22.6, crops missing/multi-panel figures from rendered PDF pages, and keeps one semantic caption per figure.
- Figure crops must be visually inspected for both excess and missing content. Chapter 22 tightens Figure 22.1 so the image no longer contains the printed PDF caption/body prose, extends Figure 22.3 to retain the x-axis labels, and widens Figure 22.6 panels to restore the left temperature axis and panel markers.
- Multi-panel figures split across source pages should be rebuilt as one web figure. Chapter 22 renders Figure 22.6 with three cropped image panels and inserts it at the correct section boundary before Section 22.6.4.
- Web reading order must repair PDF float splits. Chapter 22 moves Figures 22.2, 22.3, 22.7, 22.8, and 22.10 after complete sentences/paragraphs, and the checker now rejects broken fragments such as `maximum</p>`, `2.3</p>`, and `see the highest</p>`.
- Footnotes embedded in prose should become call-site `<sup>` markers plus `.footnote` paragraphs. Chapter 22 moves NERSC, HDF5, Cheyenne, and Titan notes out of body paragraphs and ensures their URLs wrap on mobile.
- References in technical chapters often split venue continuations into fake entries. Chapter 22 reconstructs the 37-item reference list, preserving MathJax for `\sqrt{s}=7`, keeping IEEE/ACM continuations attached, and fixing OCR strings such as `Blob-filaments`.
- Chapter-specific heading and typography overrides are useful when PDF extraction title-cases acronyms incorrectly. Chapter 22 restores `HPC`, the full Section 22.6.6 heading, the author line style, and OCR words such as `state-of-the-art`, `point-to-point`, and `in-flight`.
- Figure/table captions are now part of every chapter's visual acceptance bar. Chapter 22 browser QA confirmed `.book-figure figcaption` renders smaller than body prose, muted, left-aligned, width-constrained, and separate from stronger code-listing captions.
- When source captions contain clear technical typos, fix them deliberately and lock them in the checker. Chapter 22 renders `Gradient tree boosting (GTB)` and `newly developed method named LTAP` in Figure 22.6, while recording that the PDF prints `GBT` and `newly develop`.

## Site Index Fixes Captured

- The generated website needs a web-native contents landing page, not the extracted PDF front matter as `book/index.html`. Front Matter now renders as `book/front-matter.html`, while `book/index.html` is a clean grouped table of contents inspired by the `mlfactor` bookdown structure.
- Keep chapter pages sidebar-free, but make the landing page navigationally rich. The contents page groups Front Matter, Preamble, Parts 1-5, and Back Matter, adds concise part summaries, and keeps links to Chapter 1, Front Matter, and the generated book index.
- A static book can still have useful local search without dependencies. The contents page uses a lightweight input to filter chapter rows by part, chapter number, title, and generated section headings, implemented in `assets/afml-book.js`.
- The contents page should expose chapter-internal structure without adding sidebars back to chapter pages. The generator now extracts `h2`/`h3` section anchors from completed chapter HTML and adds section-level links under each chapter row; local-anchor audit verifies that the generated links resolve.
- The contents page should feel like a bookdown table of contents, not a dashboard card grid. The landing page now uses a `book-toc` style list with part groups, chapter rows, and collapsible section lists; search opens matched section details while normal reading keeps the directory compact.
- Site-level QA should include generated navigation checks. `scripts/audit_web_book.py` now verifies that the contents page exists, has 24 entries, links to Front Matter/Chapter 1/Back Matter, and that local `a[href]` targets and anchors resolve.
- Cache-bust CSS/JS when changing global layout. The asset version was bumped so the browser reloads the new contents-page CSS and search script.
- Book covers are not ordinary figures. The Front Matter cover now renders as `.book-cover` with descriptive alt text and no figcaption, while ordinary `.book-figure` images remain required to have selectable captions.
- Site-level media QA should not rely only on chapter-specific checks. `scripts/audit_web_book.py` now verifies local image sources, non-empty image alt text, real media inside non-code figures, figcaptions on ordinary book figures, and no raw TeX delimiters outside MathJax spans in captions.
- Caption typography is now a generated-site contract, not a manual visual preference. `scripts/audit_web_book.py` checks the compiled CSS so ordinary figure/table captions stay smaller, muted, left-aligned, width-constrained, visibly separated from figure/table content, and distinct from stronger code-listing captions.
- Code listings are now a generated-site contract too. `scripts/audit_web_book.py` verifies a non-empty caption, exactly one copy button, `.sourceCode` frame/pre/code structure, non-empty code, tokenizable Python where applicable, and no long extraction blank runs.
- Table figures are now checked as semantic HTML, not just "not `<pre>`." `scripts/audit_web_book.py` verifies `.table-wrap`, real `<table>` markup, `thead`/`tbody`, consistent row widths, header cells, and no single-cell PDF bullet artifacts.
- References are now checked as compact web lists. `scripts/audit_web_book.py` verifies `.references-list` CSS, hanging-indent item styling, non-empty list items, and that reference headings do not fall back to body paragraphs except for documented chapter-scoped introductory prose.
- Referenced image files now have a separate media-asset audit. `scripts/audit_media_assets.py` opens every local `<img>` reference with Pillow, verifies dimensions, byte size, and luma variance, and reports unreferenced extracted assets without failing on them.
- Source alignment now has a separate full-book audit. `scripts/audit_source_alignment.py` extracts Figure/Table/Snippet labels from `pdftotext -layout` as locator evidence and compares them with generated HTML captions chapter by chapter.
- Heading alignment now has a separate full-book audit. `scripts/audit_heading_alignment.py` compares source section numbering with generated `h2`/`h3`/`h4` headings, and verifies stable `sec-*` anchors and heading levels.
- Broad text coverage now has a separate smoke audit. `scripts/audit_text_coverage.py` compares normalized source and HTML vocabulary by chapter after excluding reference/exercise tails, and is meant to catch serious missing pages or paragraphs rather than prove exact transcription.
- Formula rendering now has site-level guardrails in `scripts/audit_web_book.py`: empty `.math.inline`/`.math.display` nodes fail, and raw TeX delimiters outside MathJax spans fail across the whole book, not just inside captions.
- Figure/table caption styling is a site-wide acceptance rule. Ordinary image/table captions must be visually different from body prose, while code-listing captions keep their stronger label style; the full-book review report now records this as part of the Images and captions requirement.
- Full-book acceptance is consolidated in `scripts/full_book_review.py --write-report`, which rebuilds the site, runs global audits, runs every chapter checker, and writes `docs/full-book-review.md`.
- Browser layout evidence is recorded in `docs/browser-layout-review.md` and is now a full-book acceptance gate. It covers desktop and mobile checks for the contents page, page-level overflow, MathJax rendering, loaded images, code/prose width parity, and caption typography.
- Do not run source-alignment or chapter-check audits concurrently with `scripts/build_web_book.py`, because the build recreates `book/`. Rebuild first, then run read-only audits against the completed output.

## Remaining Work

- Continue adding semantic overrides for damaged two-dimensional formulas when a reader reports a specific location. The current generator prioritizes correct MathJax for high-confidence formulas and suppresses low-confidence fragments that would otherwise display incorrectly.
- Add more semantic table overrides for complex tables. Table 13.1 is now structurally intact, but only Table 2.1 has bespoke semantic cell lists.
- Improve figure binding by using PDF image positions rather than page-level ordering. Until that exists, use chapter-scoped figure binding for reviewed chapters.
