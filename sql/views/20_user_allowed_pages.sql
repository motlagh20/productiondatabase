CREATE VIEW app.user_allowed_pages AS
SELECT
  u.user_id,
  p.page_key AS "PageKey",
  rp.can_view AS "Allowed"
FROM app.users u
JOIN app.role_permissions rp ON rp.role_id = u.role_id
JOIN app.pages p ON p.page_id = rp.page_id
WHERE u.is_active = TRUE AND p.is_active = TRUE;

