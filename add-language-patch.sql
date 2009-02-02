BEGIN;

ALTER TABLE words
  ADD language VARCHAR(5);
  
UPDATE words
  SET language = 'sv'
  WHERE language IS NULL or language = '';
  

COMMIT;

