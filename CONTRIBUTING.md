# Contributing to TermQuake

## Terminology (no coding needed)

- **Correct or add terms in the Google Sheet.** The website picks up changes
  in the nightly sync.
- **Report a problem** with an entry: use "Report a problem with this entry"
  on the website, or open an issue with the *Term correction* template.
- **Work through the QA report**: [data/export/QA_REPORT.md](data/export/QA_REPORT.md)
  lists every flagged entry by its Nr.

Please don't rename tabs or columns, and never change the Nr. of an existing
row: it is the entry's permanent ID.

## Code

1. Create a branch from `main` and open a pull request; CI must pass
   (lint, pipeline tests, web app type check and tests).
2. Keep changes small and explain *why* in the PR description.
3. If you change a design decision, add a record in `docs/adr/`.
4. Commit messages: short imperative summary (`Add Kurdish to the pilot`,
   `Fix acronym detection for Turkish capitals`). The sync bot uses the prefix `data:`.

### Setup

```bash
pip install -e ".[dev]"
termquake sync && termquake all
pytest && ruff check src tests && ruff format --check src tests

cd site && npm ci && npm run dev
npm test && npm run typecheck
```

Browser tests (need a built site and Playwright):

```bash
cd site && npm run build && npx vite preview --port 4173 --base /termquake/ &
pip install playwright && python -m playwright install chromium
E2E_URL=http://localhost:4173/termquake/ pytest tests/e2e
```

### Rules that keep the data trustworthy

- Never commit generated files except `data/raw/` and `data/export/`
  (the sync job owns those).
- Anything machine-generated must be written with `origin = 'mt'` or `'llm'`
  and `review_status = 'proposed'` (see `docs/adr/0008`).
- Search folding lives in two places (`src/termquake/textnorm.py`,
  `site/src/fold.ts`); change both and `tests/shared/fold_cases.json` together.
