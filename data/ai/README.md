# AI suggestions

Text in this folder was written by an AI model (Claude, Anthropic), on
11 November 2026, to fill gaps in the termbase. **No person has verified it.**

| File | Content |
|---|---|
| `terms/<lang>.tsv` | a term for each entry that had none in that language (3,038 entries in 28 languages) |
| `definitions/en.tsv` | short English definitions for 139 disaster, rescue and equipment entries |

How it is used:
- `termquake ai-import` loads the files. It only fills gaps: where a language
  already has a term (or a definition), nothing changes.
- Every row is stored with `origin = 'ai'` and `review_status = 'unreviewed'`.
  The website shows "AI suggestion, not verified" and can hide these terms;
  TBX carries the same note.

Limits, stated plainly:
- The model translated from the English and Turkish terms of each entry. There
  was no back-test and no native-speaker check.
- Quality is expected to be good for widely used languages and standard
  medical vocabulary, and weaker for Kurmanji Kurdish and Armenian, and for
  equipment terms that differ by country.
- **Zazaki and Albanian were not filled.** The model is not reliable enough in
  Zazaki, and Albanian has no human-written term to anchor a review.
- A term becomes trusted only when a speaker confirms it (the "This is
  correct" button on the site, or the review sheet) and its row is updated to
  `origin = 'team'` or `review_status = 'reviewed'`.
