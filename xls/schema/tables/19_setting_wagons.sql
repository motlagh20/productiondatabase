CREATE TABLE app.setting_wagons (
  wagon_id BIGSERIAL PRIMARY KEY,
  setting_id BIGINT NOT NULL REFERENCES app.production_batches(batch_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  wagon_order INTEGER NOT NULL CHECK (wagon_order BETWEEN 1 AND 4),
  wagon_no INTEGER NOT NULL,
  product_id BIGINT NOT NULL REFERENCES app.products(product_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  glaze_override TEXT,
  start_time TEXT,
  end_time TEXT,
  packages INTEGER NOT NULL CHECK (packages >= 0),
  notes TEXT,
  UNIQUE (setting_id, wagon_order),
  UNIQUE (setting_id, wagon_no)
);

CREATE INDEX setting_wagons_setting_id_idx ON app.setting_wagons (setting_id);
CREATE INDEX setting_wagons_wagon_no_idx ON app.setting_wagons (wagon_no);
CREATE INDEX setting_wagons_product_id_idx ON app.setting_wagons (product_id);

