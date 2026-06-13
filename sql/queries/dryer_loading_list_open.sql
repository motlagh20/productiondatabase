SELECT
  load_id,
  chamber_no,
  load_date_jalali,
  shift_id,
  supervisor_id,
  load_time,
  load_operator_id,
  product_id,
  finger_count,
  load_timestamp
FROM app.dryer_loading
WHERE is_unloaded IS NOT TRUE
ORDER BY load_timestamp DESC;

