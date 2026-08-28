-- ============================================================================
-- MES Database — Wagon linking across modules (Setting -> Kiln -> Packing)
-- Target: PostgreSQL 16 (staging)
-- Design basis (owner-confirmed physical model, 2026-08-27):
--   * wagon_no is a PHYSICAL NAME/PLATE (e.g. '12'), not a sequence counter.
--   * A wagon is loaded in Setting, waits in "salon-e-entezar" (waiting hall),
--     then enters the Kiln tunnel as ONE push (1 wagon per push row in the source).
--   * The kiln is a FIFO conveyor of FIXED capacity 44 (always exactly 44 wagons
--     inside). A wagon entering at push P exits at push P+43, deterministically.
--   * On exit it goes to a "list of awaiting discharge" (kiln_exit), and Packing
--     later takes one or several wagons from that list.
-- This DDL is ADD-ONLY (no DROP) so existing loaded data is preserved.
-- ============================================================================

-- 1. Wagon master: one row per physical wagon name
CREATE TABLE IF NOT EXISTS wagon (
    wagon_id    BIGSERIAL PRIMARY KEY,
    wagon_name  VARCHAR(20) UNIQUE NOT NULL,   -- the plate number, e.g. '12'
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 2. kiln_push gets a sequential push number (1,2,3... by time) for FIFO math
ALTER TABLE kiln_push ADD COLUMN IF NOT EXISTS push_seq BIGINT UNIQUE;

-- 3. Link columns on the fact tables (wagon FK, nullable, additive)
ALTER TABLE setting_wagon ADD COLUMN IF NOT EXISTS wagon_id INTEGER REFERENCES wagon(wagon_id);
ALTER TABLE kiln_wagon    ADD COLUMN IF NOT EXISTS wagon_id INTEGER REFERENCES wagon(wagon_id);
ALTER TABLE packing_wagon ADD COLUMN IF NOT EXISTS wagon_id INTEGER REFERENCES wagon(wagon_id);

-- 4. kiln_exit: the "awaiting discharge" list (waits for Packing to take it)
CREATE TABLE IF NOT EXISTS kiln_exit (
    kiln_exit_id   BIGSERIAL PRIMARY KEY,
    wagon_id       INTEGER NOT NULL REFERENCES wagon(wagon_id),
    entry_push_seq INT,                      -- push where the wagon entered the kiln
    exit_push_seq  INT,                       -- = entry_push_seq + 43 (deterministic)
    exit_date      VARCHAR(10),              -- 'YYYY.MM.DD' of the exit push
    discharged     BOOLEAN DEFAULT FALSE,    -- set TRUE when Packing consumes it
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (wagon_id, exit_push_seq)
);

CREATE INDEX IF NOT EXISTS idx_kiln_exit_undischarged ON kiln_exit(wagon_id) WHERE NOT discharged;

COMMENT ON TABLE wagon IS 'One physical wagon (by plate name) — shared across Setting/Kiln/Packing journeys';
COMMENT ON TABLE kiln_exit IS 'Awaiting-discharge list: a wagon leaves the kiln at push_seq+43 and waits here for Packing';
COMMENT ON COLUMN kiln_push.push_seq IS 'Sequential push number (1,2,3...) for deterministic 44-push FIFO math';
