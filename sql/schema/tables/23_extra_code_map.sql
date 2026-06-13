CREATE TABLE app.extra_code_map (
  extra_code TEXT PRIMARY KEY,
  extra_name TEXT NOT NULL
);

CREATE INDEX extra_code_map_name_idx ON app.extra_code_map (extra_name);
