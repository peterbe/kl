BEGIN;

ALTER TABLE words
  ADD name BOOLEAN;

ALTER TABLE words
  ALTER name SET DEFAULT false;

UPDATE words
  SET name = false
  WHERE name IS NULL;

ALTER TABLE words
  ALTER name SET NOT NULL;

UPDATE words
  SET name = true
  WHERE part_of_speech = 'egennamn';

COMMIT;
