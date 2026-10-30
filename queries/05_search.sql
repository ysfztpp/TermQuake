-- Find a word in any language. % means "anything here".
-- Note: SQLite's lower() only changes A-Z, so for Turkish letters (İ, Ş, Ç...)
-- type the word as it is written in the data. The website's search handles
-- accents and Turkish letters for you.
SELECT t.entry_id, t.lang, t.text
FROM term t
WHERE lower(t.text) LIKE '%rescue%'
ORDER BY t.entry_id, t.lang;
