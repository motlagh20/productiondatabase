-- ============================================================================
-- MES Database — Setting (فرم‌دهی/ستینگ) Module
-- Target: PostgreSQL 16
-- Source: xls/consolidated/All/Set_All_1.xlsx  (sheet 'Data')
-- Design notes:
--   * One row in the Excel = one SETTING EVENT (a chamber batch, up to 4 wagons).
--   * setting_event   -> header of the event (date/shift/chamber/supervisor/operator).
--   * setting_wagon    -> ONE physical wagon load within that event (the "wagon journey").
--                         wagon_no is NOT unique (reused across history); the natural
--                         key for a journey is (wagon_no, created_datetime).
--   * GlazeType / packages / khesht_count / start-end times live on the wagon row.
--   * productName maps to the shared Product dimension (loaded separately).
-- ============================================================================

-- ---- Shared dimensions (idempotent: create only if missing) ----------------
CREATE TABLE IF NOT EXISTS operator (
    operator_id   BIGSERIAL PRIMARY KEY,
    operator_code VARCHAR(20) UNIQUE NOT NULL,   -- legacy code from files
    full_name     VARCHAR(100),
    role          VARCHAR(50),                    -- 'setting','dryer','kiln','packing','supervisor'
    is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS chamber (
    chamber_id    BIGSERIAL PRIMARY KEY,
    chamber_code  VARCHAR(20) UNIQUE NOT NULL,   -- legacy Chamber_No / ChamberID
    chamber_type  VARCHAR(20) NOT NULL DEFAULT 'SETTING',  -- 'SETTING','DRYER','KILN'
    description   VARCHAR(100),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS product (
    product_id            BIGSERIAL PRIMARY KEY,
    product_code_kiln     VARCHAR(20),            -- e.g. 91000001
    product_code_packing  VARCHAR(20),            -- e.g. '03'
    product_name_setting  VARCHAR(100),           -- e.g. 'سفال خودرنگ'
    product_group         VARCHAR(50),
    is_active             BOOLEAN NOT NULL DEFAULT TRUE
);

-- ---- Setting module --------------------------------------------------------
CREATE TABLE IF NOT EXISTS setting_event (
    setting_event_id  BIGSERIAL PRIMARY KEY,
    date_jalali       VARCHAR(10) NOT NULL,      -- normalized 'YYYY.MM.DD'
    shift             SMALLINT,                  -- 1,2,3
    chamber_id        INTEGER REFERENCES chamber(chamber_id),
    product_id        INTEGER REFERENCES product(product_id),
    supervisor_id     INTEGER REFERENCES operator(operator_id),
    operator_id       INTEGER REFERENCES operator(operator_id),
    personnel_count   INTEGER,
    fingers_count     INTEGER,                   -- total fingers in the event
    columns_count     INTEGER,
    dryer_waste       NUMERIC(6,2),              -- waste % or qty from source
    source_row        INTEGER,                   -- traceability to Excel row
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS setting_wagon (
    setting_wagon_id   BIGSERIAL PRIMARY KEY,
    setting_event_id   INTEGER NOT NULL REFERENCES setting_event(setting_event_id),
    wagon_no           INTEGER,                  -- physical tag (e.g. 71); may be null if not recorded
    glaze_type         VARCHAR(50),
    start_time         TIME,                      -- time this wagon started loading
    end_time           TIME,                      -- time this wagon finished loading
    packages           INTEGER,                   -- number of 5-tile packs
    khesht_count       INTEGER,                   -- raw tile count (if present)
    position_in_event  SMALLINT,                  -- 1..4 (which block in the Excel row)
    created_datetime   TIMESTAMPTZ DEFAULT NOW(), -- journey anchor (wagon_no + this = natural key)
    UNIQUE (setting_event_id, wagon_no, position_in_event)
);

-- Index for tracing a physical wagon across its journeys
CREATE INDEX IF NOT EXISTS idx_setting_wagon_no ON setting_wagon(wagon_no);

COMMENT ON TABLE setting_event IS 'One setting batch (chamber load) — header row of Set_All_1.Data';
COMMENT ON TABLE setting_wagon IS 'One physical wagon loaded within a setting event (a wagon journey); up to 4 per event';
