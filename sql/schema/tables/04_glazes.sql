CREATE TABLE app.glazes (
  glaze_id BIGSERIAL PRIMARY KEY,
  glaze_code TEXT NOT NULL UNIQUE,
  glaze_name TEXT NOT NULL,
  is_self_colored BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX glazes_code_idx ON app.glazes (glaze_code);
