# The `experimental` branch

Everything here is a trial. Nothing on this branch is deployed, and `main` is
unchanged. Merge parts of it only after the team has looked at them.

## Data
| Step | Command | Result |
|---|---|---|
| One row per term | `termquake standardise` | 1,464 cells split into separate terms: synonyms (` / `), abbreviations in capitals. English also uses the review suggestions in `data/review/en.suggestions.csv`. Row ids of existing terms are kept. |
| AI gap-filling | `termquake ai-import` | 3,038 missing terms filled in 28 languages, and 139 English definitions, all marked `origin = 'ai'` (see `data/ai/README.md`). Zazaki and Albanian are not filled. |
| Schema v5 | `db/schema.sql` | `definition` gets `origin` and `review_status`, like `term`. |

Totals: 523 entries, 17,445 terms (3,476 of them AI text), 153 definitions.

## Website
- Search finds a term in any of the 30 languages, not only the selected pair,
  and says which language matched.
- "Did you mean" for typos.
- AI suggestions carry a label everywhere, and one switch hides them all.
- "Suggest a correction" and "Suggest a new term": a short form that becomes a
  pre-filled GitHub issue or a text to share (WhatsApp, e-mail). For an AI
  term, "This is correct" lets a speaker confirm it in two taps.
- "Listen" in full-screen mode reads the term aloud with the device's voice.
- "Languages and coverage" in the footer: per language, entries with a
  human-written term and entries with only an AI suggestion.
- New look: dark header band, entries as cards with the domain colour.

## Try it
```bash
git checkout experimental
pip install -e . && termquake all
cd site && npm ci && npm run dev
```

## Known gaps
- The other docs (`README.md`, `docs/`) still describe `main`.
- English review decisions were applied without a human pass; the AI-written
  English replacements are marked `origin = 'ai'`.
- Suggestions arrive as GitHub issues; there is no command yet that reads
  them back into the database.
