# 0007. One search-folding rule, tested in both languages

**Status:** accepted, October 2026

## Context
Many users type without a Turkish or Spanish keyboard ("sargi" for "sargı",
"busqueda" for "búsqueda"). The database (Python) and the web app (TypeScript)
both need the same notion of "matches".

## Decision
A single folding rule: Unicode NFKD, remove accents only in scripts where
marks are accents (Latin, Greek, Cyrillic, Armenian, Hebrew, Arabic; keep
them in Indic and Japanese), unify Turkish ı/İ with i, lowercase, punctuation
to spaces. Implemented in `textnorm.fold` and `site/src/fold.ts`; both must
pass `tests/shared/fold_cases.json`.

## Consequences
- A query behaves the same in SQL, exports and the app.
- Changing the rule means changing both implementations and the shared cases.
