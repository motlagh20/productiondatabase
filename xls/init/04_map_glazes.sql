-- Map Glaze.csv to app.glazes table
-- CSV Columns: TypeID, TypeName, Unnamed: 2
-- Table Columns: glaze_id, glaze_code, glaze_name, is_self_colored, is_active

INSERT INTO app.glazes (glaze_id, glaze_code, glaze_name, is_self_colored, is_active) VALUES
(91000001, '91000001', 'خودرنگ', TRUE, TRUE),
(91000002, '91000002', 'اخرا', FALSE, TRUE),
(91000003, '91000003', 'سبز', FALSE, TRUE),
(91000004, '91000004', 'نوک مدادی', FALSE, TRUE),
(91000005, '91000005', 'بیرنگ', FALSE, TRUE),
(91000006, '91000006', 'مشکی', FALSE, TRUE),
(91000007, '91000007', 'مولتی مشکی', FALSE, TRUE),
(91000008, '91000008', 'لعاب آزمایشی', FALSE, TRUE),
(92000001, '92000001', 'خودرنگ', TRUE, TRUE),
(92000002, '92000002', 'اخرا', FALSE, TRUE),
(92000003, '92000003', 'سبز', FALSE, TRUE),
(92000004, '92000004', 'نوک مدادی', FALSE, TRUE),
(92000005, '92000005', 'بیرنگ', FALSE, TRUE),
(92000006, '92000006', 'مشکی', FALSE, TRUE),
(92000007, '92000007', 'مولتی مشکی', FALSE, TRUE),
(92000008, '92000008', 'لعاب آزمایشی', FALSE, TRUE),
(93000001, '93000001', 'خودرنگ', TRUE, TRUE),
(93000002, '93000002', 'اخرا', FALSE, TRUE),
(93000003, '93000003', 'سبز', FALSE, TRUE),
(93000004, '93000004', 'نوک مدادی', FALSE, TRUE),
(93000005, '93000005', 'بیرنگ', FALSE, TRUE),
(93000006, '93000006', 'مشکی', FALSE, TRUE),
(93000007, '93000007', 'مولتی مشکی', FALSE, TRUE),
(93000008, '93000008', 'لعاب آزمایشی', FALSE, TRUE)
ON CONFLICT (glaze_id) DO UPDATE SET
  glaze_code = EXCLUDED.glaze_code,
  glaze_name = EXCLUDED.glaze_name,
  is_self_colored = EXCLUDED.is_self_colored,
  is_active = EXCLUDED.is_active;