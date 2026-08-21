-- M2.5 Database DDL — PostgreSQL 16
-- Derived from docs/M2_5_ERD_SCHEMA.md. Config-driven bounds (P1): NO hard-coded
-- CHECK constraints for chamber/shift/wagon/temp. Row-oriented series. Idempotent.
-- Authoritative source: xls/real data/ (read-only). No fabricated values (P2/P5).

-- ============================================================
-- 1. CONFIGURATION (P1 — bounds live here, not in code/schema)
-- ============================================================
CREATE TABLE config_chamber_bounds (
    id            SMALLINT PRIMARY KEY DEFAULT 1,
    chamber_max  SMALLINT NOT NULL DEFAULT 40,
    note         TEXT
);
CREATE TABLE config_shift_pattern (
    id          SMALLINT PRIMARY KEY,
    shift_code  SMALLINT NOT NULL,
    shift_name  TEXT NOT NULL,            -- صبح / عصر / شب
    start_hour  SMALLINT,
    end_hour    SMALLINT
);
CREATE TABLE config_wagon_bounds (
    id         SMALLINT PRIMARY KEY DEFAULT 1,
    wagon_max  SMALLINT NOT NULL DEFAULT 80,
    note       TEXT
);
CREATE TABLE config_temp_bounds (
    id            SMALLINT PRIMARY KEY DEFAULT 1,
    kiln_temp_max NUMERIC NOT NULL DEFAULT 1200,  -- owner: 1100-1200 tolerance
    note          TEXT
);
CREATE TABLE config_drying_cadence (
    id         SMALLINT PRIMARY KEY DEFAULT 1,
    hours_step SMALLINT NOT NULL DEFAULT 3,
    note       TEXT
);

-- ============================================================
-- 2. DIMENSIONS (reference masters)
-- ============================================================
CREATE TABLE operators (
    id         BIGSERIAL PRIMARY KEY,
    code       TEXT NOT NULL,            -- may be normalized per file
    full_name  TEXT NOT NULL,             -- IMMUTABLE per Master Rules §32
    role       TEXT,
    source     TEXT DEFAULT 'historical'
);
CREATE TABLE products (
    id              BIGSERIAL PRIMARY KEY,
    canonical_code  TEXT NOT NULL UNIQUE, -- P-SOFAL-KHODRANG etc (ADR-0006)
    mold_type       TEXT NOT NULL,        -- سفال / تیزه / پنجه ای
    glaze           TEXT,                 -- free text (M1-A2)
    description     TEXT,
    source          TEXT DEFAULT 'historical'
);
CREATE TABLE glazes (
    id            BIGSERIAL PRIMARY KEY,
    glaze_value   TEXT NOT NULL UNIQUE,   -- raw vocab (خودرنگ/اخرا/سبز/مولتی...)
    normalized    TEXT,
    is_combined   BOOLEAN DEFAULT FALSE,  -- مولتی = true
    note          TEXT
);

-- ============================================================
-- 3. DRYER
-- ============================================================
CREATE TABLE dryer_operations (
    id              BIGSERIAL PRIMARY KEY,
    date_jalali     TEXT NOT NULL,
    month           SMALLINT,
    day             SMALLINT,
    shift           SMALLINT,
    operator_load_id   BIGINT REFERENCES operators(id),
    operator_unload_id BIGINT REFERENCES operators(id),
    product_code    TEXT REFERENCES products(canonical_code),
    finger_count    SMALLINT,
    chamber_no      SMALLINT,
    duration        TEXT,
    notes           TEXT,
    source          TEXT DEFAULT 'historical',
    natural_key     TEXT UNIQUE  -- (date_jalali,shift,chamber_no,product_id)
);
CREATE TABLE dryer_readings (
    id            BIGSERIAL PRIMARY KEY,
    operation_id  BIGINT NOT NULL REFERENCES dryer_operations(id) ON DELETE CASCADE,
    hour_offset   SMALLINT NOT NULL,       -- parsed from header row
    metric        TEXT NOT NULL CHECK (metric IN ('temp','humidity')),
    value         NUMERIC,
    source        TEXT DEFAULT 'historical'
);

