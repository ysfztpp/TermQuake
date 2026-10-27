# Data model

The schema (`db/schema.sql`) follows the **concept-oriented** model of
terminology science, as standardised in ISO 16642 (Terminological Markup
Framework) and the **TBX-Basic** dialect (TerminOrgs, v4) of ISO 30042 (TBX):

```
concept  (one meaning, language-independent; the sheet's row / "Nr.")
 └── language section (en, tr, es, ...)
      └── term (one designation; synonyms are separate terms, ordered)
```

A dictionary-style "headword → translation" table cannot represent synonyms,
preferred vs deprecated terms, or per-language definitions cleanly. The
concept model can, and it maps 1:1 to TBX, so the data opens in every
professional translation tool.

## Tables

| Table | Holds | TBX-Basic equivalent |
|---|---|---|
| `concept` | One entry. `id` = the sheet's **Nr.** (permanent). Domain, entry type (`term` / `phrase`), status | `conceptEntry` |
| `term` | One term in one language: text, search key, order, term type, part of speech, gender, usage status, note | `termSec` + `termNote`s |
| `definition` | Definition per concept and language, with source | `descrip type="definition"` |
| `context` | Example sentences | `descrip type="context"` |
| `figure` | Images (e.g. "angle grinder") with licence | `xGraphic` |
| `concept_relation` | See-also / broader / narrower links | `crossReference` |
| `domain`, `domain_label` | Subject fields with labels per language | `descrip type="subjectField"` |
| `language` | BCP 47 code, native name, script, direction | `xml:lang` |
| `source` | TDK, AFAD, … | `admin type="source"` |
| `contributor`, `review_vote` | People and the +2 approval vote from the article | (workflow) |
| `revision` | Every change to a term or definition, old and new values | (workflow) |
| `import_batch`, `import_raw` | Lossless copy of every sheet cell, per import | (provenance) |
| `qa_issue` | Data-quality findings, by severity | (QA) |
| `data_release` | Published versions and DOIs | (release) |

Views: `v_language_completion` (coverage per language),
`v_vote_tally` (score and pass/fail per item).

## Rules worth knowing

- **IDs are permanent.** `concept.id` is the sheet's Nr. Links (`#/e/123`),
  issue reports and citations rely on it. Never renumber rows.
- **Synonyms are separate rows**, ordered by `sort_order` as in the sheet. The
  first is shown as the main term. `usage_status` (preferred / admitted /
  deprecated) stays empty until a reviewer sets it: the importer does not guess.
- **Expressions** ("İfadeler / Expressions" in the sheet) are not a subject
  field; they become `entry_type = 'phrase'` and are never split.
- **Provenance on every term and definition**: `origin` is `legacy_import`,
  `human`, `mt` or `llm`; `origin_detail` records model and prompt version;
  `review_status` is `unreviewed` → `proposed` → `approved` / `rejected`.
  The website hides rejected terms; phase 3 will publish AI output only once approved.
- **Search key** `text_norm`: lowercase, accent-free, Turkish ı/i unified,
  punctuation removed (`fold` in `textnorm.py` and `site/src/fold.ts`, kept
  identical by shared tests).

## How sheet cells are imported

The sheet's legend ("/" synonym, "-" derivation, "()" explanation) is not used
consistently, so the importer is conservative:

| In the cell | Import | QA flag |
|---|---|---|
| `enkaz / moloz` (slash with a space) | two terms | none |
| `ferido/a`, `internal/external bleeding` | kept as one term | `ambiguous_slash` |
| `shortness of breath - SOB` | kept | `dash_separator` |
| `automated external defibrillator (AED)` | kept | `acronym_in_parentheses` |
| `shovel (tool)` | kept | `parenthetical` |
| `#empty3`, `#REF!` | ignored | `placeholder_value` (error) |
| invisible characters, broken `i̇` | repaired automatically | info |

Nothing is lost: the untouched cell is always in `import_raw`. Resolving the
flags (splitting acronyms into `term_type = 'acronym'` terms, moving
explanations to `note`, merging duplicate entries) is the standardisation step,
done with human review.
