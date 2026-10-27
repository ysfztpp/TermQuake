# Data model

The schema (`db/schema.sql`) follows the **concept-oriented** model of
terminology science, as standardised in ISO 16642 (Terminological Markup
Framework) and the **TBX-Basic** dialect (TerminOrgs, v4) of ISO 30042 (TBX):

```
concept  (one meaning, language-independent; permanent id = the legacy sheet's "Nr.")
 └── language section (en, tr, es, ... 31 languages)
      └── term (one designation; synonyms are separate terms, ordered)
```

A dictionary-style "headword → translation" table cannot represent synonyms,
preferred vs deprecated terms, or per-language definitions cleanly. The
concept model can, and it maps 1:1 to TBX, so the data opens in every
professional translation tool.

## Where the data is

| | Location | Committed |
|---|---|---|
| Structure | `db/schema.sql`, `db/triggers.sql` | yes |
| Content (source of truth) | `data/db/<table>.sql`, one INSERT per row, ordered by primary key | yes |
| Working database | `build/termquake.db` (built by `termquake build`) | no |
| QA findings | `qa_issue` table, recomputed on every build; summary in `data/QA_REPORT.md` | report only |

## Tables

| Table | Holds | TBX-Basic equivalent |
|---|---|---|
| `concept` | One entry: domain, entry type (`term` / `phrase`), status, `legacy_nr` | `conceptEntry` |
| `term` | One term in one language: text, search key, order, term type, part of speech, gender, usage status, note, provenance, review status | `termSec` + `termNote`s |
| `definition` | Definition per concept and language, with source | `descrip type="definition"` |
| `context` | Example sentences | `descrip type="context"` |
| `figure` | Images (e.g. "angle grinder") with licence | `xGraphic` |
| `concept_relation` | See-also / broader / narrower links | `crossReference` |
| `domain`, `domain_label` | Subject fields with labels per language | `descrip type="subjectField"` |
| `language` | BCP 47 code, English and native name, script, direction | `xml:lang` |
| `source` | TDK, AFAD, … | `admin type="source"` |
| `contributor`, `review_vote` | People and the +2 approval vote from the article | (workflow) |
| `revision` | Every change to a term or definition: old and new values, actor, time | (history) |
| `import_batch` | Record of the one-time migration (source, version, snapshot fingerprint) | (provenance) |
| `qa_issue` | Data-quality findings, derived on each build | (QA) |
| `data_release` | Published versions and DOIs | (release) |

Views: `v_language_completion` (coverage per language),
`v_vote_tally` (score and pass/fail per voted item).

## Rules worth knowing

- **IDs are permanent.** `concept.id` equals the legacy sheet's Nr.; `term.id`
  values were assigned at migration. Links (`#/e/123`), issue reports and
  citations rely on them. Never renumber.
- **Synonyms are separate rows**, ordered by `sort_order`. The first is shown
  as the main term. `usage_status` (preferred / admitted / deprecated) stays
  empty until a reviewer sets it: the migration does not guess.
- **Expressions** ("İfadeler / Expressions" in the sheet) are not a subject
  field; they are `entry_type = 'phrase'` and are never split.
- **Provenance on every term and definition**: `origin` is `legacy_import`,
  `human`, `mt` or `llm`; `origin_detail` records model and prompt version;
  `review_status` is `unreviewed` → `proposed` → `approved` / `rejected`.
  Rejected terms are never published.
- **Search key** `text_norm`: lowercase, accent-free, Turkish ı/i unified,
  punctuation removed. Computed by `termquake dump` (the same `fold` function
  as the web app; shared tests keep them identical). A build fails if a
  hand-edited SQL file leaves it stale.
- **Published languages** are configuration, not data: `[publish] languages`
  in `termquake.toml`. All 31 languages stay in the database either way.
- **History:** triggers write to `revision` on every insert, update or delete
  of a term or definition (installed after loading, so rebuilding never logs
  fake edits). `updated_at` is maintained automatically.

## How legacy sheet cells were migrated

The sheet's legend ("/" synonym, "-" derivation, "()" explanation) was not used
consistently, so the migration was conservative:

| In the cell | Migrated as | Flag |
|---|---|---|
| `enkaz / moloz` (slash with a space) | two terms | none |
| `ferido/a`, `internal/external bleeding` | one term, verbatim | QA: `ambiguous_slash` |
| `shortness of breath - SOB` | one term, verbatim | QA: `dash_separator` |
| `automated external defibrillator (AED)` | one term, verbatim | QA: `acronym_in_parentheses` |
| `shovel (tool)` | one term, verbatim | QA: `parenthetical` |
| `#empty3`, `#REF!` | not imported | migration report |
| invisible characters, broken `i̇` | repaired | migration report |

The original cells are kept in `data/legacy/`. Resolving the QA flags
(splitting acronyms into `term_type = 'acronym'` terms, moving explanations to
`note`, merging duplicate entries) is the standardisation step, done with review.
