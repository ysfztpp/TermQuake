# 0010. Four tables, English/Turkish/Spanish, data exactly as typed

**Status:** accepted, 30 October 2026. Supersedes [0004](0004-conservative-lossless-import.md),
[0005](0005-versioning.md) (revision log part), [0007](0007-shared-search-folding.md)
(Python part) and [0008](0008-provenance-before-ai.md) (for now). The full 16-table version is kept
on the branch `archive/v0.1.1-full-schema`.

## Context
Version 0.1 modelled everything a large termbase might one day need: 16
tables, 30 languages, TBX picklist columns, a vote table, a revision log
filled by triggers, provenance and review columns, and a QA engine. Most of it
was empty: 6 tables had no rows, 8 term columns were never filled. The import
also interpreted the data (splitting synonyms at " / ", repairing characters).

The team needs something it can understand, teach and maintain: English,
Turkish and Spanish, as the volunteers typed them.

## Decision
- **Four tables**: `domain`, `entry`, `term`, `definition`, plus one view
  (`entry_overview`) that reads like the sheet. The concept-oriented core of
  0001 stays: an entry is a meaning; each language says it with a term.
- **Three languages**, enforced by CHECK constraints. Other languages stay in
  the sheet snapshot (`data/legacy/`) and on the archive branch.
- **Data exactly as typed.** One `term` row per filled cell, text unchanged:
  synonyms written together stay together, spaces and unusual characters
  stay. Only spreadsheet placeholders (`#empty1`, `#N/A`) are left out, because
  they are not terms. What deserves a look is listed in
  `data/legacy/IMPORT_REPORT.md` and found with the queries in `queries/`.
- **Industry-standard integrity** instead of more tables: primary and foreign
  keys, NOT NULL, CHECK and UNIQUE constraints, indexed foreign keys, cascade
  rules, a schema version (`PRAGMA user_version`), singular snake_case names.
- **History is git.** Every change to `data/db/` is a commit; no trigger-based
  revision table. Citable versions are data releases (0005, part 3, stays).
- **Standards at the edges.** TBX-Basic (ISO 30042) is the exchange format
  for the downloads. TBX does not prescribe a database layout, so the
  database can stay small.

## Consequences
- The schema fits on one screen and can be taught in an hour.
- `term` allows one row per entry and language (`UNIQUE (entry_id, lang)`),
  which matches the data as typed. When the team decides to split synonyms
  into separate terms, a migration replaces that constraint with
  `UNIQUE (entry_id, lang, text)` and adds an order column.
- Cells holding several synonyms are exported to TBX as one term. TBX-Basic
  expects one term per term section, so splitting them is the first
  standardisation step.
- Before AI-generated content is added (roadmap phase 3), two columns come
  back on `term` and `definition`: `origin` (who wrote it) and
  `review_status`, so unreviewed machine output is never published (0008).
