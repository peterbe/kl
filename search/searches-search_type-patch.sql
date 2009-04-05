BEGIN;

ALTER TABLE searches
  ADD search_type VARCHAR(50);

ALTER TABLE searches
  ALTER search_type SET DEFAULT '';

UPDATE searches
  SET search_type = ''
  WHERE search_type IS NULL;

ALTER TABLE searches
  ALTER search_type SET NOT NULL;

COMMIT;
