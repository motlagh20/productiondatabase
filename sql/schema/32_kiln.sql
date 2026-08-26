-- ============================================================================
-- MES Database — Kiln Module (wagon-centric, full thermal profile)
-- Target: PostgreSQL 16
-- Source: xls/consolidated/All/Kiln-Merged.xlsx (sheet 'Kiln-All')
-- Design notes:
--   * One Excel row = one KILN PUSH (a batch of wagons entering the kiln).
--   * kiln_push    -> header of the push (date/time/operator/chamber).
--   * kiln_wagon   -> wagons inside that push (wagon_no + optional setting link).
--   * kiln_sensor  -> reference of the 18 thermal sensors (extensible).
--   * kiln_reading -> LONG format: one row per sensor per push (NOT 18 wide cols).
--   * Control columns (date_control/date_changed?/flag) kept for traceability.
--   * Shared dimensions (operator, chamber, product) already exist.
-- ============================================================================

CREATE TABLE IF NOT EXISTS kiln_sensor (
    sensor_id     BIGSERIAL PRIMARY KEY,
    sensor_code   VARCHAR(30) UNIQUE NOT NULL,   -- e.g. temp_exhaust, temp_Zone00
    sensor_name   VARCHAR(50),
    position_order SMALLINT,
    is_measured   BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS kiln_push (
    kiln_push_id    BIGSERIAL PRIMARY KEY,
    push_date       VARCHAR(10) NOT NULL,         -- 'YYYY.MM.DD'
    push_time       TIME,
    shift           SMALLINT,
    chamber_id      INTEGER REFERENCES chamber(chamber_id),
    operator_id     INTEGER REFERENCES operator(operator_id),
    product_id      INTEGER REFERENCES product(product_id),
    push_duration   INTERVAL,
    source_row      INTEGER,
    date_control    VARCHAR(20),                  -- traceability from source
    date_changed    VARCHAR(60),                  -- traceability (old->new)
    flag            VARCHAR(20),                  -- 'check it' etc.
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kiln_wagon (
    kiln_wagon_id   BIGSERIAL PRIMARY KEY,
    kiln_push_id    INTEGER NOT NULL REFERENCES kiln_push(kiln_push_id),
    wagon_no        INTEGER,                      -- physical tag; may repeat over time
    setting_wagon_id INTEGER REFERENCES setting_wagon(setting_wagon_id), -- nullable link
    position_index  SMALLINT,
    UNIQUE (kiln_push_id, wagon_no, position_index)
);

CREATE TABLE IF NOT EXISTS kiln_reading (
    kiln_reading_id BIGSERIAL PRIMARY KEY,
    kiln_push_id    INTEGER NOT NULL REFERENCES kiln_push(kiln_push_id),
    sensor_id       INTEGER NOT NULL REFERENCES kiln_sensor(sensor_id),
    temperature_c   NUMERIC(6,2),
    UNIQUE (kiln_push_id, sensor_id)
);

CREATE INDEX IF NOT EXISTS idx_kiln_push_date ON kiln_push(push_date);
CREATE INDEX IF NOT EXISTS idx_kiln_wagon_no ON kiln_wagon(wagon_no);
CREATE INDEX IF NOT EXISTS idx_kiln_reading_push ON kiln_reading(kiln_push_id);

COMMENT ON TABLE kiln_push IS 'One kiln push (batch of wagons entering kiln) — header of Kiln-All';
COMMENT ON TABLE kiln_wagon IS 'Wagons inside a kiln push; links back to setting_wagon when matched';
COMMENT ON TABLE kiln_reading IS 'One thermal-sensor reading per push (long format, 18 sensors per push)';
COMMENT ON TABLE kiln_sensor IS 'Reference list of kiln thermal sensors (extensible without schema change)';
