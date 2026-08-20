CREATE TABLE app.warehouse_stock (
  stock_id BIGSERIAL PRIMARY KEY,
  batch_id BIGINT NOT NULL REFERENCES app.production_batches(batch_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  product_id BIGINT NOT NULL REFERENCES app.products(product_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  quantity INTEGER NOT NULL CHECK (quantity >= 0),
  entry_date DATE NOT NULL,
  location TEXT,
  is_available BOOLEAN DEFAULT TRUE,
  notes TEXT,
  UNIQUE (batch_id)
);

CREATE INDEX warehouse_stock_product_id_idx ON app.warehouse_stock (product_id);
CREATE INDEX warehouse_stock_is_available_idx ON app.warehouse_stock (is_available);
