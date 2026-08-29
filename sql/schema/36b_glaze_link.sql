-- 36b_glaze_link.sql
-- Link setting_wagon.glaze_type (legacy free text) to the clean glaze master.
-- Per ADR-0008: clean app core references glaze by FK; historical typos stay in
-- the raw text and are logged for review, they are NOT force-inserted into the master.

-- 1) add FK column
ALTER TABLE setting_wagon ADD COLUMN IF NOT EXISTS glaze_id BIGINT;
ALTER TABLE setting_wagon
  ADD CONSTRAINT fk_setting_wagon_glaze FOREIGN KEY (glaze_id) REFERENCES glaze(glaze_id);

-- 2) mapping from observed raw vocab -> seeded glaze_code
CREATE TEMP TABLE glaze_map_raw (raw TEXT, code VARCHAR(20));
INSERT INTO glaze_map_raw VALUES
  ('خودرنگ','KHODRANG'), ('لعاب','LAAB'), ('اخرا','AKHRA'), ('اخراء','AKHRA'),
  ('لعاب اخرا','AKHRA'), ('لعاب سبز','LAAB_SABZ'), ('لعاب مشکی','LAAB_MESHKI'),
  ('مولتی مشکی','MULTI_MESHKI'), ('کلاهک','KOLAHK');

-- 3) populate glaze_id where a clean mapping exists
UPDATE setting_wagon sw
SET glaze_id = g.glaze_id
FROM glaze_map_raw m
JOIN glaze g ON g.glaze_code = m.code
WHERE sw.glaze_type = m.raw AND sw.glaze_id IS NULL;

-- 4) report unmapped (typos) — left for ETL review layer, kept in raw glaze_type
-- SELECT DISTINCT glaze_type FROM setting_wagon WHERE glaze_id IS NULL;
