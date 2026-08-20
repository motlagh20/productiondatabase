CREATE VIEW app.role_allowed_pages AS
SELECT
  r.role_id,
  p.page_key AS "PageKey",
  rp.can_view AS "Allowed"
FROM app.role_permissions rp
JOIN app.roles r ON r.role_id = rp.role_id
JOIN app.pages p ON p.page_id = rp.page_id
WHERE r.is_active = TRUE AND p.is_active = TRUE;

