# 0005. Version history: git, revision log, data releases

**Status:** accepted, October 2026 (updated for 0009)

## Context
The team wants a full history of the terminology and citable versions for
research, without extra infrastructure.

## Decision
1. **Git history of `data/db/`.** Every saved change is a commit; files are
   sorted and one row per line, so diffs show exactly the rows that changed.
2. **`revision` table** filled by database triggers with old and new values of
   every term and definition change, saved with the data by `termquake dump`.
   Triggers are installed after loading, so a rebuild never logs fake edits.
3. **Data releases.** A tag `data-vX.Y.Z` publishes the database, TBX and CSV
   as a GitHub Release (connect Zenodo to mint a DOI per release).

## Consequences
- "What did entry 41 say in March?" is answered by `git log -p data/db/term.sql`
  or by querying `revision`.
- The revision log moves with the data if the database later runs on PostgreSQL.
