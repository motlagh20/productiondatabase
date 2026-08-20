# Appendix B — Data Assets Catalog (`xls/`)

- **Project:** Manufacturing Analytics & Execution Platform
- **Document status:** Evidence catalog — seed for the future Historical Data Migration Specification (Phase 8; Master Rules §6–§19, §33–§37)
- **Version:** 0.1
- **Date:** 2026-07-30

> The files below are **protected source data** (Master Rules §44: never overwrite source data; §53.11: source data must not be destroyed during migration). They are CSV exports of the plant's operational Excel workbooks, covering (at least) early Jalali year **1404**. The plant holds ~15 further years of history not yet supplied (Master Rules §17); this catalog covers only what is in the repository today.
>
> Row counts verified by direct count on 2026-07-30 (excluding header). "Mapping status" refers to whether the frozen reference app has any import/mapping path for the file — **no transactional file has an importer**; only three master-data files have SQL mapping seeds in `xls/init/`.

---

## 1. Transactional datasets (Master Rules Datasets A–D + kiln)

### B.1 `Dryer.csv` — Dataset A (dryer chamber load/unload)
- **Rows:** 835
- **Columns:** `ChamberNo, LoadDateJalali, LoadTime, LoadOperatorCode_FK, ProductCode_FK, UnloadDateJalali, UnloadTime, LoadOperatorCode_FK.1, loadFingerCount`
- **Sample:** `10, 1404-01-05, 8:20:00, 4, 91000000, 1404-01-09, 15:40:00, 5, 8`
- **Known quality problems:** dates use dash separator (`1404-01-05`); times unpadded text (`8:20:00`); header `LoadOperatorCode_FK.1` is an export artifact meaning *unload* operator; some rows missing unload values; `ProductCode_FK` holds mold-family codes.
- **Mapping status:** **No importer.** Target: dryer loading/unloading operation records.

### B.2 `Setting_wagons.csv` — Dataset B (wagon / glaze / packages)
- **Rows:** 2,481
- **Columns:** `SettingID, wagon_no, GlazeType, start_time, end_time, packages`
- **Sample:** `1404010718, 75, 91000001, 06:25:00, 07:25:00, 64`
- **Known quality problems:** `SettingID` repeats by design (one setting = many wagons); same wagon repeated within a setting with split quantities (partial fills, e.g. 4 + 60 = 64); times as text.
- **Mapping status:** **No importer.** Target: setting→wagon allocation records.

### B.3 `Setting_Setting.csv` — Dataset C (setting / shift / supervision)
- **Rows:** 992
- **Columns:** `date_jalali, shift, supervisorID, OperatorCode_FK, personnel_count, chamber_no, productName, fingers_count, columns_count, dryer_waste, ID`
- **Sample:** `1404/1/7, 1, 1, 9, 3, 18, 91000000, 7, 2, 150, 1404010718`
- **Known quality problems:** dates use slash separator without zero-padding (`1404/1/7`); **duplicate `ID` values** (`1404010913`, `1404011009`, `1404011404`, `1404011612`) — the ID must not become a primary key (Master Rules §9); `productName` holds mold codes.
- **Mapping status:** **No importer.** Target: setting operation records (context for B.2).

### B.4 `Packing.csv` — Dataset D (grading / quality / waste)
- **Rows:** 2,065
- **Columns:** `date_jalali, shift, OperatorCode_FK, typeOfWorkers, workerscount, productName, GlazeType, wagon_no, TotalCount, Grade1Count, WasteCount`
- **Sample:** `1404/01/04, 1, 1, , , 91000000, 91000001, 75, 1128, 1000, 128`
- **Known quality problems:** missing values (`typeOfWorkers`, `workerscount` empty in many rows); do **not** assume `TotalCount = Grade1Count + WasteCount` (Master Rules §10); slash dates with zero-padding (third distinct date convention).
- **Mapping status:** **No importer.** Target: inspection/quality-result records with configurable outcomes.

