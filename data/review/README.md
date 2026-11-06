# Review lists (standardising one language at a time)

`termquake review <lang>` writes an xlsx review sheet for one language. It is
uploaded to Google Sheets for the team to decide on. The sheet is a review form,
not the database.

- The rules in `src/termquake/review.py` propose, for each cell, the terms it
  should become: synonyms on separate lines, abbreviations and notes in their
  own place. When a rule cannot be sure, the cell is marked for review.
- `<lang>.suggestions.csv` holds suggestions for the cells that need a person's
  decision (entry, proposal, reason). These were written by Claude (AI) and are
  marked "AI" in the sheet; they are only suggestions.
- Decisions made in the sheet are read back, saved here, applied to the
  database by code and reviewed in a pull request.

Current review sheet (English): "TermQuake – Terim İnceleme Formu" in Yusuf's Google Drive.
