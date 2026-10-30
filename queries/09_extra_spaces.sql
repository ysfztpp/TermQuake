-- Cells with a space at the start or the end (invisible in the sheet, kept as typed).
-- The quotes in the second column show where the spaces are.
SELECT entry_id, lang, '"' || text || '"' AS text_with_quotes
FROM term
WHERE text <> trim(text)
ORDER BY lang, entry_id;
