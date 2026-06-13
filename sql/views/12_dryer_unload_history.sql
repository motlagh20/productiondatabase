CREATE VIEW app.dryer_unload_history AS
SELECT
  du.unload_id AS id,
  dl.chamber_no AS chamber,
  p.product_name AS product,
  du.unload_date_jalali AS date,
  du.unload_time AS time,
  COALESCE(u.full_name, u.username) AS operator,
  du.unloaded_finger_count AS finger
FROM app.dryer_unloading du
JOIN app.dryer_loading dl ON dl.load_id = du.load_id
JOIN app.products p ON p.product_id = dl.product_id
LEFT JOIN app.users u ON u.user_id = du.unload_operator_id
ORDER BY du.unload_id DESC;

