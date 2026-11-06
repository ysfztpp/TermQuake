-- How many rows does each table have?
SELECT 'language' AS "table", COUNT(*) AS "rows" FROM language
UNION ALL SELECT 'domain',     COUNT(*) FROM domain
UNION ALL SELECT 'entry',      COUNT(*) FROM entry
UNION ALL SELECT 'term',       COUNT(*) FROM term
UNION ALL SELECT 'definition', COUNT(*) FROM definition;
