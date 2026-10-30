-- Cells that hold several synonyms written together, e.g. 'enkaz / moloz'.
-- They were kept exactly as typed in the sheet.
SELECT entry_id, lang, text
FROM term
WHERE text LIKE '% / %'
ORDER BY lang, entry_id;