### B.5 `Kiln.csv` — kiln push + temperature profile
- **Rows:** 2,821
- **Columns (24):** `date_jalali, OperatorCode_FK, PushingTime_min, IncomingCarID, productName, GlazeType, temp_exhaust, temp_preheat01, temp_preheat02, temp_termostat, temp_Zone00…temp_Zone07, temp_rapid01, temp_Rapid02, temp_bottomA, temp_bottom01, temp_bottomB, temp_bottom02` (18 temperature points)
- **Sample:** `1404.01.01, 8, 1:20:00, 31, 90000001, 91000001, 190, 402, 531, 755, 820, 925, 950, 950, 935, 891, 841, 786, 607, 572, 556, 523, 408, 356`
- **Known quality problems:** dot-separated dates (`1404.01.01` — fourth format variant); `PushingTime_min` holds `H:MM:SS` text despite the `_min` name; inconsistent column-name casing (`temp_rapid01` vs `temp_Rapid02`); misspelled `temp_termostat`; **unmapped product codes** `productName ∈ {90000001, 90000002, 99999999}` — all absent from every reference CSV (needs plant validation); `GlazeType = 94000002` also unmapped; no shift column (unlike C/D). *Corroborated by [Appendix C §3](./APPENDIX_C_DATA_VS_SCHEMA.md).*
- **Mapping status:** **No importer.** Target: kiln push operation records + equipment measurements.

## 2. Reference (master) data

### B.6 `Categories.csv`
- **Rows:** 5 — `ProductCategoriesID, ProductCategories`: `1 سفال, 2 تیزه, 3 پنجه ای, 4 نیمه, 5 آجر`
- **Mapping status:** **Mapped** — `xls/init/03_map_categories.sql` seeds `app.categories`.

### B.7 `Molds.csv`
- **Rows:** 3 — `MoldID, MoldsName, Unnamed: 2`: `91000000 طبرستان (1), 92000000 پرتغالی (2), 81000000 20*10*20 (3)`
- **Quality:** pandas `Unnamed: 2` artifact column (internal category number).
- **Mapping status:** **Mapped** — `xls/init/05_map_molds.sql`.

### B.8 `Glaze.csv`
- **Rows:** 24 — `TypeID, TypeName, Unnamed: 2`: 3 families (91/92/93) × 8 finishes (خودرنگ, اخرا, سبز, نوک مدادی, بیرنگ, مشکی, مولتی مشکی, لعاب آزمایشی)
- **Quality:** `Unnamed: 2` artifact column.
- **Mapping status:** **Mapped** — `xls/init/04_map_glazes.sql`.

### B.9 `ProductName.csv`
- **Rows:** 4 — `ID, ProductName`: `11000001 سفال طبرستان خودرنگ, 21000001 تیزه طبرستان خودرنگ, 31000001 تیزه انتهایی طبرستان خودرنگ, 53000001 تیغه 20*10*20`
- **Quality:** these composed product codes use a *different* numbering scheme from the mold/glaze codes used in the transactional files — part of the mold-vs-product ambiguity (§54).
- **Mapping status:** **No importer** (the reference app *generates* product codes via trigger instead of importing these).

### B.10 `Operators.csv`
- **Rows:** 10 — `OperatorCode, operator`: codes 1–11 (not contiguous) with Persian names; overlapping family names across codes (e.g. علی پناه / علیپناه, عموزاد ×2, یخکشی ×2) — operator-code ambiguity (Master Rules §19).
- **Mapping status:** **No importer** (reference app seeds its own users separately).

### B.11 `Supervisors.csv`
- **Rows:** 2 — `supervisorID, supervisors`: `1 شاکر, 2 عموزاد`
- **Mapping status:** **No importer.**

## 3. Non-data content inside `xls/` (schema copy)

`xls/init/*.sql`, `xls/schema/`, `xls/views/`, `xls/queries/` are an **older copy of the reference app's SQL schema** plus the three master-data mapping seeds — not data assets. They are cataloged as schema copy #3 in [Appendix A §2](./APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md) and are frozen with the app.

## 4. Summary table

| File | Rows | Dataset | Mapping status |
|---|---:|---|---|
| `Dryer.csv` | 835 | A — dryer load/unload | No importer |
| `Setting_wagons.csv` | 2,481 | B — wagon/glaze/packages | No importer |
| `Setting_Setting.csv` | 992 | C — setting/shift/supervision | No importer |
| `Packing.csv` | 2,065 | D — grading/quality/waste | No importer |
| `Kiln.csv` | 2,821 | Kiln push + temperatures | No importer |
| `Categories.csv` | 5 | Reference | Mapped (`03_map_categories.sql`) |
| `Molds.csv` | 3 | Reference | Mapped (`05_map_molds.sql`) |
| `Glaze.csv` | 24 | Reference | Mapped (`04_map_glazes.sql`) |
| `ProductName.csv` | 4 | Reference | No importer |
| `Operators.csv` | 10 | Reference | No importer |
| `Supervisors.csv` | 2 | Reference | No importer |

