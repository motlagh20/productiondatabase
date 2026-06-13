CREATE VIEW app.user_options AS
SELECT user_id, username, full_name, role_id
FROM app.users
WHERE is_active = TRUE
ORDER BY username;

