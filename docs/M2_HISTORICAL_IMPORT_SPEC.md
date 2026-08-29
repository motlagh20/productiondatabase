# M2 — Historical Data Import Specification

> **Purpose:** Defines exactly how the 22 authoritative workbooks (`xls/real data/`) are imported into the platform database, per the frozen M0 model (Appendix C §1–§15) and the resolved M1 domain questions. This is the **specification** for the import tooling (build phase), not the tooling itself.
> **Principles (from ADR-0001, PART_V, Master Rules §27/§32):** config-driven (not code), minimal change to source, no fabricated values (P2/P5), idempotent/upsert, validation-class driven with human review queue.
> **Status:** Draft for owner review.

---

## 1. Source inventory (authoritative, read-only)

| Family | Files | Sheet(s) used | Rows (approx) |
|---|---|---|---|
| Dryer | Dryer-1398…1404 (7 .xlsm) | Data Entry | ~6k |
| Kiln | Kiln-1398…1404 (7, 1398/99 .xlsx rest .xlsm) | Input | ~20k |
| Setting | Set_1398.xls + Set_1399…1404 (.xlsm) | Data | ~7k (1398) + ~6k each |
| Packing | Packing-All.xlsx | Sheet1 | 93,389 |

Excluded (P2 / analytic): `راندمان` rollups, `Rand_*`, `Analyse*`, `Tabarestan`, `Note`, `Access`, `error`, backup sheets.

## 2. Code-page / encoding

- All `.xlsm`/`.xlsx` read with `openpyxl` (data_only=True, read_only=True).
- `Set_1398.xls` read with `xlrd` (legacy). MojiBake in Note sheet is analytic — ignored.
- Source is **cp1256** (Persian). Decode as cp1256; never assume UTF-8 (Appendix C §7).

## 3. Per-family import map

### 3.1 Dryer → `dryer_operations` + `dryer_readings`
- **Header row** (`dryer_operations`): date_jalali, month, day, shift, operator_load, operator_unload, product_name, product_code, finger_count, chamber_no, duration, notes.
- **Temp/humidity** (`dryer_readings`): parse the **header row above the 2 data rows** for hour labels (0,3,6…). For each chamber op: row above data = temp, row below = humidity. Emit `(op_id, hour_offset, metric, value)` rows. **Blank cell = skip (not zero).** Variable column count → do NOT hard-code 51.
- **Bounds:** chamber 1–40 (flag >40), shift 1–3 (flag), finger 1–20 plausible (flag outside).
- **Product:** re-derive canonical code from (نوع محصول + شرح محصول) per M1-A1; map via `product_mapping_blueprint.csv`.

### 3.2 Kiln → `kiln_pushes` + `kiln_temperature_readings`
- **Push row** (`kiln_pushes`): date_jalali, hour, shift, operator, product (code+type), input_type (خام/شارژی ≡ خشت خام/سفال پخته), incoming_car_id (= wagon_no), pushing_time_min, push_seq.
- **Temps** (`kiln_temperature_readings`): 18 `temp_*` columns (1404) OR single `دمای اگزوز` (1398–1403). Map each column to (group, reading_type) via **config vocab** (Appendix C §12). Row-oriented.
- **Bounds:** temp >1200 °C → **Invalid/Review** (×10 typo pattern; ÷10 suggested, owner confirms). Wagon 1–80 (flag >80). input_type enum.

### 3.3 Setting → `setting_operations` + `setting_shift_unloads` + `setting_wagons` + `wagon_master`
- **Header** (`setting_operations`): date_jalali, shift, supervisor_id, operator_code, personnel_count, chamber_no, product, finger_count, column_count, dryer_waste. Batch key = `ID` (NOT surrogate PK).
- **Per shift-unload** (`setting_shift_unloads`): composite (ID, shift).
- **Per wagon** (`setting_wagons`): FK SettingID → ID; wagon_no, glaze_id (FK→glaze master), glaze_type (raw text), start_time, end_time, packages.
- **wagon_master**: aggregate `wagon_no` across all ops (cross-chamber/cross-shift continuous entity, ADR-0005).
- **Repeating blocks**: Set `Data` has 1–4 wagon blocks (cols 12–19, 20–27, 28–35, 36–43) → parse by block pattern, not fixed index.
- **Glaze**: `glaze` is an independent **dimension table** (`glaze` with glaze_code/glaze_name/formula/description, 36_glaze.sql). `setting_wagon.glaze_id` links to it; raw `glaze_type` text retained for typo review (ADR-0008). Seeded 7 distinct historical glazes; 9 typo rows (??, 20:45, etc.) left unmapped.
- **Bounds:** chamber 1–40, shift 1–3, wagon 1–80 (flag).

