-- =====================================================================
-- TermQuake database schema (SQLite), version 3
--
-- Five tables, one idea: an ENTRY is one meaning, and each language says it
-- with a TERM. This is the concept-oriented model that professional
-- termbases use (ISO 16642; TBX, ISO 30042), reduced to what the project
-- needs: the 31 language columns of the original sheet.
--
--   domain   1 ──< entry 1 ──< term         (one row per term; a language may have several)
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
-- term: how one language says an entry. One row per term: synonyms and
-- abbreviations are separate rows, ordered by sort_order (1 = main term).
-- Cells from the sheet that still hold several synonyms ('enkaz / moloz')
-- stay one row until the language's review decides how to split them.
-- origin says where a text came from (the sheet, the team, or an AI
-- suggestion); review_status says whether a person has checked it.
-- TBX: langSec + termSec (termType, note).
-- ---------------------------------------------------------------------
CREATE TABLE term (
  id            INTEGER PRIMARY KEY,
  entry_id      INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
  lang          TEXT NOT NULL REFERENCES language(code) ON DELETE RESTRICT,
  text          TEXT NOT NULL CHECK (trim(text) <> ''),    -- no blank terms
  sort_order    INTEGER NOT NULL DEFAULT 1 CHECK (sort_order >= 1),  -- 1 = main term, shown first
  term_type     TEXT NOT NULL DEFAULT 'fullForm'           -- TBX-Basic term types
                CHECK (term_type IN ('fullForm', 'abbreviation', 'acronym', 'shortForm', 'variant', 'phrase')),
  note          TEXT CHECK (note IS NULL OR trim(note) <> ''),  -- usage note, e.g. 'tool'
  origin        TEXT NOT NULL DEFAULT 'sheet'              -- where the text came from
                CHECK (origin IN ('sheet', 'team', 'ai')),
  review_status TEXT NOT NULL DEFAULT 'unreviewed'         -- has a person checked it in review?
                CHECK (review_status IN ('unreviewed', 'reviewed')),
  UNIQUE (entry_id, lang, text),                           -- no duplicate term in a language
  UNIQUE (entry_id, lang, sort_order)                      -- one position per term
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
-- Each language column joins that language's terms in order, main term
-- first, with ' / ' (group_concat with GROUP BY turns rows into columns).
-- ---------------------------------------------------------------------
CREATE VIEW entry_overview AS
SELECT e.id,
       d.name_en AS domain,
       group_concat(CASE WHEN t.lang = 'en' THEN t.text END, ' / ') AS "en",
       group_concat(CASE WHEN t.lang = 'tr' THEN t.text END, ' / ') AS "tr",
       group_concat(CASE WHEN t.lang = 'es' THEN t.text END, ' / ') AS "es",
       group_concat(CASE WHEN t.lang = 'de' THEN t.text END, ' / ') AS "de",
       group_concat(CASE WHEN t.lang = 'ru' THEN t.text END, ' / ') AS "ru",
       group_concat(CASE WHEN t.lang = 'fr' THEN t.text END, ' / ') AS "fr",
       group_concat(CASE WHEN t.lang = 'kmr' THEN t.text END, ' / ') AS "kmr",
       group_concat(CASE WHEN t.lang = 'zza' THEN t.text END, ' / ') AS "zza",
       group_concat(CASE WHEN t.lang = 'ar' THEN t.text END, ' / ') AS "ar",
       group_concat(CASE WHEN t.lang = 'el' THEN t.text END, ' / ') AS "el",
       group_concat(CASE WHEN t.lang = 'ja' THEN t.text END, ' / ') AS "ja",
       group_concat(CASE WHEN t.lang = 'he' THEN t.text END, ' / ') AS "he",
       group_concat(CASE WHEN t.lang = 'it' THEN t.text END, ' / ') AS "it",
       group_concat(CASE WHEN t.lang = 'hy' THEN t.text END, ' / ') AS "hy",
       group_concat(CASE WHEN t.lang = 'nl' THEN t.text END, ' / ') AS "nl",
       group_concat(CASE WHEN t.lang = 'zh-Hans' THEN t.text END, ' / ') AS "zh-Hans",
       group_concat(CASE WHEN t.lang = 'zh-Hant' THEN t.text END, ' / ') AS "zh-Hant",
       group_concat(CASE WHEN t.lang = 'bg' THEN t.text END, ' / ') AS "bg",
       group_concat(CASE WHEN t.lang = 'ko' THEN t.text END, ' / ') AS "ko",
       group_concat(CASE WHEN t.lang = 'fa' THEN t.text END, ' / ') AS "fa",
       group_concat(CASE WHEN t.lang = 'hi' THEN t.text END, ' / ') AS "hi",
       group_concat(CASE WHEN t.lang = 'pt' THEN t.text END, ' / ') AS "pt",
       group_concat(CASE WHEN t.lang = 'sv' THEN t.text END, ' / ') AS "sv",
       group_concat(CASE WHEN t.lang = 'ro' THEN t.text END, ' / ') AS "ro",
       group_concat(CASE WHEN t.lang = 'sr' THEN t.text END, ' / ') AS "sr",
       group_concat(CASE WHEN t.lang = 'mk' THEN t.text END, ' / ') AS "mk",
       group_concat(CASE WHEN t.lang = 'hu' THEN t.text END, ' / ') AS "hu",
       group_concat(CASE WHEN t.lang = 'fi' THEN t.text END, ' / ') AS "fi",
       group_concat(CASE WHEN t.lang = 'sq' THEN t.text END, ' / ') AS "sq",
       group_concat(CASE WHEN t.lang = 'cs' THEN t.text END, ' / ') AS "cs",
       group_concat(CASE WHEN t.lang = 'pl' THEN t.text END, ' / ') AS "pl",
       (SELECT text FROM definition df WHERE df.entry_id = e.id AND df.lang = 'tr') AS definition_tr
FROM entry e
LEFT JOIN domain d ON d.id = e.domain_id
LEFT JOIN (SELECT * FROM term ORDER BY entry_id, lang, sort_order) t ON t.entry_id = e.id
GROUP BY e.id;

PRAGMA user_version = 4;  -- schema version, checked by the tools
