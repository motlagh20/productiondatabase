CREATE TABLE app.shifts_definition (
  shift_id BIGSERIAL PRIMARY KEY,
  shift_code SMALLINT NOT NULL UNIQUE CHECK (shift_code IN (1,2,3)),
  shift_name TEXT NOT NULL,
  start_time TIME,
  end_time TIME,
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX shifts_definition_is_active_idx ON app.shifts_definition (is_active);

