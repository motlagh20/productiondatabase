CREATE TABLE app.kiln_push_data (
  push_id BIGSERIAL PRIMARY KEY,
  push_date_jalali TEXT NOT NULL,
  shift_id BIGINT NOT NULL REFERENCES app.shifts_definition(shift_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  operator_id BIGINT NOT NULL REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  product_id BIGINT NOT NULL REFERENCES app.products(product_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  incoming_car_id INTEGER NOT NULL,
  pushing_time_min NUMERIC(10,2),
  temp_exhaust NUMERIC(10,2),
  temp_preheat01 NUMERIC(10,2),
  temp_preheat02 NUMERIC(10,2),
  temp_thermostat NUMERIC(10,2),
  temp_zone00 NUMERIC(10,2),
  temp_zone01 NUMERIC(10,2),
  temp_zone02 NUMERIC(10,2),
  temp_zone03 NUMERIC(10,2),
  temp_zone04 NUMERIC(10,2),
  temp_zone05 NUMERIC(10,2),
  temp_zone06 NUMERIC(10,2),
  temp_zone07 NUMERIC(10,2),
  temp_rapid01 NUMERIC(10,2),
  temp_rapid02 NUMERIC(10,2),
  temp_bottom_a NUMERIC(10,2),
  temp_bottom01 NUMERIC(10,2),
  temp_bottom_b NUMERIC(10,2),
  temp_bottom02 NUMERIC(10,2),
  push_timestamp TEXT GENERATED ALWAYS AS (push_date_jalali || ' ' || '00:00:00') STORED,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT,
  UNIQUE (push_date_jalali, incoming_car_id)
);

CREATE INDEX kiln_push_date_idx ON app.kiln_push_data (push_date_jalali);
CREATE INDEX kiln_push_operator_idx ON app.kiln_push_data (operator_id);
CREATE INDEX kiln_push_product_idx ON app.kiln_push_data (product_id);
CREATE INDEX kiln_push_shift_idx ON app.kiln_push_data (shift_id);
CREATE INDEX kiln_push_car_idx ON app.kiln_push_data (incoming_car_id);

