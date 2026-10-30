-- =====================================================================
-- TermQuake database schema (SQLite), version 2
--
-- Four tables, one idea: an ENTRY is one meaning, and each language says it
-- with a TERM. This is the concept-oriented model that professional
-- termbases use (ISO 16642; TBX, ISO 30042), reduced to what the project
-- needs today: English, Turkish and Spanish, as typed in the original sheet.
--
--   domain 1 ──< entry 1 ──< term         (one row per entry per language)
--                      1 ──< definition   (one row per entry per language)
--
-- Conventions: singular snake_case table names; every table has an integer
-- `id` primary key; a column that points to another table is called
-- <table>_id and is a foreign key; languages use BCP 47 codes.
-- =====================================================================

PRAGMA foreign_keys = ON;  -- SQLite checks foreign keys only when this is on (per connection)

-- ---------------------------------------------------------------------
-- domain: the sheet's "Domain" column, as a list of six values.
-- TBX: subjectField (except "expressions", exported as termType "phrase").
-- ---------------------------------------------------------------------
CREATE TABLE domain (
  id       INTEGER PRIMARY KEY,
  code     TEXT NOT NULL UNIQUE,         -- stable name used in code and links, e.g. 'first_aid'
  name_en  TEXT NOT NULL,                -- display names in the three languages
  name_tr  TEXT NOT NULL,
  name_es  TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- entry: one meaning (one row of the sheet).
-- TBX: conceptEntry.
-- ---------------------------------------------------------------------
CREATE TABLE entry (
  id         INTEGER PRIMARY KEY,        -- the sheet's "Nr.": permanent, never reused or renumbered
  domain_id  INTEGER REFERENCES domain(id) ON DELETE RESTRICT  -- NULL when the sheet had no domain
);

CREATE INDEX entry_domain_id_idx ON entry(domain_id);  -- foreign keys are indexed

-- ---------------------------------------------------------------------
-- term: how one language says an entry, exactly as typed in the sheet.
-- One row per entry per language. A cell may hold several synonyms
-- separated by " / " (e.g. 'enkaz / moloz'): they are kept together, as
-- typed, until the team decides how to split them.
-- TBX: langSec + termSec.
-- ---------------------------------------------------------------------
CREATE TABLE term (
  id        INTEGER PRIMARY KEY,
  entry_id  INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
  lang      TEXT NOT NULL CHECK (lang IN ('en', 'tr', 'es')),
  text      TEXT NOT NULL CHECK (trim(text) <> ''),  -- no blank terms: an empty cell has no row
  UNIQUE (entry_id, lang)                             -- one cell per entry and language
);

-- ---------------------------------------------------------------------
-- definition: what an entry means, in one language, with its source.
-- TBX: descrip type="definition" (+ source).
-- ---------------------------------------------------------------------
CREATE TABLE definition (
  id        INTEGER PRIMARY KEY,
  entry_id  INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
  lang      TEXT NOT NULL CHECK (lang IN ('en', 'tr', 'es')),
  text      TEXT NOT NULL CHECK (trim(text) <> ''),
  source    TEXT,                                     -- as typed in the sheet, e.g. 'TDK'; NULL if none
  UNIQUE (entry_id, lang)                             -- at most one definition per entry and language
);

-- ---------------------------------------------------------------------
-- entry_overview: the database read back as the sheet looked
-- (one row per entry, one column per language). A view stores nothing:
-- it is a saved query that runs every time it is opened.
-- ---------------------------------------------------------------------
CREATE VIEW entry_overview AS
SELECT e.id,
       d.name_en AS domain,
       en.text   AS en,
       tr.text   AS tr,
       es.text   AS es,
       df.text   AS definition_tr
FROM entry e
LEFT JOIN domain d      ON d.id = e.domain_id
LEFT JOIN term en       ON en.entry_id = e.id AND en.lang = 'en'
LEFT JOIN term tr       ON tr.entry_id = e.id AND tr.lang = 'tr'
LEFT JOIN term es       ON es.entry_id = e.id AND es.lang = 'es'
LEFT JOIN definition df ON df.entry_id = e.id AND df.lang = 'tr';

PRAGMA user_version = 2;  -- schema version, checked by the tools
