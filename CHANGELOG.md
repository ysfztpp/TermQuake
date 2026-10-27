# Changelog

Software changes. Terminology changes are in the history of `data/db/`
(`git log -p data/db/term.sql`) and in data releases (`data-v*` tags).

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
