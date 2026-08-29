# M5_PROPOSED_SCHEMA — Consolidated schema reference (100%)

> Single source of truth for the M5 application schema. Maps the **conceptual model** to the
> **actual staging tables** (already loaded, DDL `sql/schema/30–36_*.sql`), and explicitly
> flags the 30% of the system that is ETL-heavy (sensor temps, FIFO linking, glaze, trip).
> Per ADR-0008 the app core models these cleanly; the ETL layer owns the messy reconciliation.

## 1. Naming map (conceptual → staging)

| Conceptual (earlier drafts) | Staging table (CANONICAL) | Notes |
|------------------------------|----------------------------|-------|
| Setting_Header | `setting_event` | one row per (date, shift, chamber, supervisor) |
| Setting_Wagons | `setting_wagon` | 1–4 wagons per event; `glaze_id` FK + raw `glaze_type` |
| Dryer_Header | `dryer_cycle` | one drying cycle per chamber load/unload |
| Kiln_Cycle | `kiln_push` | one push = one wagon; `push_seq` = physical order |
| Kiln_Wagons | `kiln_wagon` | links push → wagon plate |
| (Kiln temps) | `kiln_reading` | **separate** — 18 sensors × push, row-oriented |
| Packing_Header | `packing_header` | one packing batch |
| — | `kiln_sensor` | 18 sensor definitions (reference) |
| — | `kiln_exit` | FIFO-44 discharge waiting list |
| — | `wagon_trip` | trip spine (populated by app, empty in staging) |
| — | `glaze` | glaze dimension master (36_glaze.sql) |
| — | `wagon` | 89 physical plate names |
| — | `chamber` | 40 dryer chambers (CH01–CH40) |
| — | `operator` / `product` | dimension masters (ADR-0006) |

## 2. The 30% — ETL-heavy parts (explicit)

### 2.1 Sensor temperature model (Kiln)
- **Reality:** 698,014 rows in `kiln_reading`, each = (push_seq, sensor, value). 18 sensors defined in `kiln_sensor`.
- **Why separate:** sensor count grew over time (1 in 1398 → 18 in 1404), so a column-per-sensor design would break. Row-oriented is required.
- **App core:** `kiln_reading(kiln_push_id FK, sensor_id FK, value)` — clean. No app logic for missing sensors; ETL recovers any present value (merge-first-valid).

### 2.2 Wagon linking — FIFO-44
- **Reality:** tunnel capacity is FIXED 44. Wagon entering at `push_seq` P exits at `push_seq` P+43.
- **Tables:** `wagon_trip` (spine) + `kiln_exit` (awaiting-discharge list, `exit_push_seq = entry_push_seq + 43`).
- **App core:** on Kiln push, system assigns `trip_id` (FK on kiln_wagon); on discharge, append to `kiln_exit`. No manual sequencing — deterministic FIFO.
- **ETL:** `etl_link.py` computes this from `row_seq`; 38,710/38,710 exits verified correct.

### 2.3 Glaze dimension (independent)
- **Reality:** `glaze` master (glaze_code/name/formula/description), seeded 7 distinct historical glazes.
- `setting_wagon.glaze_id` FK → `glaze`; raw `glaze_type` text retained for the 9 typo rows (ADR-0008 review).
- **App core:** glaze is a dropdown dimension, not free text.

### 2.4 Trip spine (wagon_trip)
- `wagon_trip(trip_id PK, wagon_id FK, started_at, completed_at, status, source_module)`.
- Empty in staging; **the M5 app assigns `trip_id` at Setting load start** (owner-approved 2026-08-29).
- `setting_wagon` / `kiln_wagon` / `packing_wagon` each carry `trip_id` FK.

## 3. Clean-core modeling rules (what the app assumes)

- Wagon identity = FK to `wagon(wagon_id)`; **no "wagon name > 80" validator** (ADR-0008).
- Dates/times = system-generated; no date-typo tolerance.
- Chamber = FK to `chamber` (1–40); Setting `chamber_no` is a REFERENCE to dryer chamber, not a Setting-owned chamber.
- Glaze = FK to `glaze`; typos stay in raw `glaze_type` for review.
- Trip = system-assigned sequential `trip_id`; never typed by operator.

## 4. Modules NOT yet in scope

| Module | Status | Note |
|--------|--------|------|
| Forming (فرم دهی) | deferred | owner: "فعلا نداریم" |
| Glazing (لعاب زنی) | deferred | owner: "فعلا نداریم"; glaze *dimension* exists, but no glazing *process* table yet |
| Waiting hall (سالن انتظار) | modeled as state | not a table — it is the `waiting_hall` state in `wagon_trip` between Setting and Kiln push |

## 5. Staging → App boundary

The staging load is the **historical data source**. Django migrations own the **application** schema.
The app schema mirrors §1 (canonical names) with the clean-core rules of §3. The 30% (§2) is
represented by clean FKs; all scrubbing/flagging lives in `scripts/historical_import/` only.

**Loaded row counts (verified 2026-08-29):**
`setting_event` 20,522 · `setting_wagon` 67,694 · `dryer_cycle` 18,558 · `dryer_reading` 18,370 ·
`kiln_push` 38,820 · `kiln_wagon` 38,820 · `kiln_reading` 698,014 · `kiln_sensor` 18 ·
`kiln_exit` 38,710 · `packing_header` 8,543 · `packing_wagon` 93,381 · `glaze` 7 · `wagon_trip` 0.
