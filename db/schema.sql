-- =====================================================================
-- TermQuake database schema (SQLite), version 3
--
-- Five tables, one idea: an ENTRY is one meaning, and each language says it
-- with a TERM. This is the concept-oriented model that professional
-- termbases use (ISO 16642; TBX, ISO 30042), reduced to what the project
-- needs: the 31 language columns of the original sheet, as typed.
--
--   domain   1 ──< entry 1 ──< term         (one row per entry per language)
--                        1 ──< definition   (one row per entry per language)
--   language 1 ──< term, definition         (which language a text is in)
--
-- Conventions: singular snake_case table names; every table has an integer
-- `id` primary key; a column that points to another table is called
-- <table>_id and is a foreign key; languages use BCP 47 codes.
-- =====================================================================

PRAGMA foreign_keys = ON;  -- SQLite checks foreign keys only when this is on (per connection)

-- ---------------------------------------------------------------------
-- language: the languages of the termbase, in display order (the sheet's
-- column order). `code` is a BCP 47 language tag (the standard used by
-- browsers, TBX and xml:lang), e.g. 'tr', 'kmr' (Kurmanji Kurdish),
-- 'zh-Hans' (Chinese in simplified characters).
-- To add a language: add a row here, then add its line to entry_overview below.
-- ---------------------------------------------------------------------
CREATE TABLE language (
  id           INTEGER PRIMARY KEY,           -- display order
  code         TEXT NOT NULL UNIQUE,          -- BCP 47 tag, used by term.lang and definition.lang
  name_en      TEXT NOT NULL,                 -- English name, e.g. 'Turkish'
  name_native  TEXT NOT NULL,                 -- the language's own name, e.g. 'Türkçe'
  direction    TEXT NOT NULL DEFAULT 'ltr' CHECK (direction IN ('ltr', 'rtl'))  -- writing direction
);

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
  lang      TEXT NOT NULL REFERENCES language(code) ON DELETE RESTRICT,
  text      TEXT NOT NULL CHECK (trim(text) <> ''),  -- no blank terms: an empty cell has no row
  UNIQUE (entry_id, lang)                             -- one cell per entry and language
);

CREATE INDEX term_lang_idx ON term(lang);

-- ---------------------------------------------------------------------
-- definition: what an entry means, in one language, with its source.
-- TBX: descrip type="definition" (+ source).
-- ---------------------------------------------------------------------
CREATE TABLE definition (
  id        INTEGER PRIMARY KEY,
  entry_id  INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
  lang      TEXT NOT NULL REFERENCES language(code) ON DELETE RESTRICT,
  text      TEXT NOT NULL CHECK (trim(text) <> ''),
  source    TEXT,                                     -- as typed in the sheet, e.g. 'TDK'; NULL if none
  UNIQUE (entry_id, lang)                             -- at most one definition per entry and language
);

-- ---------------------------------------------------------------------
-- entry_overview: the database read back as the sheet looked
-- (one row per entry, one column per language). A view stores nothing:
-- it is a saved query that runs every time it is opened.
-- Each language column picks that language's term from the entry's rows
-- (MAX(CASE ...) with GROUP BY turns rows into columns).
-- ---------------------------------------------------------------------
CREATE VIEW entry_overview AS
SELECT e.id,
       d.name_en AS domain,
       MAX(CASE WHEN t.lang = 'en' THEN t.text END) AS "en",
       MAX(CASE WHEN t.lang = 'tr' THEN t.text END) AS "tr",
       MAX(CASE WHEN t.lang = 'es' THEN t.text END) AS "es",
       MAX(CASE WHEN t.lang = 'de' THEN t.text END) AS "de",
       MAX(CASE WHEN t.lang = 'ru' THEN t.text END) AS "ru",
       MAX(CASE WHEN t.lang = 'fr' THEN t.text END) AS "fr",
       MAX(CASE WHEN t.lang = 'kmr' THEN t.text END) AS "kmr",
       MAX(CASE WHEN t.lang = 'zza' THEN t.text END) AS "zza",
       MAX(CASE WHEN t.lang = 'ar' THEN t.text END) AS "ar",
       MAX(CASE WHEN t.lang = 'el' THEN t.text END) AS "el",
       MAX(CASE WHEN t.lang = 'ja' THEN t.text END) AS "ja",
       MAX(CASE WHEN t.lang = 'he' THEN t.text END) AS "he",
       MAX(CASE WHEN t.lang = 'it' THEN t.text END) AS "it",
       MAX(CASE WHEN t.lang = 'hy' THEN t.text END) AS "hy",
       MAX(CASE WHEN t.lang = 'nl' THEN t.text END) AS "nl",
       MAX(CASE WHEN t.lang = 'zh-Hans' THEN t.text END) AS "zh-Hans",
       MAX(CASE WHEN t.lang = 'zh-Hant' THEN t.text END) AS "zh-Hant",
       MAX(CASE WHEN t.lang = 'bg' THEN t.text END) AS "bg",
       MAX(CASE WHEN t.lang = 'ko' THEN t.text END) AS "ko",
       MAX(CASE WHEN t.lang = 'fa' THEN t.text END) AS "fa",
       MAX(CASE WHEN t.lang = 'hi' THEN t.text END) AS "hi",
       MAX(CASE WHEN t.lang = 'pt' THEN t.text END) AS "pt",
       MAX(CASE WHEN t.lang = 'sv' THEN t.text END) AS "sv",
       MAX(CASE WHEN t.lang = 'ro' THEN t.text END) AS "ro",
       MAX(CASE WHEN t.lang = 'sr' THEN t.text END) AS "sr",
       MAX(CASE WHEN t.lang = 'mk' THEN t.text END) AS "mk",
       MAX(CASE WHEN t.lang = 'hu' THEN t.text END) AS "hu",
       MAX(CASE WHEN t.lang = 'fi' THEN t.text END) AS "fi",
       MAX(CASE WHEN t.lang = 'sq' THEN t.text END) AS "sq",
       MAX(CASE WHEN t.lang = 'cs' THEN t.text END) AS "cs",
       MAX(CASE WHEN t.lang = 'pl' THEN t.text END) AS "pl",
       (SELECT text FROM definition df WHERE df.entry_id = e.id AND df.lang = 'tr') AS definition_tr
FROM entry e
LEFT JOIN domain d ON d.id = e.domain_id
LEFT JOIN term t   ON t.entry_id = e.id
GROUP BY e.id;

PRAGMA user_version = 3;  -- schema version, checked by the tools
