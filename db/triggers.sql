-- =====================================================================
-- TermQuake — row-level change history (SQLite)
-- Installed AFTER data/db is loaded, so a rebuild never logs the load itself
-- as edits. Every later change to a term or definition (SQL, a script, a
-- database GUI) is recorded in the revision table with old and new values,
-- and saved together with the data by `termquake dump`.
-- Postgres (phase 2): replace with plpgsql triggers or an audit extension.
-- =====================================================================

CREATE TRIGGER trg_term_insert AFTER INSERT ON term BEGIN
  INSERT INTO revision(entity_type, entity_id, action, new_values, actor_id)
  VALUES ('term', NEW.id, 'insert',
          json_object('concept_id',NEW.concept_id,'lang',NEW.lang,'text',NEW.text,
                      'usage_status',NEW.usage_status,'review_status',NEW.review_status,
                      'origin',NEW.origin),
          NEW.created_by);
END;

CREATE TRIGGER trg_term_update AFTER UPDATE ON term
WHEN OLD.text IS NOT NEW.text OR OLD.usage_status IS NOT NEW.usage_status
  OR OLD.review_status IS NOT NEW.review_status OR OLD.term_type IS NOT NEW.term_type
  OR OLD.part_of_speech IS NOT NEW.part_of_speech OR OLD.note IS NOT NEW.note
BEGIN
  INSERT INTO revision(entity_type, entity_id, action, old_values, new_values, actor_id)
  VALUES ('term', NEW.id, 'update',
          json_object('text',OLD.text,'usage_status',OLD.usage_status,'review_status',OLD.review_status,
                      'term_type',OLD.term_type,'part_of_speech',OLD.part_of_speech,'note',OLD.note),
          json_object('text',NEW.text,'usage_status',NEW.usage_status,'review_status',NEW.review_status,
                      'term_type',NEW.term_type,'part_of_speech',NEW.part_of_speech,'note',NEW.note),
          NEW.updated_by);
END;

CREATE TRIGGER trg_term_delete AFTER DELETE ON term BEGIN
  INSERT INTO revision(entity_type, entity_id, action, old_values)
  VALUES ('term', OLD.id, 'delete',
          json_object('concept_id',OLD.concept_id,'lang',OLD.lang,'text',OLD.text));
END;

CREATE TRIGGER trg_definition_insert AFTER INSERT ON definition BEGIN
  INSERT INTO revision(entity_type, entity_id, action, new_values, actor_id)
  VALUES ('definition', NEW.id, 'insert',
          json_object('concept_id',NEW.concept_id,'lang',NEW.lang,'text',NEW.text,
                      'review_status',NEW.review_status,'origin',NEW.origin),
          NEW.updated_by);
END;

CREATE TRIGGER trg_definition_update AFTER UPDATE ON definition
WHEN OLD.text IS NOT NEW.text OR OLD.review_status IS NOT NEW.review_status
BEGIN
  INSERT INTO revision(entity_type, entity_id, action, old_values, new_values, actor_id)
  VALUES ('definition', NEW.id, 'update',
          json_object('text',OLD.text,'review_status',OLD.review_status),
          json_object('text',NEW.text,'review_status',NEW.review_status),
          NEW.updated_by);
END;

CREATE TRIGGER trg_definition_delete AFTER DELETE ON definition BEGIN
  INSERT INTO revision(entity_type, entity_id, action, old_values)
  VALUES ('definition', OLD.id, 'delete',
          json_object('concept_id',OLD.concept_id,'lang',OLD.lang,'text',OLD.text));
END;

-- Keep updated_at current on every edit. These do not create revision rows:
-- the revision triggers above only fire when content columns change.
CREATE TRIGGER trg_term_touch AFTER UPDATE ON term
WHEN NEW.updated_at IS OLD.updated_at
BEGIN
  UPDATE term SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER trg_definition_touch AFTER UPDATE ON definition
WHEN NEW.updated_at IS OLD.updated_at
BEGIN
  UPDATE definition SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER trg_concept_touch AFTER UPDATE ON concept
WHEN NEW.updated_at IS OLD.updated_at
BEGIN
  UPDATE concept SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
