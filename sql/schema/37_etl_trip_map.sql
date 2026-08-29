-- 37_etl_trip_map.sql
-- ETL reconciliation map: links each historical Excel row (by row_seq / source_row) to the
-- clean-core trip_id assigned by the M5 app. This is the bridge described in M5_SRS §5
-- ("an ETL map (etl_trip_map) reconciles them to the clean core post-build").
--
-- Per ADR-0008 this table lives in the ETL/historical layer ONLY — it is NOT an app model.
-- It is populated after the clean core exists, by a reconciliation script that matches
-- Setting load → Kiln push → Packing unload via wagon name + 1..10 day window evidence.
--
-- It is created empty now (schema-ready); the ownership/population logic is a separate
-- historical-ETL step, not part of M5 v1 app code.

CREATE TABLE IF NOT EXISTS etl_trip_map (
    map_id        BIGSERIAL PRIMARY KEY,
    source_module TEXT NOT NULL,        -- 'setting' | 'kiln' | 'packing'
    source_row    INTEGER NOT NULL,     -- the file-wide row_seq used by etl_*.py (not Excel 'ردیف')
    trip_id       BIGINT,               -- FK to wagon_trip once the app assigns trips (NULL until reconciled)
    wagon_id      BIGINT,               -- FK to wagon (plate name resolved)
    matched_at    TIMESTAMPTZ,
    note          TEXT,
    UNIQUE (source_module, source_row)
);

CREATE INDEX IF NOT EXISTS ix_etl_trip_map_trip ON etl_trip_map(trip_id);
CREATE INDEX IF NOT EXISTS ix_etl_trip_map_wagon ON etl_trip_map(wagon_id);

-- NOTE: no INSERT here. Population is the responsibility of the historical ETL reconciliation
-- step (post M5 build), which reads setting_wagon/kiln_wagon/packing_wagon source_row values
-- and resolves them to wagon_trip.trip_id. See M5_SRS §5 and ADR-0008.
