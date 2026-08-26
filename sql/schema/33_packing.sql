-- ============================================================================
-- MES Database — Packing Module (wagon-centric, downstream of kiln)
-- Target: PostgreSQL 16
-- Source: xls/consolidated/All/Packing-All.xlsx (sheet 'Sheet1')
-- Design notes:
--   * One Excel row = one wagon packed on a given date/shift by a controller.
--   * packing_header -> groups by (date, shift, controller) -- the packing session.
--   * packing_wagon  -> one row per wagon (grades 1/2, waste, total, efficiency).
--   * Date format in source is 'YYYY/MM/DD' (slashes) -> normalized to 'YYYY.MM.DD'.
--   * product_code (e.g. '03') maps to shared product dimension.
--   * 'تعداد کل محصول' is repeated per wagon row in source; we keep per-wagon values
--     as recorded and also store header-level totals derived from wagons.
-- ============================================================================

CREATE TABLE IF NOT EXISTS packing_header (
    packing_header_id BIGSERIAL PRIMARY KEY,
    pack_date         VARCHAR(10) NOT NULL,        -- 'YYYY.MM.DD'
    shift             SMALLINT,
    controller_id     INTEGER REFERENCES operator(operator_id),
    worker_type       VARCHAR(30),                -- 'پیمانکاران' etc.
    worker_count      INTEGER,
    month_name        VARCHAR(20),
    day_name          VARCHAR(20),
    source_row        INTEGER,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS packing_wagon (
    packing_wagon_id  BIGSERIAL PRIMARY KEY,
    packing_header_id INTEGER NOT NULL REFERENCES packing_header(packing_header_id),
    wagon_no          INTEGER,
    product_id        INTEGER REFERENCES product(product_id),
    product_desc      VARCHAR(100),               -- شرح محصول (free text from source)
    total_count       INTEGER,
    grade1_count      INTEGER,
    grade2_count      INTEGER,
    waste_count       INTEGER,
    efficiency_pct    NUMERIC(6,2),
    position_index    SMALLINT
);

CREATE INDEX IF NOT EXISTS idx_packing_header_date ON packing_header(pack_date);
CREATE INDEX IF NOT EXISTS idx_packing_wagon_no ON packing_wagon(wagon_no);

COMMENT ON TABLE packing_header IS 'One packing session (date/shift/controller) — header of Packing-All.Sheet1';
COMMENT ON TABLE packing_wagon IS 'One wagon packed in a session, with grade/waste/efficiency';
