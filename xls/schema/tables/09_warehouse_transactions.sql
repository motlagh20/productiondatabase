CREATE TABLE app.warehouse_transactions (
  transaction_id BIGSERIAL PRIMARY KEY,
  stock_id BIGINT NOT NULL REFERENCES app.warehouse_stock(stock_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  transaction_type TEXT NOT NULL CHECK (transaction_type IN ('Entry', 'Sale', 'ReturnToProduction')),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
  transaction_time TIME NOT NULL DEFAULT CURRENT_TIME,
  operator TEXT NOT NULL,
  related_batch_id BIGINT REFERENCES app.production_batches(batch_id) ON UPDATE CASCADE ON DELETE SET NULL,
  customer_name TEXT,
  invoice_number TEXT,
  notes TEXT,
  CHECK (transaction_type <> 'ReturnToProduction' OR related_batch_id IS NOT NULL)
);

CREATE INDEX warehouse_transactions_stock_id_idx ON app.warehouse_transactions (stock_id);
CREATE INDEX warehouse_transactions_type_idx ON app.warehouse_transactions (transaction_type);
CREATE INDEX warehouse_transactions_date_idx ON app.warehouse_transactions (transaction_date);
CREATE INDEX warehouse_transactions_related_batch_id_idx ON app.warehouse_transactions (related_batch_id);
