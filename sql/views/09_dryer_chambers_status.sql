CREATE VIEW app.dryer_chambers_status AS
WITH chambers AS (
  SELECT generate_series(1, 32) AS chamber_no
),
occupied AS (
  SELECT
    dl.chamber_no,
    dl.load_time,
    COALESCE(u.full_name, u.username) AS operator_name,
    p.product_name
  FROM app.dryer_loading dl
  LEFT JOIN app.dryer_unloading du ON du.load_id = dl.load_id
  LEFT JOIN app.users u ON u.user_id = dl.load_operator_id
  LEFT JOIN app.products p ON p.product_id = dl.product_id
  WHERE du.unload_id IS NULL
)
SELECT
  c.chamber_no AS "ChamberNo",
  (o.chamber_no IS NOT NULL) AS occupied,
  o.product_name AS "ProductName",
  o.load_time AS "LoadTime",
  o.operator_name AS "Operator"
FROM chambers c
LEFT JOIN occupied o ON o.chamber_no = c.chamber_no
ORDER BY c.chamber_no;

