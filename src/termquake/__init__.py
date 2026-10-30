"""TermQuake: a small terminology database for disaster relief and search & rescue.

data/db/*.sql (source of truth, in git) -> build/termquake.db (SQLite) -> downloads, website
"""

__version__ = "0.2.0"

# Version of db/schema.sql, stored in the database as PRAGMA user_version.
# Bump it whenever the tables change.
SCHEMA_VERSION = 2
