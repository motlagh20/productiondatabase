CREATE TABLE app.dryer_loading (
  load_id BIGSERIAL PRIMARY KEY,
  chamber_no INTEGER NOT NULL CHECK (chamber_no BETWEEN 1 AND 32),
  load_date_jalali TEXT NOT NULL,
  shift_id BIGINT NOT NULL REFERENCES app.shifts_definition(shift_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  supervisor_id BIGINT NOT NULL REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  load_time TEXT NOT NULL,
  load_operator_id BIGINT NOT NULL REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  product_id BIGINT NOT NULL REFERENCES app.products(product_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  finger_count INTEGER NOT NULL CHECK (finger_count >= 0),
  load_timestamp TEXT GENERATED ALWAYS AS (load_date_jalali || ' ' || load_time) STORED,
  is_unloaded BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (chamber_no, load_date_jalali, load_time)
);

CREATE INDEX dryer_loading_chamber_no_idx ON app.dryer_loading (chamber_no);
CREATE INDEX dryer_loading_timestamp_idx ON app.dryer_loading (load_timestamp);
CREATE INDEX dryer_loading_operator_idx ON app.dryer_loading (load_operator_id);
CREATE INDEX dryer_loading_shift_id_idx ON app.dryer_loading (shift_id);
CREATE INDEX dryer_loading_supervisor_id_idx ON app.dryer_loading (supervisor_id);
CREATE INDEX dryer_loading_chamber_shift_idx ON app.dryer_loading (chamber_no, shift_id);