-- ============================================================
-- 4. KILN
-- ============================================================
CREATE TABLE kiln_pushes (
    id               BIGSERIAL PRIMARY KEY,
    date_jalali      TEXT NOT NULL,
    hour             TEXT,
    shift            SMALLINT,
    operator_id      BIGINT REFERENCES operators(id),
    product_code     TEXT REFERENCES products(canonical_code),
    input_type       TEXT CHECK (input_type IN ('خشت خام','سفال پخته')),
    incoming_car_id  TEXT,                 -- = wagon_no (M1-E4)
    pushing_time_min NUMERIC,
    push_seq         TEXT,
    source           TEXT DEFAULT 'historical',
    natural_key      TEXT UNIQUE          -- (date_jalali,hour,incoming_car_id)
);
CREATE TABLE kiln_temperature_readings (
    id             BIGSERIAL PRIMARY KEY,
    push_id        BIGINT NOT NULL REFERENCES kiln_pushes(id) ON DELETE CASCADE,
    zone_group     TEXT NOT NULL,         -- exhaust/preheat/thermostat/zone/rapid/bottom
    zone_reading   TEXT NOT NULL,         -- index 00-07 / A/01/B/02 / 1-2
    value          NUMERIC,               -- RAW as imported (never overwritten)
    corrected_value NUMERIC,               -- owner-confirmed correction; NULL until applied
    source         TEXT DEFAULT 'historical'
);

-- Proposed correction for out-of-range kiln temps (owner directive: NO auto-apply).
-- For each flagged reading, the nearest valid value of the SAME (zone_group, zone_reading)
-- in OTHER pushes is recorded as `proposed_value`. Plant reviews before any apply.
CREATE TABLE kiln_temp_correction (
    id              BIGSERIAL PRIMARY KEY,
    reading_id      BIGINT NOT NULL REFERENCES kiln_temperature_readings(id),
    push_id         BIGINT NOT NULL,
    zone_group      TEXT NOT NULL,
    zone_reading    TEXT NOT NULL,
    raw_value       NUMERIC,
    proposed_value  NUMERIC,               -- nearest valid same-zone value in other pushes
    neighbor_1      NUMERIC,               -- 3 nearest healthy same-zone values (for plant review)
    neighbor_2      NUMERIC,
    neighbor_3      NUMERIC,
    applied         BOOLEAN DEFAULT FALSE, -- always FALSE until plant confirms
    correction_reason TEXT,                -- structured reason: 'mean_of_neighbors' etc.
    corrected_by    TEXT DEFAULT 'system',  -- who/what applied the correction
    note            TEXT
);

-- ============================================================
-- 5. SETTING (4-layer, ADR-0005)
-- ============================================================
CREATE TABLE setting_operations (
    id             BIGSERIAL PRIMARY KEY,
    batch_key      TEXT NOT NULL,          -- legacy ID (NOT surrogate PK)
    date_jalali    TEXT NOT NULL,
    shift          SMALLINT,
    supervisor_id  BIGINT REFERENCES operators(id),
    operator_id    BIGINT REFERENCES operators(id),
    personnel_count SMALLINT,
    chamber_no     SMALLINT,
    product_code   TEXT REFERENCES products(canonical_code),
    finger_count   SMALLINT,
    column_count   SMALLINT,
    dryer_waste    NUMERIC,
    source         TEXT DEFAULT 'historical'
);
CREATE TABLE setting_shift_unloads (
    id            BIGSERIAL PRIMARY KEY,
    operation_id  BIGINT NOT NULL REFERENCES setting_operations(id) ON DELETE CASCADE,
    shift         SMALLINT,
    sub_id        SMALLINT,
    UNIQUE (operation_id, shift)
);
CREATE TABLE setting_wagons (
    id              BIGSERIAL PRIMARY KEY,
    shift_unload_id BIGINT NOT NULL REFERENCES setting_shift_unloads(id) ON DELETE CASCADE,
    wagon_no        TEXT NOT NULL,
    glaze           TEXT,                 -- kept as text (M1-A2)
    start_time      TEXT,
    end_time        TEXT,
    packages        NUMERIC,
    source          TEXT DEFAULT 'historical',
    UNIQUE (shift_unload_id, wagon_no)
);
CREATE TABLE wagon_master (
    id             BIGSERIAL PRIMARY KEY,
    wagon_no       TEXT NOT NULL UNIQUE,  -- one physical unit (M1-E4)
    first_seen     TEXT,
    last_seen      TEXT,
    total_packages NUMERIC,
    source         TEXT DEFAULT 'historical'
);

