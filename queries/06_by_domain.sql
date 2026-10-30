-- How many entries does each domain have? Entries without a domain show as NULL.
SELECT d.name_en AS domain, COUNT(e.id) AS entries
FROM entry e
LEFT JOIN domain d ON d.id = e.domain_id
GROUP BY d.id
ORDER BY entries DESC;
