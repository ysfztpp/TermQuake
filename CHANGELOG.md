# Changelog

Software changes. Terminology changes are recorded by the nightly sync commits
(`git log -- data/export`) and in data releases (`data-v*` tags).

## 0.1.0 (2026-10-27)

First version of the infrastructure.

- Termbase schema following TBX-Basic v4 / ISO 16642: concepts, terms,
  definitions, contexts, figures, relations, votes, revision history,
  provenance and QA tables.
- Pipeline: nightly Google Sheet snapshot → SQLite → TSV exports, QA report,
  TBX, CSV and SQLite downloads, web app data.
- Conservative, lossless import with data-quality flags for ambiguous cells.
- Offline web app (PWA) for English, Turkish and Spanish: accent-insensitive
  search, domain filters, full-screen "show" mode, deep links, Turkish/English/
  Spanish interface, light and dark themes.
- CI, nightly sync with a mass-deletion guard, GitHub Pages deployment with
  browser tests (including offline), tagged data releases.
