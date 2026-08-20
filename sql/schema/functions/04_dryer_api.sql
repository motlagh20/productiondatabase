CREATE FUNCTION app.create_dryer_loading(
  p_chamber_no INTEGER,
  p_load_date_jalali TEXT,
  p_shift_id BIGINT,
  p_supervisor_id BIGINT,
  p_load_time TEXT,
  p_load_operator_id BIGINT,
  p_product_id BIGINT,
  p_finger_count INTEGER
) RETURNS BIGINT AS $$
DECLARE
  v_load_id BIGINT;
BEGIN
  INSERT INTO app.dryer_loading(
    chamber_no, load_date_jalali, shift_id, supervisor_id, load_time,
    load_operator_id, product_id, finger_count
  ) VALUES (
    p_chamber_no, p_load_date_jalali, p_shift_id, p_supervisor_id, p_load_time,
    p_load_operator_id, p_product_id, p_finger_count
  )
  RETURNING load_id INTO v_load_id;
  RETURN v_load_id;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION app.create_dryer_reading_by_chamber(
  p_chamber_no INTEGER,
  p_record_date_jalali TEXT,
  p_record_time TEXT,
  p_temperature NUMERIC,
  p_humidity NUMERIC,
  p_recorded_by BIGINT,
  p_notes TEXT DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
  v_load_id BIGINT;
  v_point INTEGER;
  v_reading_id BIGINT;
BEGIN
  SELECT dl.load_id INTO v_load_id
  FROM app.dryer_loading dl
  LEFT JOIN app.dryer_unloading du ON du.load_id = dl.load_id
  WHERE dl.chamber_no = p_chamber_no AND du.unload_id IS NULL
  ORDER BY dl.load_id DESC
  LIMIT 1;

  IF v_load_id IS NULL THEN
    RAISE EXCEPTION 'No active dryer load found for chamber %', p_chamber_no;
  END IF;

  SELECT COALESCE(MAX(point_number), 0) + 1 INTO v_point
  FROM app.dryer_readings
  WHERE load_id = v_load_id;

  IF v_point > 21 THEN
    RAISE EXCEPTION 'Maximum reading points reached for load %', v_load_id;
  END IF;

  INSERT INTO app.dryer_readings(
    load_id, point_number, record_date_jalali, record_time,
    temperature, humidity, recorded_by, notes
  ) VALUES (
    v_load_id, v_point, p_record_date_jalali, p_record_time,
    p_temperature, p_humidity, p_recorded_by, p_notes
  )
  RETURNING reading_id INTO v_reading_id;

  RETURN v_reading_id;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION app.create_dryer_unloading(
  p_load_id BIGINT,
  p_unload_date_jalali TEXT,
  p_shift_id BIGINT,
  p_supervisor_id BIGINT,
  p_unload_time TEXT,
  p_unload_operator_id BIGINT,
  p_unloaded_finger_count INTEGER,
  p_dryer_waste INTEGER DEFAULT 0
) RETURNS BIGINT AS $$
DECLARE
  v_unload_id BIGINT;
BEGIN
  INSERT INTO app.dryer_unloading(
    load_id, unload_date_jalali, shift_id, supervisor_id, unload_time,
    unload_operator_id, unloaded_finger_count, dryer_waste
  ) VALUES (
    p_load_id, p_unload_date_jalali, p_shift_id, p_supervisor_id, p_unload_time,
    p_unload_operator_id, p_unloaded_finger_count, COALESCE(p_dryer_waste,0)
  )
  RETURNING unload_id INTO v_unload_id;
  RETURN v_unload_id;
END;
$$ LANGUAGE plpgsql;
