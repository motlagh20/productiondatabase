CREATE VIEW app.operators_dryer AS
SELECT
  u.user_id AS "OperatorCode",
  COALESCE(u.full_name, u.username) AS "OperatorName"
FROM app.users u
JOIN app.roles r ON r.role_id = u.role_id
WHERE u.is_active = TRUE AND r.role_name = 'Operator'
ORDER BY "OperatorName";

