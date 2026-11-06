# 0012. Mechanical clean-up, enforced by a check

**Status:** accepted, 6 November 2026. First clean-up step allowed by
[0010](0010-four-tables-raw-data.md) (each step decided separately).

## Context
The sheet's cells contain characters a reader cannot see but a computer
compares: spaces at the start or end (609 cells), line breaks and double
spaces, a no-break space, a soft hyphen, Hindi letters stored in two
different Unicode forms, Turkish "i̇" (i + combining dot, from lower-casing
"İ" without Turkish rules) and one `_x0002_` (the xlsx code for an invisible
control character). They break search, duplicate detection and sorting, and
TBX tools treat "deprem" and "deprem " as different terms.

## Decision
Five rules, in `src/termquake/clean.py`, run by `termquake clean`:

| Rule | Change | Texts (6 Nov 2026) |
|---|---|---:|
| `spreadsheet_code` | remove xlsx control-character codes (`_x0002_`) | 1 |
| `turkish_dotted_i` | Turkish only: i + combining dot → i | 6 |
| `invisible` | remove soft hyphens, zero-width spaces, BOM | 1 |
| `space` | no-break spaces, tabs, line breaks → space; collapse runs; trim | 632 |
| `unicode_nfc` | Unicode normalisation form C (W3C / web standard) | 25 |

663 texts changed (660 terms, 3 definition texts or sources). Words, letters,
separators (`/`, `-`, `,`), brackets and punctuation are never changed; those
are content decisions for later steps. Zero-width (non-)joiners are kept: they
are part of correct spelling in Persian (11 cells) and other scripts.

The check `termquake clean --check` runs in CI, so every future edit follows
the same rules.

## Consequences
- The git diff of `data/db/term.sql` is the change log: each changed row shows
  before and after. A script confirmed that, ignoring whitespace and invisible
  characters, every changed text is identical to the original.
- A contributor who saves a trailing space gets a failing check with the fix:
  `termquake clean`, then `termquake dump`.
- The website no longer needs to trim cells for display (it still does, harmlessly).
