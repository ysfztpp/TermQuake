# 0011. All sheet languages, in a `language` table

**Status:** accepted, 6 November 2026. Changes [0010](0010-four-tables-raw-data.md) in one point:
the languages. Everything else in 0010 stays (data exactly as typed, git is the history).

## Context
0010 limited the database to English, Turkish and Spanish, enforced by
`CHECK (lang IN ('en', 'tr', 'es'))`. The project's goal is a multilingual
termbase: the sheet has 31 language columns (30 with data; Albanian is empty),
and the clean-up and gap-filling work planned next needs every language in the
database. Adding a language should be a new row, not a schema change.

The live sheet was compared with the 27 October snapshot on 6 November 2026
(read-only, cell by cell): no cell had changed, so the snapshot was used.

## Decision
- **A fifth table, `language`**: `id` (display order), `code` (BCP 47 tag),
  `name_en`, `name_native`, `direction` (`ltr` or `rtl`). `term.lang` and
  `definition.lang` are foreign keys to `language.code`, replacing the CHECK.
- **All 31 sheet columns** are rows of `language`; every filled cell is a
  `term` row, exactly as typed: 12,415 terms in 30 languages.
- **Codes** follow BCP 47: `kmr` for the sheet's Kurdish column (Kurmanji, in
  Latin script), `zza` for Zazaki, `zh-Hans` / `zh-Hant` for simplified and
  traditional Chinese. `name_native` uses the standard self-name (e.g. 한국어,
  not the header's 한국인 "Korean person").
- **Placeholders in any script** are left out like `#empty1`: the Persian
  `#خالی1`–`#خالی3` and French `#N/A`. Listed in `data/legacy/IMPORT_REPORT.md`.
- **The import report no longer flags Persian zero-width non-joiners** (they
  are correct spelling) and now flags `_x0002_`, the spreadsheet code for a
  control character (one Korean cell).
- `entry_overview` has one column per language.
- Website and downloads show every language that has at least one term.

## Consequences
- Term ids were renumbered (entry by entry, languages in display order). The
  English, Turkish and Spanish texts are byte-for-byte unchanged; every one of
  the 12,415 cells matches the sheet snapshot.
- `termquake.toml` no longer lists languages; the database does.
- Adding a language: add a row to `language`, and a line to `entry_overview`
  in `db/schema.sql`.
- The website data grows from about 60 KB to about 400 KB (it is compressed in
  transit and cached for offline use).
