BEGIN;

ALTER TABLE searches
  ADD language VARCHAR(5);
  
UPDATE searches
  SET language = 'sv'
  WHERE language IS NULL or language = '';
  

COMMIT;

