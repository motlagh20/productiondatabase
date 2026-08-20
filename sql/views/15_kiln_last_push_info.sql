CREATE VIEW app.kiln_last_push_info AS
SELECT
  push_id,
  push_date_jalali,
  incoming_car_id
FROM app.kiln_push_data
ORDER BY push_id DESC
LIMIT 1;

