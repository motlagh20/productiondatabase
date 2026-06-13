CREATE TABLE app.fuel_types (
  fuel_type_id BIGSERIAL PRIMARY KEY,
  fuel_name TEXT NOT NULL UNIQUE,
  is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX fuel_types_active_idx ON app.fuel_types (is_active);

