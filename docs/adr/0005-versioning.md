# 0005. Version history: git snapshots, data releases, revision log

**Status:** accepted, October 2026

## Context
The team wants a full history of the terminology and citable versions for
research, without extra infrastructure.

## Decision
1. Commit `data/raw` and `data/export` on every sync that changes something.
   Exports are sorted and timestamp-free so diffs show only real changes.
2. Tag `data-vX.Y.Z` to publish a GitHub Release with the database, TBX and
   CSV (connect Zenodo to mint a DOI per release).
3. Keep a `revision` table filled by database triggers, for phase 2 when edits
   happen in the database. Triggers are installed after the bulk import, so a
   rebuild doesn't log fake edits.

## Consequences
- "What did entry 41 say in March?" is answered by `git log -p`.
- History of who edited inside the sheet is not captured (the sheet's own
  version history still has it); per-person history starts in phase 2.
