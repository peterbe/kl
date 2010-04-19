BEGIN;
ALTER TABLE words ALTER definition DROP not null;
ALTER TABLE words ALTER definition SET DEFAULT null;
UPDATE words SET definition =NULL WHERE definition='';
COMMIT;