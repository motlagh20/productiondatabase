CREATE TABLE app.pages (
  page_id BIGSERIAL PRIMARY KEY,
  page_name TEXT NOT NULL UNIQUE,
  page_title TEXT NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX pages_is_active_idx ON app.pages (is_active);

