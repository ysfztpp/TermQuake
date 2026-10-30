# Contributing to TermQuake

## Terminology (no coding needed)

- **Report a problem** with an entry: use "Report a problem with this entry"
  on the website, or open an issue with the *Term correction* template.
- **Fix one term**: open [`data/db/term.sql`](data/db/term.sql) on GitHub,
  press the pencil icon, find the line (search for the word), change the text
  between the quotes, and choose "Propose changes". Keep everything else on
  the line as it is. A quote inside a term is written twice: `'112''yi arayın'`.

## Editing the database

```bash
git pull
pip install -e ".[dev]"
termquake build                 # data/db/*.sql -> build/termquake.db
```

Edit `build/termquake.db` with [DB Browser for SQLite](https://sqlitebrowser.org/)
(remember *Write Changes*) or SQL; see [`queries/10_change_data.sql`](queries/10_change_data.sql).
Then:

```bash
termquake dump                  # saves data/db/*.sql
git diff data/db                # check: only the rows you meant to change
```

Commit on a branch and open a pull request. The checks rebuild the database,
make sure the files are canonical and run the tests. Merging into `main`
publishes the website.

If you pulled new commits since your last build, run `termquake build` before
editing. `build` won't discard edits you haven't dumped, and `dump` won't
overwrite changes it didn't load; both say what to do (`--force` overrides).

Rules that keep the data trustworthy:

- **Never renumber** entries (`entry.id`, the sheet's Nr.) or terms
  (`term.id`). They are permanent: links, issues and citations use them. A new
  entry takes the next free number.
- **Don't delete a duplicate entry without agreement** in an issue: links to it
  would break. Discuss first.
- **One change per pull request**, with a short reason: "Fix typo in entry 474
  (en)", not "updates".
- **Machine-generated terms** (machine translation, LLMs) are not added yet.
  The schema first gets `origin` and `review_status` columns
  ([ADR 0008](docs/adr/0008-provenance-before-ai.md)).

## Changing the tables

The schema is in [`db/schema.sql`](db/schema.sql). A change to the tables is a
design decision:

1. Write a short decision record in `docs/adr/` (context, decision, consequences).
2. Change `db/schema.sql` and raise `SCHEMA_VERSION` in `src/termquake/__init__.py`.
3. Update `data/db/` (for a new column, add it to every row), the tools in
   `src/termquake/`, the tests and `docs/DATA_MODEL.md`.
4. Run all the checks below.

## Code

1. Branch from `main` and open a pull request; the checks must pass.
2. Keep changes small and explain *why* in the description.
3. Commit messages: a short imperative summary (`Add Arabic`, `Fix CSV export
   of definitions`).

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
