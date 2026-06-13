CREATE VIEW app.role_page_permissions AS
SELECT
  r.role_name,
  p.page_name,
  p.page_title,
  rp.can_view,
  rp.can_add,
  rp.can_edit,
  rp.can_delete
FROM app.role_permissions rp
JOIN app.roles r ON rp.role_id = r.role_id
JOIN app.pages p ON rp.page_id = p.page_id;

