# 0013. One row per term, with type, note, origin and review status

**Status:** accepted, 10 November 2026. Schema version 4. Implements the
provenance columns planned in [0008](0008-provenance-before-ai.md).

## Context
A sheet cell often holds several terms: synonyms (`enkaz / moloz`), an
abbreviation (`cardiopulmonary resuscitation (CPR)`) or a note
(`shovel (tool)`). The language-by-language review decides how to split them,
and AI suggestions for missing terms are planned. Schema v3 had room for one
text per entry and language, with nothing to say where it came from.

## Decision
`term` gets five columns; nothing else changes:

| Column | Values | Why |
|---|---|---|
| `sort_order` | 1, 2, ... (1 = main term) | synonyms in a fixed order; the site shows the main term first |
| `term_type` | TBX-Basic: `fullForm` (default), `abbreviation`, `acronym`, `shortForm`, `variant`, `phrase` | standard types that translation tools read |
| `note` | free text or empty | usage notes such as "tool" instead of brackets in the term |
| `origin` | `sheet` (default), `team`, `ai` | AI text can never pass as human text |
| `review_status` | `unreviewed` (default), `reviewed` | what the language reviews have covered |

`UNIQUE (entry_id, lang)` becomes `UNIQUE (entry_id, lang, text)` and
`UNIQUE (entry_id, lang, sort_order)`.

Existing rows keep their ids and texts; they get the defaults, and the
1,154 expression rows get `term_type = 'phrase'`.

## Consequences
- Splitting a cell is an UPDATE of the first row plus INSERTs: no id changes.
- TBX: one `termSec` per term, with `termType` and `note`; AI terms carry the
  note "AI suggestion, not verified". CSV joins a language's terms with " / ".
- Website: abbreviation and note shown next to a term; AI terms get a
  visible "AI suggestion, not verified" label.
- `entry_overview` joins a language's terms in order with " / ".
