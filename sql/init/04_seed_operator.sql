INSERT INTO app.roles (role_name, description)
VALUES ('Operator', 'Production operator')
ON CONFLICT (role_name) DO NOTHING;

INSERT INTO app.users (username, full_name, password_hash, role_id, is_active)
SELECT 'operator','Operator User','$2b$12$KIXIDZrt6G8R1JywgnPuu.uFRlI2PlxFMCXARfG3hwlRf5s3QhC5K', role_id, TRUE
FROM app.roles WHERE role_name='Operator'
ON CONFLICT (username) DO NOTHING;

INSERT INTO app.user_credentials (user_id, password_hash, password_algorithm, must_change_password)
SELECT user_id, '$2b$12$KIXIDZrt6G8R1JywgnPuu.uFRlI2PlxFMCXARfG3hwlRf5s3QhC5K', 'bcrypt', TRUE
FROM app.users WHERE username='operator'
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO app.role_permissions (role_id, page_id, can_view, can_add, can_edit, can_delete)
SELECT r.role_id, p.page_id,
       CASE WHEN p.page_key IN ('home','dryer_dashboard','dryer_load','dryer_unload','setting_entry','setting_transactions','kiln_pushing') THEN TRUE ELSE FALSE END,
       CASE WHEN p.page_key IN ('dryer_load','dryer_unload') THEN TRUE ELSE FALSE END,
       FALSE,
       FALSE
FROM app.roles r
CROSS JOIN app.pages p
WHERE r.role_name='Operator'
ON CONFLICT (role_id, page_id) DO NOTHING;
