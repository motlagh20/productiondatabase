CREATE VIEW app.dryer_occupied AS
SELECT
  dl.load_id AS "CycleID",
  dl.chamber_no AS "ChamberNo",
  p.product_name AS "ProductName",
  dl.load_date_jalali AS "LoadDateJalali",
  dl.load_time AS "LoadTime"
FROM app.dryer_loading dl
LEFT JOIN app.dryer_unloading du ON du.load_id = dl.load_id
LEFT JOIN app.products p ON p.product_id = dl.product_id
WHERE du.unload_id IS NULL
ORDER BY dl.chamber_no;

