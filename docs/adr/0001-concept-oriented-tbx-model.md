# 0001. Concept-oriented data model following TBX-Basic / ISO 16642

**Status:** accepted, October 2026

## Context
The sheet stores one row per meaning with one column per language, and packs
synonyms, notes and acronyms into single cells. We need a database that can
hold synonyms, preferred/deprecated status, definitions per language and
provenance, and that professional translation tools can import.

## Decision
Use the concept → language → term model of ISO 16642 (TMF) with TBX-Basic v4
data categories (term type, part of speech, grammatical gender, usage status,
definition, context, subject field, source). Each synonym is its own `term`
row. Workflow tables (votes, revisions, QA, provenance) sit beside the core.

## Consequences
- Exports to TBX (ISO 30042) are a direct mapping; IATE and CAT tools can read them.
- Adding a language means adding rows, not columns: the schema never changes.
- More tables than a flat dictionary; `docs/DATA_MODEL.md` explains them.
