-- M4: Clean materialized-ready VIEWS over the historical (flag-only corrected) data.
-- Raw values are NEVER modified; each view surfaces COALESCE(corrected, raw).
-- These are the read layer the future application (Django/DRF) consumes.

-- 1. Packing: cleaned grade1 + composite product join + flag-only wagon status
CREATE OR REPLACE VIEW v_clean_packing AS
SELECT
    pr.id,
    pr.date_jalali,
    pr.month,
    pr.day,
    pr.shift,
    pr.controller,
    pr.worker_type,
    pr.worker_count,
    pr.product_code,
    p.mold_type,
    p.glaze,
    p.description AS product_desc,
    pr.wagon_no,
    pr.total,
    COALESCE(pr.corrected_grade1, pr.grade1) AS grade1,   -- corrected if available
    pr.grade1 AS grade1_raw,
    pr.grade2,
    pr.waste,
    pr.efficiency_raw,
    -- flag-only anomalies kept verbatim (owner: verify from ledgers, do NOT auto-fix)
    CASE WHEN pr.wagon_no ~ '^[0-9]+$' AND pr.wagon_no::int > 80 THEN TRUE ELSE FALSE END AS wagon_flagged,
    pr.natural_key
FROM packing_records pr
LEFT JOIN products p ON p.canonical_code = pr.product_code;

-- 2. Kiln temperatures: corrected value where applied
CREATE OR REPLACE VIEW v_clean_kiln_temps AS
SELECT
    kt.id,
    kt.push_id,
    kp.date_jalali,
    kt.zone_group,
    kt.zone_reading,
    COALESCE(kt.corrected_value, kt.value) AS value,   -- corrected if applied
    kt.value AS value_raw,
    kt.corrected_value IS NOT NULL AS was_corrected,
    kp.incoming_car_id AS wagon_no
FROM kiln_temperature_readings kt
JOIN kiln_pushes kp ON kp.id = kt.push_id;

-- 3. Dryer readings: corrected value where applied (temp + humidity)
CREATE OR REPLACE VIEW v_clean_dryer_readings AS
SELECT
    dr.id,
    dr.operation_id,
    dr.hour_offset,
    dr.metric,
    COALESCE(dr.corrected_value, dr.value) AS value,   -- corrected if applied
    dr.value AS value_raw,
    dr.corrected_value IS NOT NULL AS was_corrected
FROM dryer_readings dr;

-- 4. Open anomalies still needing plant ledger review (flag-only, no value change)
-- record_date is the canonicalized first '|' segment of natural_key:
--   2-digit year -> 13xx, all separators -> '.', format 'YYYY.MM.DD'.
-- natural_key itself is the JOIN key and is left UNTOUCHED.
CREATE OR REPLACE VIEW v_open_anomalies AS
SELECT
    rq.id,
    rq.table_name,
    rq.field_name,
    rq.raw_value,
    rq.issue_class,
    rq.natural_key,
    CASE
        WHEN split_part(rq.natural_key, '|', 1) ~ '^[0-9]{2}[./-]' THEN
            (SELECT '13' || lpad(a[1],2,'0') || '.' || lpad(a[2],2,'0') || '.' || lpad(a[3],2,'0')
             FROM (SELECT regexp_split_to_array(split_part(rq.natural_key,'|',1), '[./-]') AS a) s)
        WHEN split_part(rq.natural_key, '|', 1) ~ '^[0-9]{4}[./-]' THEN
            (SELECT a[1] || '.' || lpad(a[2],2,'0') || '.' || lpad(a[3],2,'0')
             FROM (SELECT regexp_split_to_array(split_part(rq.natural_key,'|',1), '[./-]') AS a) s)
        ELSE split_part(rq.natural_key, '|', 1)
    END AS record_date,
    rq.suggested_fix,
    rq.correction_reason
FROM review_queue rq
WHERE NOT rq.resolved
ORDER BY rq.table_name, rq.field_name;
