-- 35_wagon_trip.sql
-- Wagon trip spine for the CLEAN app core (ADR-0008).
-- A "trip" = one wagon's journey from Setting load -> Kiln push -> Packing unload.
-- trip_id is assigned at LOAD START (per owner decision 2026-08-29), NOT at completion,
-- so an incomplete Setting load that finishes the next day still carries one trip_id.
-- Historical Excel defects are NOT modeled here (handled by the separate ETL layer).

CREATE TABLE IF NOT EXISTS wagon_trip (
    trip_id        BIGSERIAL PRIMARY KEY,
    wagon_id       INTEGER NOT NULL REFERENCES wagon(wagon_id),
    started_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),   -- when the Setting load began
    completed_at   TIMESTAMPTZ,                          -- NULL until the trip is finished
    status         VARCHAR(20) NOT NULL DEFAULT 'in_progress'
                   CHECK (status IN ('in_progress','completed','abandoned','incomplete')),
    source_module  VARCHAR(20) NOT NULL DEFAULT 'setting'
                   CHECK (source_module IN ('setting','kiln','packing','historical')),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_wagon_trip_wagon    ON wagon_trip(wagon_id);
CREATE INDEX IF NOT EXISTS ix_wagon_trip_status   ON wagon_trip(status);
CREATE INDEX IF NOT EXISTS ix_wagon_trip_started  ON wagon_trip(started_at);

-- Each fact row references the trip it belongs to.
-- NULL allowed so legacy/historical rows that have no mapped trip stay loadable.
ALTER TABLE setting_wagon  ADD COLUMN IF NOT EXISTS trip_id BIGINT REFERENCES wagon_trip(trip_id);
ALTER TABLE kiln_wagon     ADD COLUMN IF NOT EXISTS trip_id BIGINT REFERENCES wagon_trip(trip_id);
ALTER TABLE packing_wagon  ADD COLUMN IF NOT EXISTS trip_id BIGINT REFERENCES wagon_trip(trip_id);

CREATE INDEX IF NOT EXISTS ix_setting_wagon_trip ON setting_wagon(trip_id);
CREATE INDEX IF NOT EXISTS ix_kiln_wagon_trip    ON kiln_wagon(trip_id);
CREATE INDEX IF NOT EXISTS ix_packing_wagon_trip ON packing_wagon(trip_id);
