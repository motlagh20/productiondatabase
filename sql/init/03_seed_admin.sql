INSERT INTO app.roles (role_name, description)
VALUES ('Admin', 'System administrator')
ON CONFLICT (role_name) DO NOTHING;

INSERT INTO app.pages (page_key, page_name, page_title)
VALUES
  ('home','home','صفحه اصلی'),
  ('dryer_dashboard','dryer_dashboard','داشبورد خشک‌کن'),
  ('dryer_load','dryer_load','ثبت بارگیری خشک‌کن'),
  ('dryer_unload','dryer_unload','ثبت تخلیه خشک‌کن'),
  ('dryer_readings','dryer_readings','ثبت قرائت‌های خشک‌کن'),
  ('setting_entry','setting_entry','ثبت ستینگ'),
  ('setting_transactions','setting_transactions','تراکنش‌های ستینگ'),
  ('kiln_pushing','kiln_pushing','پوشینگ کوره'),
  ('admin_shifts','admin_shifts','تعریف شیفت‌ها'),
  ('admin_fuel','admin_fuel','تعریف سوخت‌ها'),
  ('admin_roles','admin_roles','تعریف نقش‌ها'),
  ('admin_users_roles','admin_users_roles','کاربران و نقش‌ها'),
  ('admin_access','admin_access','دسترسی صفحات'),
  ('admin_products','admin_products','مدیریت محصولات'),
  ('admin_categories','admin_categories','مدیریت دسته‌ها'),
  ('admin_product_categories','admin_product_categories','دسته‌بندی محصول'),
  ('admin_glazes','admin_glazes','تعریف لعاب‌ها'),
  ('admin_molds','admin_molds','تعریف قالب‌ها'),
  ('users','users','مدیریت کاربران'),
  ('login','login','ورود')
ON CONFLICT (page_key) DO NOTHING;

INSERT INTO app.users (username, full_name, password_hash, role_id, is_active)
SELECT 'admin','Administrator','$2b$12$KIXIDZrt6G8R1JywgnPuu.uFRlI2PlxFMCXARfG3hwlRf5s3QhC5K', role_id, TRUE
FROM app.roles WHERE role_name='Admin'
ON CONFLICT (username) DO NOTHING;

INSERT INTO app.user_credentials (user_id, password_hash, password_algorithm, must_change_password)
SELECT user_id, '$2b$12$KIXIDZrt6G8R1JywgnPuu.uFRlI2PlxFMCXARfG3hwlRf5s3QhC5K', 'bcrypt', TRUE
FROM app.users WHERE username='admin'
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO app.role_permissions (role_id, page_id, can_view, can_add, can_edit, can_delete)
SELECT r.role_id, p.page_id, TRUE, TRUE, TRUE, TRUE
FROM app.roles r CROSS JOIN app.pages p
WHERE r.role_name='Admin'
ON CONFLICT (role_id, page_id) DO NOTHING;

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

INSERT INTO app.molds (mold_id, mold_code, mold_name, category_id, is_active) VALUES
(91000000, '91000000', 'طبرستان', 1, TRUE),
(92000000, '92000000', 'پرتغالی', 1, TRUE),
(81000000, '81000000', '20*10*20', 1, TRUE)
ON CONFLICT (mold_id) DO UPDATE SET
  mold_code = EXCLUDED.mold_code,
  mold_name = EXCLUDED.mold_name,
  category_id = EXCLUDED.category_id,
  is_active = EXCLUDED.is_active;
