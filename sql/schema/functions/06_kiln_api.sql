CREATE FUNCTION app.kiln_push(
  push_date_jalali TEXT,
  shift_id BIGINT,
  operator_id BIGINT,
  product_id BIGINT,
  fuel_type_id INTEGER,
  incoming_car_id INTEGER,
  pushing_time_min NUMERIC(10,2) DEFAULT NULL,
  temp_exhaust NUMERIC(10,2) DEFAULT NULL,
  temp_preheat01 NUMERIC(10,2) DEFAULT NULL,
  temp_preheat02 NUMERIC(10,2) DEFAULT NULL,
  temp_thermostat NUMERIC(10,2) DEFAULT NULL,
  temp_zone00 NUMERIC(10,2) DEFAULT NULL,
  temp_zone01 NUMERIC(10,2) DEFAULT NULL,
  temp_zone02 NUMERIC(10,2) DEFAULT NULL,
  temp_zone03 NUMERIC(10,2) DEFAULT NULL,
  temp_zone04 NUMERIC(10,2) DEFAULT NULL,
  temp_zone05 NUMERIC(10,2) DEFAULT NULL,
  temp_zone06 NUMERIC(10,2) DEFAULT NULL,
  temp_zone07 NUMERIC(10,2) DEFAULT NULL,
  temp_rapid01 NUMERIC(10,2) DEFAULT NULL,
  temp_rapid02 NUMERIC(10,2) DEFAULT NULL,
  temp_bottom_a NUMERIC(10,2) DEFAULT NULL,
  temp_bottom01 NUMERIC(10,2) DEFAULT NULL,
  temp_bottom_b NUMERIC(10,2) DEFAULT NULL,
  temp_bottom02 NUMERIC(10,2) DEFAULT NULL,
  notes TEXT DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
  v_push_id BIGINT;
BEGIN
  INSERT INTO app.kiln_push_data(
    push_date_jalali, shift_id, operator_id, product_id, incoming_car_id,
    pushing_time_min, temp_exhaust, temp_preheat01, temp_preheat02, temp_thermostat,
    temp_zone00, temp_zone01, temp_zone02, temp_zone03, temp_zone04, temp_zone05, temp_zone06, temp_zone07,
    temp_rapid01, temp_rapid02, temp_bottom_a, temp_bottom01, temp_bottom_b, temp_bottom02, notes
  ) VALUES (
    push_date_jalali, shift_id, operator_id, product_id, incoming_car_id,
    pushing_time_min, temp_exhaust, temp_preheat01, temp_preheat02, temp_thermostat,
    temp_zone00, temp_zone01, temp_zone02, temp_zone03, temp_zone04, temp_zone05, temp_zone06, temp_zone07,
    temp_rapid01, temp_rapid02, temp_bottom_a, temp_bottom01, temp_bottom_b, temp_bottom02, notes
  )
  RETURNING push_id INTO v_push_id;
  RETURN v_push_id;
END;
$$ LANGUAGE plpgsql;

