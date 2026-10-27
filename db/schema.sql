-- =====================================================================
-- TermQuake termbase — schema v1 (PRAGMA user_version = 1)
-- Model: concept-oriented, following ISO 16642 (TMF) and TBX-Basic v4
--        (ISO 30042) data categories:
--          concept (conceptEntry) → language (langSec) → term (termSec)
-- Dialect: SQLite 3.38+ (pilot). Written to port 1:1 to PostgreSQL:
--   INTEGER PRIMARY KEY → bigint GENERATED ALWAYS AS IDENTITY
--   TEXT timestamps     → timestamptz;  json TEXT → jsonb
--   triggers at bottom  → rewritten as plpgsql (or Supabase audit)
-- =====================================================================
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- 1. Reference tables
-- ---------------------------------------------------------------------
CREATE TABLE language (
  code         TEXT PRIMARY KEY,              -- BCP 47: 'tr','en','kmr','zh-Hans','sr-Cyrl'
  name_en      TEXT NOT NULL,
  name_native  TEXT NOT NULL,
  script       TEXT,                          -- ISO 15924: Latn, Arab, Cyrl, Hans ...
  direction    TEXT NOT NULL DEFAULT 'ltr' CHECK (direction IN ('ltr','rtl')),
  is_active    INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
  sort_order   INTEGER NOT NULL DEFAULT 100
);

CREATE TABLE domain (                         -- TBX: subjectField
  id         INTEGER PRIMARY KEY,
  code       TEXT NOT NULL UNIQUE,            -- 'search_rescue','first_aid',...
  parent_id  INTEGER REFERENCES domain(id)
);

CREATE TABLE domain_label (
  domain_id  INTEGER NOT NULL REFERENCES domain(id) ON DELETE CASCADE,
  lang       TEXT NOT NULL REFERENCES language(code),
  label      TEXT NOT NULL,
  PRIMARY KEY (domain_id, lang)
);

CREATE TABLE source (                         -- TBX: source / sourceOfDefinition
  id          INTEGER PRIMARY KEY,
  short_name  TEXT NOT NULL UNIQUE,           -- 'TDK','AFAD','IATE','WHO'...
  title       TEXT,
  url         TEXT,
  license     TEXT
);

