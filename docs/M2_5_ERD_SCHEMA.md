# M2.5 — Database ERD / Schema Specification

> **Purpose:** Logical ERD + table definitions for the platform database (PostgreSQL 16), derived from the M0 model (Appendix C §1–§15) and resolved M1 questions. Per Master Rules §27 (P1: config over code) and §32 (no Excel-shaped schema), bounds live in **config tables**, not CHECK constraints. Row-oriented for variable-count series (kiln temps, dryer temp/humidity, setting wagons).
> **Status:** *Target ERD for the final app schema.* A **staging load** (DDLs `sql/schema/30–33_*.sql`) has been executed on PostgreSQL 16 with **row-oriented tables that differ in name/shape** from the spec below (e.g. `kiln_push`+`kiln_wagon`+`kiln_reading`+`kiln_sensor` instead of `kiln_pushes`+`kiln_temperature_readings`). The staging tables are a working historical load; this ERD remains the canonical target the final app schema should converge to. See README "Deviation note" + `docs/IMPORT_RUNBOOK.md`.

---

## 1. Design rules

- **Config over code (P1):** chamber_max=40, shift_count=3, wagon_max=80, kiln_temp_max=1200, drying cadence=3h → all in `config_*` tables, never hard-coded.
- **No fabricated values (P2/P5):** every unmapped/empty field → `needs_review` flag, never synthetic fill.
- **Canonical, not Excel-shaped:** tables model business entities (operation, wagon, reading), not source columns.
- **Idempotent upsert:** natural keys defined per table; re-import merges.
- **One model, two sources (§53.21):** historical (migrated) and live (app-created) rows share the same tables, distinguished by `source` flag.

## 2. Entity overview

```
config_chamber_bounds ─┐
config_shift_pattern  ─┤  (parameter tables, P1)
config_wagon_bounds  ─┤
config_temp_bounds   ─┘

operators (personnel)        products (composite)       glazes (text vocab)
     │                            │                          │
     └──── reference by FK ───────┴──────────────────────────┘

dryer_operations ──< dryer_readings (temp/humidity, row-oriented)
kiln_pushes      ──< kiln_temperature_readings (18 zones, row-oriented)
setting_operations ─< setting_shift_unloads ─< setting_wagons
wagon_master (aggregates wagon_no across ops)
packing_records
     │
     └── wagon_master (FK, traceability setting→kiln→packing)

review_queue (holds Invalid/Warning/Needs-Review rows)
```

## 3. Tables

### 3.1 Configuration (P1 — bounds live here)
```sql
config_chamber_bounds(id, chamber_max, note)            -- 40
config_shift_pattern(id, shift_code, shift_name, start, end)  -- 1..3 صبح/عصر/شب
config_wagon_bounds(id, wagon_max, note)                -- 80
config_temp_bounds(id, kiln_temp_max, note)             -- 1200
config_drying_cadence(id, hours_step, note)             -- 3
```

### 3.2 Dimensions (reference)
```sql
operators(id PK, code, full_name, role, source)         -- full_name immutable (§32)
products(id PK, canonical_code, mold_type, glaze,        -- composite (ADR-0006)
         description, source)
glazes(id PK, glaze_value, normalized, is_combined, note) -- text vocab, validation only
```

### 3.3 Dryer
```sql
dryer_operations(id PK, date_jalali, month, day, shift,
                 operator_load_id FK, operator_unload_id FK,
                 product_id FK, finger_count, chamber_no,
                 duration, notes, source, natural_key UNIQUE)
dryer_readings(id PK, operation_id FK, hour_offset INT,
               metric TEXT CHECK(metric IN ('temp','humidity')),
               value NUMERIC, source)
-- hour_offset parsed from header row; blank cell = row not inserted
```

### 3.4 Kiln
```sql
kiln_pushes(id PK, date_jalali, hour, shift, operator_id FK,
             product_id FK, input_type TEXT CHECK(input_type IN
             ('خشت خام','سفال پخته')),  -- canonical; 1398-1403 خام/شارژی mapped
             incoming_car_id,  -- = wagon_no
             pushing_time_min, push_seq, source, natural_key UNIQUE)
kiln_temperature_readings(id PK, push_id FK,
             zone_group TEXT, zone_reading TEXT,  -- (exhaust/preheat/thermostat/zone/rapid/bottom, index)
             value NUMERIC, source)
-- 18 zones → row-oriented; >1200 → review flag
```

### 3.5 Setting (4-layer, ADR-0005)
```sql
setting_operations(id PK, batch_key TEXT,  -- the legacy ID, NOT surrogate
                   date_jalali, shift, supervisor_id FK, operator_id FK,
                   personnel_count, chamber_no, product_id FK,
                   finger_count, column_count, dryer_waste, source)
setting_shift_unloads(id PK, operation_id FK, shift, sub_id,
                       UNIQUE(operation_id, shift))
setting_wagons(id PK, shift_unload_id FK, wagon_no, glaze TEXT,
               start_time, end_time, packages, source)
wagon_master(id PK, wagon_no UNIQUE,
             first_seen, last_seen, total_packages,  -- aggregated across ops
             source)
-- setting_wagons.wagon_no → wagon_master.wagon_no (cross-chamber/cross-shift)
```

### 3.6 Packing
```sql
packing_records(id PK, date_jalali, month, day, shift, controller,
                worker_type, worker_count, product_id FK,
                wagon_no FK→wagon_master,  -- traceability (M1-E4)
                total, grade1, grade2,  -- grade2 = waste; carry if present
                waste, efficiency_raw,  -- analytic stored raw, re-derived later
                source, natural_key UNIQUE)
```

### 3.7 Review queue (P2/P5)
```sql
review_queue(id PK, table_name, natural_key, field_name,
             raw_value, issue_class,  -- Valid/Warning/Invalid/Duplicate/Unmapped/NeedsReview
             suggested_fix, resolved BOOL, resolved_by, note)
```

## 4. Relationships
- `operators` ← dryer/kiln/setting (by id; name never altered)
- `products` ← all fact tables (canonical, re-derived from نوع+شرح per M1-A1)
- `wagon_master` ← setting_wagons, kiln_pushes.incoming_car_id, packing_records.wagon_no (one physical unit, M1-E4)
- `review_queue` ← any table row that failed a validation class

## 5. Indexes / upsert keys (idempotency)
- dryer_operations: (date_jalali, shift, chamber_no, product_id)
- kiln_pushes: (date_jalali, hour, incoming_car_id)
- setting_operations: (batch_key) — batch_key is the natural op key
- setting_wagons: (shift_unload_id, wagon_no)
- packing_records: (date_jalali, shift, wagon_no, product_id)
- Re-import → ON CONFLICT DO UPDATE (no duplicate rows; M1/M2 idempotency rule)

## 6. Excluded (P2 / analytic, not migrated as raw)
`راندمان` rollups, `Rand_*`, `Analyse*`, `Tabarestan`, `Note`. Re-derived later from facts.

## 7. Open P1 items to resolve before DDL build
- «تعداد ستون» / «کارکرد» / «صحت اعداد» exact meaning (Set)
- Kiln «پوشینگ» / «لوله باتوم/خشک کن» meaning
- Packing «نوع کارگران» (garbage dates), «کنترلر», «کد اقتصادی»
- MojiBake `پ` column (Set)

---
*Generated 2026-08-20. Depends on: Appendix C §1–§15, ADR-0005/0006, M1 (P0 resolved), M2 import spec, MASTER_SPEC §I.3 (PostgreSQL 16 stack).*
