# Changelog

Software changes. Terminology changes are in the history of `data/db/`
(`git log -p data/db/term.sql`) and in data releases (`data-v*` tags).

## 0.2.0 (2026-10-30)

A simpler database that the team can learn and teach ([ADR 0010](docs/adr/0010-four-tables-raw-data.md)).
Version 0.1.1 is kept on the branch `archive/v0.1.1-full-schema`.

- **Four tables** instead of 16: `domain`, `entry`, `term`, `definition`, plus
  the view `entry_overview`. Constraints enforce the rules (keys, languages,
  no blank terms, one cell per entry and language).
- **English, Turkish and Spanish only**, re-imported from the sheet snapshot
  **exactly as typed**: 523 entries, 1,502 terms, 14 definitions. Synonyms
  written together stay together; spaces and characters are unchanged; only
  the three `#empty` placeholders were left out. See `data/legacy/IMPORT_REPORT.md`.
- **Expressions** are a domain like the others (as in the sheet's Domain column).
- Removed: the revision log and its triggers (git is the history), the QA
  engine and report (replaced by the example queries), vote/contributor/
  release/import tables, provenance and review columns (they return before
  AI-generated content), and the 27 other languages.
- New: `queries/`, ten commented example queries, tested on every change.
- Commands: `termquake migrate` is now `termquake import-sheet`.
- Website: a more compact header on phones, an interface-language button that
  cannot be mistaken for the term languages, calmer result rows (no colour
  stripes or marker highlights), filters that show they scroll, and the list
  rendered in batches (Lighthouse mobile performance 93 to 99).

## 0.1.1 (2026-10-27)

Fixes from an independent review.

- `build` refuses to discard edits that were not dumped; `dump` refuses to
  overwrite `data/db` changes made after the build (pull, branch switch, hand
  edit). `--force` overrides either.
- Search keys are derived data: computed on every build, no longer stored in
  `data/db/term.sql`, so edits made directly in the files (e.g. on GitHub) work.
- Machine-made (MT/LLM) terms and definitions are published only once
  approved; a reviewer's approval outranks an automatic QA flag.
- History: the author of an edit is recorded only when the edit sets
  `updated_by` (no longer blamed on the import bot); editing an imported term
  marks it `origin = 'human'`.
- Line breaks inside values are saved exactly (`\r\n`, `\r`); data files are
  always LF (`.gitattributes`).
- Rows may refer to rows loaded later (e.g. `merged_into`); broken references
  are reported clearly and block `dump`.
- Deploy runs the tests and data checks itself before publishing; Playwright
  is pinned.
- Web app: download links work after the offline worker is installed; links
  to merged entries open the replacement; a link to a missing entry explains
  itself; a saved filter for a removed domain falls back to All; right-to-left
  search text is handled.
- CSV download: cells starting with `= + - @` can't run as spreadsheet formulas.
- A volunteer's email address was removed from the legacy snapshot.

## 0.1.0 (2026-10-27)

First version of the infrastructure.

- SQL termbase following TBX-Basic v4 / ISO 16642: concepts, terms,
  definitions, contexts, figures, relations, votes, revision history,
  provenance and QA.
- The database is the source of truth, stored in git as canonical SQL
  (`data/db/`); `termquake build`, `dump`, `dump --check`, `export`.
- One-time, read-only migration of the legacy Google Sheet: 523 entries,
  14,004 terms in 30 languages, 14 definitions; frozen snapshot and migration
  report in `data/legacy/`.
- QA checks recomputed on every build; `data/QA_REPORT.md` with coverage for
  all languages and a worklist for published ones.
- Offline web app (PWA) publishing English, Turkish and Spanish:
  accent-insensitive search, domain filters, full-screen "show" mode with
  screen wake lock, deep links, Turkish/English/Spanish interface, light and
  true-black dark themes, strict CSP.
- Downloads: SQLite, TBX-Basic, CSV.
- CI (lint, tests, database consistency), GitHub Pages deployment with
  browser tests including offline use, tagged data releases, Dependabot.
