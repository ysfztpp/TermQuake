# Example queries

Short, commented SQL queries for learning the database and for everyday checks.
They run against `build/termquake.db` (run `termquake build` first) or the
`termquake.db` file from the website's downloads.

**DB Browser for SQLite:** open the database, go to the *Execute SQL* tab, paste a
query and press ▶ (or Ctrl/Cmd+Enter).
**Command line:** `sqlite3 build/termquake.db < queries/03_coverage.sql`

| File | What it shows | SQL ideas |
|---|---|---|
| `01_tables.sql` | How many rows each table has | `COUNT`, `UNION ALL` |
| `02_one_entry.sql` | Everything about one entry | `JOIN` |
| `03_coverage.sql` | How complete each language is | `GROUP BY`, percentages |
| `04_missing_spanish.sql` | Entries with no Spanish term yet | `NOT EXISTS` |
| `05_search.sql` | Find a word in any language | `LIKE`, `lower()` |
| `06_by_domain.sql` | How many entries each domain has | `LEFT JOIN`, `GROUP BY` |
| `07_same_term_twice.sql` | The same term used for two entries | `GROUP BY ... HAVING` |
| `08_several_terms_in_one_cell.sql` | Cells holding synonyms (`a / b`) | `LIKE` |
| `09_extra_spaces.sql` | Cells with a space at the start or end | `trim()` |
| `10_change_data.sql` | How to add, fix and remove a term | `INSERT`, `UPDATE`, `DELETE` |

Changes made with queries like `10_change_data.sql` are saved to the
repository with `termquake dump` (see CONTRIBUTING.md).
