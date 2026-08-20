CREATE TABLE app.molds (
  mold_id BIGSERIAL PRIMARY KEY,
  mold_code TEXT NOT NULL UNIQUE,
  mold_name TEXT NOT NULL,
  category_id BIGINT REFERENCES app.categories(category_id) ON UPDATE CASCADE ON DELETE SET NULL,
  width NUMERIC(10,2),
  length NUMERIC(10,2),
  height NUMERIC(10,2),
  pieces_per_press INTEGER DEFAULT 1,
  is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX molds_code_idx ON app.molds (mold_code);
CREATE INDEX molds_category_idx ON app.molds (category_id);
