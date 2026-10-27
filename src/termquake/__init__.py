"""TermQuake data pipeline.

Google Sheet  ->  data/raw/*.csv  ->  SQLite (build/termquake.db)  ->  exports, TBX, web app data
   (sync)            (committed)          (build)                        (export)
"""

__version__ = "0.1.1"

# Bump when db/schema.sql changes in a way that matters to consumers of the
# published database. Stored in the database as PRAGMA user_version.
SCHEMA_VERSION = 1
