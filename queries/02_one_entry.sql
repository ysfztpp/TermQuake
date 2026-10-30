-- Everything about entry 5: its domain, its terms and its definitions.
-- JOIN follows the links between tables: term.entry_id -> entry.id -> domain.id.
SELECT e.id      AS entry,
       d.name_en AS domain,
       t.lang,
       t.text    AS term
FROM entry e
LEFT JOIN domain d ON d.id = e.domain_id
JOIN term t        ON t.entry_id = e.id
WHERE e.id = 5
ORDER BY t.lang;

-- Its definitions (entry 5 has none yet; try 35):
SELECT lang, text, source FROM definition WHERE entry_id = 5;
