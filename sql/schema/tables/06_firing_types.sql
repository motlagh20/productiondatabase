CREATE TABLE app.firing_types (
  firing_type_id BIGSERIAL PRIMARY KEY,
  firing_name TEXT NOT NULL UNIQUE,
  description TEXT
);

CREATE INDEX firing_types_name_idx ON app.firing_types (firing_name);

