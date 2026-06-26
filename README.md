# AFML Static Web Book

Static web edition of *Advances in Financial Machine Learning*.

## Local Preview

From this directory:

```bash
python3 -m http.server 8787
```

Then open:

```text
http://127.0.0.1:8787/book/index.html
```

## Build and Review

Regenerate the static site:

```bash
python3 scripts/build_web_book.py
```

Run the full acceptance review:

```bash
python3 scripts/full_book_review.py --write-report
```

Reports:

- `docs/full-book-review.md`
- `docs/browser-layout-review.md`

## GitHub Pages

The repository includes a GitHub Pages workflow at `.github/workflows/pages.yml`.

The deployed site artifact contains only the static website files: `index.html`, `.nojekyll`, `assets/`, and `book/`.

See `docs/github-pages.md` before making the repository or site public.
