CREATE VIEW app.kiln_pushing_recent AS
SELECT
  k.push_date_jalali,
  s.shift_name,
  p.product_name,
  k.incoming_car_id,
  k.push_timestamp,
  COALESCE(u.full_name, u.username) AS operator_name
FROM app.kiln_push_data k
LEFT JOIN app.shifts_definition s ON s.shift_id = k.shift_id
LEFT JOIN app.products p ON p.product_id = k.product_id
LEFT JOIN app.users u ON u.user_id = k.operator_id
ORDER BY k.push_id DESC
LIMIT 50;

