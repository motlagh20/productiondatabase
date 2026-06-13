CREATE TABLE app.production_batches (
  batch_id BIGSERIAL PRIMARY KEY,
  batch_number TEXT UNIQUE NOT NULL,

  product_id BIGINT NOT NULL REFERENCES app.products(product_id) ON UPDATE CASCADE ON DELETE RESTRICT,

  input_type TEXT NOT NULL CHECK (input_type IN ('RawTile', 'FiredTile')),
  input_batch_id BIGINT REFERENCES app.production_batches(batch_id) ON UPDATE CASCADE ON DELETE SET NULL,
  input_stock_id BIGINT REFERENCES app.warehouse_stock(stock_id) ON UPDATE CASCADE ON DELETE SET NULL,
  CHECK ((input_type = 'RawTile' AND input_batch_id IS NULL AND input_stock_id IS NULL)
     OR (input_type = 'FiredTile' AND input_batch_id IS NOT NULL AND input_stock_id IS NOT NULL)),

  setting_date DATE NOT NULL,
  shift SMALLINT NOT NULL CHECK (shift IN (1,2,3)) REFERENCES app.shifts_definition(shift_code),
  setting_operator TEXT NOT NULL,
  quantity_input INTEGER NOT NULL CHECK (quantity_input >= 0),
  quantity_output INTEGER NOT NULL CHECK (quantity_output >= 0),
  waste_count INTEGER DEFAULT 0 CHECK (waste_count >= 0),
  CHECK (quantity_output <= quantity_input),

  wagon_numbers TEXT,

  firing_type TEXT GENERATED ALWAYS AS (
    CASE WHEN input_type = 'RawTile' THEN 'Single' ELSE 'Double' END
  ) STORED,

  notes TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX production_batches_product_id_idx ON app.production_batches (product_id);
CREATE INDEX production_batches_input_type_idx ON app.production_batches (input_type);
CREATE INDEX production_batches_input_batch_id_idx ON app.production_batches (input_batch_id);
CREATE INDEX production_batches_setting_date_idx ON app.production_batches (setting_date);

