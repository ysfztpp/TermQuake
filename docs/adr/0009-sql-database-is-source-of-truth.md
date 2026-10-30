# 0009. The SQL database is the source of truth, stored in git as SQL

**Status:** accepted, 27 October 2026 (supersedes 0002). Still in force; since [0010](0010-four-tables-raw-data.md) the database holds English, Turkish and Spanish only.

## Context
The project needs a professional, structured database rather than a
spreadsheet, and nothing automated should read or write the production Google
Sheet. The data must stay versioned and reviewable, hosting must cost nothing,
and the public tool must never depend on a running server.

## Decision
- The legacy sheet was downloaded once, read-only, on 27 October 2026
  (`data/legacy/`), and migrated with `termquake migrate` into the SQL
  database, including every language column (30 with terms), not only the
  three published ones.
- The database content lives in `data/db/` as plain SQL: one file per table,
  one INSERT per row, ordered by primary key. `termquake build` creates a
  SQLite database from it; `termquake dump` writes edits back. CI fails if the
  committed files are not exactly what `dump` produces.
- QA findings are derived from the data on every build, not stored.
- Which languages are published is configuration (`termquake.toml`), not data.

## Alternatives considered
- **Hosted PostgreSQL now (e.g. Supabase).** Real-time multi-user editing, but
  needs accounts, has a free tier that pauses after a week of inactivity, and
  needs its own backup and history strategy. Worth it once many people edit
  through a web form; the schema is ready for it (phase 2), with `data/db`
  kept as the nightly-exported history.
- **Committing the SQLite file itself.** Binary diffs: no readable history, no review.
- **Dolt (git for SQL).** Similar idea with its own server and tooling; plain
  SQL text in git needs nothing extra.

## Consequences
- Every change to the terminology is a reviewed commit with a readable diff;
  `git log -p data/db/term.sql` is the history of every term.
- Editors need the repository and either SQL, a GUI such as DB Browser for
  SQLite, or a script. A web editor for non-technical volunteers is phase 2.
- Edits made in the old sheet after 27 October 2026 are not picked up
  automatically; `termquake fetch-sheet` on a copy plus a reviewed import is
  the deliberate way to bring any in.
