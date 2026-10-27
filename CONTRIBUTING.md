# Contributing to TermQuake

## Terminology (no coding needed)

- **Report a problem** with an entry: use "Report a problem with this entry"
  on the website, or open an issue with the *Term correction* template.
- **See what needs work**: [data/QA_REPORT.md](data/QA_REPORT.md) lists
  coverage per language and every flagged entry by number.

The Google Sheet is no longer the database (see `docs/adr/0009`). Corrections
go into the SQL database, through an issue or a pull request.

## Editing the database

```bash
pip install -e ".[dev]"
termquake build                 # data/db/*.sql -> build/termquake.db
```

Edit `build/termquake.db` with SQL (`sqlite3`), a GUI such as
[DB Browser for SQLite](https://sqlitebrowser.org/), or a script. Then:

```bash
termquake dump                  # saves data/db/*.sql and data/QA_REPORT.md
git diff data/                  # check: only the rows you meant to change
```

Commit on a branch and open a pull request. CI rebuilds the database, checks
the files are canonical (`termquake dump --check`) and runs the tests. Merging
to `main` runs the same checks again, then redeploys the website.

If you pulled new commits since your last build, run `termquake build` before
editing. `build` won't discard edits you haven't dumped, and `dump` won't
overwrite changes it didn't load; both say what to do (`--force` overrides).

Rules that keep the data trustworthy:

- Never renumber entries (`concept.id`) or terms (`term.id`): they are
  permanent IDs used in links and citations.
- Hand-edit `data/db/*.sql` (e.g. in GitHub's web editor) only for small
  fixes inside a line; for anything bigger, edit the database and `dump`.
  Search keys are computed by the build, so a hand edit can't leave one stale.
- Machine-generated content must be written with `origin = 'mt'` or `'llm'`,
  `origin_detail` (model, prompt version) and `review_status = 'proposed'`
  (see `docs/adr/0008`). It is published only once a person sets
  `review_status = 'approved'`.
- Set `updated_by` to your `contributor` id in every UPDATE, so the revision
  log says who changed what. Without it the author is recorded as unknown
  (git still shows who committed).

## Code

1. Branch from `main`, open a pull request; CI must pass.
2. Keep changes small and explain *why* in the description.
3. If you change a design decision, add a record in `docs/adr/`.
4. Commit messages: short imperative summary (`Publish Kurdish`, `Fix acronym
   detection for Turkish capitals`).

```bash
pytest && ruff check src tests && ruff format --check src tests
cd site && npm ci && npm test && npm run typecheck && npm run dev
```

Browser tests (need a built site and Playwright):

```bash
termquake all && (cd site && npm run build)
(cd site && npx vite preview --port 4173 --base /TermQuake/ &)
pip install -e ".[e2e]" && python -m playwright install chromium
E2E_URL=http://localhost:4173/TermQuake/ pytest tests/e2e
```

Search folding lives in two places (`src/termquake/textnorm.py`,
`site/src/fold.ts`); change both and `tests/shared/fold_cases.json` together.
