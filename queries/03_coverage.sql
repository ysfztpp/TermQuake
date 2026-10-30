-- How complete is each language? (share of entries that have a term)
SELECT lang,
       COUNT(*) AS entries_with_a_term,
       (SELECT COUNT(*) FROM entry) AS all_entries,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM entry), 1) AS percent
FROM term
GROUP BY lang
ORDER BY percent DESC;
