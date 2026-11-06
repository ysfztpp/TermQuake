-- How complete is each language? (share of entries that have a term)
-- LEFT JOIN keeps languages that have no term yet (they show 0).
SELECT l.code,
       l.name_en,
       COUNT(t.id) AS entries_with_a_term,
       (SELECT COUNT(*) FROM entry) AS all_entries,
       ROUND(100.0 * COUNT(t.id) / (SELECT COUNT(*) FROM entry), 1) AS percent
FROM language l
LEFT JOIN term t ON t.lang = l.code
GROUP BY l.id
ORDER BY percent DESC, l.id;
