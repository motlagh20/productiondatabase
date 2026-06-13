CREATE VIEW app.dryer_readings_recent AS
SELECT
  dl.chamber_no AS "ChamberNo",
  dr.record_date_jalali AS "DateJalali",
  dr.record_time AS "Time",
  dr.temperature AS "Temperature",
  dr.humidity AS "Humidity",
  COALESCE(u.full_name, u.username) AS "OperatorName"
FROM app.dryer_readings dr
LEFT JOIN app.dryer_loading dl ON dl.load_id = dr.load_id
LEFT JOIN app.users u ON u.user_id = dr.recorded_by
ORDER BY dr.reading_id DESC
LIMIT 50;

