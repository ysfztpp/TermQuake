# 0002. Keep the sheet for editing; build SQLite from a committed snapshot

**Status:** accepted, October 2026

## Context
More than a hundred volunteers know the Google Sheet. Moving editing to a new
tool on day one would stall contributions, and a hosted database needs
accounts, maintenance and money.

## Decision
Phase 1: the sheet stays the place where people edit. A nightly job downloads
it (public xlsx export, no API key) and commits the selected tabs as CSV in
`data/raw/`. The SQLite database is a build artifact, recreated from that
snapshot with `db/schema.sql`. The schema is written to port to PostgreSQL
(phase 2) without redesign.

## Consequences
- Zero hosting cost and nothing to keep running; builds are reproducible from any commit.
- Structure the sheet can't express (usage status, term types) can only be
  added once editing moves to the database (phase 2).
- Renaming tabs or columns in the sheet breaks the sync loudly (by design);
  fix `termquake.toml`.
