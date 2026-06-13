-- Map Categories.csv to app.categories table
-- CSV Columns: ProductCategoriesID, ProductCategories
-- Table Columns: category_id, category_code, category_name, description, is_active, created_at

INSERT INTO app.categories (category_id, category_code, category_name, description, is_active) VALUES
(1, '1', 'سفال', '', TRUE),
(2, '2', 'تیزه', '', TRUE),
(3, '3', 'پنجه ای', '', TRUE),
(4, '4', 'نیمه', '', TRUE),
(5, '5', 'آجر', '', TRUE)
ON CONFLICT (category_id) DO UPDATE SET
  category_code = EXCLUDED.category_code,
  category_name = EXCLUDED.category_name,
  description = EXCLUDED.description,
  is_active = EXCLUDED.is_active;