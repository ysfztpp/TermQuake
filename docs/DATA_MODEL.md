# Data model

The database has **five tables** and follows one idea used by every
professional termbase (ISO 16642, TBX): an **entry** is one meaning, and each
language says it with a **term**.

```mermaid
erDiagram
    domain   ||--o{ entry : "groups"
    entry    ||--o{ term : "is said with"
    entry    ||--o{ definition : "is explained by"
    language ||--o{ term : "is written in"
    language ||--o{ definition : "is written in"

    language {
        INTEGER id PK "display order"
        TEXT code UK "BCP 47, e.g. tr, kmr, zh-Hans"
        TEXT name_en
        TEXT name_native
        TEXT direction "ltr or rtl"
    }

    domain {
        INTEGER id PK
        TEXT code UK "e.g. first_aid"
        TEXT name_en
        TEXT name_tr
        TEXT name_es
    }
    entry {
        INTEGER id PK "the sheet's Nr."
        INTEGER domain_id FK "may be empty"
    }
    term {
        INTEGER id PK
        INTEGER entry_id FK
        TEXT lang FK "language.code"
        TEXT text "as typed in the sheet"
    }
    definition {
        INTEGER id PK
        INTEGER entry_id FK
        TEXT lang FK "language.code"
        TEXT text
        TEXT source "e.g. TDK"
    }
```

The full definitions, with comments, are in [`db/schema.sql`](../db/schema.sql).

## The tables

| Table | One row is | Rows today | Columns |
|---|---|---:|---|
| `language` | a language of the termbase (a language column of the sheet) | 31 | `id`, `code`, `name_en`, `name_native`, `direction` |
| `domain` | a value of the sheet's Domain column | 6 | `id`, `code`, `name_en`, `name_tr`, `name_es` |
| `entry` | one meaning (one row of the sheet) | 523 | `id` (the sheet's Nr.), `domain_id` |
| `term` | what one language calls an entry (one cell of the sheet) | 12,415 | `id`, `entry_id`, `lang`, `text` |
| `definition` | what an entry means in one language | 14 | `id`, `entry_id`, `lang`, `text`, `source` |

Plus one **view**, `entry_overview`: a saved query that shows the data the way
the sheet did, one row per entry with one column per language (`en`, `tr`, `es`, `de`, ...). A view stores
nothing; it is computed each time it is opened.

### Why split the sheet into tables?

The sheet had one row per meaning and one column per language. As tables:

- `entry` holds what is true of the meaning in every language (its number, its domain);
- `term` holds what differs per language (the words).

This is **normalisation**: each fact is stored once. A new language needs new
rows, not a new column, and "every Spanish term" is one simple query.

### Example: entry 5

```sql
SELECT lang, text FROM term WHERE entry_id = 5;
```

| lang | text |
|---|---|
| en | debris / rubble |
| tr | enkaz / moloz |
| es | escombros |
| de | Trümmer / Schutt |
| ... | (one row per language that has a term) |

The same rows in the file git stores (`data/db/term.sql`), one line per row:

```sql
INSERT INTO term (id, entry_id, lang, text) VALUES (13, 5, 'en', 'debris / rubble');
INSERT INTO term (id, entry_id, lang, text) VALUES (14, 5, 'tr', 'enkaz / moloz');
INSERT INTO term (id, entry_id, lang, text) VALUES (15, 5, 'es', 'escombros');
```

## The rules the database enforces

These make it a database rather than a spreadsheet: wrong data is refused
when someone tries to save it.

| Rule | SQL | What it prevents |
|---|---|---|
| Every row has a unique number | `id INTEGER PRIMARY KEY` | two rows that cannot be told apart |
| A term belongs to an entry that exists | `REFERENCES entry(id)` (foreign key) | orphan terms |
| A term has a language and a text | `NOT NULL`, `CHECK (trim(text) <> '')` | blank cells saved as terms |
| Only languages in the `language` table | `lang REFERENCES language(code)` | typos such as `'TR'` or `'tur'` |
| A language in use cannot be deleted | `ON DELETE RESTRICT` | terms in a language that no longer exists |
| Writing direction is left-to-right or right-to-left | `CHECK (direction IN ('ltr', 'rtl'))` | values the website cannot use |
| One cell per entry and language | `UNIQUE (entry_id, lang)` | the same cell entered twice |
| A domain in use cannot be deleted | `ON DELETE RESTRICT` | entries pointing to nothing |
| Deleting an entry deletes its terms | `ON DELETE CASCADE` | leftover terms of a removed entry |

SQLite checks foreign keys only when `PRAGMA foreign_keys = ON`. The
`termquake` tools always switch it on; DB Browser for SQLite does too by default.

## Conventions (industry practice)

- Table names are singular and in snake_case: `term`, not `Terms`.
- Every table has an integer primary key called `id`.
- A column that points to another table is named `<table>_id` and is a foreign key.
- Foreign keys have an index (`entry_domain_id_idx`, `term_lang_idx`); `UNIQUE` constraints create their own.
- Languages use BCP 47 codes: `en`, `tr`, `kmr` (Kurmanji Kurdish), `zh-Hans` (simplified Chinese).
- The schema has a version number (`PRAGMA user_version = 3`), raised whenever the tables change.
- Every column has a comment in `db/schema.sql` saying what it holds.

## The data: as typed, mechanically cleaned

The data was imported from the sheet exactly as typed ([ADR 0010](adr/0010-four-tables-raw-data.md),
[0011](adr/0011-all-languages-language-table.md)); only spreadsheet placeholders
(`#empty1`–`#empty3`, the Persian `#خالی1`–`#خالی3`, French `#N/A`) were left out.

Then one clean-up step was applied ([ADR 0012](adr/0012-mechanical-cleanup.md)):
spaces at the start and end, line breaks, double and no-break spaces, invisible
characters, the Turkish "i̇" and the Unicode form. It changes how text is stored,
never the words: a cell with several synonyms, such as `enkaz / moloz`, is still
one term row. `termquake clean --check` makes sure every later edit follows
the same rules.

[`data/legacy/IMPORT_REPORT.md`](../data/legacy/IMPORT_REPORT.md) lists what the
import noticed, and the queries in [`queries/`](../queries/) find what is left
to decide. Each further clean-up step is the team's decision, made in the
database and reviewed in git.

## Mapping to TBX (the ISO exchange format)

TBX-Basic requires only two things in an entry: the term and its language;
the rest is recommended. The download `termquake.tbx` maps as follows:

| TBX | TermQuake |
|---|---|
| `conceptEntry` | `entry` (id `tq5` for entry 5) |
| `descrip type="subjectField"` | `domain.name_en` |
| `langSec xml:lang` | `term.lang` |
| `termSec / term` | `term.text` |
| `descrip type="definition"` + `admin type="source"` | `definition.text`, `definition.source` |
| `termNote type="termType"` = `phrase` | entries in the Expressions domain |

TBX defines files for exchanging terminology, not how a database must be laid
out inside, so a small database is fully compatible with it.

## What is deliberately not in the database (yet)

| Not here | Why | When it comes back |
|---|---|---|
| A change-history table | git already records every change, by whom and why | not needed |
| Votes, contributors | there is no editing website; changes go through GitHub | if an editing website is built |
| Who wrote a term (`origin`) and its review status | every term comes from the sheet | before AI-generated terms are added (roadmap phase 3) |
| Part of speech, gender, usage status | nobody fills them yet | when the team standardises entries |
