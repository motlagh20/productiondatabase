CREATE TABLE app.dryer_readings (
  reading_id BIGSERIAL PRIMARY KEY,
  load_id BIGINT NOT NULL REFERENCES app.dryer_loading(load_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  point_number INTEGER NOT NULL CHECK (point_number BETWEEN 1 AND 21),
  record_date_jalali TEXT,
  record_time TEXT NOT NULL,
  record_timestamp TEXT GENERATED ALWAYS AS (record_date_jalali || ' ' || record_time) STORED,
  temperature NUMERIC(10,2),
  humidity NUMERIC(10,2),
  recorded_by BIGINT REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE SET NULL,
  notes TEXT,
  UNIQUE (load_id, point_number)
);

CREATE INDEX dryer_readings_load_id_idx ON app.dryer_readings (load_id);
CREATE INDEX dryer_readings_point_number_idx ON app.dryer_readings (point_number);
