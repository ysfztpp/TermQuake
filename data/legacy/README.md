# Legacy Google Sheet snapshot (frozen)

Until October 2026 the TermQuake termbase lived in a Google Sheet
(`docs.google.com/spreadsheets/d/1LfFJZxpbCbz2lRpKQ0_kTMKNJVDJ9FyrlAoP15TU8wU`).
On **27 October 2026** the tabs below were downloaded once, read-only (the
sheet's xlsx export; the sheet itself was never modified), and committed here.
`termquake migrate` then created the SQL database in `data/db/` from these files.

| File | Sheet tab | Used by the migration |
|---|---|---|
| `terms.csv` | All Terms and Expressions /Terimler ve İfadeler | yes: entries, terms in 30 languages (the Albanian column was empty) |
| `definitions.csv` | Terms Needing Definition Selection | yes: definitions and their sources |
| `term_candidates.csv` | Source Term Selection | no: archived (validator votes on candidate terms) |
| `term_submissions.csv` | Term submission | no: archived (volunteer submissions) |

What could not be imported as-is is listed in [MIGRATION_REPORT.md](MIGRATION_REPORT.md).

Privacy: a reviewer comment in `definitions.csv` contained a volunteer's
email address (a sheet @-mention). It was replaced with `[email removed]` on
27 October 2026, after the migration; nothing else was changed.

These files are a historical record. **Don't edit them**: the database in
`data/db/` is the source of truth now. The old web app (afet-terim.web.app)
still reads the live sheet; changes made there after 27 October 2026 are not
in this database unless re-imported deliberately.
