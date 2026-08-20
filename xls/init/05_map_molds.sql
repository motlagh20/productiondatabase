-- Map Molds.csv to app.molds table
-- CSV Columns: MoldID, MoldsName, Unnamed: 2
-- Table Columns: mold_id, mold_code, mold_name, category_id, width, length, height, pieces_per_press, is_active

-- Note: For molds, we need to assign a category_id. Since this information is not in the CSV,
-- we'll use a placeholder value of 1 (assuming the first category exists).
-- You may need to adjust the category_id values based on your actual data.

INSERT INTO app.molds (mold_id, mold_code, mold_name, category_id, is_active) VALUES
(91000000, '91000000', 'طبرستان', 1, TRUE),
(92000000, '92000000', 'پرتغالی', 1, TRUE),
(81000000, '81000000', '20*10*20', 1, TRUE)
ON CONFLICT (mold_id) DO UPDATE SET
  mold_code = EXCLUDED.mold_code,
  mold_name = EXCLUDED.mold_name,
  category_id = EXCLUDED.category_id,
  is_active = EXCLUDED.is_active;