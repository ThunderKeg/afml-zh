#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tokenize
from pathlib import Path

from bs4 import BeautifulSoup


BAD_TEXT_PATTERNS = [
    "−4p2",
    "𝜃 2",
    "𝜋 2",
    "p𝜃",
    "pθ",
    "T1",
    "Sec-",
    "frequen-",
    "num- ber",
    "p\\theta^*",
    "d\\tilde{i}",
    "Vo1.",
    "minimumvariance",
    "crosssectionally",
    "reestimated",
    "Smalldata",
    "∈ Aw",
    "p[x] = ‖A‖",
    "log2 p[x]",
    "Hn,k",
    "h = 1.42",
    "None count",
    "PIN =",
    "V𝜏B",
    "𝜃i",
    "riskadjusted",
    "T t=1 Lt",
    "St = 1 + e𝛼t",
    "WHAT IS MICROSTRUCTURAL INFORMATION? 295",
    "[1980] derives that, for continuously observed prices",
    "i_n Zb",
    "outputed",
    "non-negative(integer",
    "K N+ N− 1− 1",
    "pK,N",
    "K1 pi",
    "{{ s the",
    "Asset 1 Asset 1",
    "Units of capital Units of capital",
    "Measurements of√",
    "Hpc Hardware",
    "Hpc Software",
    "Figure 22.6: (Continued)",
    "IEEE. Choi",
    "ACM. Fox",
    "Microsoft research Redmond, WA. Hirschman",
    "Blobfilaments",
    "state-ofthe-art",
    "pointto-point",
    "inflight analysis",
    "cuttingedge",
    "onceper-minute",
    "DE-AC02- 05CH11231",
    "PROJECTS USUALLY FAIL",
    "FAQs 15",
    "FAQs 17",
    "evi- dence",
    "iso- lation",
    "gradu- ated",
    "com- petitors",
    "largescale",
]
BAD_HTML_PATTERNS = [
    r"<figure><figcaption>",
    r"<p>Financial Machine Learning as a Distinct Subject</p>",
    r"Chapter</p>\s*<ol><li>Instead",
    r"<tr><td>backtesting</td><td>analysis",
    r"<tr><td>labeling</td><td>method",
    r"<tr><td>samples</td><td>sequential",
    r"<tr><td>leakage</td><td>embargoing",
    r"<tr><td>\(historical\) backtesting</td><td>cross-validation",
    r"π</span>\s*2",
    r"𝜋</span>\s*2",
    r"P\[p\s*(?:&lt;|<)\s*p\\theta",
    r"<li>\s*D\., Rubel",
    r"\\tilde\{b\}\s+defined by the columns",
    r"afml-349_1\.jpg",
    r"<ul><li>\s*=\s*diag",
    r"<li>\s*𝜏1\s*\[𝜔\]",
]
BAD_CODE_GLYPH_RE = re.compile(r"[–—−’‘“”]")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def chapter_path(root: Path, chapter: str | None, file_arg: str | None) -> Path:
    if file_arg:
        path = Path(file_arg)
        return path if path.is_absolute() else root / path
    if not chapter:
        raise SystemExit("Provide --chapter chapter-XX or --file path/to/chapter.html")
    file_name = f"{chapter}.html" if chapter.startswith("chapter-") else chapter
    return root / "book" / file_name


def max_blank_run(text: str) -> int:
    max_run = 0
    run = 0
    for line in text.splitlines():
        if line.strip():
            run = 0
        else:
            run += 1
            max_run = max(max_run, run)
    return max_run


