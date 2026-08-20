CREATE TABLE app.categories (
  category_id BIGSERIAL PRIMARY KEY,
  category_code TEXT NOT NULL UNIQUE,
  category_name TEXT NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX categories_code_idx ON app.categories (category_code);
