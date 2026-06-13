CREATE VIEW app.dryer_history AS
SELECT
  dl.load_id AS id,
  dl.chamber_no AS chamber,
  p.product_name AS product,
  dl.load_date_jalali AS date,
  dl.load_time AS time,
  dl.finger_count AS finger
FROM app.dryer_loading dl
JOIN app.products p ON p.product_id = dl.product_id
ORDER BY dl.load_id DESC;

