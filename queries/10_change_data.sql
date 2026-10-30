-- How to change the data. Run one statement at a time, check the result,
-- then save it to the repository with `termquake dump` and commit.

-- Add a Spanish term to entry 470 (an entry can have one term per language):
INSERT INTO term (entry_id, lang, text) VALUES (470, 'es', 'relleno');

-- Fix a term:
UPDATE term SET text = 'relleno compactado' WHERE entry_id = 470 AND lang = 'es';

-- Remove it again:
DELETE FROM term WHERE entry_id = 470 AND lang = 'es';

-- Add a definition with its source:
-- INSERT INTO definition (entry_id, lang, text, source)
-- VALUES (5, 'tr', 'Yıkılan yapılardan geriye kalan parçalar.', 'TDK');
