# Google Sheet snapshot (frozen)

Until October 2026 the TermQuake termbase lived in a Google Sheet
(`docs.google.com/spreadsheets/d/1LfFJZxpbCbz2lRpKQ0_kTMKNJVDJ9FyrlAoP15TU8wU`).
On **27 October 2026** the tabs below were downloaded once, read-only (the
sheet's xlsx export; the sheet itself was never modified), and committed here.
`termquake import-sheet` created the database in `data/db/` from these files.

| File | Sheet tab | Imported |
|---|---|---|
| `terms.csv` | All Terms and Expressions /Terimler ve İfadeler | Nr., Domain, English, Turkish and Spanish columns, each cell exactly as typed |
| `definitions.csv` | Terms Needing Definition Selection | definitions and their sources, as typed |
| `term_candidates.csv` | Source Term Selection | no: archived (validator votes on candidate terms) |
| `term_submissions.csv` | Term submission | no: archived (volunteer submissions) |

The other 27 language columns of `terms.csv` are kept here; they are not in the
database (see [ADR 0010](../../docs/adr/0010-four-tables-raw-data.md)).
What was left out, and what is worth a look, is listed in
[IMPORT_REPORT.md](IMPORT_REPORT.md).

Privacy: a reviewer comment in `definitions.csv` contained a volunteer's
email address (a sheet @-mention). It was replaced with `[email removed]` on
27 October 2026; nothing else was changed.

These files are a historical record. **Don't edit them**: the database in
`data/db/` is the source of truth. The old web app (afet-terim.web.app)
still reads the live sheet; changes made there after 27 October 2026 are not
in this database unless imported deliberately.
