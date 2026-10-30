-- Entries that have no Spanish term yet, with their English and Turkish terms.
-- Change 'es' to 'en' or 'tr' to check another language.
SELECT e.id, en.text AS english, tr.text AS turkish
FROM entry e
LEFT JOIN term en ON en.entry_id = e.id AND en.lang = 'en'
LEFT JOIN term tr ON tr.entry_id = e.id AND tr.lang = 'tr'
WHERE NOT EXISTS (SELECT 1 FROM term t WHERE t.entry_id = e.id AND t.lang = 'es')
ORDER BY e.id;
