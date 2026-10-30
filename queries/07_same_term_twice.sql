-- The same term (same language, same text, ignoring case and spaces around it)
-- used for more than one entry: possible duplicate entries to review.
SELECT lang,
       trim(lower(text)) AS term,
       COUNT(*) AS entries,
       group_concat(entry_id, ', ') AS entry_ids
FROM term
GROUP BY lang, trim(lower(text))
HAVING COUNT(*) > 1
ORDER BY lang, term;