### 3.4 Packing → `packing_records`
- Columns: date_jalali, month, day, shift, controller, worker_type, worker_count, product (re-derived from نوع+شرح per M1-A1), wagon_no (1–80 flag), total, grade1, grade2 (=waste; carry if present, blank if absent per M1-E1), waste, efficiency (analytic — store raw, re-derive later).
- **Product codes 1–28** mapped to canonical via `product_mapping_blueprint.csv` (§11.1): note code 20 → P-PANJEH-SABZ.
- **Year 1397** has only months 1–10 → import as-is; complete months 11–12 post-build (idempotent re-import).
- **Wagon traceability**: `wagon_no` here = same physical unit as Setting/Kiln (M1-E4) → enable FK to `wagon_master`.

## 4. Cleaning / mapping layer (config-driven)

For each source, an **import mapping definition** (versioned, Master Rules §18) declares:
- column → target field
- value normalization (e.g. اخراء→اخرا, 2-digit year→13xx, HH:MM strip seconds)
- code → canonical mapping (operator / product / glaze blueprints)
- bound/plausibility rules (chamber 40, shift 3, wagon 80, temp 1200)
- validation class per cell: **Valid / Warning / Invalid / Duplicate / Unmapped / Needs Review**

No synthetic fallback values (P2/P5). Unmapped/empty → **Needs Review queue**, never auto-filled.

## 5. Validation classes & review queue

| Class | Example | Action |
|---|---|---|
| Valid | chamber 18, shift 2, temp 930 | load |
| Warning | wagon 81 (typo) | flag, load with review mark |
| Invalid | temp 9930 (>1200) | flag ×10, hold for review |
| Duplicate | Setting ID repeated (multi-shift) | keep as separate shift-unload row |
| Unmapped | product code not in blueprint | route to REVIEW_product |
| Needs Review | grade-2 value present | load as-is, mark for QA |

Review outputs → `xls/consolidated/REVIEW_*.txt` (as built in M0 phase) + DB review table.

## 6. Idempotency / upsert

- Natural key per family: e.g. `(date_jalali, shift, chamber_no, wagon_no)` for setting; `(date_jalali, hour, wagon_no)` for kiln.
- Re-running import (e.g. after 1397 completion or typo correction) **merges**, never duplicates (Master Rules §32, owner 2026-08-17).
- **No destructive merge** of setting wagons — aggregation is a query (ADR-0005).

## 7. Reconciliation gates (before sign-off of import run)

1. Row counts per family match source (± review-queued).
2. All product codes map (0 Unmapped after review resolution).
3. All wagons 1–80 except flagged (>80 → review).
4. All kiln temps ≤1200 except flagged.
5. Setting wagon_master count = distinct wagon_no across ops.

## 8. Open items carried to build phase

- **P1 (refine):** exact meaning of «تعداد ستون», «کارکرد», «صحت اعداد», MojiBake `پ`, Kiln «پوشینگ»/«لوله», Packing «نوع کارگران» garbage, «کنترلر»/«کد اقتصادی».
- **P2 (post-build):** 1397 months 11–12, wagon/operator typo corrections from physical ledgers, numerical-error QA pass (owner: frequent).

---
*Generated 2026-08-20. Depends on: Appendix C §1–§15, ADR-0001/0005/0006, M1 (P0 resolved), PART_V_ADDENDUM (config-driven layer), product/glaze/operator blueprints.*