**Total transactional records currently in repository: 9,242** (835 + 2,481 + 992 + 2,065 + 2,821). *Corrected 2026-08-15 from an earlier 9,194 — recounted directly from the CSVs.*

## 5. Requirements this catalog imposes on the migration design (Phase 8)

1. Staging tables preserving every original value verbatim, with lineage (file, row, import batch, mapping version — Master Rules §18).
2. A Jalali date parser accepting all four observed conventions (`-`, `.`, `/` padded, `/` unpadded) producing the canonical temporal representation plus preserved original text (Master Rules §20).
3. Duplicate-ID resolution strategy for Dataset C (business-key discovery, flagged review queue — Master Rules §9, §33).
4. Code-mapping tables for mold/glaze/category/product/operator codes, including **unmapped-code handling** (e.g. `90000001/90000002/99999999` in `Kiln.csv`, `140` operator in `Setting_Setting.csv`, `22` shift in `Packing.csv`, `81000001` glaze, `93000000` product — see [Appendix C §3](./APPENDIX_C_DATA_VS_SCHEMA.md)).
5. Validation classification per record: `Valid / Warning / Invalid / Duplicate / Needs Review / Mapped / Unmapped` (Master Rules §19).
6. A data-quality report per import batch (Master Rules §37).

---

## 6. Authoritative source of truth — `xls/real data/` (the plant's native workbooks)

**As of 2026-08-15 the owner placed the plant's native Excel files in `xls/real data/`.** These are the **authoritative source** — the `xls/*.csv` files (cataloged above) are an *intentional normalized-design prototype* (one shared operators master, header/detail Setting pair, separated dimensions), **not** a 1:1 extraction of these workbooks (see [Appendix C §7](./APPENDIX_C_DATA_VS_SCHEMA.md)). The native workbooks are the reference the platform must ultimately ingest.

| Family | Files (Jalali year) | Format | ~Size |
|---|---|---|---|
| **Dryer** | `Dryer-1398` … `Dryer-1404` (7 files) | `.xlsm` | ~17 MB |
| **Kiln** | `Kiln-1398` … `Kiln-1404` (7 files) | `.xlsm` (1398/1399 also have `.xlsx` valid copies) | ~24 MB |
| **Setting** | `Set_1398` (`.xls`) + `Set_1399` … `Set_1404` (7 `.xlsm`) | `.xls` / `.xlsm` | ~33 MB |

Total **19 files, ~75 MB**, spanning **15 years (1398–1404)** of operational history — far beyond the 1404-only CSV prototype.

**Structural notes (verified read-only):**
- Each workbook's data lives on a named sheet — Dryer: `Data Entry` (≈75 cols, incl. 0–150 timing + chamber temps); Kiln: `Input` (≈27 cols, ~15,400 data rows/yr); Setting: `Data` (≈56 cols, multi-shift unload rows). A `CODE` sheet holds product/operator lookups.
- The Setting `ID` (date+chamber) **repeats across shifts** — one chamber loading unloaded over two shifts (domain rule, [ADR-0005](./../adr/ADR-0005-setting-three-layer-model.md)).
- **Corrupt originals recovered:** the original `Kiln-1398.xlsm` / `Kiln-1399.xlsm` were truncated (failed to open as zip — power-loss history). The owner re-saved them as `Kiln-1398.xlsx` / `Kiln-1399.xlsx`, which open correctly and carry the full ~15,400-row history each. The corrupt `.xlsm` copies were removed (2026-08-15); the `.xlsx` copies are now authoritative for those two years.
- `.xlsm`/`.xlsx` binary workbooks are **outside CSV tooling**; ingestion requires a reproducible extraction step (openpyxl-style reader → staging) defined in the M2 mapping spec, not ad-hoc manual CSV export.

**Implication:** the migration target must ingest the *native workbooks* (full 15-year history), with the `xls/*.csv` prototype serving as the **schema/design reference**, not the data source. Source workbooks are protected per Master Rules §44/§53.11 — never modified in place.
