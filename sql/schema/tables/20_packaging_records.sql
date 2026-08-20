CREATE TABLE app.packaging_records (
  package_id BIGSERIAL PRIMARY KEY,
  package_date_jalali TEXT NOT NULL,
  shift_id BIGINT NOT NULL REFERENCES app.shifts_definition(shift_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  operator_id BIGINT NOT NULL REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  type_of_workers TEXT,
  workers_count INTEGER CHECK (workers_count >= 0),
  product_id BIGINT NOT NULL REFERENCES app.products(product_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  wagon_no INTEGER,
  total_count INTEGER NOT NULL CHECK (total_count >= 0),
  grade1_count INTEGER NOT NULL CHECK (grade1_count >= 0),
  waste_count INTEGER DEFAULT 0 CHECK (waste_count >= 0),
  grade2_count INTEGER GENERATED ALWAYS AS (total_count - grade1_count - waste_count) STORED,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT,
  CHECK (grade1_count + waste_count <= total_count)
);

CREATE INDEX packaging_date_idx ON app.packaging_records (package_date_jalali);
CREATE INDEX packaging_shift_idx ON app.packaging_records (shift_id);
CREATE INDEX packaging_operator_idx ON app.packaging_records (operator_id);
CREATE INDEX packaging_product_idx ON app.packaging_records (product_id);
CREATE INDEX packaging_wagon_idx ON app.packaging_records (wagon_no);