CREATE TABLE contributor (
  id            INTEGER PRIMARY KEY,
  display_name  TEXT NOT NULL,
  email         TEXT UNIQUE,                  -- private; never exported
  role          TEXT NOT NULL DEFAULT 'translator'
                CHECK (role IN ('admin','validator','translator','viewer','bot')),
  created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- 2. Core termbase (TBX-Basic levels)
-- ---------------------------------------------------------------------
CREATE TABLE concept (                        -- TBX: conceptEntry
  id           INTEGER PRIMARY KEY,
  legacy_nr    INTEGER UNIQUE,                -- "Nr." column of the Google Sheet
  domain_id    INTEGER REFERENCES domain(id),
  entry_type   TEXT NOT NULL DEFAULT 'term'
               CHECK (entry_type IN ('term','phrase')),   -- phrase = "İfadeler / Expressions"
  status       TEXT NOT NULL DEFAULT 'active'
               CHECK (status IN ('candidate','active','deprecated','merged')),
  merged_into  INTEGER REFERENCES concept(id),
  priority     TEXT CHECK (priority IN ('primary','secondary')),
  note         TEXT,                          -- internal editorial note
  created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (status <> 'merged' OR merged_into IS NOT NULL)
);

CREATE TABLE definition (                     -- TBX: definition (langSec level)
  id            INTEGER PRIMARY KEY,
  concept_id    INTEGER NOT NULL REFERENCES concept(id) ON DELETE CASCADE,
  lang          TEXT NOT NULL REFERENCES language(code),
  text          TEXT NOT NULL,
  source_id     INTEGER REFERENCES source(id),
  review_status TEXT NOT NULL DEFAULT 'unreviewed'
                CHECK (review_status IN ('unreviewed','proposed','approved','rejected')),
  origin        TEXT NOT NULL DEFAULT 'human'
                CHECK (origin IN ('legacy_import','human','mt','llm')),
  updated_by    INTEGER REFERENCES contributor(id),
  created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (concept_id, lang)
);

CREATE TABLE term (                           -- TBX: termSec
  id                 INTEGER PRIMARY KEY,
  concept_id         INTEGER NOT NULL REFERENCES concept(id) ON DELETE CASCADE,
  lang               TEXT NOT NULL REFERENCES language(code),
  text               TEXT NOT NULL,           -- the term exactly as displayed
  text_norm          TEXT NOT NULL,           -- search key: locale-aware casefold + diacritic fold
  sort_order         INTEGER NOT NULL DEFAULT 0,   -- order of synonyms within a language
  -- TBX-Basic termNotes (picklists from TBX-Basic v4)
  term_type          TEXT CHECK (term_type IN
                       ('fullForm','acronym','abbreviation','shortForm','variant','phrase')),
  part_of_speech     TEXT CHECK (part_of_speech IN
                       ('noun','verb','adjective','adverb','properNoun','other')),
  grammatical_gender TEXT CHECK (grammatical_gender IN ('masculine','feminine','neuter','other')),
  usage_status       TEXT CHECK (usage_status IN ('preferred','admitted','deprecated')),
  geographical_usage TEXT,                    -- e.g. 'es-419', 'pt-BR'
  note               TEXT,                    -- user-facing note, e.g. disambiguator "(tool)"
  -- workflow & provenance (needed before any AI-generated content goes in)
  review_status      TEXT NOT NULL DEFAULT 'unreviewed'
                     CHECK (review_status IN ('unreviewed','proposed','approved','rejected')),
  origin             TEXT NOT NULL DEFAULT 'human'
                     CHECK (origin IN ('legacy_import','human','mt','llm')),
  origin_detail      TEXT,                    -- e.g. '{"model":"...","prompt":"v3"}'
  source_id          INTEGER REFERENCES source(id),
  created_by         INTEGER REFERENCES contributor(id),
  updated_by         INTEGER REFERENCES contributor(id),
  created_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (concept_id, lang, text)
);

CREATE TABLE context (                        -- TBX: context (example sentence)
  id         INTEGER PRIMARY KEY,
  term_id    INTEGER NOT NULL REFERENCES term(id) ON DELETE CASCADE,
  text       TEXT NOT NULL,
  source_id  INTEGER REFERENCES source(id)
);

CREATE TABLE figure (                         -- TBX: xGraphic (e.g. "angle grinder" image)
  id           INTEGER PRIMARY KEY,
  concept_id   INTEGER NOT NULL REFERENCES concept(id) ON DELETE CASCADE,
  uri          TEXT NOT NULL,
  caption      TEXT,
  license      TEXT,
  attribution  TEXT
);

CREATE TABLE concept_relation (               -- TBX: crossReference
  from_concept_id  INTEGER NOT NULL REFERENCES concept(id) ON DELETE CASCADE,
  to_concept_id    INTEGER NOT NULL REFERENCES concept(id) ON DELETE CASCADE,
  relation_type    TEXT NOT NULL
                   CHECK (relation_type IN ('see_also','broader','narrower','related')),
  PRIMARY KEY (from_concept_id, to_concept_id, relation_type),
  CHECK (from_concept_id <> to_concept_id)
);

-- ---------------------------------------------------------------------
-- 3. Crowdsourcing workflow (replaces "Source Term Selection" voting tab)
--    Rule from the paper: approve when SUM(vote) >= +2
-- ---------------------------------------------------------------------
CREATE TABLE review_vote (
  id              INTEGER PRIMARY KEY,
  target_type     TEXT NOT NULL CHECK (target_type IN ('concept','term','definition')),
  target_id       INTEGER NOT NULL,
  contributor_id  INTEGER NOT NULL REFERENCES contributor(id),
  vote            INTEGER NOT NULL CHECK (vote IN (-1, 1)),
  comment         TEXT,
  created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (target_type, target_id, contributor_id)
);

-- ---------------------------------------------------------------------
-- 4. Provenance, history, QA, releases
-- ---------------------------------------------------------------------
CREATE TABLE import_batch (
  id              INTEGER PRIMARY KEY,
  source_url      TEXT NOT NULL,
  fetched_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  script_version  TEXT NOT NULL,              -- git commit of the importer
  notes           TEXT
);

CREATE TABLE import_raw (                     -- lossless copy of every legacy cell
  batch_id     INTEGER NOT NULL REFERENCES import_batch(id) ON DELETE CASCADE,
  sheet        TEXT NOT NULL,
  row_number   INTEGER NOT NULL,
  column_name  TEXT NOT NULL,
  raw_value    TEXT NOT NULL,
  concept_id   INTEGER REFERENCES concept(id),
  PRIMARY KEY (batch_id, sheet, row_number, column_name)
);

CREATE TABLE qa_issue (                       -- review queue for messy legacy cells
  id           INTEGER PRIMARY KEY,
  entity_type  TEXT NOT NULL CHECK (entity_type IN ('concept','term','definition','row')),
  entity_id    INTEGER NOT NULL,
  severity     TEXT NOT NULL DEFAULT 'warning'
               CHECK (severity IN ('error','warning','info')),
  issue_type   TEXT NOT NULL,                 -- 'ambiguous_slash','dash_separator','missing_domain',
                                              -- 'duplicate_term','placeholder_value',... (see docs)
  lang         TEXT REFERENCES language(code),
  detail       TEXT,
  status       TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','resolved','wontfix')),
  created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_by  INTEGER REFERENCES contributor(id)
);

CREATE TABLE revision (                       -- row-level change history (filled by triggers)
  id           INTEGER PRIMARY KEY,
  entity_type  TEXT NOT NULL,
  entity_id    INTEGER NOT NULL,
  action       TEXT NOT NULL CHECK (action IN ('insert','update','delete')),
  old_values   TEXT,                          -- JSON
  new_values   TEXT,                          -- JSON
  actor_id     INTEGER REFERENCES contributor(id),
  created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE data_release (                   -- tagged dataset versions (git tag / Zenodo DOI)
  version      TEXT PRIMARY KEY,              -- semver: '1.0.0'
  released_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  git_commit   TEXT,
  doi          TEXT,
  notes        TEXT
);

-- ---------------------------------------------------------------------
-- 5. Indexes
-- ---------------------------------------------------------------------
CREATE INDEX idx_term_concept_lang ON term(concept_id, lang);
CREATE INDEX idx_term_lang_norm    ON term(lang, text_norm);
CREATE INDEX idx_concept_domain    ON concept(domain_id);
CREATE INDEX idx_vote_target       ON review_vote(target_type, target_id);
CREATE INDEX idx_revision_entity   ON revision(entity_type, entity_id);
CREATE INDEX idx_qa_open           ON qa_issue(status, issue_type);

-- ---------------------------------------------------------------------
-- 6. Views
-- ---------------------------------------------------------------------
-- Language completion (replaces the % row in the sheet)
CREATE VIEW v_language_completion AS
SELECT l.code, l.name_en,
       COUNT(DISTINCT t.concept_id)                                  AS concepts_covered,
       (SELECT COUNT(*) FROM concept WHERE status = 'active')        AS concepts_total,
       ROUND(100.0 * COUNT(DISTINCT t.concept_id) /
             NULLIF((SELECT COUNT(*) FROM concept WHERE status = 'active'), 0), 2) AS pct
FROM language l
LEFT JOIN term t    ON t.lang = l.code AND t.review_status <> 'rejected'
LEFT JOIN concept c ON c.id = t.concept_id AND c.status = 'active'
GROUP BY l.code, l.name_en;

-- Vote tally per target (approval threshold: score >= 2)
CREATE VIEW v_vote_tally AS
SELECT target_type, target_id,
       SUM(vote) AS score,
       SUM(vote = 1) AS approvals,
       SUM(vote = -1) AS rejections,
       CASE WHEN SUM(vote) >= 2 THEN 1 ELSE 0 END AS passes_threshold
FROM review_vote
GROUP BY target_type, target_id;
