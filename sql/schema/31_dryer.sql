-- ============================================================================
-- MES Database — Dryer Module (chamber-centric, NO wagon)
-- Target: PostgreSQL 16
-- Sources: xls/consolidated/All/Dryer-All.xlsx
--   'Data Entry' -> dryer_cycle (one row per chamber load/unload event)
--   'Humidity'/'Temp' -> dryer_reading (one row per hour-offset time series)
-- Design notes:
--   * Dryer has NO wagon: a Finger Car moves trays between forming -> chamber
--     -> setting. The chamber is the physical anchor.
--   * One Data Entry row = one chamber cycle (load in + unload out).
--   * Humidity/Temp sheets carry 22 time points (hour 0..63) per ChamberID;
--     these are unpivoted into dryer_reading (long format) for flexibility.
--   * Shared dimensions (operator, chamber, product) already exist from 30_setting.sql
-- ============================================================================

CREATE TABLE IF NOT EXISTS dryer_cycle (
    dryer_cycle_id   BIGSERIAL PRIMARY KEY,
    chamber_id       INTEGER REFERENCES chamber(chamber_id),
    load_date        VARCHAR(10),                  -- normalized 'YYYY.MM.DD'
    load_time        TIME,
    unload_date      VARCHAR(10),
    unload_time      TIME,
    load_operator_id INTEGER REFERENCES operator(operator_id),
    unload_operator_id INTEGER REFERENCES operator(operator_id),
    product_id       INTEGER REFERENCES product(product_id),
    finger_count     INTEGER,
    chamber_no       INTEGER,                      -- legacy ChamberNo from source
    source_row       INTEGER,                      -- traceability to Excel row
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dryer_reading (
    dryer_reading_id BIGSERIAL PRIMARY KEY,
    dryer_cycle_id   INTEGER NOT NULL REFERENCES dryer_cycle(dryer_cycle_id),
    hour_offset      SMALLINT NOT NULL,            -- 0,3,6,...,63 (from source)
    humidity_pct     NUMERIC(5,2),
    temperature_c    NUMERIC(5,2),
    UNIQUE (dryer_cycle_id, hour_offset)
);

CREATE INDEX IF NOT EXISTS idx_dryer_cycle_chamber ON dryer_cycle(chamber_id);
CREATE INDEX IF NOT EXISTS idx_dryer_reading_cycle ON dryer_reading(dryer_cycle_id);

COMMENT ON TABLE dryer_cycle IS 'One dryer chamber cycle (load+unload) — header of Dryer-All.Data Entry';
COMMENT ON TABLE dryer_reading IS 'Hour-offset time series (humidity/temp) for a dryer cycle, from Dryer-All.Humidity/Temp';
