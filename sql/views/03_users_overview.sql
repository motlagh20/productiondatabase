CREATE VIEW app.users_overview AS
SELECT
  u.user_id,
  u.username,
  u.full_name,
  u.is_active,
  u.last_login,
  r.role_name,
  c.failed_attempts,
  c.locked_until,
  c.must_change_password,
  c.password_last_changed_at
FROM app.users u
LEFT JOIN app.roles r ON u.role_id = r.role_id
LEFT JOIN app.user_credentials c ON c.user_id = u.user_id;

