CREATE TABLE app.dryer_unloading (
  unload_id BIGSERIAL PRIMARY KEY,
  load_id BIGINT NOT NULL UNIQUE REFERENCES app.dryer_loading(load_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  unload_date_jalali TEXT NOT NULL,
  shift_id BIGINT NOT NULL REFERENCES app.shifts_definition(shift_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  supervisor_id BIGINT NOT NULL REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  unload_time TEXT NOT NULL,
  unload_operator_id BIGINT NOT NULL REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  unloaded_finger_count INTEGER NOT NULL CHECK (unloaded_finger_count >= 0),
  dryer_waste INTEGER DEFAULT 0 CHECK (dryer_waste >= 0),
  unload_timestamp TEXT GENERATED ALWAYS AS (unload_date_jalali || ' ' || unload_time) STORED,
  drying_hours NUMERIC(10,2),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX dryer_unloading_load_id_idx ON app.dryer_unloading (load_id);
CREATE INDEX dryer_unloading_shift_id_idx ON app.dryer_unloading (shift_id);
CREATE INDEX dryer_unloading_supervisor_id_idx ON app.dryer_unloading (supervisor_id);
