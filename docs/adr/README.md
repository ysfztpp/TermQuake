# Architecture decision records

Short notes on why the project is built the way it is, so future team members
can change a decision knowingly instead of by accident. Format: context,
decision, consequences. Add a new numbered file when a decision changes;
don't rewrite old ones.

| # | Decision |
|---|---|
| [0001](0001-concept-oriented-tbx-model.md) | Concept-oriented data model following TBX-Basic / ISO 16642 |
| [0002](0002-sheet-snapshot-and-sqlite.md) | ~~Keep the sheet for editing~~ (superseded by 0009) |
| [0003](0003-static-offline-site.md) | Static, offline-first web app on GitHub Pages |
| [0004](0004-conservative-lossless-import.md) | ~~Conservative, lossless import with a QA worklist~~ (superseded by 0010) |
| [0005](0005-versioning.md) | Version history: git history of `data/db`, revision log, data releases |
| [0006](0006-web-stack.md) | Preact + TypeScript + Vite, Atkinson Hyperlegible |
| [0007](0007-shared-search-folding.md) | One search-folding rule (now in the web app only, see 0010) |
| [0008](0008-provenance-before-ai.md) | Provenance and review status before any AI-generated content (deferred until then, see 0010) |
| [0009](0009-sql-database-is-source-of-truth.md) | The SQL database is the source of truth, stored in git as SQL |
| [0010](0010-four-tables-raw-data.md) | Four tables, English/Turkish/Spanish, data exactly as typed |
