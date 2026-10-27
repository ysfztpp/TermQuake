# 0002. Keep the sheet for editing; build SQLite from a committed snapshot

**Status:** superseded by [0009](0009-sql-database-is-source-of-truth.md), 27 October 2026

## Context
More than a hundred volunteers know the Google Sheet. Moving editing to a new
tool on day one could stall contributions.

## Decision (original)
The sheet stays the place where people edit; a nightly job snapshots it into
git and the SQLite database is rebuilt from that snapshot.

## Why it was replaced
The technical lead decided the SQL database should be the master from the
start, and that automated jobs should not touch the production sheet at all.
The snapshot taken on 27 October 2026 became a one-time migration instead.