-- ============================================================
-- 6. PACKING
-- ============================================================
CREATE TABLE packing_records (
    id             BIGSERIAL PRIMARY KEY,
    date_jalali    TEXT NOT NULL,
    month          TEXT,                     -- source mixes number (1-12) and name (فروردین)
    day            TEXT,
    shift          SMALLINT,
    controller     TEXT,
    worker_type    TEXT,
    worker_count   SMALLINT,
    product_code   TEXT REFERENCES products(canonical_code),
    wagon_no       TEXT REFERENCES wagon_master(wagon_no),  -- traceability
    total          NUMERIC,
    grade1         NUMERIC,
    grade2         NUMERIC,                 -- = waste; carry if present (M1-E1)
    waste          NUMERIC,
    efficiency_raw NUMERIC,                 -- analytic, stored raw
    source         TEXT DEFAULT 'historical',
    natural_key    TEXT UNIQUE              -- (date_jalali,shift,wagon_no,product_id)
);

-- ============================================================
-- 7. REVIEW QUEUE (P2/P5 — holds flagged rows)
-- ============================================================
CREATE TABLE review_queue (
    id           BIGSERIAL PRIMARY KEY,
    table_name   TEXT NOT NULL,
    natural_key  TEXT,
    field_name   TEXT,
    raw_value    TEXT,
    issue_class  TEXT NOT NULL,  -- Valid/Warning/Invalid/Duplicate/Unmapped/NeedsReview
    suggested_fix TEXT,
    resolved     BOOLEAN DEFAULT FALSE,
    resolved_by  TEXT,
    note         TEXT
);

-- ============================================================
-- 8. INDEXES (idempotent upsert support)
-- ============================================================
CREATE INDEX ix_dryer_op_nk      ON dryer_operations(natural_key);
CREATE INDEX ix_kiln_push_nk     ON kiln_pushes(natural_key);
CREATE INDEX ix_setting_op_bk    ON setting_operations(batch_key);
CREATE INDEX ix_setting_wagon    ON setting_wagons(shift_unload_id, wagon_no);
CREATE INDEX ix_packing_nk       ON packing_records(natural_key);
CREATE INDEX ix_dryer_read_op    ON dryer_readings(operation_id);
CREATE INDEX ix_kiln_temp_push   ON kiln_temperature_readings(push_id);
CREATE INDEX ix_review_tbl       ON review_queue(table_name, resolved);

-- ============================================================
-- 9. SEED config (owner-confirmed bounds)
-- ============================================================
INSERT INTO config_chamber_bounds (chamber_max, note) VALUES (40, 'owner-confirmed 2026-08-17');
INSERT INTO config_shift_pattern (id, shift_code, shift_name) VALUES
    (1, 1, 'صبح'), (2, 2, 'عصر'), (3, 3, 'شب');
INSERT INTO config_wagon_bounds (wagon_max, note) VALUES (80, 'owner-confirmed; >80 = typo');
INSERT INTO config_temp_bounds (kiln_temp_max, note) VALUES (1200, 'kiln tolerance 1100-1200; >1200 = typo');
INSERT INTO config_drying_cadence (hours_step) VALUES (3);