def audit(path: Path) -> tuple[dict[str, object], list[str]]:
    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=False)
    failures: list[str] = []
    chapter_slug = path.stem

    ids = [tag.get("id") for tag in soup.select("[id]") if tag.get("id")]
    duplicate_ids = len(ids) - len(set(ids))
    if duplicate_ids:
        failures.append(f"duplicate ids: {duplicate_ids}")

    if soup.select(".formula"):
        failures.append(f"legacy .formula blocks: {len(soup.select('.formula'))}")

    headings = [h.get_text(" ", strip=True).upper() for h in soup.select("h1,h2,h3,h4")]
    if "EXERCISES" in headings:
        failures.append("exercise heading remains")

    heading_continuations = []
    for heading in soup.select("h2,h3,h4"):
        next_tag = heading.find_next_sibling()
        if next_tag and next_tag.name == "p":
            continuation = next_tag.get_text(" ", strip=True)
            if (
                heading.get_text(" ", strip=True).rstrip().endswith(("Vs.", "vs.", "Vs", "vs"))
                and re.fullmatch(r"[A-Z][A-Z0-9 ,/&'’.-]{4,}", continuation)
            ):
                heading_continuations.append(f"{heading.get_text(' ', strip=True)} / {continuation}")
    if heading_continuations:
        failures.append(f"heading continuation paragraphs remain: {heading_continuations}")

    if chapter_slug == "chapter-01":
        sec_1_2 = soup.select_one("#sec-1-2")
        if sec_1_2 is None or sec_1_2.get_text(" ", strip=True) != "1.2 The Main Reason Financial Machine Learning Projects Usually Fail":
            failures.append("chapter-01 section 1.2 heading is not merged")
        if len(soup.select(".faq-question")) < 10:
            failures.append("chapter-01 FAQ questions are not structurally separated")
        if len(soup.select("p.footnote sup")) != 3:
            failures.append("chapter-01 footnotes are not semantic")
        table_1_1 = next((fig for fig in soup.select("figure.table-figure") if fig.get_text(" ", strip=True).startswith("Table 1.1:")), None)
        if table_1_1 is None:
            failures.append("chapter-01 Table 1.1 missing")
        else:
            rows = [[td.get_text(" ", strip=True) for td in tr.select("td")] for tr in table_1_1.select("tbody tr")]
            checks = {
                "5": ["X", "X", "", "X", "", ""],
                "6": ["", "X", "", "", "", ""],
                "7": ["", "X", "", "", "X", "X"],
                "16": ["", "X", "", "X", "X", "X"],
                "20": ["", "X", "X", "X", "", ""],
            }
            by_chapter = {row[1]: row[2:] for row in rows if len(row) >= 8}
            bad = {chapter: by_chapter.get(chapter) for chapter, expected in checks.items() if by_chapter.get(chapter) != expected}
            if len(rows) != 21 or bad:
                failures.append(f"chapter-01 Table 1.1 X matrix is wrong: {bad}")
        table_1_2 = next((fig for fig in soup.select("figure.table-figure") if fig.get_text(" ", strip=True).startswith("Table 1.2:")), None)
        if table_1_2 is None:
            failures.append("chapter-01 Table 1.2 missing")
        else:
            rows = [[td.get_text(" ", strip=True) for td in tr.select("td")] for tr in table_1_2.select("tbody tr")]
            if len(rows) != 10 or any(len(row) != 5 for row in rows):
                failures.append("chapter-01 Table 1.2 has fake continuation rows")

    if chapter_slug == "chapter-02":
        figure_2_3 = next((fig for fig in soup.select("figure") if fig.get_text(" ", strip=True).startswith("Figure 2.3:")), None)
        if figure_2_3 is None or not figure_2_3.select_one('img[src="media/afml-67_1.jpg"]'):
            failures.append("chapter-02 Figure 2.3 is not bound to its extracted chart image")
        prose_text = "\n".join(p.get_text(" ", strip=True) for p in soup.select("p"))
        if "gaps.loc[rollDates[1:]]" in prose_text:
            failures.append("chapter-02 duplicate Snippet 2.2 code tail remains as prose")
        snippet_2_2 = next((fig for fig in soup.select("figure.code-listing") if fig.get_text(" ", strip=True).startswith("Snippet 2.2:")), None)
        if snippet_2_2 is None:
            failures.append("chapter-02 Snippet 2.2 missing")
        else:
            code_tag = snippet_2_2.select_one("code")
            source = code_tag.get_text("", strip=False) if code_tag else ""
            if source.count("def rollGaps") != 1 or "return gaps" not in source:
                failures.append("chapter-02 Snippet 2.2 is incomplete")
        snippet_2_4 = next((fig for fig in soup.select("figure.code-listing") if fig.get_text(" ", strip=True).startswith("Snippet 2.4:")), None)
        if snippet_2_4 is None or "CUSUM" not in snippet_2_4.select_one("figcaption").get_text(" ", strip=True):
            failures.append("chapter-02 Snippet 2.4 caption does not preserve CUSUM acronym")
        table_2_1 = next((fig for fig in soup.select("figure.table-figure") if fig.get_text(" ", strip=True).startswith("Table 2.1:")), None)
        if table_2_1 is None or table_2_1.select("td")[2].get_text(" ", strip=True).split()[-1] != "...":
            failures.append("chapter-02 Table 2.1 Analytics column is missing ellipsis")
        if "Λ ∕2" in text or r"\left|\sum_{i=\tau}^{t}" in html:
            failures.append("chapter-02 formula artifact remains")
        if r"P[b_t=1]+P[b_t=-1]=1" not in html:
            failures.append("chapter-02 TIB probability normalization sentence is missing")
        if r"\tau_i=1E-4" not in html or "negative) dividend" not in text or r"\{\tilde{c}_t\}" not in html or r"v_{i,t}" not in html:
            failures.append("chapter-02 ETF transaction-cost definitions are incomplete")
        if "returns of stocks" not in text or "changes in yield of bonds" not in text or "options' volatilities" not in text:
            failures.append("chapter-02 PCA invariant examples are missing")
        if r"\sum_{i=\tau}^{t}\left(y_i-\mathbb{E}_{i-1}[y_i]\right)\ge h" not in html:
            failures.append("chapter-02 CUSUM run-up condition is not one-sided")
        if r"1-P[b_t=-1]" in html:
            failures.append("chapter-02 tick-runs probability explanation is inconsistent")
        if "Chapters 17– 19" in text:
            failures.append("chapter-02 chapter-range spacing artifact remains")
        if any(p.get_text(" ", strip=True).endswith("using misaligned") for p in soup.select("p")):
            failures.append("chapter-02 Fundamental Data paragraph is still split before Table 2.1")
        if any(p.get_text(" ", strip=True).startswith("fundamental data, especially") for p in soup.select("p")):
            failures.append("chapter-02 Fundamental Data continuation remains after Table 2.1")
        article = soup.select_one("article")
        if article and table_2_1:
            ordered = article.find_all(["h3", "figure"])
            try:
                if ordered.index(table_2_1) > ordered.index(soup.select_one("#sec-2-2-1")):
                    failures.append("chapter-02 Table 2.1 appears after the Fundamental Data heading")
            except ValueError:
                pass

    if chapter_slug == "chapter-03":
        chapter_3_bad = [
            "A_n observation",
            "rti,0",
            "pti,0",
            "\\sigma_{t}i",
            "metalabeling",
            "meta- labels",
            "Remem- ber",
            "predictions.1",
            "minPtc",
            "inst['Close']",
            "̇Zbikowski",
        ]
        for pattern in chapter_3_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-03 artifact remains: {pattern}")
        if r"y_i=\begin{cases}-1, &amp; r_{t_{i,0},t_{i,0}+h}&lt;-\tau" not in html:
            failures.append("chapter-03 fixed-time horizon label formula is not reconstructed")
        if r"r_{t_{i,0},t_{i,0}+h}=\dfrac{p_{t_{i,0}+h}}{p_{t_{i,0}}}-1" not in html:
            failures.append("chapter-03 return formula is not reconstructed")
        snippet_3_2 = next((fig for fig in soup.select("figure.code-listing") if fig.get_text(" ", strip=True).startswith("Snippet 3.2:")), None)
        if snippet_3_2 is None:
            failures.append("chapter-03 Snippet 3.2 missing")
        else:
            source = snippet_3_2.select_one("code").get_text("", strip=False)
            if "def applyPtSlOnT1(close, events, ptSl, molecule):" not in source or "    if ptSl[0] > 0:" not in source:
                failures.append("chapter-03 Snippet 3.2 indentation/source is wrong")
        snippet_3_6 = next((fig for fig in soup.select("figure.code-listing") if fig.get_text(" ", strip=True).startswith("Snippet 3.6:")), None)
        if snippet_3_6 is None:
            failures.append("chapter-03 Snippet 3.6 missing")
        else:
            source = snippet_3_6.select_one("code").get_text("", strip=False)
            if "close=close" not in source or "inst['Close']" in source:
                failures.append("chapter-03 Snippet 3.6 does not call applyPtSlOnT1 with close=close")
        snippet_3_8 = next((fig for fig in soup.select("figure.code-listing") if fig.get_text(" ", strip=True).startswith("Snippet 3.8:")), None)
        if snippet_3_8 is None:
            failures.append("chapter-03 Snippet 3.8 missing")
        else:
            source = snippet_3_8.select_one("code").get_text("", strip=False)
            if "def dropLabels(events, minPct=.05):" not in source:
                failures.append("chapter-03 Snippet 3.8 parameter name is not minPct")
        figure_3_1 = next((fig for fig in soup.select("figure.book-figure") if fig.get_text(" ", strip=True).startswith("(a) (b) Figure 3.1:")), None)
        if figure_3_1 is None or len(figure_3_1.select("img")) != 2 or not figure_3_1.select_one(".figure-panels"):
            failures.append("chapter-03 Figure 3.1 is not rendered as one two-panel figure")
        if any(p.get_text(" ", strip=True).startswith("characteristic (ROC) curve") for p in soup.select("p")):
            failures.append("chapter-03 Figure 3.2 still splits the ROC sentence")
        if len(soup.select("p.footnote sup")) != 1:
            failures.append("chapter-03 footnote is not semantic")
        refs = [li.get_text(" ", strip=True) for li in soup.select(".references-list li")]
        if not any(ref.startswith("Wei, P. and N. Wang") for ref in refs) or not any(ref.startswith("Zbikowski, K.") for ref in refs):
            failures.append("chapter-03 Wei/Zbikowski references are not separate entries")
        css_path = path.parents[1] / "assets" / "afml-book.css"
        if css_path.exists():
            css = css_path.read_text(encoding="utf-8")
            if ".book-figure figcaption" not in css or ".figure-panels" not in css:
                failures.append("chapter-03 figure caption/panel CSS is missing")

    if chapter_slug == "chapter-04":
        chapter_4_bad = [
            "sequensequential bootstrap",
            "= 1 t,j",
            "{t=1 }",
            r"\tilde{w_i} I \tilde{w_j}",
            "can[ be defined]",
            "the[ sample]weights",
            "Random T1",
        ]
        for pattern in chapter_4_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-04 artifact remains: {pattern}")
        expected_figures = {
            "Figure 4.1:": "media/afml-88_1.jpg",
            "Figure 4.2:": "media/afml-95_1.jpg",
            "Figure 4.3:": "media/chapter-04-figure-4-3.png",
        }
        for prefix, src in expected_figures.items():
            figure = next((fig for fig in soup.select("figure.book-figure") if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one(f'img[src="{src}"]'):
                failures.append(f"chapter-04 {prefix.rstrip(':')} is not bound to {src}")
        if r"\bar u_i=\left(\sum_{t=1}^{T}u_{t,i}\right)\left(\sum_{t=1}^{T}1_{t,i}\right)^{-1}" not in html:
            failures.append("chapter-04 average uniqueness formula is missing")
        if r"\delta_j^{(2)}=\bar u_j^{(2)}\left(\sum_{k=1}^{I}\bar u_k^{(2)}\right)^{-1}" not in html:
            failures.append("chapter-04 sequential bootstrap probability formula is missing")
        if r"\tilde w_i=\left|\sum_{t=t_{i,0}}^{t_{i,1}}\frac{r_{t-1,t}}{c_t}\right|" not in html:
            failures.append("chapter-04 return-attribution weight formula is missing")
        if r"d[x]\ge0,\ \forall x\in\left[0,\sum_{i=1}^{I}\bar u_i\right]" not in html:
            failures.append("chapter-04 time-decay domain formula is missing")
        snippet_4_1 = next((fig for fig in soup.select("figure.code-listing") if fig.get_text(" ", strip=True).startswith("Snippet 4.1:")), None)
        if snippet_4_1 is None or "return count.loc[molecule[0]:t1[molecule].max()]" not in snippet_4_1.select_one("code").get_text("", strip=False):
            failures.append("chapter-04 Snippet 4.1 is incomplete")
        snippet_4_9 = next((fig for fig in soup.select("figure.code-listing") if fig.get_text(" ", strip=True).startswith("Snippet 4.9:")), None)
        if snippet_4_9 is None:
            failures.append("chapter-04 Snippet 4.9 missing")
        else:
            snippet_4_9_source = snippet_4_9.select_one("code").get_text("", strip=False)
            if "if numThreads == 1" not in snippet_4_9_source or "print pd.DataFrame(out).describe()" not in snippet_4_9_source:
                failures.append("chapter-04 Snippet 4.9 is incomplete")
        snippet_4_5_text = next((p.get_text(" ", strip=True) for p in soup.select("p") if p.get_text(" ", strip=True).startswith("Snippet 4.5 gives")), "")
        if "columns in indM" not in snippet_4_5_text or "rows in indM" in snippet_4_5_text:
            failures.append("chapter-04 Snippet 4.5 description has the wrong sample dimension")
        css_path = path.parents[1] / "assets" / "afml-book.css"
        if css_path.exists():
            css = css_path.read_text(encoding="utf-8")
            if not re.search(r"\.book-figure figcaption,\s*figure\.table-figure figcaption\s*\{[^}]*font-size:\s*\.82rem", css, re.S):
                failures.append("chapter-04 figure captions are not visually distinct from body text")

    if chapter_slug == "chapter-05":
        chapter_5_bad = [
            "( (1)- B)",
            "k=0 xy = k=0",
            "with weights 𝜔 { }",
            "X̃ t = lk=0",
            "0 if k > l∗",
            "adfStat (right) corr",
            "Int[d]",
            "logprices",
        ]
        for pattern in chapter_5_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-05 artifact remains: {pattern}")
        if re.search(r"<p>\s*quently, the weights converge", html):
            failures.append("chapter-05 artifact remains: quently, the weights converge")
        if re.search(r"<p>\s*ling for weight loss", html):
            failures.append("chapter-05 artifact remains: ling for weight loss")
        expected_figures = {
            "Figure 5.1:": "media/chapter-05-figure-5-1.png",
            "Figure 5.2:": "media/chapter-05-figure-5-2.png",
            "Figure 5.3:": "media/chapter-05-figure-5-3.png",
            "Figure 5.4:": "media/chapter-05-figure-5-4.png",
            "Figure 5.5:": "media/chapter-05-figure-5-5.png",
        }
        book_figures = soup.select("figure.book-figure")
        if len(book_figures) != 5:
            failures.append(f"chapter-05 expected 5 book figures, found {len(book_figures)}")
        for prefix, src in expected_figures.items():
            figure = next((fig for fig in book_figures if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one(f'img[src="{src}"]'):
                failures.append(f"chapter-05 {prefix.rstrip(':')} is not bound to {src}")
        required_formula_fragments = [
            r"(1-B)^2X_t=X_t-2X_{t-1}+X_{t-2}",
            r"(1+x)^d=\sum_{k=0}^{\infty}\binom{d}{k}x^k",
            r"\widetilde X_t=\sum_{k=0}^{\infty}\omega_k X_{t-k}",
            r"\omega_k=-\omega_{k-1}\frac{d-k+1}{k}",
            r"\lambda_l=\frac{\sum_{j=T-l}^{T}|\omega_j|}{\sum_{i=0}^{T-1}|\omega_i|}",
            r"\widetilde\omega_k=\begin{cases}\omega_k, &amp; k\le l^*\\0, &amp; k&gt;l^*\end{cases}",
            r"d=1\gg0.35",
        ]
        for fragment in required_formula_fragments:
            if fragment not in html:
                failures.append(f"chapter-05 formula missing: {fragment}")
        snippet_5_3 = next((fig for fig in soup.select("figure.code-listing") if fig.get_text(" ", strip=True).startswith("Snippet 5.3:")), None)
        if snippet_5_3 is None:
            failures.append("chapter-05 Snippet 5.3 missing")
        else:
            source = snippet_5_3.select_one("code").get_text("", strip=False)
            if "\n    for name in series.columns:" not in source or "\nfor name in series.columns:" in source:
                failures.append("chapter-05 Snippet 5.3 loop indentation is wrong")
        table_5_1 = next((fig for fig in soup.select("figure.table-figure") if fig.get_text(" ", strip=True).startswith("Table 5.1:")), None)
        if table_5_1 is None:
            failures.append("chapter-05 Table 5.1 missing")
        else:
            header = [th.get_text(" ", strip=True) for th in table_5_1.select("thead th")]
            first_row_header = table_5_1.select_one("tbody tr th[scope='row']")
            if not header or header[0] != "Contract" or first_row_header is None:
                failures.append("chapter-05 Table 5.1 contract column is not semantic")
        css_path = path.parents[1] / "assets" / "afml-book.css"
        if css_path.exists():
            css = css_path.read_text(encoding="utf-8")
            if not re.search(r"\.book-figure figcaption,\s*figure\.table-figure figcaption\s*\{[^}]*font-size:\s*\.82rem", css, re.S):
                failures.append("chapter-05 figure captions are not visually distinct from body text")

    if chapter_slug == "chapter-06":
        chapter_6_bad = [
            r"\varepsilon2i",
            r"\sigma\varepsilon",
            "f̂ [x]",
            "1\\sum 1 \\sum",
            "V \\varphi [c] = 2",
            "P X&gt; =1-P X",
            "N1 N",
            "1k",
            "min_weight_fraction_ leaf",
            "max_ samples",
            "max_ features",
            "balanced_ subsample",
            "sequential boot- strapping",
            "unpre- dictable",
            "discrep- ancy",
            r"\rhō",
            r"\sigmā",
        ]
        for pattern in chapter_6_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-06 artifact remains: {pattern}")
        if any(p.get_text(" ", strip=True).startswith(("are determined by the accuracy", "the number of estimators", "science, the problem addressed")) for p in soup.select("p")):
            failures.append("chapter-06 page-break continuation paragraph remains")
        expected_figures = {
            "Figure 6.1:": "media/afml-122_1.jpg",
            "Figure 6.2:": "media/afml-124_1.jpg",
            "Figure 6.3:": "media/afml-127_1.jpg",
        }
        book_figures = soup.select("figure.book-figure")
        if len(book_figures) != 3:
            failures.append(f"chapter-06 expected 3 book figures, found {len(book_figures)}")
        for prefix, src in expected_figures.items():
            figure = next((fig for fig in book_figures if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one(f'img[src="{src}"]'):
                failures.append(f"chapter-06 {prefix.rstrip(':')} is not bound to {src}")
        figure_6_2 = next((fig for fig in book_figures if fig.get_text(" ", strip=True).startswith("Figure 6.2:")), None)
        if figure_6_2 is None or "number of estimators" not in figure_6_2.get_text(" ", strip=True) or r"\(k=2\)" not in str(figure_6_2):
            failures.append("chapter-06 Figure 6.2 caption is incomplete")
        required_formula_fragments = [
            r"\mathbb{E}[\varepsilon_i^2]=\sigma_\varepsilon^2",
            r"\mathbb{E}\left[(y_i-\hat f[x_i])^2\right]",
            r"\bar\sigma^2\left(\bar\rho+\frac{1-\bar\rho}{N}\right)",
            r"\bar\rho=\frac{1}{\bar\sigma^2N(N-1)}",
            r"P\left[X&gt;\frac{N}{k}\right]",
            r"\sum_{i=0}^{\lfloor N/k\rfloor}\binom{N}{i}p^i(1-p)^{N-i}",
            r"p&gt;\frac{1}{k}\Rightarrow P\left[X&gt;\frac{N}{k}\right]&gt;p",
        ]
        for fragment in required_formula_fragments:
            if fragment not in html:
                failures.append(f"chapter-06 formula missing: {fragment}")
        error_list = soup.select_one("#sec-6-2 + p + ol")
        if error_list is None or len(error_list.select(":scope > li")) != 3:
            failures.append("chapter-06 bias/variance/noise list is not a single 3-item list")
        rf_heading = soup.select_one("#sec-6-4")
        rf_list = None
        if rf_heading is not None:
            for sibling in rf_heading.find_all_next(["ol", "h2"], limit=8):
                if sibling.name == "h2":
                    break
                if sibling.name == "ol":
                    rf_list = sibling
                    break
        if rf_list is None or len(rf_list.select(":scope > li")) != 5:
            failures.append("chapter-06 RF overfitting remedies list is not a single 5-item list")
        elif not rf_list.select_one("ol[type='a']") or not rf_list.select_one("code"):
            failures.append("chapter-06 RF list lacks nested code examples")
        boosting_diff_heading = soup.select_one("#sec-6-6")
        boosting_list = None
        if boosting_diff_heading is not None:
            for sibling in boosting_diff_heading.find_all_next(["ul", "h2"], limit=6):
                if sibling.name == "h2":
                    break
                if sibling.name == "ul":
                    boosting_list = sibling
                    break
        if boosting_list is None or len(boosting_list.select(":scope > li")) != 4:
            failures.append("chapter-06 bagging-vs-boosting bullet list is not a single 4-item list")
        if len(soup.select("p.footnote sup")) != 4:
            failures.append("chapter-06 footnotes are not semantic")

    if chapter_slug == "chapter-07":
        chapter_7_bad = [
            "A SOLUTION: PURGED K-FOLD CV",
            "<figure><figcaption>",
            "kfold CV",
            "kx1",
            "Y_t+1",
            "X_t+1",
            "Yt+1",
            "Xt+1",
            "Xi and Xj",
            "Yi and Yj",
            "tj,0",
            "ti,0",
            "k∗",
            "scikit- learn",
            "Snip- pet",
            "Why K-Fold Cv",
            "Purged K-Fold Cv",
            "Sklearn’S",
        ]
        for pattern in chapter_7_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-07 artifact remains: {pattern}")
        expected_headings = {
            "sec-7-2": "7.2 The Goal of Cross-Validation",
            "sec-7-3": "7.3 Why K-Fold CV Fails in Finance",
            "sec-7-4": "7.4 A Solution: Purged K-Fold CV",
            "sec-7-5": "7.5 Bugs in Sklearn's Cross-Validation",
        }
        for section_id, expected in expected_headings.items():
            heading = soup.select_one(f"#{section_id}")
            if heading is None or heading.get_text(" ", strip=True) != expected:
                failures.append(f"chapter-07 heading wrong: {section_id}")
        expected_figures = {
            "Figure 7.1:": "media/afml-131_1.jpg",
            "Figure 7.2:": "media/afml-134_1.jpg",
            "Figure 7.3:": "media/afml-135_1.jpg",
        }
        book_figures = soup.select("figure.book-figure")
        if len(book_figures) != 3:
            failures.append(f"chapter-07 expected 3 book figures, found {len(book_figures)}")
        for prefix, src in expected_figures.items():
            figure = next((fig for fig in book_figures if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one(f'img[src="{src}"]'):
                failures.append(f"chapter-07 {prefix.rstrip(':')} is not bound to {src}")
        required_fragments = [
            r"\(i=1,\ldots,k\)",
            r"\(k\times1\)",
            r"\(\frac{1}{2}\)",
            r"\(X_t\approx X_{t+1}\)",
            r"\(Y_t\approx Y_{t+1}\)",
            r"\(\mathbb{E}[Y_{t+1}\mid X_{t+1}]\)",
            r"\((X_i,Y_i)\approx(X_j,Y_j)\)",
            r"\(\Phi_i\cap\Phi_j\ne\emptyset\)",
            r"\(t\in[t_{j,0},t_{j,1}]\)",
            r"\(\operatorname{sgn}[r_{t_{j,0},t_{j,1}}]\)",
            r"\(t_{j,0}\le t_{i,0}\le t_{j,1}\)",
            r"\(k^*\)",
            r"\(t_{j,1}\le t_{i,0}\le t_{j,1}+h\)",
            r"\(Y_j=f[[t_{j,0},t_{j,1}+h]]\)",
            r"\(h\approx.01T\)",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-07 formula missing: {fragment}")
        kfold_list = soup.select_one("#sec-7-2 ~ ol")
        if kfold_list is None or len(kfold_list.select(":scope > li")) != 2 or not kfold_list.select_one("ol[type='a']"):
            failures.append("chapter-07 k-fold algorithm list is not nested")
        leakage_list = soup.select_one("#sec-7-3 ~ ol")
        if leakage_list is None or len(leakage_list.select(":scope > li")) != 2 or not leakage_list.select_one("ol[type='i']"):
            failures.append("chapter-07 leakage remedies list is not nested")
        purging_heading = soup.select_one("#sec-7-4-1")
        purging_list = None
        if purging_heading is not None:
            for sibling in purging_heading.find_all_next(["ol", "h3", "h2"], limit=8):
                if sibling.name in {"h2", "h3"}:
                    break
                if sibling.name == "ol":
                    purging_list = sibling
                    break
        if purging_list is None or len(purging_list.select(":scope > li")) != 3:
            failures.append("chapter-07 purging sufficient conditions list is not three formulas")
        bugs_heading = soup.select_one("#sec-7-5")
        bugs_list = None
        if bugs_heading is not None:
            for sibling in bugs_heading.find_all_next(["ol", "h2"], limit=5):
                if sibling.name == "h2":
                    break
                if sibling.name == "ol":
                    bugs_list = sibling
                    break
        if bugs_list is None or len(bugs_list.select(":scope > li")) != 2 or not bugs_list.select_one("a[href*='6231']") or not bugs_list.select_one("a[href*='9144']"):
            failures.append("chapter-07 sklearn bug list is not semantic")

    if chapter_slug == "chapter-08":
        chapter_8_bad = [
            "<figure><figcaption>",
            "<p>imp=pd.concat",
            "<p>return</p>",
            r"\(\sigma_{n}-1\)",
            "Xt,n",
            "Zt,n",
            "P′",
            "Z ′",
            "NxN",
            "𝜆",
            "Λj",
            "X̃",
            "∼ X",
            "scikitlearn.org",
            "pre- dictor",
            "func- tions",
            "pres- ence",
            "unimpor- tant",
            "out-ofsample",
            "correspondance",
            "engenvector",
            "most importance features",
            "(a) Every feature",
            "(b) Make sure",
        ]
        for pattern in chapter_8_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-08 artifact remains: {pattern}")
        expected_headings = {
            "sec-8-2": "8.2 The Importance of Feature Importance",
            "sec-8-3": "8.3 Feature Importance with Substitution Effects",
            "sec-8-4": "8.4 Feature Importance without Substitution Effects",
            "sec-8-5": "8.5 Parallelized vs. Stacked Feature Importance",
            "sec-8-6": "8.6 Experiments with Synthetic Data",
        }
        for section_id, expected in expected_headings.items():
            heading = soup.select_one(f"#{section_id}")
            if heading is None or heading.get_text(" ", strip=True) != expected:
                failures.append(f"chapter-08 heading wrong: {section_id}")
        expected_figures = {
            "Figure 8.1:": "media/afml-147_1.jpg",
            "Figure 8.2:": "media/afml-152_1.jpg",
            "Figure 8.3:": "media/afml-153_1.jpg",
            "Figure 8.4:": "media/afml-153_2.jpg",
        }
        book_figures = soup.select("figure.book-figure")
        if len(book_figures) != 4:
            failures.append(f"chapter-08 expected 4 book figures, found {len(book_figures)}")
        for prefix, src in expected_figures.items():
            figure = next((fig for fig in book_figures if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one(f'img[src="{src}"]'):
                failures.append(f"chapter-08 {prefix.rstrip(':')} is not bound to {src}")
        required_fragments = [
            r"\(Z_{t,n}=\sigma_n^{-1}(X_{t,n}-\mu_n)\)",
            r"\(\{X_{t,n}\}_{t=1,\ldots,T}\)",
            r"\(Z'ZW=W\Lambda\)",
            r"\(N\times N\)",
            r"\(P=ZW\)",
            r"\(P'P=W'Z'ZW=W'W\Lambda W'W=\Lambda\)",
            r"\(\lambda_{i,j,k}\)",
            r"\(\Lambda_{j,k}\)",
            r"\(\{(\widetilde X_i,y_i)\}_{i=1,\ldots,I}\)",
            r"\(\widetilde X_i\sim X\)",
            r"\(\frac{1}{40}\)",
            r"\(10\times\)",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-08 formula missing: {fragment}")
        captions_to_code = {
            fig.select_one("figcaption").get_text(" ", strip=True): (fig.select_one("code").get_text() if fig.select_one("code") else "")
            for fig in soup.select("figure.code-listing")
        }
        snippet_8_2 = next((code for caption, code in captions_to_code.items() if caption.startswith("Snippet 8.2:")), "")
        if "imp=pd.concat" not in snippet_8_2 or "return imp" not in snippet_8_2:
            failures.append("chapter-08 Snippet 8.2 is missing its page-break continuation")
        snippet_8_9 = next((code for caption, code in captions_to_code.items() if caption.startswith("Snippet 8.9:")), "")
        if "out.to_csv" not in snippet_8_9 or "return" not in snippet_8_9:
            failures.append("chapter-08 Snippet 8.9 is missing its final return")
        mdi_heading = soup.select_one("#sec-8-3-1")
        mdi_list = None
        if mdi_heading is not None:
            for sibling in mdi_heading.find_all_next(["ol", "h3", "h2"], limit=5):
                if sibling.name in {"h2", "h3"}:
                    break
                if sibling.name == "ol":
                    mdi_list = sibling
                    break
        if mdi_list is None or len(mdi_list.select(":scope > li")) != 6 or not mdi_list.select_one("ol[type='a']") or not mdi_list.select_one("code"):
            failures.append("chapter-08 MDI considerations list is not nested")
        mda_heading = soup.select_one("#sec-8-3-2")
        mda_list = None
        if mda_heading is not None:
            for sibling in mda_heading.find_all_next(["ol", "p", "h3", "h2"], limit=6):
                if sibling.name in {"h2", "h3"}:
                    break
                if sibling.name == "ol":
                    mda_list = sibling
                    break
        if mda_list is None or len(mda_list.select(":scope > li")) != 5:
            failures.append("chapter-08 MDA considerations list should have 5 items")
        elif "Snippet 8.3 implements" in mda_list.get_text(" ", strip=True):
            failures.append("chapter-08 MDA list swallowed the Snippet 8.3 prose")
        sfi_heading = soup.select_one("#sec-8-4-1")
        sfi_list = None
        if sfi_heading is not None:
            for sibling in sfi_heading.find_all_next(["ol", "h3", "h2"], limit=5):
                if sibling.name in {"h2", "h3"}:
                    break
                if sibling.name == "ol":
                    sfi_list = sibling
                    break
        if sfi_list is None or len(sfi_list.select(":scope > li")) != 4:
            failures.append("chapter-08 SFI considerations list should have 4 items")
        if not soup.select_one('a[href="http://scikit-learn.org/stable/modules/generated/sklearn.datasets.make_classification.html"]'):
            failures.append("chapter-08 sklearn make_classification URL is broken")

    if chapter_slug == "chapter-09":
        chapter_9_bad = [
            r"\[[ a log-uniform",
            "[ ] for a",
            "log ax logc ax",
            "∼U",
            "pn,k",
            "yn,k",
            "crossentropy",
            "markto-market",
            "loglinear",
            "<p>n=0 k=0</p>",
            "<p>fit_params[",
            "kernel.1",
            "loss3",
            "Begstra",
            "b∕a",
            "1E −",
            "http://stackoverflow.com/questions/ 576169",
            "<p>1 http://scikit-learn.org",
            "<p>3 http://scikit-learn.org",
        ]
        for pattern in chapter_9_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-09 artifact remains: {pattern}")
        required_fragments = [
            r"\(\log[x]\sim U[\log[a],\log[b]]\)",
            r"\begin{cases}\dfrac{\log[x]-\log[a]}{\log[b]-\log[a]}",
            r"\dfrac{1}{x\log[b/a]}",
            r"\frac{\log[x/a]}{\log[b/a]}=\frac{\log_c[x/a]}{\log_c[b/a]}",
            r"\sum_{n=0}^{N-1}\sum_{k=0}^{K-1}",
            r"\(p_{n,k}\)",
            r"\(y_{n,k}=1\)",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-09 formula missing: {fragment}")
        captions_to_code = {
            fig.select_one("figcaption").get_text(" ", strip=True): (fig.select_one("code").get_text() if fig.select_one("code") else "")
            for fig in soup.select("figure.code-listing")
        }
        snippet_9_1 = next((code for caption, code in captions_to_code.items() if caption.startswith("Snippet 9.1:")), "")
        if "Snippet 9.1 lists" in snippet_9_1 or "which implements a purged" in snippet_9_1:
            failures.append("chapter-09 Snippet 9.1 swallowed prose")
        if "return gs" not in snippet_9_1 or "GridSearchCV" not in snippet_9_1:
            failures.append("chapter-09 Snippet 9.1 is incomplete")
        snippet_9_2 = next((code for caption, code in captions_to_code.items() if caption.startswith("Snippet 9.2:")), "")
        if "fit_params[self.steps[-1][0]+'__sample_weight']=sample_weight" not in snippet_9_2 or "return super(MyPipeline,self).fit" not in snippet_9_2:
            failures.append("chapter-09 Snippet 9.2 is incomplete")
        if snippet_9_2.rstrip().endswith(":"):
            failures.append("chapter-09 Snippet 9.2 ends with an open suite")
        if len(soup.select("p.footnote")) < 3:
            failures.append("chapter-09 footnotes are not semantic")
        if not soup.select_one('a[href="http://stackoverflow.com/questions/576169/understanding-python-super-with-init-methods"]'):
            failures.append("chapter-09 Stack Overflow URL is broken")
        if len(soup.select("figure.book-figure")) != 2:
            failures.append(f"chapter-09 expected 2 book figures, found {len(soup.select('figure.book-figure'))}")

    if chapter_slug == "chapter-10":
        chapter_10_bad = [
            "p^2 , p3",
            "F[c_t ] - F[0] if c",
            "max 1{c }",
            "H_0: p [x = 1] = 12",
            "p[x=1]- 21",
            "the test statistic z = √",
            "i=1 pi = 1",
            "p̃ = maxi {pi }",
            "⏟⏞",
            "Usu-",
            "scores-andprobabilities",
            "m∗ = round md d",
            r"q\hat{i},t",
            "m^* -2",
            "power function ̃",
            "̃ [𝜔, x]",
            "m_t = c_t,l ̄c1",
            "c̄ l",
            "c̄ s",
            "10.1 Using the formulation",
            "10.7 Modify Snippet 10.4",
            "stepSize=.01",
            "Figure 10.3: f [x] = sgn [x] |x|2",
            "<p>ally these probabilities",
            "<p>if &#x27;side&#x27; in events:signal0*=",
            "<p>’’’ At time loc",
            "<p>2 Uncertainty is absolute",
            "<figure><figcaption>Figure 10.3:",
        ]
        for pattern in chapter_10_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-10 artifact remains: {pattern}")
        required_fragments = [
            r"\([m_{1,1},m_{1,2},m_{1,3}]=[.5,1,0]\)",
            r"\([p_1,p_2,p_3]=[1,.5,1.25]\)",
            r"m_t=\begin{cases}\dfrac{F[c_t]-F[0]}{1-F[0]}",
            r"\frac{c_{t,l}}{\max_i\{c_{i,l}\}}-\frac{c_{t,s}}{\max_i\{c_{i,s}\}}",
            r"H_0:p[x=1]=\frac{1}{2}",
            r"\begin{aligned}z&amp;=\frac{p[x=1]-\frac{1}{2}}{\sqrt{p[x=1](1-p[x=1])}}",
            r"\sum_{i=1}^{\|X\|}p_i=1",
            r"\tilde p=\max_i\{p_i\}",
            r"H_0:\tilde p=\frac{1}{\|X\|}",
            r"m=x\underbrace{(2Z[z]-1)}_{\in[0,1]}",
            r"m^*=\operatorname{round}\left[\frac{m}{d}\right]d",
            r"E_{t_{i,0}}[p_{t_{i,1}}]",
            r"\hat q_{i,t}&amp;=\operatorname{int}",
            r"m[\omega,x]&amp;=\frac{x}{\sqrt{\omega+x^2}}",
            r"\bar p=\frac{1}{|\hat q_{i,t}-q_t|}",
            r"\sum_{j=|q_t+\operatorname{sgn}[\hat q_{i,t}-q_t]|}^{|\hat q_{i,t}|}L\!\left[f_i,\omega,\frac{j}{Q}\right]",
            r"L[f_i,\omega,m]=f_i-m\sqrt{\frac{\omega}{1-m^2}}",
            r"\omega=x^2\left((m^*)^{-2}-1\right)",
            r"\bar p=112.3657",
            r"p_t&lt;\bar p&lt;f_i",
            r"\tilde m[\omega,x]=\operatorname{sgn}[x]|x|^\omega",
            r"\(f[x]=\operatorname{sgn}[x]|x|^2\)",
            r"\(f[x]=x(.1+x^2)^{-.5}\)",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-10 formula missing: {fragment}")
        captions_to_code = {
            fig.select_one("figcaption").get_text(" ", strip=True): (fig.select_one("code").get_text() if fig.select_one("code") else "")
            for fig in soup.select("figure.code-listing")
        }
        snippet_10_1 = next((code for caption, code in captions_to_code.items() if caption.startswith("Snippet 10.1:")), "")
        if "if 'side' in events" not in snippet_10_1 or "return signal1" not in snippet_10_1:
            failures.append("chapter-10 Snippet 10.1 is incomplete")
        snippet_10_2 = next((code for caption, code in captions_to_code.items() if caption.startswith("Snippet 10.2:")), "")
        if "def mpAvgActiveSignals" not in snippet_10_2 or "return out" not in snippet_10_2:
            failures.append("chapter-10 Snippet 10.2 is incomplete")
        snippet_10_4 = next((code for caption, code in captions_to_code.items() if caption.startswith("Snippet 10.4:")), "")
        if "return x**2*(m**-2-1)" not in snippet_10_4 or "def limitPrice" not in snippet_10_4:
            failures.append("chapter-10 Snippet 10.4 is incomplete")
        expected_figures = {
            "Figure 10.1:": "media/afml-170_1.jpg",
            "Figure 10.2:": "media/afml-172_1.jpg",
            "Figure 10.3:": "media/chapter-10-figure-10-3.png",
        }
        book_figures = soup.select("figure.book-figure")
        if len(book_figures) != 3:
            failures.append(f"chapter-10 expected 3 book figures, found {len(book_figures)}")
        for prefix, src in expected_figures.items():
            figure = next((fig for fig in book_figures if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one(f'img[src="{src}"]'):
                failures.append(f"chapter-10 {prefix.rstrip(':')} is not bound to {src}")
        figure_10_3 = next((fig for fig in book_figures if fig.get_text(" ", strip=True).startswith("Figure 10.3:")), None)
        if figure_10_3 is not None:
            image = figure_10_3.select_one("img")
            if image is None or "power function" not in (image.get("alt") or "") or "sigmoid" not in (image.get("alt") or ""):
                failures.append("chapter-10 Figure 10.3 alt text is not semantically useful")
        if len(soup.select("p.footnote")) < 2:
            failures.append("chapter-10 footnotes are not semantic")
        if not soup.select_one('a[href="http://scikit-learn.org/stable/modules/svm.html#scores-and-probabilities"]'):
            failures.append("chapter-10 sklearn SVM probability URL is broken")

    if chapter_slug == "chapter-11":
        chapter_11_bad = [
            r"\begin{aligned}( ) ( ) S∕ -1",
            "<p>2 2 S∕ S</p>",
            r"\[i=0 ∕2 - i\]",
            "TS S2 xN = T2 xN",
            "Form ̄ ̄ ( T )the testing set J",
            "[ 𝜔̄ ]",
            "𝜆c = log 1−𝜔c̄",
            "when ̄ High",
            "with ∫−∞",
            "PBO = ∫−∞ f",
            r"\[1 | OOS Perf. Degradation\]",
            r"\[1 | Hist. of Rank Logits\]",
            "<p>Prob Overfit=0.74</p>",
            "<p>SR OOS</p>",
            "<p>SR IS</p>",
            "<p>Frequency</p>",
            "<p>Logits</p>",
            "ignor- ing",
            "crossvalidation",
            "backtesting1",
            "method.2",
            "opti- mization",
            "per- formance",
            "ssrn .com",
            "ssrn. com",
            "jpm .2017",
            "/ abstract",
            "Available at ttps://",
            "media/afml-184_1.jpg",
        ]
        for pattern in chapter_11_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-11 artifact remains: {pattern}")
        required_fragments = [
            r"\binom{S}{S/2}",
            r"\prod_{i=0}^{S/2-1}\frac{S-i}{S/2-i}",
            r"\(T\times N\)",
            r"\((T/S)\times N\)",
            r"\(C_S\)",
            r"\bar J",
            r"\bar R_{n^*}",
            r"\bar\omega_c\in(0,1)",
            r"\lambda_c=\log\left[\frac{\bar\omega_c}{1-\bar\omega_c}\right]",
            r"\int_{-\infty}^{\infty} f(\lambda)\,d\lambda=1",
            r"\mathrm{PBO}=\int_{-\infty}^{0} f(\lambda)\,d\lambda",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-11 formula missing: {fragment}")
        if soup.select("figure.code-listing"):
            failures.append("chapter-11 quote snippet should not render as code listing")
        quote = soup.select_one("figure.quote-snippet")
        quote_text = quote.get_text(" ", strip=True) if quote else ""
        for fragment in ["Backtesting while researching", "Do not research under the influence", "Marcos López de Prado"]:
            if fragment not in quote_text:
                failures.append(f"chapter-11 quote snippet missing: {fragment}")
        expected_figures = {
            "Figure 11.1:": "media/chapter-11-figure-11-1.png",
            "Figure 11.2:": "media/chapter-11-figure-11-2.png",
        }
        book_figures = soup.select("figure.book-figure")
        if len(book_figures) != 2:
            failures.append(f"chapter-11 expected 2 book figures, found {len(book_figures)}")
        for prefix, src in expected_figures.items():
            figure = next((fig for fig in book_figures if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one(f'img[src="{src}"]'):
                failures.append(f"chapter-11 {prefix.rstrip(':')} is not bound to {src}")
        if len(soup.select("p.footnote")) < 1:
            failures.append("chapter-11 footnote is not semantic")
        if "Even If Your Backtest Is Flawless, It Is Probably Wrong" not in html:
            failures.append("chapter-11 split heading was not merged")

    if chapter_slug == "chapter-12":
        chapter_12_bad = [
            "period)that",
            "34 T0 + 14",
            "<p>=</p>",
            "There are 64 = 15",
            "<p>I I</p>",
            "Z -1",
            r"\gamma_{Z}",
            "2log [I]",
            r"\varphi-2",
            "ρ̄i",
            "𝜌̄i",
            "lim𝜑→∞",
            "[ 𝜑 ≤ 𝜑 T, T2",
            "outof-sample",
            "histori- cal",
            "compara- ble",
            "train- ing",
            "respec- tive",
            "<figure><figcaption>Figure 12.",
            "ADDRESSES BACKTEST OVERFITTING",
        ]
        for pattern in chapter_12_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-12 artifact remains: {pattern}")
        required_fragments = [
            r"\left(\frac{T-t_0}{2}\right)^{-1}",
            r"\frac{3}{4}\frac{t_0}{T}+\frac{1}{4}",
            r"\binom{N}{N-k}=\frac{\prod_{i=0}^{k-1}(N-i)}{k!}",
            r"\varphi[N,k]=\frac{k}{N}\binom{N}{N-k}",
            r"\binom{6}{4}=15",
            r"\binom{N}{N-2}",
            r"\mathbb{E}[\max\{x_i\}_{i=1,\ldots,I}]",
            r"\le\sqrt{2\log[I]}",
            r"\frac{y_i}{\sigma[y_i]}\sim Z",
            r"\sigma^2[\mu_i]=\varphi^{-2}",
            r"\bar\rho_i",
            r"\varphi^{-1}\sigma_i^2\le\sigma^2[\mu_i]&lt;\sigma_i^2",
            r"\lim_{\varphi\to\infty}\sigma^2[\mu_i]=0",
            r"\varphi\le\varphi[T,T/2]",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-12 formula missing: {fragment}")
        if len(soup.select("figure.cpcv-figure")) != 2:
            failures.append(f"chapter-12 expected 2 CPCV table figures, found {len(soup.select('figure.cpcv-figure'))}")
        expected_tables = {
            "Figure 12.1:": {
                "G1": {"S1": "x", "S2": "x", "S3": "x", "S4": "x", "S5": "x"},
                "G2": {"S1": "x", "S6": "x", "S7": "x", "S8": "x", "S9": "x"},
                "G3": {"S2": "x", "S6": "x", "S10": "x", "S11": "x", "S12": "x"},
                "G4": {"S3": "x", "S7": "x", "S10": "x", "S13": "x", "S14": "x"},
                "G5": {"S4": "x", "S8": "x", "S11": "x", "S13": "x", "S15": "x"},
                "G6": {"S5": "x", "S9": "x", "S12": "x", "S14": "x", "S15": "x"},
            },
            "Figure 12.2:": {
                "G1": {"S1": "1", "S2": "2", "S3": "3", "S4": "4", "S5": "5"},
                "G2": {"S1": "1", "S6": "2", "S7": "3", "S8": "4", "S9": "5"},
                "G3": {"S2": "1", "S6": "2", "S10": "3", "S11": "4", "S12": "5"},
                "G4": {"S3": "1", "S7": "2", "S10": "3", "S13": "4", "S14": "5"},
                "G5": {"S4": "1", "S8": "2", "S11": "3", "S13": "4", "S15": "5"},
                "G6": {"S5": "1", "S9": "2", "S12": "3", "S14": "4", "S15": "5"},
            },
        }
        for prefix, expected in expected_tables.items():
            figure = next((fig for fig in soup.select("figure.cpcv-figure") if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one("table"):
                failures.append(f"chapter-12 {prefix.rstrip(':')} missing semantic table")
                continue
            headers = [th.get_text(" ", strip=True) for th in figure.select("thead th")]
            if headers != ["Group"] + [f"S{i}" for i in range(1, 16)] + ["Paths"]:
                failures.append(f"chapter-12 {prefix.rstrip(':')} headers are wrong")
                continue
            for row in figure.select("tbody tr"):
                row_header = row.select_one("th")
                group = row_header.get_text(" ", strip=True) if row_header else ""
                cells = [td.get_text(" ", strip=True) for td in row.select("td")]
                if group not in expected or len(cells) != 16:
                    failures.append(f"chapter-12 {prefix.rstrip(':')} malformed row {group}")
                    continue
                nonempty = {headers[index + 1]: value for index, value in enumerate(cells[:-1]) if value}
                if nonempty != expected[group] or cells[-1] != "5":
                    failures.append(f"chapter-12 {prefix.rstrip(':')} row {group} has wrong assignments")
            if len(figure.select("tbody tr")) != 6:
                failures.append(f"chapter-12 {prefix.rstrip(':')} should have 6 group rows")
        if "How Combinatorial Purged Cross-Validation Addresses Backtest Overfitting" not in html:
            failures.append("chapter-12 split heading was not merged")
        stress_list = next((li for li in soup.select("ol li") if li.get_text(" ", strip=True).startswith("The performance we will obtain for 2008")), None)
        if stress_list is not None:
            failures.append("chapter-12 CV stress paragraph is still rendered as a list item")

    if chapter_slug == "chapter-13":
        chapter_13_bad = [
            r"\operatorname{\operatorname{SR}}",
            r"\varphi_{P}i,t-1",
            "m2i",
            "π) targets a",
            "MeΩ E |",
            "P_{i,t}-1",
            "𝜑 = 2 𝜏",
            "𝜑 = 2 ∕𝜏",
            "2 ∕τ",
            r"\(\sigma}\)",
            "− 12",
            "<p>mi i,t</p>",
            "Forecast=",
            "<p>Stop-Loss</p>",
            "<p>Profit-Taking</p>",
            "⎢",
            "⎥",
            "\x02",
            '<figure><figcaption>Figure 13.',
        ]
        for pattern in chapter_13_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-13 artifact remains: {pattern}")
        required_fragments = [
            r"R^*&amp;=\arg\max_{R\in\Omega}",
            r"\operatorname{SR}_R&amp;=\frac{\mathbb{E}[\pi_{i,T_i}\mid R]}{\sigma[\pi_{i,T_i}\mid R]}",
            r"\frac{1}{m_i}\pi_{i,t}",
            r"\varphi P_{i,t-1}",
            r"\sum_{j=0}^{t-1}\varphi^j",
            r"m_i^2\sigma^2\sum_{j=0}^{t-1}\varphi^{2j}",
            r"P_{i,t-1}-\mathbb{E}_0[P_{i,T_i}]",
            r"\hat{\varphi}&amp;=\frac{\operatorname{cov}[Y,X]}{\operatorname{cov}[X,X]}",
            r"\hat{\sigma}&amp;=\sqrt{\operatorname{cov}[\hat{\xi}_t,\hat{\xi}_t]}",
            r"\tau=-\frac{\log[2]}{\log[\varphi]}",
            r"\varphi=2^{-1/\tau}",
            r"\underline{\pi}",
            r"\bar{\pi}",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-13 formula missing: {fragment}")
        heatmaps = soup.select("figure.heatmap-figure")
        if len(heatmaps) != 25:
            failures.append(f"chapter-13 expected 25 heatmap figures, found {len(heatmaps)}")
        for number in range(1, 26):
            figure = next((fig for fig in heatmaps if f"Figure 13.{number}:" in fig.get_text(" ", strip=True)), None)
            expected_src = f"media/chapter-13-figure-13-{number}.png"
            if figure is None or not figure.select_one(f'img[src="{expected_src}"]'):
                failures.append(f"chapter-13 Figure 13.{number} is not bound to {expected_src}")
        table = soup.select_one("table.chapter-13-inputs")
        expected_params = [
            (0, 5),
            (0, 10),
            (0, 25),
            (0, 50),
            (0, 100),
            (5, 5),
            (5, 10),
            (5, 25),
            (5, 50),
            (5, 100),
            (10, 5),
            (10, 10),
            (10, 25),
            (10, 50),
            (10, 100),
            (-5, 5),
            (-5, 10),
            (-5, 25),
            (-5, 50),
            (-5, 100),
            (-10, 5),
            (-10, 10),
            (-10, 25),
            (-10, 50),
            (-10, 100),
        ]
        if table is None:
            failures.append("chapter-13 Table 13.1 semantic table is missing")
        else:
            rows = [[cell.get_text(" ", strip=True) for cell in row.select("th,td")] for row in table.select("tbody tr")]
            if len(rows) != 25:
                failures.append(f"chapter-13 Table 13.1 expected 25 rows, found {len(rows)}")
            for index, (forecast, half_life) in enumerate(expected_params, start=1):
                expected = [f"13.{index}", str(forecast), str(half_life), "1", "100"]
                actual = rows[index - 1] if index - 1 < len(rows) else []
                if actual != expected:
                    failures.append(f"chapter-13 Table 13.1 row {index} wrong: {actual}")
        article = soup.select_one("article")
        if article is not None:
            ordered = article.find_all(["h3", "figure"])
            fig_13_15 = next((node for node in ordered if node.name == "figure" and "Figure 13.15:" in node.get_text(" ", strip=True)), None)
            fig_13_16 = next((node for node in ordered if node.name == "figure" and "Figure 13.16:" in node.get_text(" ", strip=True)), None)
            negative_heading = soup.select_one("#sec-13-6-3")
            try:
                if not (ordered.index(fig_13_15) < ordered.index(negative_heading) < ordered.index(fig_13_16)):
                    failures.append("chapter-13 heatmap figures are ordered across the positive/negative sections incorrectly")
            except ValueError:
                failures.append("chapter-13 could not verify heatmap section ordering")
        snippet_13_2 = next(
            (
                fig.select_one("code").get_text("", strip=False)
                for fig in soup.select("figure.code-listing")
                if fig.get_text(" ", strip=True).startswith("Snippet 13.2:")
            ),
            "",
        )
        if "\nreturn output1" in snippet_13_2 or "    return output1" not in snippet_13_2:
            failures.append("chapter-13 Snippet 13.2 return indentation is wrong")
        if "        mean, std" not in snippet_13_2 or "        output1.append" not in snippet_13_2:
            failures.append("chapter-13 Snippet 13.2 loop body indentation is wrong")

    if chapter_slug == "chapter-14":
        chapter_14_bad = [
            "ri,t = Ki,t",
            "j=1 j=1",
            "𝜑i,T",
            "𝜃i,j,t",
            "( )-1",
            "t wt t",
            "a_n equivalent",
            "w∑",
            "PSR ⎥",
            "SR ⎣ 4 ⎦",
            r"\hat{for} \hat{\gamma}4",
            r"\operatorname{SR} = V \operatorname{SR}",
            r"\mathbb{V}[{\operatorname{SR}\hat{n} }] and N",
            r"\operatorname{SR}^* as a function of \mathbb{V}[{\operatorname{SR}",
            "TP + TN accuracy =",
            "TP precision =",
            "TP recall =",
            "precision ⋅ recall F1 = 2 precision + recall",
            "<figure><figcaption>Figure 14.1",
            "http://www .alacra",
            "http:// citeseerx",
            "abstract= 2308659",
            "DOI: 10.1080/00031305.2016. 1154108",
        ]
        for pattern in chapter_14_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-14 artifact remains: {pattern}")
        required_fragments = [
            r"r_{i,t}&amp;=\frac{\pi_{i,t}}{K_{i,t}}",
            r"\sum_{j=1}^{J}",
            r"\bar{\tilde P}_{j,t}",
            r"\varphi_{i,T}=\prod_{t=1}^{T}(1+r_{i,t})",
            r"R_i=(\varphi_{i,T})^{1/y_i}-1",
            r"w^+&amp;=\left\{r_t^+\left(\sum_t r_t^+\right)^{-1}\right\}_{t=1,\ldots,T}",
            r"h^+&amp;\equiv\frac{\sum_t(w_t^+)^2-\lVert w^+\rVert^{-1}}{1-\lVert w^+\rVert^{-1}}",
            r"SR=\frac{\mu}{\sigma}",
            r"\widehat{PSR}[SR^*]",
            r"\frac{(\widehat{SR}-SR^*)\sqrt{T-1}}",
            r"\frac{\hat{\gamma}_4-1}{4}\widehat{SR}^{2}",
            r"SR^*=\sqrt{\mathbb{V}[\{\widehat{SR}_n\}]}",
            r"Z^{-1}\left[1-\frac{1}{N}e^{-1}\right]",
            r"\mathrm{accuracy}=\frac{TP+TN}{TP+TN+FP+FN}",
            r"\mathrm{precision}=\frac{TP}{TP+FP}",
            r"\mathrm{recall}=\frac{TP}{TP+FN}",
            r"F_1=2\frac{\mathrm{precision}\cdot\mathrm{recall}}{\mathrm{precision}+\mathrm{recall}}",
            r"F_1=2\frac{\mathrm{recall}}{1+\mathrm{recall}}\ge\mathrm{recall}",
            r"F_1=2\frac{\mathrm{precision}}{1+\mathrm{precision}}\ge\mathrm{precision}",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-14 formula missing: {fragment}")
        figures = {
            "Figure 14.1:": "media/afml-229_1.jpg",
            "Figure 14.2:": "media/afml-231_1.jpg",
            "Figure 14.3:": "media/afml-232_1.jpg",
        }
        for prefix, src in figures.items():
            figure = next((fig for fig in soup.select("figure.book-figure") if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one(f'img[src="{src}"]'):
                failures.append(f"chapter-14 {prefix.rstrip(':')} is not bound to {src}")
        snippet_14_3 = next(
            (
                fig.select_one("code").get_text("", strip=False)
                for fig in soup.select("figure.code-listing")
                if fig.get_text(" ", strip=True).startswith("Snippet 14.3:")
            ),
            "",
        )
        for fragment in ["tHHI=getHHI", "def getHHI", "return hhi"]:
            if fragment not in snippet_14_3:
                failures.append(f"chapter-14 Snippet 14.3 missing code: {fragment}")
        if any(fig.get_text(" ", strip=True).startswith("Snippet 14.5:") for fig in soup.select("figure.code-listing")):
            failures.append("chapter-14 Snippet 14.5 should render as a quote snippet, not code")
        quote = soup.select_one("figure.quote-snippet")
        quote_text = quote.get_text(" ", strip=True) if quote else ""
        for fragment in ["Every backtest result", "false discovery probability", "Marcos López de Prado"]:
            if fragment not in quote_text:
                failures.append(f"chapter-14 quote snippet missing: {fragment}")
        table = next((fig for fig in soup.select("figure.table-figure") if fig.get_text(" ", strip=True).startswith("Table 14.1:")), None)
        if table is None:
            failures.append("chapter-14 Table 14.1 is missing")
        else:
            rows = [[cell.get_text(" ", strip=True) for cell in row.select("td")] for row in table.select("tbody tr")]
            expected_rows = [
                ["Observed all 1s", "TN=FP=0", "=recall", "1", "[0,1]", "[0,1]"],
                ["Observed all 0s", "TP=FN=0", "[0,1]", "0", "NaN", "NaN"],
                ["Predicted all 1s", "TN=FN=0", "=precision", "[0,1]", "1", "[0,1]"],
                ["Predicted all 0s", "TP=FP=0", "[0,1]", "NaN", "0", "NaN"],
            ]
            if rows != expected_rows:
                failures.append(f"chapter-14 Table 14.1 rows are wrong: {rows}")
        links = {a.get_text(" ", strip=True) for a in soup.select(".references-list a")}
        for url in [
            "http://www.alacra.com/alacra/help/barra_handbook_US.pdf",
            "https://www.msci.com/eqb/methodology/meth_docs/MSCI_Barra_Factor%20Indices_Methodology_Nov13.pdf",
            "http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.318.7169",
            "http://ssrn.com/abstract=2308659",
        ]:
            if url not in links:
                failures.append(f"chapter-14 reference URL missing: {url}")

    if chapter_slug == "chapter-15":
        chapter_15_bad = [
            "p &gt; 1/2",
            "0 ≤ p ≤ 1",
            "FAQs 15",
            "EXERCISES",
            "15.1 A portfolio manager",
            "Figure 15.3: Implied frequency as a function of p and, with",
            "<figure><figcaption>Figure 15.",
            "stoploss",
            "p= 2a",
            "m_t = c_t,l",
            "t−value of p",
        ]
        for pattern in chapter_15_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-15 artifact remains: {pattern}")
        required_fragments = [
            r"\mathbb{V}[X_i]=\pi^2-\pi^2(2p-1)^2=\pi^2[1-(2p-1)^2]=4\pi^2p(1-p)",
            r"\theta[p,n]=\frac{n\mathbb{E}[X_i]}{\sqrt{n\mathbb{V}[X_i]}}=",
            r"\underbrace{\frac{2p-1}{2\sqrt{p(1-p)}}}_{\substack{\text{t-value of }p",
            r"\text{under }H_0:p=\frac12}}\sqrt{n}",
            r"p&gt;\frac{1}{2}",
            r"p=\frac{1}{2}\left(1+\sqrt{1-\frac{n}{\theta^2+n}}\right)",
            r"\theta[p,n,\pi_-,\pi_+]=\frac{n\mathbb{E}[X_i]}{\sqrt{n\mathbb{V}[X_i]}}=",
            r"\frac{(\pi_+-\pi_-)p+\pi_-}{(\pi_+-\pi_-)\sqrt{p(1-p)}}\sqrt{n}",
            r"\theta[p,n,-\pi_+,\pi_+]=\frac{2\pi_+p-\pi_+}{2\pi_+\sqrt{p(1-p)}}\sqrt{n}",
            r"p=\frac{-b+\sqrt{b^2-4ac}}{2a}",
            r"a&amp;=(n+\theta^2)(\pi_+-\pi_-)^2",
            r"b&amp;=\left[2n\pi_- - \theta^2(\pi_+-\pi_-)\right](\pi_+-\pi_-)",
            r"c&amp;=n\pi_-^2",
            r"p_{\theta^*}=\max\{p\mid\theta\le\theta^*\}",
            r"p_{\theta^*=0}=\frac{2}{3}",
            r"p&lt;p_{\theta^*=0}\Rightarrow\theta\le0",
            r"\lfloor nk\rfloor",
            r"\{\pi_j^{(i)}\}_{j=1,\ldots,\lfloor nk\rfloor}",
            r"p_i=\frac{1}{\lfloor nk\rfloor}",
            "number of years used by investors to assess a strategy (e.g., 2 years)",
            r"f[p]\sim N[\bar p,\bar p(1-\bar p)]",
            r"\mathbb{P}[p&lt;p_{\theta^*}]=\int_{-\infty}^{p_{\theta^*}} f[p]\,dp",
            r"P[p&lt;p_{\theta^*}]&gt;.05",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-15 formula missing: {fragment}")
        figures = {
            "Figure 15.1:": "media/chapter-15-figure-15-1.png",
            "Figure 15.2:": "media/afml-242_1.jpg",
            "Figure 15.3:": "media/afml-243_1.jpg",
        }
        for prefix, src in figures.items():
            figure = next((fig for fig in soup.select("figure.book-figure") if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one(f'img[src="{src}"]'):
                failures.append(f"chapter-15 {prefix.rstrip(':')} is not bound to {src}")
            if figure is not None:
                image = figure.select_one("img")
                alt = image.get("alt") if image else ""
                if r"\(" in alt or r"\)" in alt:
                    failures.append(f"chapter-15 {prefix.rstrip(':')} alt text contains TeX delimiters")
        for prefix in ["Figure 15.2:", "Figure 15.3:"]:
            figure = next((fig for fig in soup.select("figure.book-figure") if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or len(figure.select("figcaption .math.inline")) < 3:
                failures.append(f"chapter-15 {prefix.rstrip(':')} caption formulas are not semantic MathJax spans")
            if figure is not None:
                caption = figure.select_one("figcaption")
                raw_text_nodes = []
                if caption:
                    for text_node in caption.find_all(string=True):
                        if text_node.find_parent(class_="math"):
                            continue
                        raw_text_nodes.append(str(text_node))
                if any(r"\(" in node or r"\)" in node for node in raw_text_nodes):
                    failures.append(f"chapter-15 {prefix.rstrip(':')} caption contains raw TeX delimiters")
        captions_to_code = {
            fig.select_one("figcaption").get_text(" ", strip=True): (fig.select_one("code").get_text() if fig.select_one("code") else "")
            for fig in soup.select("figure.code-listing")
        }
        expected_code = {
            "Snippet 15.1:": ["np.random.binomial", "print np.mean(out),np.std(out),np.mean(out)/np.std(out)"],
            "Snippet 15.2:": ["from sympy import *", "factor(v)"],
            "Snippet 15.3:": ["def binHR", "p=(-b+(b**2-4*a*c)**.5)/(2.*a)", "return p"],
            "Snippet 15.4:": ["def binFreq", "if not np.isclose(binSR(sl,pt,freq,p),tSR):", "        return", "return freq"],
            "Snippet 15.5:": ["def mixGaussians", "def probFailure", "risk=ss.norm.cdf", "print 'Prob strategy will fail',probF"],
        }
        for prefix, fragments in expected_code.items():
            code = next((code for caption, code in captions_to_code.items() if caption.startswith(prefix)), "")
            if not code:
                failures.append(f"chapter-15 {prefix.rstrip(':')} is missing")
                continue
            for fragment in fragments:
                if fragment not in code:
                    failures.append(f"chapter-15 {prefix.rstrip(':')} missing code: {fragment}")
        if not soup.select_one('a[href="http://live.sympy.org/"]'):
            failures.append("chapter-15 SymPy Live URL is not linked")
        links = {a.get_text(" ", strip=True) for a in soup.select(".references-list a")}
        for url in [
            "https://ssrn.com/abstract=2460551",
            "https://ssrn.com/abstract=1821643",
            "https://ssrn.com/abstract=1931734",
            "http://ssrn.com/abstract=641702",
        ]:
            if url not in links:
                failures.append(f"chapter-15 reference URL missing: {url}")

    if chapter_slug == "chapter-16":
        chapter_16_bad = [
            "Vo1. 42",
            "EXERCISES",
            "FAQs 16",
            "<figure><figcaption>Figure 16.",
            "16.A.4 REPRODUCING",
            "2. If |L_i",
            "<p>well as algorithms in the scipy library",
            "Derivation of IVP. We apply",
            "Lopez de Prado",
            "observations X",
            "10000x10",
            "matrix rho as a distance matrix D",
            "{{ s the",
            "d̃",
            "𝜌",
            "𝜔",
        ]
        for pattern in chapter_16_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-16 artifact remains: {pattern}")
        required_fragments = [
            r"\frac{1}{2}N(N+1)",
            r"T\times N",
            r"\rho=\{\rho_{i,j}\}_{i,j=1,\ldots,N}",
            r"d_{i,j}=d[X_i,X_j]=\sqrt{\frac{1}{2}(1-\rho_{i,j})}\in[0,1]",
            r"\tilde d_{i,j}=\tilde d[D_i,D_j]=\sqrt{\sum_{n=1}^{N}(d_{n,i}-d_{n,j})^2}",
            r"(i^*,j^*)=\arg\min_{(i,j),\,i\ne j}\{\tilde d_{i,j}\}",
            r"\dot d_{i,u[1]}=\min[\{\tilde d_{i,j}\}_{j\in u[1]}]",
            r"\tilde V_i^{(j)}\equiv \tilde w_i^{(j)\prime}V_i^{(j)}\tilde w_i^{(j)}",
            r"\tilde w_i^{(j)}=\frac{\operatorname{diag}[V_i^{(j)}]^{-1}}{\operatorname{tr}[\operatorname{diag}[V_i^{(j)}]^{-1}]}",
            r"\alpha_i=1-\frac{\tilde V_i^{(1)}}{\tilde V_i^{(1)}+\tilde V_i^{(2)}}",
            r"T(n)=\mathcal{O}(\log_2[n])",
            r"\sigma_{\mathrm{CLA}}^2=0.1157",
            r"\sigma_{\mathrm{IVP}}^2=0.0928",
            r"\sigma_{\mathrm{HRP}}^2=0.0671",
            r"d_E[x,y]=\sqrt{2T(1-\rho[x,y])}=2\sqrt{T}\,d[x,y]",
            r"\omega=\frac{V^{-1}a}{a^\prime V^{-1}a}",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-16 formula missing: {fragment}")
        if len(soup.select(".example-caption")) != 6:
            failures.append("chapter-16 example captions are not all reconstructed")
        example_16_1 = next((p for p in soup.select(".example-caption") if p.get_text(" ", strip=True).startswith("Example 16.1")), None)
        if example_16_1 is None or len(example_16_1.select(".math.inline")) < 2:
            failures.append("chapter-16 Example 16.1 caption does not use MathJax for rho and D")
        if not soup.select_one("p.footnote sup") or not soup.select_one('a[href="http://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.distance.pdist.html"]'):
            failures.append("chapter-16 scipy footnote is not semantic")
        figures = {
            "Figure 16.1:": ["media/chapter-16-figure-16-1.png"],
            "Figure 16.2:": ["media/afml-252_1.jpg"],
            "Figure 16.3:": ["media/chapter-16-figure-16-3.png"],
            "Figure 16.4:": ["media/afml-258_1.jpg"],
            "Figure 16.5:": ["media/chapter-16-figure-16-5.png"],
            "Figure 16.6:": ["media/afml-260_1.jpg"],
            "Figure 16.7:": ["media/chapter-16-figure-16-7-ab.png", "media/chapter-16-figure-16-7-c.png"],
            "Figure 16.8:": ["media/afml-264_1.jpg", "media/afml-264_2.jpg"],
        }
        for prefix, expected_srcs in figures.items():
            figure = next((fig for fig in soup.select("figure.book-figure") if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None:
                failures.append(f"chapter-16 {prefix.rstrip(':')} missing")
                continue
            srcs = [img.get("src") for img in figure.select("img")]
            if srcs != expected_srcs:
                failures.append(f"chapter-16 {prefix.rstrip(':')} media mismatch: {srcs}")
        figure_16_7 = next((fig for fig in soup.select("figure.book-figure") if fig.get_text(" ", strip=True).startswith("Figure 16.7:")), None)
        if figure_16_7 is None or "(a) Time series of allocations for IVP; (b) HRP; (c) CLA" not in figure_16_7.get_text(" ", strip=True):
            failures.append("chapter-16 Figure 16.7 caption does not preserve panel semantics")
        panel_notes = [p.get_text(" ", strip=True) for p in soup.select("p") if p.get_text(" ", strip=True).startswith(("(a) IVP.", "(b) HRP.", "(c) CLA."))]
        if len(panel_notes) != 3:
            failures.append("chapter-16 Figure 16.7 panel notes are not split into three paragraphs")
        table_16_1 = next((fig for fig in soup.select("figure.table-figure") if fig.get_text(" ", strip=True).startswith("Table 16.1:")), None)
        if table_16_1 is None:
            failures.append("chapter-16 Table 16.1 missing")
        else:
            rows = [[cell.get_text(" ", strip=True) for cell in tr.select("th,td")] for tr in table_16_1.select("tr")]
            expected_rows = [
                ["Weight #", "CLA", "HRP", "IVP"],
                ["1", "14.44%", "7.00%", "10.36%"],
                ["5", "18.68%", "9.72%", "10.31%"],
                ["10", "0.00%", "12.79%", "9.61%"],
            ]
            for expected in expected_rows:
                if expected not in rows:
                    failures.append(f"chapter-16 Table 16.1 row missing: {expected}")
        captions_to_code = {
            fig.select_one("figcaption").get_text(" ", strip=True): (fig.select_one("code").get_text() if fig.select_one("code") else "")
            for fig in soup.select("figure.code-listing")
        }
        expected_code = {
            "Snippet 16.1:": ["sch.linkage(dist,'single')"],
            "Snippet 16.2:": ["def getQuasiDiag", "sortIx=pd.Series([link[-1,0],link[-1,1]])", "return sortIx.tolist()"],
            "Snippet 16.3:": ["def getRecBipart", "alpha=1-cVar0/(cVar0+cVar1)", "w[cItems0]*=alpha"],
            "Snippet 16.4:": ["def getIVP", "def correlDist", "def plotCorrMatrix", "if __name__=='__main__':main()"],
            "Snippet 16.5:": ["def generateData", "def hrpMC", "df1/df1['getHRP']-1", "if __name__=='__main__':hrpMC()"],
        }
        for prefix, fragments in expected_code.items():
            code = next((code for caption, code in captions_to_code.items() if caption.startswith(prefix)), "")
            if not code:
                failures.append(f"chapter-16 {prefix.rstrip(':')} is missing")
                continue
            for fragment in fragments:
                if fragment not in code:
                    failures.append(f"chapter-16 {prefix.rstrip(':')} missing code: {fragment}")
        expected_headings = {
            "16.A.1 Correlation-Based Metric",
            "16.A.2 Inverse Variance Allocation",
            "16.A.3 Reproducing the Numerical Example",
            "16.A.4 Reproducing the Monte Carlo Experiment",
        }
        headings_text = {h.get_text(" ", strip=True) for h in soup.select("h2,h3,h4")}
        for heading in expected_headings:
            if heading not in headings_text:
                failures.append(f"chapter-16 appendix heading missing: {heading}")
        links = {a.get_text(" ", strip=True) for a in soup.select(".references-list a")}
        for url in [
            "http://ssrn.com/abstract=2066170",
            "http://ssrn.com/abstract=2197616",
            "http://ssrn.com/abstract=2308659",
            "http://ssrn.com/abstract=2379314",
            "http://ssrn.com/abstract=2379319",
        ]:
            if url not in links:
                failures.append(f"chapter-16 reference URL missing: {url}")

    if chapter_slug == "chapter-17":
        chapter_17_bad = [
            "Sadf’s",
            "Sadf's",
            "getXY",
            "FAQs 17",
            "EXERCISES",
            "<figure><figcaption>Figure 17.",
            "At time T we can test",
            "𝜏 ∗ T",
            r"H_1:\delta&gt;1",
            r"H_1:\delta>1",
            r"\sum_{t=\tau}^{T}g(N,T,\tau)",
            r"n\in[1,t]",
            r"t_0\in[0,t-\tau]",
            "beyond -1.5",
            "no time trend, only a constant",
            r"\alpha e^{\beta t}+\varepsilon_t",
            r"\alpha t^\beta+\varepsilon_t",
            "Vol. 35",
        ]
        for pattern in chapter_17_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-17 artifact remains: {pattern}")
        required_fragments = [
            r"y_t=\beta_t^\prime x_t+\varepsilon_t",
            r"\hat{\omega}_t=\frac{y_t-\hat{\beta}_{t-1}^{\prime}x_t}{\sqrt{f_t}}",
            r"f_t=\hat{\sigma}_{\varepsilon}^{2}\left[1+x_t^\prime(X_t^\prime X_t)^{-1}x_t\right]",
            r"S_{n,t}=(y_t-y_n)\left(\hat{\sigma}_t\sqrt{t-n}\right)^{-1}",
            r"c_{\alpha}[n,t]=\sqrt{b_{\alpha}+\log[t-n]}",
            r"n\in[1,t-1]",
            r"S_t=\sup_{n\in[1,t-1]}\{S_{n,t}\}",
            r"H_1:\ y_t=\begin{cases}y_{t-1}+\varepsilon_t,&amp;t=1,\ldots,\tau^*T",
            r"\Delta y_t=\delta y_{t-1}D_t[\tau^*]+\varepsilon_t",
            r"H_1:\delta&gt;0",
            r"SDFC=\sup_{\tau^*\in[\tau_0,1-\tau_0]}\{DFC_{\tau^*}\}",
            r"\Delta y_t=\alpha+\beta y_{t-1}+\sum_{l=1}^{L}\gamma_l\Delta y_{t-l}+\varepsilon_t",
            r"SADF_t=\sup_{t_0\in[1,t-\tau]}\{ADF_{t_0,t}\}",
            r"\sum_{t=\tau}^{T}(t-\tau+1)=\frac{1}{2}(T-\tau+2)(T-\tau+1)=\binom{T-\tau+2}{2}",
            r"f(N,T)=N^3+N^2(2T+3)+N(4T-1)+2T+2",
            r"g(N,T,\tau)=\sum_{t=\tau}^{T}f(N,t)+T-\tau",
            r"\sum_{t=\tau}^{T}g(N,t,\tau)",
            r"(T,N)=(356631,3)",
            r"\Delta\log[y_t]=\alpha+\beta\log[y_{t-1}]+\varepsilon_t",
            r"\mathbb{E}[\log[y_t]]=-\frac{\alpha}{\beta}+(1+\beta)^t\left(\log[y_0]+\frac{\alpha}{\beta}\right)",
            r"-2&lt;\beta&lt;0",
            r"-1&lt;\beta&lt;0",
            r"s_t=\{ADF_{t_0,t}\}_{t_0\in[1,t-\tau]}",
            r"C_{t,q}=K^{-1}\int_{Q_{t,q}}^{\infty}x f[x]\,dx",
            r"\dot C_{t,q}=\sqrt{K^{-1}\int_{Q_{t,q}}^{\infty}(x-C_{t,q})^2 f[x]\,dx}",
            r"\(-1.5\)",
            r"y_t=\alpha e^{\beta t}\eta_t,\quad \log[\eta_t]=\xi_t",
            r"y_t=\alpha t^\beta\eta_t,\quad \log[\eta_t]=\xi_t",
            r"SMT_t=\sup_{t_0\in[1,t-\tau]}\left\{\frac{|\hat{\beta}_{t_0,t}|}{\hat{\sigma}_{\beta_{t_0,t}}}\right\}",
            r"SMT_t=\sup_{t_0\in[1,t-\tau]}\left\{\frac{|\hat{\beta}_{t_0,t}|}{\hat{\sigma}_{\beta_{t_0,t}}(t-t_0)^\varphi}\right\}",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-17 formula missing: {fragment}")
        figures = {
            "Figure 17.1:": "media/chapter-17-figure-17-1.png",
            "Figure 17.2:": "media/chapter-17-figure-17-2.png",
            "Figure 17.3:": "media/chapter-17-figure-17-3.png",
        }
        for prefix, src in figures.items():
            figure = next((fig for fig in soup.select("figure.book-figure") if fig.get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one(f'img[src="{src}"]'):
                failures.append(f"chapter-17 {prefix.rstrip(':')} is not bound to {src}")
            if figure is not None:
                caption = figure.select_one("figcaption")
                if caption and any(r"\(" in str(node) or r"\)" in str(node) for node in caption.find_all(string=True) if not node.find_parent(class_="math")):
                    failures.append(f"chapter-17 {prefix.rstrip(':')} caption contains raw TeX delimiters")
        figure_17_3 = next((fig for fig in soup.select("figure.book-figure") if fig.get_text(" ", strip=True).startswith("Figure 17.3:")), None)
        if figure_17_3 is None or len(figure_17_3.select("figcaption .math.inline")) < 3:
            failures.append("chapter-17 Figure 17.3 caption formulas are not semantic MathJax spans")
        table_17_1 = next((fig for fig in soup.select("figure.table-figure") if fig.get_text(" ", strip=True).startswith("Table 17.1:")), None)
        if table_17_1 is None:
            failures.append("chapter-17 Table 17.1 missing")
        else:
            header = [th.get_text(" ", strip=True) for th in table_17_1.select("thead th")]
            rows = [[cell.get_text(" ", strip=True) for cell in row.select("td")] for row in table_17_1.select("tbody tr")]
            if header != ["Matrix Operation", "FLOPs"] or len(rows) != 8:
                failures.append("chapter-17 Table 17.1 structure is wrong")
            expected_rows = [
                [r"\(o_1=X^\prime y\)", r"\((2T-1)N\)"],
                [r"\(o_7=o_3o_6\frac{1}{T-N}\)", r"\(2+N^2\)"],
                [r"\(o_8=\frac{o_4[0,0]}{\sqrt{o_7[0,0]}}\)", r"\(1\)"],
            ]
            for expected in expected_rows:
                if expected not in rows:
                    failures.append(f"chapter-17 Table 17.1 row missing: {expected}")
        captions_to_code = {
            fig.select_one("figcaption").get_text(" ", strip=True): (fig.select_one("code").get_text() if fig.select_one("code") else "")
            for fig in soup.select("figure.code-listing")
        }
        expected_code = {
            "Snippet 17.1:": ["def get_bsadf", "startPoints,bsadf,allADF=range(0,y.shape[0]+lags-minSL+1),None,[]", "out={'Time':logP.index[-1],'gsadf':bsadf}"],
            "Snippet 17.2:": ["def getYX", "series_=series.diff().dropna()", "return y,x"],
            "Snippet 17.3:": ["def lagDF", "df_=df0.shift(lag).copy(deep=True)", "return df1"],
            "Snippet 17.4:": ["def getBetas", "xxinv=np.linalg.inv(xx)", "return bMean,bVar"],
        }
        for prefix, fragments in expected_code.items():
            code = next((code for caption, code in captions_to_code.items() if caption.startswith(prefix)), "")
            if not code:
                failures.append(f"chapter-17 {prefix.rstrip(':')} is missing")
                continue
            for fragment in fragments:
                if fragment not in code:
                    failures.append(f"chapter-17 {prefix.rstrip(':')} missing code: {fragment}")
        if not any(caption.startswith("Snippet 17.1: SADF") for caption in captions_to_code):
            failures.append("chapter-17 Snippet 17.1 caption does not preserve SADF acronym")
        refs = [li.get_text(" ", strip=True) for li in soup.select(".references-list li")]
        if len(refs) != 11 or not any(ref.startswith("Brown, R.L., J. Durbin") for ref in refs) or not any(ref.startswith("Phillips, P., S. Shi") for ref in refs):
            failures.append("chapter-17 references are not a clean unordered list")
        if not any("Journal of the Royal Statistical Society: Series B, Vol. 37, No. 2, pp. 149-192" in ref for ref in refs):
            failures.append("chapter-17 Brown-Durbin-Evans reference is not corrected")

    if chapter_slug == "chapter-18":
        chapter_18_bad = [
            "∈ Aw",
            "p[x] = ‖A‖",
            "log2 p[x]",
            "Hn,k",
            "h = 1.42",
            "None count",
            "PIN =",
            "The Lempel-Ziv (LZ)</p>",
            "0 ≤ R[X] ≤ 1",
            "stream of returns rt",
            "|rt |",
            "rt ’s",
            "“01100001’",
            "Liquidity,information",
            "1547–1493",
            "Bienestock",
            "<figure><figcaption>Figure 18.",
            "EXERCISES",
        ]
        for pattern in chapter_18_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-18 artifact remains: {pattern}")
        required_fragments = [
            r'discrete random variable <span class="math inline">\(X\)</span> with possible values <span class="math inline">\(x\in A\)</span>',
            r"H[X]\equiv-\sum_{x\in A}p[x]\log_2 p[x]",
            r"0\le H[X]\le \log_2[\|A\|]",
            r"H[X]=\log_2[\|A\|]\Leftrightarrow p[x]=1/\|A\|",
            r"\log_2\frac{1}{p[x]}",
            r"R[X]\equiv1-\frac{H[X]}{\log_2\|A\|}",
            r"0\le R[X]\le1",
            r"MI[X,Y]=E_{f[x,y]}\left[\log\frac{f[x,y]}{f[x]f[y]}\right]=H[X]+H[Y]-H[X,Y]",
            r"MI[X,Y]=-\frac{1}{2}\log[1-\rho^2]",
            r"\hat{H}_{n,w}=-\frac{1}{w}\sum_{y_1^w\in A^w}",
            r"L_i^n=1+\max\left\{l\mid x_i^{i+l}=x_j^{j+l}",
            "Ornstein and Weiss",
            r"\lim_{n\to\infty}\frac{L_i^n}{\log_2[n]}=\frac{1}{H}",
            r"\hat{H}_{n,k}=\left[\frac{1}{k}\sum_{i=1}^{k}\frac{L_i^n}{\log_2[n]}\right]^{-1}",
            r"\tilde{H}_{n,k}=\frac{1}{k}\sum_{i=1}^{k}\frac{\log_2[n]}{L_i^n}",
            "recall that <span class=\"math inline\">\\(x_i\\)</span> is at the center",
            r"N\approx n+(\log_2[n])^2",
            r"r_t&gt;0",
            r"r_t&lt;0",
            r"r_t=0",
            r"|r_t|",
            r"H=\frac{1}{2}\log[2\pi e\sigma^2]",
            r"\sigma_H=\frac{e^{H-1/2}}{\sqrt{2\pi}}",
            r"M_q[x,p]=\left(\sum_{i=1}^{n}p_i x_i^q\right)^{1/q}",
            r"N_q[p]=\frac{1}{M_{q-1}[p,p]}=\left(\sum_{i=1}^{n}p_i^q\right)^{1/(1-q)}",
            r"\frac{\partial M_q[p,p]}{\partial q}\ge0,\qquad\frac{\partial N_q[p]}{\partial q}\le0",
            r"H[p]=\sum_{i=1}^{n}-p_i\log[p_i]",
            r"\theta_i=\frac{[f_\omega]_i^2\Lambda_{i,i}}{\sum_{n=1}^{N}[f_\omega]_n^2\Lambda_{n,n}}",
            r"H=1-\frac{1}{N}\exp\left[-\sum_{i=1}^{N}\theta_i\log[\theta_i]\right]",
            r"VPIN&amp;=\frac{\alpha\mu}{\alpha\mu+2\varepsilon}",
            r"=\mathbb{E}\left[\left|2v_{\tau}^{B}-1\right|\right]",
            r"X=[f[v_1^B],f[v_2^B],\ldots,f[v_N^B]]",
            r"\{F[H[X_\tau]]\}_{\tau=1,\ldots,N}",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-18 required fragment missing: {fragment}")
        for url in [
            "http://cran.r-project.org/web/packages/entropy/entropy.pdf",
            "https://code.google.com/archive/p/pyentropy/",
        ]:
            if not soup.select_one(f'a[href="{url}"]'):
                failures.append(f"chapter-18 entropy estimator URL is not linked: {url}")
        if re.search(r"<p>\s*not discussed in what follows", html):
            failures.append("chapter-18 orphaned encoding-schemes continuation paragraph remains")
        figure_18_1 = next(
            (
                fig
                for fig in soup.select("figure.book-figure")
                if (fig.select_one("figcaption") and fig.select_one("figcaption").get_text(" ", strip=True).startswith("Figure 18.1:"))
            ),
            None,
        )
        if figure_18_1 is None:
            failures.append("chapter-18 Figure 18.1 missing")
        else:
            srcs = [img.get("src") for img in figure_18_1.select("img")]
            if srcs != ["media/chapter-18-figure-18-1-ab.png", "media/chapter-18-figure-18-1-cd.png"]:
                failures.append(f"chapter-18 Figure 18.1 media mismatch: {srcs}")
            if not figure_18_1.select_one(".figure-panels") or len(figure_18_1.select(".panel-label")) != 2:
                failures.append("chapter-18 Figure 18.1 is not rendered as an explicit multi-panel figure")
            if "(a) 10, (b) 7, (c) 5, and (d) 2" not in figure_18_1.get_text(" ", strip=True):
                failures.append("chapter-18 Figure 18.1 caption lacks panel semantics")
        figure_18_2 = next((fig for fig in soup.select("figure.book-figure") if fig.get_text(" ", strip=True).startswith("Figure 18.2:")), None)
        if figure_18_2 is None or not figure_18_2.select_one('img[src="media/chapter-18-figure-18-2.png"]'):
            failures.append("chapter-18 Figure 18.2 is not bound to its cropped chart")
        article_children = list(soup.select_one("article").children) if soup.select_one("article") else []
        try:
            if article_children.index(figure_18_1) > article_children.index(soup.select_one("#sec-18-7")):
                failures.append("chapter-18 Figure 18.1 appears after the Section 18.7 heading")
        except ValueError:
            pass
        captions_to_code = {
            fig.select_one("figcaption").get_text(" ", strip=True): (fig.select_one("code").get_text() if fig.select_one("code") else "")
            for fig in soup.select("figure.code-listing")
        }
        expected_code = {
            "Snippet 18.1:": ["def plugIn", "def pmf1", "for i in xrange(w,len(msg))", "return pmf"],
            "Snippet 18.2:": ["def lempelZiv_lib", "lib.append(msg_)", "return lib"],
            "Snippet 18.3:": ["def matchLength", "break # search for higher l.", "return len(subS)+1,subS"],
            "Snippet 18.4:": ["def konto", "points=xrange(window,len(msg)-window+1)", "out['r']=1-out['h']/np.log2(len(msg))"],
        }
        for prefix, fragments in expected_code.items():
            code = next((code for caption, code in captions_to_code.items() if caption.startswith(prefix)), "")
            if not code:
                failures.append(f"chapter-18 {prefix.rstrip(':')} is missing")
                continue
            for fragment in fragments:
                if fragment not in code:
                    failures.append(f"chapter-18 {prefix.rstrip(':')} missing code: {fragment}")
        refs = [li.get_text(" ", strip=True) for li in soup.select(".references-list li")]
        if len(refs) != 23:
            failures.append(f"chapter-18 expected 23 references/bibliography items, found {len(refs)}")
        for required_ref in [
            "Liquidity, information, and infrequently traded stocks",
            "Review of Financial Studies, Vol. 25, No. 5, pp. 1457–1493",
            "E. Bienenstock",
            "Minimum entropy as a measure of effective dimensionality",
        ]:
            if not any(required_ref in ref for ref in refs):
                failures.append(f"chapter-18 reference fix missing: {required_ref}")
        css_path = path.parents[1] / "assets" / "afml-book.css"
        if css_path.exists():
            css = css_path.read_text(encoding="utf-8")
            if not re.search(r"\.references-list\s*\{[^}]*list-style:\s*none", css, re.S):
                failures.append("chapter-18/global references list is not using hanging indent styling")
            if not re.search(r"\.references-list li\s*\{[^}]*text-indent:\s*-1\.5rem", css, re.S):
                failures.append("chapter-18/global references list lacks hanging indent")
            if not re.search(r"\.book-figure figcaption,\s*figure\.table-figure figcaption\s*\{[^}]*font-size:\s*\.82rem", css, re.S):
                failures.append("chapter-18/global figure captions are not smaller than body text")
            if not re.search(r"\.book-figure figcaption,\s*figure\.table-figure figcaption\s*\{[^}]*color:\s*#666666", css, re.S):
                failures.append("chapter-18/global figure captions are not muted")
            if not re.search(r"\.book-figure figcaption,\s*figure\.table-figure figcaption\s*\{[^}]*text-align:\s*left", css, re.S):
                failures.append("chapter-18/global figure captions are not book-style left aligned")
            if not re.search(r"\.book-figure figcaption,\s*figure\.table-figure figcaption\s*\{[^}]*max-width:\s*52rem", css, re.S):
                failures.append("chapter-18/global figure captions are not width constrained")
            if not re.search(r"\.book-figure figcaption mjx-container,\s*figure\.table-figure figcaption mjx-container\s*\{[^}]*font-size:\s*100% !important", css, re.S):
                failures.append("chapter-18/global figure-caption MathJax does not inherit caption sizing")
            if not re.search(r"figure\.code-listing figcaption\s*\{[^}]*font-weight:\s*600", css, re.S):
                failures.append("chapter-18/global code-listing captions lost their stronger style")

    if chapter_slug == "chapter-19":
        chapter_19_bad = [
            "buyinitiated",
            "bidask",
            "highfrequency",
            "socalled",
            "Distibution",
            "{mt }",
            "Δmt = mt",
            "{pt }",
            "probability 𝛼",
            "probability 𝛿",
            "{𝜙𝜏 }",
            "y = x + u",
            "adversely selected by</p>",
            "WHAT IS MICROSTRUCTURAL INFORMATION? 295",
            "St = 1 + e𝛼t",
            "T t=1 Lt",
            "afml-316_1.jpg",
            "afml-317_1.jpg",
            "Corwin-schultz",
            r"\alpha=p_0\sqrt{\frac{\sigma_u^2}{\Sigma_0}}",
            r"+\alpha(1-\delta)(\varepsilon-(\mu+\varepsilon))+\alpha\delta(\mu+\varepsilon-\varepsilon)=\alpha\mu(1-2\delta)",
            "EXERCISES",
        ]
        for pattern in chapter_19_bad:
            if pattern in html or pattern in text:
                failures.append(f"chapter-19 artifact remains: {pattern}")
        if re.search(r"<p>\s*informed traders, and the bid-ask spread", html):
            failures.append("chapter-19 review-of-literature page-break continuation paragraph remains")
        required_fragments = [
            "adversely selected by informed traders",
            "high-frequency microstructural models",
            "A buy-initiated trade is labeled",
            r'<span class="math inline">\(\{m_t\}\)</span>',
            r'<span class="math inline">\(\Delta m_t=m_t-m_{t-1}\)</span>',
            r'<span class="math inline">\(\{p_t\}\)</span>',
            "bid-ask spread estimator",
            "Snippet 19.1: Implementation of the Corwin-Schultz Algorithm",
            r"c=\sqrt{\max\{0,-\sigma[\Delta p_t,\Delta p_{t-1}]\}}",
            r"E\left[\frac{1}{T}\sum_{t=1}^{T}\left(\log\left[\frac{H_t}{L_t}\right]\right)^2\right]=k_1\sigma_{HL}^{2}",
            r"S_t=\frac{2(e^{\alpha_t}-1)}{1+e^{\alpha_t}}",
            r"\alpha_t=\frac{\sqrt{2\beta_t}-\sqrt{\beta_t}}{3-2\sqrt{2}}-\sqrt{\frac{\gamma_t}{3-2\sqrt{2}}}",
            r"\(y=x+u\)",
            r"\alpha=-p_0\sqrt{\frac{\sigma_u^2}{\Sigma_0}}",
            r"\mathbb{E}[\pi]=\frac{(v-p_0)^2}{2}\sqrt{\frac{\sigma_u^2}{\Sigma_0}}=\frac{1}{4\lambda}(v-p_0)^2",
            r"\Delta p_t=\lambda(b_t V_t)+\varepsilon_t",
            r"\left|\Delta\log[\tilde p_{\tau}]\right|=\lambda\sum_{t\in B_{\tau}}(p_tV_t)+\varepsilon_{\tau}",
            r"\log[\tilde p_{i,\tau}]-\log[\tilde p_{i,\tau-1}]=\lambda_i\sum_{t\in B_{i,\tau}}b_{i,t}\sqrt{p_{i,t}V_{i,t}}+\varepsilon_{i,\tau}",
            r'<span class="math inline">\(S_0\)</span>',
            r'<span class="math inline">\(S_B\)</span>',
            r'<span class="math inline">\(S_G\)</span>',
            r'<span class="math inline">\(\alpha\)</span>',
            r'<span class="math inline">\(\delta\)</span>',
            r'<span class="math inline">\(1-\delta\)</span>',
            r"PIN_t=\frac{\alpha_t\mu}{\alpha_t\mu+2\varepsilon}",
            r"P[V^B,V^S]&amp;=(1-\alpha)P[V^B,\varepsilon]P[V^S,\varepsilon]",
            r"E[V^B-V^S]=(1-\alpha)(\varepsilon-\varepsilon)+\alpha(1-\delta)((\mu+\varepsilon)-\varepsilon)+\alpha\delta(\varepsilon-(\mu+\varepsilon))=\alpha\mu(1-2\delta)",
            r"VPIN_{\tau}=\frac{\sum_{\tau=1}^{n}|V_{\tau}^{B}-V_{\tau}^{S}|}{\sum_{\tau=1}^{n}(V_{\tau}^{B}+V_{\tau}^{S})}",
            "19.6.1 Distribution of Order Sizes",
            "so-called “mouse” or “GUI” traders",
            r'<span class="math inline">\(\{5,10,20,25,50,100,200,\ldots\}\)</span>',
            r"\hat y_\tau=E_\tau[y_\tau\mid X]",
            r"\phi_\tau=F[-L_\tau]",
            r'<span class="math inline">\(\{\phi_\tau\}\)</span>',
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-19 required fragment missing: {fragment}")
        for prefix, expected_src in [
            ("Figure 19.1:", "media/chapter-19-figure-19-1.png"),
            ("Figure 19.2:", "media/chapter-19-figure-19-2.png"),
            ("Figure 19.3:", "media/chapter-19-figure-19-3.png"),
        ]:
            figure = next((fig for fig in soup.select("figure.book-figure") if fig.select_one("figcaption") and fig.select_one("figcaption").get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one(f'img[src="{expected_src}"]'):
                failures.append(f"chapter-19 {prefix.rstrip(':')} is not bound to its cropped white-background chart")
            if not (path.parent / expected_src).exists():
                failures.append(f"chapter-19 {prefix.rstrip(':')} media file is missing: {expected_src}")
        predatory = next((ul for ul in soup.select("ul") if "Quote stuffers:" in ul.get_text(" ", strip=True)), None)
        predatory_items = [li.get_text(" ", strip=True) for li in predatory.select(":scope > li")] if predatory else []
        expected_predatory = ["Quote stuffers:", "Quote danglers:", "Liquidity squeezers:", "Pack hunters:"]
        if len(predatory_items) != 4 or any(not item.startswith(expected) for item, expected in zip(predatory_items, expected_predatory)):
            failures.append("chapter-19 predatory algorithm list is not a clean four-item list")
        captions_to_code = {
            fig.select_one("figcaption").get_text(" ", strip=True): (fig.select_one("code").get_text() if fig.select_one("code") else "")
            for fig in soup.select("figure.code-listing")
        }
        expected_code = {
            "Snippet 19.1:": ["def getBeta(series,sl):", "den=3-2*2**.5", "alpha[alpha<0]=0", "spread.columns=['Spread','Start_Time']"],
            "Snippet 19.2:": ["def getSigma(beta,gamma):", "k2=(8/np.pi)**.5", "sigma[sigma<0]=0", "return sigma"],
        }
        for prefix, fragments in expected_code.items():
            code = next((code for caption, code in captions_to_code.items() if caption.startswith(prefix)), "")
            if not code:
                failures.append(f"chapter-19 {prefix.rstrip(':')} is missing")
                continue
            for fragment in fragments:
                if fragment not in code:
                    failures.append(f"chapter-19 {prefix.rstrip(':')} missing code: {fragment}")
        refs = [li.get_text(" ", strip=True) for li in soup.select(".references-list li")]
        if len(refs) != 40:
            failures.append(f"chapter-19 expected 40 references, found {len(refs)}")
        if any(ref.startswith("D., Rubel") for ref in refs):
            failures.append("chapter-19 Bethel/Rubel reference split remains")
        for required_ref in [
            "Bethel, E. W., Leinweber. D., Rubel, O., and K. Wu",
            "Flow toxicity and liquidity in a high frequency world",
            "Patzelt, F. and J. Bouchaud",
            "Toth, B., I. Palit, F. Lillo, and J. Farmer",
        ]:
            if not any(required_ref in ref for ref in refs):
                failures.append(f"chapter-19 reference missing: {required_ref}")

    if chapter_slug == "chapter-20":
        if re.search(r"<p>\s*MULTIPROCESSING\s*</p>", html):
            failures.append("chapter-20 heading continuation paragraph remains")
        for pattern in [
            "condition 12",
            "N(N + 1). Solving for rm",
            "outputed list",
            "Zb W",
            "BIBLIOGRAPHY 317",
        ]:
            if pattern in html or pattern in text:
                failures.append(f"chapter-20 artifact remains: {pattern}")
        required_fragments = [
            "20.3 Single-Thread Vs. Multithreading Vs. Multiprocessing",
            r"\frac{1}{2}r_1(r_1+1)=\frac{1}{2M}N(N+1)",
            r"r_1=\frac{-1+\sqrt{1+4N(N+1)M^{-1}}}{2}",
            r"\frac{1}{2}(r_2+r_1+1)(r_2-r_1)=\frac{1}{2M}N(N+1)",
            r"\frac{1}{2}(r_m+r_{m-1}+1)(r_m-r_{m-1})=\frac{1}{2M}N(N+1)",
            r"\left(\sum_{m=1}^{M}\Lambda_{m,m}\right)\left(\sum_{n=1}^{N}\Lambda_{n,n}\right)^{-1}\ge\tau",
            r"P=Z\tilde W=\sum_{b=1}^{B}Z_b\tilde W_b",
            r"\(\tilde W_b\)",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-20 required fragment missing: {fragment}")
        for fragment in [
            r'<span class="math inline">\(\frac{1}{2}r_1(r_1+1)=\frac{1}{2M}N(N+1)\)</span>',
            r'<span class="math inline">\(\frac{1}{2}(r_2+r_1+1)(r_2-r_1)=\frac{1}{2M}N(N+1)\)</span>',
            r'<span class="math inline">\(\frac{1}{2}(r_m+r_{m-1}+1)(r_m-r_{m-1})=\frac{1}{2M}N(N+1)\)</span>',
        ]:
            if fragment in html:
                failures.append("chapter-20 long partition condition remains inline instead of display math")
        for prefix, expected_src in [
            ("Figure 20.1:", "media/chapter-20-figure-20-1.png"),
            ("Figure 20.2:", "media/chapter-20-figure-20-2.png"),
        ]:
            figure = next((fig for fig in soup.select("figure.book-figure") if fig.select_one("figcaption") and fig.select_one("figcaption").get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None or not figure.select_one(f'img[src="{expected_src}"]'):
                failures.append(f"chapter-20 {prefix.rstrip(':')} is not bound to its cropped white-background chart")
            if not (path.parent / expected_src).exists():
                failures.append(f"chapter-20 {prefix.rstrip(':')} media file is missing: {expected_src}")
        captions_to_code = {
            fig.select_one("figcaption").get_text(" ", strip=True): (fig.select_one("code").get_text() if fig.select_one("code") else "")
            for fig in soup.select("figure.code-listing")
        }
        if len(captions_to_code) != 14:
            failures.append(f"chapter-20 expected 14 code snippets, found {len(captions_to_code)}")

        def code_for(prefix: str) -> str:
            return next((code for caption, code in captions_to_code.items() if caption.startswith(prefix)), "")

        snippet_20_4 = code_for("Snippet 20.4:")
        if not snippet_20_4:
            failures.append("chapter-20 Snippet 20.4 is missing")
        else:
            if "parts=np.linspace(0,r.shape[1],min(numThreads,r.shape[1])+1)" not in snippet_20_4:
                failures.append("chapter-20 Snippet 20.4 does not partition the Gaussian paths along the column axis")
            if "parts=np.linspace(0,r.shape[0]" in snippet_20_4:
                failures.append("chapter-20 Snippet 20.4 source erratum has regressed")
        snippet_20_7 = code_for("Snippet 20.7:")
        if not snippet_20_7:
            failures.append("chapter-20 Snippet 20.7 is missing")
        else:
            for bad in ["Heisenbugs", "argList", "2 https://pypi", "3 http://scikit-learn"]:
                if bad in snippet_20_7:
                    failures.append(f"chapter-20 Snippet 20.7 includes non-code artifact: {bad}")
            for fragment in [
                "linParts(len(pdObj[1]),numThreads*mpBatches)",
                "nestedParts(len(pdObj[1]),numThreads*mpBatches)",
                "job={pdObj[0]:pdObj[1][parts[i-1]:parts[i]],'func':func}",
            ]:
                if fragment not in snippet_20_7:
                    failures.append(f"chapter-20 Snippet 20.7 missing code: {fragment}")
        snippet_20_12 = code_for("Snippet 20.12:")
        for fragment in ["out,redux,reduxInPlace=[out_],list.append,True", "copy.deepcopy(out_)", "out=out.sort_index()"]:
            if fragment not in snippet_20_12:
                failures.append(f"chapter-20 Snippet 20.12 missing reduction code: {fragment}")
        snippet_20_14 = code_for("Snippet 20.14:")
        for fragment in ["redux=pd.DataFrame.add", "eVec.loc[df0.columns].values", "pcs=pd.DataFrame(pcs,index=df0.index,columns=eVec.columns)"]:
            if fragment not in snippet_20_14:
                failures.append(f"chapter-20 Snippet 20.14 missing PCA code: {fragment}")
        refs = [li.get_text(" ", strip=True) for li in soup.select(".references-list li")]
        if len(refs) != 7:
            failures.append(f"chapter-20 expected 7 references/bibliography items, found {len(refs)}")

    if chapter_slug == "chapter-21":
        for pattern in [
            "Consider a set on assets",
            "an globally",
            "porftolio",
            "non-continuous",
            "pK,N",
            "K1 pi",
            "⏟",
            "afml-349_1.jpg",
            "Asset 1 Asset 1 Asset 2 Asset 2 Asset 3 Asset 3",
            "Units of capital Units of capital",
            "BIBLIOGRAPHY 329",
            "EXERCISES",
        ]:
            if pattern in html or pattern in text:
                failures.append(f"chapter-21 artifact remains: {pattern}")
        for pattern in [r"(^|\n)\s*torial solution\b", r"(^|\n)\s*lute weights\b"]:
            if re.search(pattern, text):
                failures.append(f"chapter-21 OCR line fragment remains: {pattern}")
        required_fragments = [
            "Consider a set of assets",
            r"r=\operatorname{diag}[\mu^\prime\omega]-\tau[\omega]",
            r"\tau_1[\omega]&amp;=\sum_{n=1}^{N}c_{n,1}\sqrt{|\omega_{n,1}-\omega_n^*|}",
            r"\tau_h[\omega]&amp;=\sum_{n=1}^{N}c_{n,h}\sqrt{|\omega_{n,h}-\omega_{n,h-1}|}",
            r"SR[r]=\frac{\sum_{h=1}^{H}\left(\mu_h^\prime\omega_h-\tau_h[\omega]\right)}{\sqrt{\sum_{h=1}^{H}\omega_h^\prime V_h\omega_h}}",
            r"\max_{\omega}\quad &amp; SR[r]",
            r"\sum_{i=1}^{N}|\omega_{i,h}|=1,\quad \forall h=1,\ldots,H",
            r"x_1+\cdots+x_N=K",
            r"\binom{K+N-1}{N-1}",
            r"p^{K,N}=\left\{\{p_i\}_{i=1,\ldots,N}\mid p_i\in\mathbb{W},\ \sum_{i=1}^{N}p_i=K\right\}",
            r"\Omega=\left\{\left\{\frac{s_j}{K}p_j\right\}_{j=1,\ldots,N}",
            r"\Phi=\underbrace{\Omega\times\cdots\times\Omega}_{H}",
            r"\omega^*=0",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-21 required fragment missing: {fragment}")
        figure = next((fig for fig in soup.select("figure.book-figure") if fig.select_one("figcaption") and fig.select_one("figcaption").get_text(" ", strip=True).startswith("Figure 21.1:")), None)
        if figure is None or not figure.select_one('img[src="media/chapter-21-figure-21-1.png"]'):
            failures.append("chapter-21 Figure 21.1 is not bound to its cropped white-background chart")
        if not (path.parent / "media/chapter-21-figure-21-1.png").exists():
            failures.append("chapter-21 Figure 21.1 media file is missing")
        captions_to_code = {
            fig.select_one("figcaption").get_text(" ", strip=True): (fig.select_one("code").get_text() if fig.select_one("code") else "")
            for fig in soup.select("figure.code-listing")
        }
        if len(captions_to_code) != 7:
            failures.append(f"chapter-21 expected 7 code snippets, found {len(captions_to_code)}")
        if 'Snippet 21.2: Set <span class="math inline">\\(\\Omega\\)</span>' not in html:
            failures.append("chapter-21 Snippet 21.2 caption does not render Omega as MathJax")

        def code_for(prefix: str) -> str:
            return next((code for caption, code in captions_to_code.items() if caption.startswith(prefix)), "")

        expected_code = {
            "Snippet 21.1:": ["def pigeonHole(k,n):", "combinations_with_replacement(xrange(n),k)", "yield r"],
            "Snippet 21.2:": ["def getAllWeights(k,n):", "parts,w,seen=pigeonHole(k,n),None,set()", "product([-1,1],repeat=n)", "w_signed_=(w_*prod_).reshape(-1,1)", "if key in seen:", "seen.add(key)"],
            "Snippet 21.3:": ["def evalTCosts(w,params,w0=None):", "w_=np.zeros(w.shape[0]) if w0 is None else np.asarray(w0).reshape(-1)", "def evalSR(params,w,tcost):", "def dynOptPort(params,k=None,w0=None):", "tcost_=evalTCosts(w_,params,w0=w0)", "for prod_ in product(w_all.T,repeat=len(params)):"],
            "Snippet 21.5:": ["def genMean(size):", "for h in range(horizon):", "params.append({'mean':mean_,'cov':cov_,'c':c_})"],
            "Snippet 21.6:": ["# Static optimal portfolio", "def statOptPortf(cov,a):", "w/=abs(w).sum()", "print 'static SR:',sr_stat"],
            "Snippet 21.7:": ["w_dyn=dynOptPort(params)", "tcost_dyn=evalTCosts(w_dyn,params)", "print 'dynamic SR:',sr_dyn"],
        }
        for prefix, fragments in expected_code.items():
            code = code_for(prefix)
            if not code:
                failures.append(f"chapter-21 {prefix.rstrip(':')} is missing")
                continue
            for fragment in fragments:
                if fragment not in code:
                    failures.append(f"chapter-21 {prefix.rstrip(':')} missing code: {fragment}")
        snippet_21_6 = code_for("Snippet 21.6:")
        if "porftolio" in snippet_21_6:
            failures.append("chapter-21 Snippet 21.6 typo remains")
        refs = [li.get_text(" ", strip=True) for li in soup.select(".references-list li")]
        if len(refs) != 5:
            failures.append(f"chapter-21 expected 5 references, found {len(refs)}")
        for required_ref in [
            "Dynamic trading with predictable returns and transaction costs",
            "Hardy-Ramanujan-Rademacher formula",
            "Solving the optimal trading trajectory problem using a quantum annealer",
            "Exact algorithms for NP-hard problems",
        ]:
            if not any(required_ref in ref for ref in refs):
                failures.append(f"chapter-21 reference missing: {required_ref}")

    if chapter_slug == "chapter-22":
        for pattern in [
            "Figure 22.6: (Continued)",
            "QDR Infiniband",
            "Compute Servers 504 Nodes",
            "QDR InfiniBand Aggregation Switch",
            "Big Memory ANI Servers",
            "GPU Servers 266 Nvidia",
            "IB 10G - TCPoEth",
            "90 T T+1",
            "Electricity Usage (KWh)",
            "Temperature (°F)",
            "90 LTAP(T)",
            "GTB(T)",
            "M(T+1)",
            "Gradient tree boosting (GBT)",
            "newly develop method",
            "Figure 1 includes",
            "In Figure 2,",
            "Figure 3 that",
            "<p>the distributed approach",
            "The non-optimized commercial</p>",
            "<p>cloud instances run these software",
            "<p>approximately 50% more expensive",
            "maximum</p>",
            "<p>possible price allowed",
            "2.3</p>",
            "<p>times longer for the computer",
            "see the highest</p>",
            "<p>amplitude was for the frequency",
            "Armburst",
            "Yelick et al. [2010]",
            "strong evidences",
            "a HPC",
            "state-ofthe-art",
            "pointto-point",
            "inflight analysis",
            "cuttingedge",
            "onceper-minute",
            "DE-AC02- 05CH11231",
            "IEEE. Choi",
            "ACM. Fox",
            "Redmond, WA. Hirschman",
            "EXERCISES",
        ]:
            if pattern in html or pattern in text:
                failures.append(f"chapter-22 artifact remains: {pattern}")
        if "daily peak electricity</p>" in html:
            failures.append("chapter-22 summary sentence is split before figure footnotes")
        required_fragments = [
            '<p class="chapter-authors">Kesheng Wu and Horst D. Simon</p>',
            "Theoretically, an HPC system is built with custom high-cost components",
            "The storage system in Figure 22.1 includes both rotating disks and flash storage",
            "Figure 22.2, we see that PARATEC took 53 times longer",
            "Figure 22.3 that, as the number of cores",
            "high-performance signal-processing tools",
            "strong evidence of High Frequency Trading",
            "daily peak electricity usage years into the future",
            "Gradient tree boosting (GTB)",
            "newly developed method named LTAP",
            'href="http://crd.lbl.gov/cift/"',
            r"\nu=0.1",
            r"\(\alpha\)",
            r"\sqrt{s}=7",
            r"8\,\mathrm{TeV}",
        ]
        for fragment in required_fragments:
            if fragment not in html:
                failures.append(f"chapter-22 required fragment missing: {fragment}")
        expected_figures = [
            ("Figure 22.1:", ["media/chapter-22-figure-22-1.png"]),
            ("Figure 22.2:", ["media/afml-360_1.jpg"]),
            ("Figure 22.3:", ["media/chapter-22-figure-22-3.png"]),
            ("Figure 22.4:", ["media/afml-365_1.jpg"]),
            ("Figure 22.5:", ["media/afml-366_1.jpg"]),
            ("Figure 22.6:", ["media/chapter-22-figure-22-6-ab.png", "media/chapter-22-figure-22-6-cd.png", "media/chapter-22-figure-22-6-ef.png"]),
            ("Figure 22.7:", ["media/afml-372_1.jpg"]),
            ("Figure 22.8:", ["media/afml-373_1.jpg"]),
            ("Figure 22.9:", ["media/afml-374_1.jpg"]),
            ("Figure 22.10:", ["media/afml-375_1.jpg"]),
        ]
        for prefix, expected_srcs in expected_figures:
            figure = next((fig for fig in soup.select("figure.book-figure") if fig.select_one("figcaption") and fig.select_one("figcaption").get_text(" ", strip=True).startswith(prefix)), None)
            if figure is None:
                failures.append(f"chapter-22 {prefix.rstrip(':')} figure is missing")
                continue
            actual_srcs = [img.get("src") for img in figure.select("img")]
            for src in expected_srcs:
                if src not in actual_srcs:
                    failures.append(f"chapter-22 {prefix.rstrip(':')} missing media: {src}")
                if not (path.parent / src).exists():
                    failures.append(f"chapter-22 {prefix.rstrip(':')} media file is missing: {src}")
        fig_22_6 = next((fig for fig in soup.select("figure.book-figure") if fig.select_one("figcaption") and fig.select_one("figcaption").get_text(" ", strip=True).startswith("Figure 22.6:")), None)
        if fig_22_6 and len(fig_22_6.select("img")) != 3:
            failures.append("chapter-22 Figure 22.6 should be a three-panel semantic figure")
        footnotes = soup.select("p.footnote")
        if len(footnotes) != 4:
            failures.append(f"chapter-22 expected 4 semantic footnotes, found {len(footnotes)}")
        for href in [
            "http://nersc.gov/",
            "https://www.hdfgroup.org/",
            "https://www.whitehouse.gov/sites/whitehouse.gov/files/images/NSCI%20Strategic%20Plan.pdf",
            "https://en.wikipedia.org/wiki/National_Strategic_Computing_Initiative",
            "https://hpc4mfg.llnl.gov/",
        ]:
            if not soup.select_one(f'a[href="{href}"]'):
                failures.append(f"chapter-22 footnote/link missing: {href}")
        refs = [li.get_text(" ", strip=True) for li in soup.select(".references-list li")]
        if len(refs) != 37:
            failures.append(f"chapter-22 expected 37 references, found {len(refs)}")
        for required_ref in [
            "Performance analysis of high performance computing applications on the Amazon Web Services Cloud",
            "Hello ADIOS",
            "Towards real-time detection and tracking of spatio-temporal features: Blob-filaments in fusion plasma",
            "Observation of gravitational waves from a binary black hole merger",
            "The European Physical Journal C",
        ]:
            if not any(required_ref in ref for ref in refs):
                failures.append(f"chapter-22 reference missing: {required_ref}")

    reference_paragraph_nodes = soup.select(".references-heading ~ p")
    if chapter_slug == "chapter-04":
        reference_paragraph_nodes = [
            p
            for p in reference_paragraph_nodes
            if not p.get_text(" ", strip=True).startswith("Sample weighting is a common topic")
        ]
    reference_paragraphs = len(reference_paragraph_nodes)
    if reference_paragraphs:
        failures.append(f"paragraphs after references heading: {reference_paragraphs}")

    missing_media = []
    for fig in soup.select("figure:not(.code-listing):not(.quote-snippet)"):
        if not fig.select_one("img,svg,canvas,table"):
            caption = fig.get_text(" ", strip=True)[:120]
            missing_media.append(caption)
    if missing_media:
        failures.append(f"non-code figures missing media: {missing_media}")

    css_path = path.parents[1] / "assets" / "afml-book.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        if re.search(r"html,\s*body\s*\{[^}]*overflow-x:\s*hidden", css, re.S):
            failures.append("global overflow-x hidden masks layout overflow")
    if soup.select("figure.book-figure figcaption, figure.table-figure figcaption") and css_path.exists():
        caption_rule = re.search(r"\.book-figure figcaption,\s*figure\.table-figure figcaption\s*\{(?P<body>[^}]*)\}", css, re.S)
        caption_rule_body = caption_rule.group("body") if caption_rule else ""
        if not caption_rule:
            failures.append("figure/table caption CSS rule is missing")
        if "font-size: .82rem" not in caption_rule_body:
            failures.append("figure/table captions are not smaller than body text")
        if "text-align: left" not in caption_rule_body:
            failures.append("figure/table captions should use book-style left alignment")
        if "color: #666666" not in caption_rule_body:
            failures.append("figure/table captions are not muted")
        if "max-width: 52rem" not in caption_rule_body:
            failures.append("figure/table captions are not constrained as a caption block")
        if "overflow-wrap: anywhere" not in caption_rule_body:
            failures.append("figure/table captions are not protected against long-caption overflow")
        if "padding-top: .55rem" not in caption_rule_body or "border-top: 1px solid #eeeeee" not in caption_rule_body:
            failures.append("figure/table captions do not have a visible separator from body/image content")
        if "figure.code-listing figcaption" in caption_rule.group(0) if caption_rule else False:
            failures.append("code-listing captions are incorrectly included in the figure/table caption rule")
        if not re.search(r"\.book-figure figcaption \.math\.inline,\s*figure\.table-figure figcaption \.math\.inline\s*\{[^}]*font-size:\s*1em", css, re.S):
            failures.append("figure/table caption inline MathJax does not inherit caption size")
        if not re.search(r"\.book-figure figcaption mjx-container,\s*figure\.table-figure figcaption mjx-container\s*\{[^}]*font-size:\s*100%\s*!important", css, re.S):
            failures.append("figure/table caption MathJax does not inherit caption size")

    bad_text = []
    for pattern in BAD_TEXT_PATTERNS:
        if pattern == "T1":
            if re.search(r"\bT1\b", text):
                bad_text.append(pattern)
        elif pattern in text:
            if pattern == "PIN =" and not re.search(r"(?<!V)\bPIN\s*=", text):
                continue
            bad_text.append(pattern)
    for pattern in bad_text:
        failures.append(f"text artifact remains: {pattern}")

    bad_html = [pattern for pattern in BAD_HTML_PATTERNS if re.search(pattern, html)]
    for pattern in bad_html:
        failures.append(f"html artifact remains: {pattern}")

    code_reports = []
    for fig in soup.select("figure.code-listing"):
        caption = fig.select_one("figcaption")
        label = caption.get_text(" ", strip=True) if caption else "unknown snippet"
        code_el = fig.select_one("code")
        if code_el is None:
            failures.append(f"{label}: missing code element")
            continue
        code = code_el.get_text()
        blank_run = max_blank_run(code)
        code_reports.append({"caption": label, "max_blank_run": blank_run})
        if blank_run > 2:
            failures.append(f"{label}: extraction blank run {blank_run}")
        if "python" in (code_el.get("class") or []):
            try:
                list(tokenize.generate_tokens(io.StringIO(code).readline))
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{label}: Python tokenize failed: {type(exc).__name__}: {exc}")
            if re.search(r"^\s*\d+(?:\.[A-Z0-9]+)+\s+[A-Z][A-Z0-9 -]+$", code, re.MULTILINE):
                failures.append(f"{label}: section heading appears inside code block")
            for line_no, line in enumerate(code.splitlines(), 1):
                if BAD_CODE_GLYPH_RE.search(line):
                    failures.append(f"{label}: non-ASCII code glyph on line {line_no}")

    math_spans = [node.get_text(" ", strip=True) for node in soup.select(".math.inline")]
    long_math_spans = [span[:180] for span in math_spans if len(span) > 240]
    if long_math_spans:
        failures.append(f"suspiciously long inline math spans: {long_math_spans}")

    report = {
        "file": str(path),
        "code_listings": len(soup.select("figure.code-listing")),
        "non_code_figures": len(soup.select("figure:not(.code-listing):not(.quote-snippet)")),
        "missing_figure_media": len(missing_media),
        "math_display": len(soup.select(".math.display")),
        "math_inline": len(soup.select(".math.inline")),
        "legacy_formula": len(soup.select(".formula")),
        "reference_lists": len(soup.select(".references-list")),
        "reference_items": len(soup.select(".references-list li")),
        "duplicate_ids": duplicate_ids,
        "code_reports": code_reports,
        "bad_text": bad_text,
        "bad_html": bad_html,
    }
    return report, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit one generated AFML web-book chapter.")
    parser.add_argument("--chapter", help="Chapter slug, for example chapter-15")
    parser.add_argument("--file", help="Generated chapter HTML path")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()

    root = repo_root()
    path = chapter_path(root, args.chapter, args.file)
    if not path.exists():
        raise SystemExit(f"Missing chapter file: {path}")

    report, failures = audit(path)
    if args.json:
        print(json.dumps({"report": report, "failures": failures}, indent=2, ensure_ascii=False))
    else:
        for key, value in report.items():
            if key != "code_reports":
                print(f"{key}: {value}")
        for item in report["code_reports"]:
            print(f"code: {item['caption']} blank_run={item['max_blank_run']}")
        if failures:
            print("\nFailures:", file=sys.stderr)
            for failure in failures:
                print(f"- {failure}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
