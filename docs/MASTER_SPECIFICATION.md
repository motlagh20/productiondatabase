# Manufacturing Analytics Platform — Master Product & Architecture Specification

- **Version:** 0.1
- **Status:** Draft for approval — supersedes the former standalone documents `01_PROJECT_CHARTER.md`, `02_GLOSSARY.md`, `03_BUSINESS_DOMAIN_MODEL.md`, `04_BUSINESS_PROCESS_SPECIFICATION.md` (see [ADR-0003](../adr/ADR-0003-consolidated-master-specification.md))
- **Constitution:** [00_MASTER_PROJECT_RULES.md](./00_MASTER_PROJECT_RULES.md) remains the permanent product constitution; this specification is its executable elaboration. On conflict, the Master Rules win.
- **Evidence annexes:** [Appendix A — Current System Inventory](./APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md) · [Appendix B — Data Assets Catalog](./APPENDIX_B_DATA_ASSETS.md)
- **Date:** 2026-07-30

---

## 0. How to use this document (the "anti-short-memory" rule)

This is the **single controlled project blueprint**. Every design decision must be traceable back to (a) a Master Rules section, (b) evidence in the historical data / frozen reference app, or (c) an ADR. Anything not traceable is an open question — flagged, never invented.

**Protocol for every working session (human or AI):**

1. Load this specification (and the ADRs) *before* any work.
2. Work only within the approved parts; the AI collaboration rules in [Part VIII](#part-viii--ai-collaboration-protocol) are binding.
3. Proposed changes to architecture or scope go through a new ADR — never through silent edits.

Document map:

| Part | Content | Master Rules basis |
|---|---|---|
| I | Project Charter | §2, §3, §45, §48, §49 |
| II | Glossary (with evidence flags) | §54, §59 |
| III | Business Domain Model | §4, §31, §32 |
| IV | Business Process (as-is) | §5, §7–§10 |
| V | Historical Data Architecture | §6, §17–§20, §33–§37 |
| VI | Architectural Principles | §26–§32, §40–§44 |
| VII | Roadmap | §48 (refined by ADR-0003) |
| VIII | AI Collaboration Protocol | §1, §46–§47 |

---

# Part I — Project Charter

## I.1 Purpose

Build a **configurable Manufacturing Analytics & Execution Platform** that digitizes manufacturing operations and turns historical and real-time production data into operational intelligence. The initial (reference) implementation targets the existing roof-tile / ceramic plant that supplied the historical production data now stored in this repository under `xls/`.

The platform must answer, over time: *What happened? What is happening? Why did it happen? What will happen? What should we do?* (Master Rules §2).

## I.2 Scope

### In scope (product)

- Configurable manufacturing execution: master data, production recording, workflows, quality, waste.
- Historical data import subsystem with staging, mapping, validation, cleaning, deduplication, and full lineage (Master Rules §17–19, §33–35; detailed in [Part V](#part-v--historical-data-architecture)).
- Analytics as a first-class capability: KPIs, historical charts, baselines, statistical analysis; later forecasting and ML (Master Rules §21–25, §38).
- Multi-company / multi-factory architecture with role-based access (Master Rules §29, §42) — it must work for **different roof-tile and brick manufacturers**, not one factory.
- API-first design suitable for future PLC/SCADA/IoT integration (Master Rules §41).

### Out of scope (for now)

- Advanced AI/ML capabilities in the first release (architecture must be ready; implementation deferred — Master Rules §49).
- Any further feature development on the existing legacy application (see §I.5 below).

## I.3 Target technology stack (Master Rules §45)

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript |
| Backend | Django + Django REST Framework |
| Database | PostgreSQL |
| Cache / background jobs | Redis; Celery where background processing is required |
| Analytics | Python ecosystem: Pandas, NumPy, SciPy, Scikit-learn |
| Deployment | Docker containers, Nginx reverse proxy, Linux/Ubuntu compatible; on-premise and future cloud |

## I.4 MVP definition (Master Rules §49)

The first release proves the platform architecture using the initial plant and must demonstrate: Authentication + Master Data + Production Recording + Historical Import + Production History + Quality + Waste + Basic Dashboards + KPI Calculation + Historical Charts.

## I.5 Status of the existing application — FROZEN REFERENCE IMPLEMENTATION

> **Formal declaration (approved by the project owner, 2026-07-30; see [ADR-0002](../adr/ADR-0002-freeze-legacy-app-as-reference.md)):**
>
> The existing application in this repository is **frozen as a read-only reference implementation**. It receives **no further feature development**. Its code, schema, and UI are treated as *evidence of the current plant's real-world process* (Master Rules §1) — **not** as the design of the future platform.

The frozen reference implementation consists of:

| Component | Files | Notes |
|---|---|---|
| Active containerized stack | `docker-compose.yml`, `sql/` (PostgreSQL schema + seeds), `postgrest.conf`, `nginx.conf` | PostgreSQL 16 + PostgREST + Nginx |
| Web SPA | `web/` (vanilla JS, Persian/RTL) | Served by Nginx, calls PostgREST |
| Legacy Flask backend | `server.py` + `kiln_monitoring.db`, `production.db`, root `schema.sql` | Superseded SQLite path |
| Utility scripts | `*.py` at repository root | SQLite-era one-off scripts |
| Design system docs | `DESIGN_*.md`, `IMPLEMENTATION_GUIDE.md`, `QUICK_REFERENCE.md`, `web/design-standards.css` | UI reference material |

Rules for the frozen reference:

1. Nothing is moved, renamed, or deleted — the app remains runnable for domain discovery.
2. No new features, endpoints, tables, or UI screens are added to it.
3. Its known defects (documented in [Appendix A](./APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md)) are **not** fixed; they are recorded as lessons for the new platform.
4. The historical CSVs in `xls/` are protected source data (Master Rules §44: *never overwrite source data*).

## I.6 Key assets

- **Historical data:** `xls/*.csv` — the plant's exported operational records (Datasets A–D of the Master Rules plus reference data). Cataloged in [Appendix B](./APPENDIX_B_DATA_ASSETS.md). The plant holds ~15 years of additional history to be imported later.
- **Domain knowledge:** the frozen reference implementation encodes the plant's current recording practices (dryer, setting, kiln, packaging, warehouse).
- **This specification** and its ADRs.

## I.7 Success criteria

1. All Master Rules §53 non-negotiable requirements are satisfied by the delivered platform.
2. The full historical dataset is importable with lineage and a data-quality report.
3. The reference plant operates daily recording on the new platform.
4. A second (hypothetical) plant configuration can be expressed without code changes to the generic core.

## I.8 Risks and constraints

| Risk | Mitigation |
|---|---|
| Domain ambiguities (finger/package/column, mold-vs-product) become wrong schema assumptions | Glossary items flagged `Needs plant validation` (Part II) must be confirmed with plant staff before database design |
| Historical data quality (duplicate IDs, mixed Jalali formats, missing values) | Dedicated migration subsystem with staging + review queue (Part V; Master Rules §33) |
| Temptation to copy the frozen app's Excel-shaped schema | Master Rules §32 is binding; the domain model (Part III) is designed from the business domain, not from existing columns |
| Jalali/Gregorian date handling errors | Canonical internal temporal representation with original Jalali text preserved (Master Rules §20) |
| AI-driven architecture drift | AI Collaboration Protocol (Part VIII); architecture changes only via ADR |

---

# Part II — Glossary

**Status:** Draft — **requires plant validation before approval** (Master Rules §59: "The glossary must be approved before the final domain model and database schema are created.")

## II.0 How to read this part

Every entry gives:

- **Definition** — the meaning *as currently understood from the evidence*. Nothing here is invented; where the evidence is insufficient the definition says so.
- **Persian term** — only where a Persian term actually appears in the historical data (`xls/*.csv`) or the frozen reference UI (`web/app.js` i18n strings). Blank means no evidenced Persian term; we do not coin translations.
- **Evidence** — the specific CSV column, database object, or code location proving the term exists in the plant's practice.
- **Status:**
  - `Confirmed` — the term's existence *and* meaning are supported by the evidence.
  - `Needs plant validation` — the term exists in the data, but its exact meaning, unit, or relationships are among the §54 unknowns and must be confirmed with plant staff before database design.

Evidence shorthand used below:

| Shorthand | Source |
|---|---|
| Dataset A | `xls/Dryer.csv` (dryer load/unload, 835 rows) |
| Dataset B | `xls/Setting_wagons.csv` (wagon/glaze/packages, 2,481 rows) |
| Dataset C | `xls/Setting_Setting.csv` (dryer production/shift/supervision, 992 rows) |
| Dataset D | `xls/Packing.csv` (grading/quality/waste, 2,065 rows) |
| Schema | `sql/init/00_schema.sql` (frozen reference PostgreSQL schema) |
| UI | `web/app.js` Persian i18n labels (frozen reference SPA) |

## II.1 Product and materials

### Product
- **Definition:** A manufactured item that the plant produces and tracks (e.g. "سفال طبرستان خودرنگ" = Tabarestan self-colored clay tile). In the historical data a *product* is a numeric code (e.g. `11000001`), and the reference schema derives it from a category + mold + glaze combination.
- **Persian term:** محصول (evidenced in reference data values, `xls/ProductName.csv`)
- **Evidence:** `xls/ProductName.csv` (`11000001 | سفال طبرستان خودرنگ` …); Schema `app.products` with `UNIQUE (category_id, mold_id, glaze_id, extra_code)` and trigger `compute_product_code_name`; Master Rules §16.
- **Status:** `Needs plant validation` — the exact hierarchy Product ↔ Family ↔ Variant ↔ Mold ↔ Glaze is a §54 unknown. The historical field `productName`/`ProductCode_FK` sometimes carries a **mold** code (`91000000`), not a product code (Master Rules §13).

### Product Family
- **Definition:** A grouping of related products. Not directly present in the historical data; implied by the code structure (codes `91xxxxxx`, `92xxxxxx`, `93xxxxxx` share glaze suffixes — Master Rules §14).
- **Persian term:** — (not evidenced)
- **Evidence:** Code-prefix pattern in `xls/Glaze.csv` and `xls/Molds.csv`; Master Rules §13, §14, §16.
- **Status:** `Needs plant validation` — concept required by Master Rules but not explicitly present in plant records.

### Product Variant
- **Definition:** A specific sellable/trackable combination (e.g. product + glaze finish). Implied by the glaze-code table where each mold family (91/92/93) repeats the same eight finishes.
- **Persian term:** — (not evidenced)
- **Evidence:** `xls/Glaze.csv` (24 rows = 3 families × 8 finishes); Master Rules §14, §16.
- **Status:** `Needs plant validation`

### Product Category
- **Definition:** Administrator-defined product classification. The plant currently uses five: سفال (clay tile), تیزه (ridge tile), پنجه ای, نیمه (half), آجر (brick).
- **Persian term:** دسته / دسته‌بندی (UI: `admin_categories`)
- **Evidence:** `xls/Categories.csv` (5 rows); Schema `app.categories`; Master Rules §15.
- **Status:** `Confirmed` (values); the meaning of پنجه ای and نیمه as physical products is `Needs plant validation`.

### Mold
- **Definition:** The physical forming tool that shapes the raw clay product. Known molds: `91000000` طبرستان, `92000000` پرتغالی, `81000000` 20\*10\*20.
- **Persian term:** قالب (UI: `admin_mold_name`)
- **Evidence:** `xls/Molds.csv` (3 rows); Schema `app.molds`; Master Rules §13.
- **Status:** `Needs plant validation` — mold codes are used interchangeably with product codes in Datasets A and C (`ProductCode_FK = 91000000`), a §54 ambiguity that must be resolved before modeling.

### Glaze
- **Definition:** The surface finish/coating applied to the product before firing. Eight finish types per mold family: خودرنگ (self-colored), اخرا (ochre), سبز (green), نوک مدادی (pencil-gray), بیرنگ (colorless), مشکی (black), مولتی مشکی (multi-black), لعاب آزمایشی (experimental glaze).
- **Persian term:** لعاب (UI: `admin_glazes_title`)
- **Evidence:** `xls/Glaze.csv` (24 rows); Dataset B column `GlazeType`; Schema `app.glazes`; Master Rules §14.
- **Status:** `Confirmed` (existence and naming); relationship to product/variant is `Needs plant validation`.

### Clay body
- **Definition:** The raw formed ceramic material before drying/firing. Mentioned as a Level-3 concept; no operational records for it exist in the supplied data.
- **Persian term:** — (not evidenced)
- **Evidence:** Master Rules §4 (Level 3 examples) only.
- **Status:** `Needs plant validation` — raw-material data is a §54 unknown.

## II.2 Process stages and equipment

### Dryer
- **Definition:** The drying facility composed of numbered chambers where formed products are dried after forming.
- **Persian term:** خشک‌کن (UI: `nav_dryer_main`)
- **Evidence:** Dataset A (entire file); Schema `app.dryer_loading`, `app.dryer_unloading`; UI dryer pages.
- **Status:** `Confirmed`

### Chamber
- **Definition:** An individual numbered compartment of the dryer that is loaded and unloaded as a unit. The current plant has **40 chambers** (owner-confirmed; Appendix C §9). The reference schema hardcoded 1–32 — this must become configuration in the new platform (Master Rules §27/P1).
- **Persian term:** چمبر (UI: `dryer_chamber` = "شماره چمبر")
- **Evidence:** Dryer `Data Entry` `شماره چمبر` (values 1–40); Set `Data` `شماره چمبر` (1–75 observed, >40 flagged as typo per owner); Schema `CHECK (chamber_no BETWEEN 1 AND 32)` in `app.dryer_loading` (superseded → config 1–40).
- **Status:** `Confirmed` (existence, numbering); whether 32 is fixed or varies is `Needs plant validation`.

### Kiln
- **Definition:** The firing furnace. Products arranged on wagons/cars are pushed through it; the reference system records push events with temperature readings. **The count of temperature points grew over time**: Kiln-1398→1403 recorded only `دمای اگزوز` (~1 point); Kiln-1404 records **18 points** (exhaust, preheat 1–2, thermostat, zones 00–07, rapid 1–2, bottom A/01/B/02). The schema must be **row-oriented** (Appendix C §12), not a fixed 18-column block. Max plausible reading = **1200 °C** (kiln tolerance; >1200 = typo/sensor fault, flag — Appendix C §12.1).
- **Persian term:** کوره (UI: `nav_kiln_main`)
- **Evidence:** Kiln `Input` `temp_*` columns (1404, 18 pts) + `دمای اگزوز` (1398–1403, 1 pt); Kiln-1404 `incomingProduct_Type` = {خشت خام, سفال پخته} (≡ خام/شارژی in 1398–1403, Appendix C §13).

### Kiln Push
- **Definition:** The recorded event of pushing an incoming car/wagon into the kiln, with date, time, shift, operator, product, fuel type, pushing duration (minutes) and temperature profile.
- **Persian term:** پوشینگ کوره (UI: `nav_kiln_pushing`)
- **Evidence:** `xls/Kiln.csv` rows; Schema `app.kiln_push_data` (`incoming_car_id`, `pushing_time_min`).
- **Status:** `Confirmed` (recording practice); process semantics `Needs plant validation`.

### Wagon
- **Definition:** A numbered car onto which packages of dried product are arranged (the "setting" operation) for transport through the kiln. One production setting may span multiple wagons, and a wagon may be **partially filled and completed across chambers/shifts** (Master Rules §8; Appendix C §14). The wagon is a **continuous entity spanning stages**: dryer chamber → setting → kiln push — the same `wagon_no` recurs under multiple setting operations.
- **Persian term:** واگن (UI: `kiln_car_incoming` = "واگن ورودی"; Kiln-1404 also names it `IncomingCarID`)
- **Evidence:** `Setting_wagons.csv` column `wagon_no` (FK `SettingID`); Set `Data` repeating wagon blocks; Kiln `واگن ورودی/خروجی` / `IncomingCarID`. Max 4 wagons per setting op observed (Appendix C §14).

### Finger / Finger car
- **Definition:** A carrying unit of dried bricks arranged inside a dryer chamber column. In the historical data `fingers_count` / `loadFingerCount` records how many fingers (load units) were placed per chamber load/setting record (typical 4–8). Per owner (Appendix C §13), the dryer logs a **per-3h temperature + humidity series** per chamber, and each chamber row carries the finger count as the load unit. Physical meaning = a tray-rack / carrier of bricks loaded into the chamber column.
- **Persian term:** فینگر (UI: `dryer_finger_count` = "تعداد فینگر")
- **Evidence:** Dryer `Data Entry` `تعداد فینگر تولیدی`; Set `Data` `تعداد فینگر`; Dataset A `loadFingerCount`; Dataset C `fingers_count`.
- **Status:** `Needs plant validation` — **§54 open question ("Exact meaning of 'finger'")**.

### Tray
- **Definition (uncertain):** Listed in the initial process understanding ("Tray / Finger Handling", Master Rules §5). No tray field exists in any supplied dataset; relationship to "finger" unknown.
- **Persian term:** — (not evidenced)
- **Evidence:** Master Rules §5 only.
- **Status:** `Needs plant validation`

### Equipment
- **Definition:** Platform-level concept (Master Rules §4 Level 1) covering machines such as dryer chambers, kilns, wagons. The current plant data identifies equipment only implicitly (chamber numbers, wagon numbers, one kiln).
- **Persian term:** — (not evidenced)
- **Evidence:** Master Rules §4; implicit in Datasets A, B and `xls/Kiln.csv`.
- **Status:** `Needs plant validation` — no explicit equipment registry exists in the plant data.

## II.3 Production recording units

### Production Setting
- **Definition:** A production/arrangement operation identified by `SettingID` (a composite-looking Jalali-date-based number, e.g. `1404010718`), linking a dryer/shift context (Dataset C) to one or more wagons (Dataset B). **One setting = many wagons** is proven by the data; `SettingID` values repeat across rows and must not become a primary key (Master Rules §9).
- **Persian term:** چیدمان / ثبت چیدمان (UI setting pages; label `setting_supervisor` etc.)
- **Evidence:** Dataset B column `SettingID`; Dataset C column `ID` (same value space, duplicates such as `1404010913`, `1404011009`, `1404011404`, `1404011612`); Schema `app.setting_processes` + `app.setting_wagons_data` (FK `setting_id`, `UNIQUE (setting_id, wagon_order)`).
- **Status:** `Needs plant validation` — existence confirmed; exact business meaning, key structure, and relationship to dryer/grading records are §54 unknowns.

### Package
- **Definition (uncertain):** A counting unit recorded per wagon in Dataset B (`packages`, e.g. 64 per wagon, sometimes split 4 + 60 across partial fills). Whether it is a physical bundle, a fixed count of tiles, or something else is **explicitly not yet defined** (Master Rules §54).
- **Persian term:** بسته (UI wagon row label "بسته")
- **Evidence:** Dataset B column `packages`; Schema `packages` in `app.setting_wagons_data`.
- **Status:** `Needs plant validation` — **§54 open question ("Exact meaning of 'package'")**.

### Column
- **Definition (uncertain):** A counting unit recorded per setting record in Dataset C (`columns_count`, small integers such as 2). Presumably a stacking column of product, but **explicitly not yet defined** (Master Rules §54).
- **Persian term:** ستون (UI: `setting_columns_count` = "تعداد ستون")
- **Evidence:** Dataset C column `columns_count`; Schema `columns_count` in `app.setting_processes`.
- **Status:** `Needs plant validation` — **§54 open question ("Exact meaning of 'column'")**.

### Packing (بسته‌بندی)
- **Definition:** The final packing stage. `Packing-All.xlsx` (93,389 rows, all years 1391–1404) is the **authoritative source** — the richest operational transaction set. Records per packed batch: date, month, day, shift, controller, worker type/count, product type/code/name, wagon number, total product, grade 1, grade 2, waste, efficiency (`راندمان`).
- **Persian term:** بسته‌بندی (UI: packing pages)
- **Evidence:** `xls/real data/Packing-All.xlsx` `Sheet1` (Appendix C §11). Product coded 1–28 (separate legacy scheme from Dryer/Kiln A–E+91xxxx); wagon 1–80 (typos >80 flagged, Appendix C §9). Shift = 1–3 (صبح/عصر/شب). Year 1397 missing 2 months (complete later).
- **Note:** the `xls/Packing.csv` *prototype* previously referenced was a sample with wrong figures (e.g. implied "shift 22"); the real source is `Packing-All.xlsx`. Packing efficiency (`راندمان`) is an **analytic** column — excluded from raw migration, re-derived later (Appendix C §15).
- **Status:** `Confirmed` (existence & grain); product-code mapping to canonical composite product is via ADR-0006 / `product_mapping_blueprint.csv`.

### Batch
- **Definition:** Platform-level concept (Master Rules §4). The reference schema has an `app.production_batches` table, but no batch identifier exists in the historical CSVs; "Production batch definition" is a §54 unknown.
- **Persian term:** — (not evidenced)
- **Evidence:** Master Rules §4, §54; Schema `app.production_batches` (reference implementation's own invention — evidence of practice, not of plant terminology).
- **Status:** `Needs plant validation`

### Work Order
- **Definition:** Platform-level concept (Master Rules §4). No work-order data exists anywhere in the plant's records; "Work-order definition" is a §54 unknown.
- **Persian term:** — (not evidenced)
- **Evidence:** Master Rules §4, §54 only.
- **Status:** `Needs plant validation`

### Production Run
- **Definition:** A continuous execution of production for a product over a period. Not present as an explicit record in the supplied data; candidate future concept to group settings/batches.
- **Persian term:** — (not evidenced)
- **Evidence:** Master Rules §59 term list only.
- **Status:** `Needs plant validation`

### Operation / Process Stage
- **Definition:** A configurable step in a manufacturing workflow (Level 2, Master Rules §4). The stages evidenced for the current plant: forming → tray/finger handling → dryer loading → drying → dryer unloading → setting/wagons → kiln → sorting/grading → waste classification (Master Rules §5). These must be configuration, not code, in the new platform.
- **Persian term:** — (stage names appear individually in the UI: بارگذاری خشک‌کن, تخلیه خشک‌کن, پوشینگ کوره …)
- **Evidence:** Master Rules §5; Datasets A–D each cover one stage; UI page structure.
- **Status:** `Needs plant validation` — "Exact production workflow" is the first §54 unknown.

## II.4 Quality, grading, and waste

### Grade
- **Definition:** A quality classification assigned during sorting after the kiln. Evidence exists only for **Grade 1** (`Grade1Count`); the reference schema *derives* a "grade 2" (`grade2_count = total − grade1 − waste`), which is an assumption, not plant evidence. The future quality model must support multiple configurable outcomes (Master Rules §10).
- **Persian term:** درجه (conventional; not directly evidenced in UI strings)
- **Evidence:** Dataset D column `Grade1Count`; Schema `app.packaging_records.grade2_count GENERATED` + `CHECK (grade1_count + waste_count <= total_count)`.
- **Status:** `Needs plant validation` — "Exact quality classification rules" is a §54 unknown; do **not** assume `Total = Grade1 + Waste` (Master Rules §10).

### Waste
- **Definition:** Rejected/lost product. Two distinct waste measurements exist in the data: **dryer waste** (`dryer_waste` in Dataset C, recorded at the drying stage, e.g. 150 units) and **sorting waste** (`WasteCount` in Dataset D, recorded at grading). Whether these use the same unit and classification is unknown.
- **Persian term:** ضایعات (UI: `setting_dryer_waste` = "ضایعات خشک‌کن")
- **Evidence:** Dataset C column `dryer_waste`; Dataset D column `WasteCount`; Schema `dryer_waste`, `waste_count`.
- **Status:** `Needs plant validation` — "Exact waste categories" is a §54 unknown.

### Scrap
- **Definition:** Term from the Master Rules process diagram ("Waste / Scrap Classification", §5). No separate scrap field exists in the data; relationship to "waste" unknown.
- **Persian term:** — (not evidenced)
- **Evidence:** Master Rules §5, §59 only.
- **Status:** `Needs plant validation`

### Rework
- **Definition:** Reprocessing of defective product. No rework data exists anywhere in the supplied records; "Rework rules" is a §54 unknown. The quality model must nevertheless be able to represent it (Master Rules §10).
- **Persian term:** — (not evidenced)
- **Evidence:** Master Rules §10, §54 only.
- **Status:** `Needs plant validation`

### Production Quantity / Total Count
- **Definition:** The total number of units processed in a grading record (`TotalCount`, e.g. 1,128).
- **Persian term:** — (not directly evidenced as a label)
- **Evidence:** Dataset D column `TotalCount`; Schema `total_count`.
- **Status:** `Confirmed` (as a recorded figure); its unit (tiles? packages?) is `Needs plant validation`.

### Good Quantity
- **Definition:** The count of first-quality units (`Grade1Count`, e.g. 1,000 of 1,128).
- **Persian term:** — (not directly evidenced as a label)
- **Evidence:** Dataset D column `Grade1Count`.
- **Status:** `Confirmed` (as a recorded figure); classification rules `Needs plant validation`.

### Yield
- **Definition:** Derived metric: `Grade 1 Yield % = Grade1Count / TotalCount × 100` (Master Rules §10). A calculation, not a stored plant record.
- **Persian term:** — (not evidenced)
- **Evidence:** Master Rules §10 formula; computable from Dataset D.
- **Status:** `Confirmed` (as a defined KPI formula), pending validation of the underlying counts.

## II.5 People, organization, and time

### Shift
- **Definition:** A work period within a day. The plant records shifts 1, 2, 3 (hardcoded as `CHECK (shift_code IN (1,2,3))` in the reference schema — must become a configurable shift pattern in the new platform, Master Rules §27).
- **Persian term:** شیفت (UI: `kiln_shift`)
- **Evidence:** Datasets C and D column `shift` (values 1–3); Schema `app.shifts_definition`.
- **Status:** `Confirmed` (three shifts exist today); shift times/pattern `Needs plant validation`.

### Operator
- **Definition:** A production worker who performs and is recorded against an operation (loading, unloading, setting, kiln push, grading). Ten historical operators with numeric codes 1–11 (codes map to overlapping family names, an acknowledged ambiguity — Master Rules §19 "operator-code ambiguity").
- **Persian term:** اپراتور (UI: `dryer_operator`)
- **Evidence:** `xls/Operators.csv` (10 rows, e.g. `4 | سید حسین جلالی`); Dataset A `LoadOperatorCode_FK`; Datasets C, D `OperatorCode_FK`.
- **Status:** `Confirmed` (existence and mapping); identity ambiguities `Needs plant validation`.

### Supervisor
- **Definition:** The shift/production supervisor recorded on setting records. Two historical supervisors: `1 | شاکر`, `2 | عموزاد`.
- **Persian term:** سرشیفت (UI: `setting_supervisor`); data file header "supervisors"
- **Evidence:** `xls/Supervisors.csv` (2 rows); Dataset C column `supervisorID`.
- **Status:** `Confirmed`

### Personnel (count)
- **Definition:** The number of workers present for a recorded operation (`personnel_count` in Dataset C; `workerscount` + `typeOfWorkers` in Dataset D).
- **Persian term:** — (not directly evidenced as a label)
- **Evidence:** Dataset C `personnel_count`; Dataset D `typeOfWorkers`, `workerscount`; Schema `personnel_count`, `workers_count`, `type_of_workers`.
- **Status:** `Confirmed` (recorded figure); meaning of `typeOfWorkers` values `Needs plant validation`.

## II.6 Derived time metrics (analytics vocabulary)

These are calculated values, not stored plant records. The platform must compute them from canonical date/time values (Master Rules §7).

### Drying Time / Drying Duration
- **Definition:** Unload timestamp − load timestamp for a chamber load (e.g. loaded 1404-01-05 08:20, unloaded 1404-01-09 15:40 ≈ 4.3 days).
- **Evidence:** Dataset A load/unload date+time columns; Master Rules §7 ("drying duration").
- **Status:** `Confirmed` (computable); note the reference app hardcodes a 72-hour "overdue" rule in `api.dryer_chambers_status` — that threshold is factory-specific and `Needs plant validation`.

### Cycle Time
- **Definition:** Duration of one complete pass of a unit/equipment through a stage or the whole process (chamber cycle time, kiln cycle time, production cycle time — Master Rules §7, §21).
- **Evidence:** Master Rules §7, §21; computable from Datasets A/B and `xls/Kiln.csv` times.
- **Status:** `Needs plant validation` — exact start/end anchor points per cycle must be defined with the plant.

### Waiting Time
- **Definition:** Idle time between stages (e.g. production waiting time, delayed unloading — Master Rules §7, §21).
- **Evidence:** Master Rules §7, §21.
- **Status:** `Needs plant validation`

## II.7 Open questions checklist (must be answered by plant staff)

Extracted from Master Rules §54; the glossary cannot be approved until each item is resolved:

1. Exact production workflow (validate §5 diagram end-to-end).
2. Exact meaning of **finger** (physical object? capacity? relation to tray?).
3. Exact meaning of **package** (bundle size? per-product?).
4. Exact meaning of **column** (stacking unit? capacity?).
5. Exact relationship between **mold, product, product variant, and glaze** (resolve the `productName` = mold-code ambiguity).
6. Exact relationship between **dryer records and wagon records** (does a setting consume specific chamber unloads?).
7. Exact relationship between **wagon records and grading records** (is Dataset D's `wagon_no` the same wagon as Dataset B's?).
8. Exact **kiln process** and meaning of each temperature point in `xls/Kiln.csv`.
9. Exact **quality classification rules** (does Grade 2 exist? is `Total = Grade1 + Waste` always true?).
10. Exact **waste categories** (dryer waste vs sorting waste vs other).
11. **Rework** rules, **batch** definition, **work order** definition.
12. Shift times/pattern; the 72-hour drying threshold; whether 32 chambers and 4 wagons/setting are fixed.
13. Raw material, recipe, energy, maintenance, downtime, and IoT/PLC data availability.
14. Structure and inventory of the full ~15-year historical dataset and remaining Excel workbooks.

Every `Needs plant validation` flag above blocks the corresponding assumption from entering the domain model (Part III) or any future schema.

---

# Part III — Business Domain Model

> **This part is explicitly NOT a database schema.** Per Master Rules §31, the domain model describes business concepts and their relationships. Tables, keys, and columns belong to the Database phase and may not be derived from this part until it is approved. Per Master Rules §32, nothing here copies the Excel structure or the frozen reference schema — those are *evidence*, mapped below, not design.

## III.1 The three levels (Master Rules §4)

Every concept in the platform belongs to exactly one level. The level determines *where it lives*:

| Level | Nature | Lives in | Examples for this project |
|---|---|---|---|
| **1 — Platform** | Generic, applies to almost any manufacturer | Core code + core model | Company, Factory, Production Line, User, Employee, Role, Shift, Product, Equipment, Work Order, Batch, Operation, Inspection, Quality Result, Waste, KPI, Event, Alert |
| **2 — Configurable Manufacturing** | Structure varies per factory | Configuration data, defined by administrators | Process stages & workflows, equipment types, quality characteristics & outcome sets, product attributes, KPI definitions, shift patterns, units of measure, production rules |
| **3 — Industry / Factory Specific** | The initial plant's concrete items | Configuration *values* (or an industry module) | Roof tile, clay body, mold طبرستان, 32 dryer chambers, finger cars, wagons, glaze اخرا, "Grade 1", dryer waste, operator codes 1–11 |

**Binding rule:** a Level-3 item must never appear in Level-1 code. The frozen reference app violates this repeatedly (32 chambers, 3 shifts, 4 wagons, 20 temperature columns hardcoded — see [Appendix A](./APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md)); those violations are the primary lesson this model corrects. Another factory must be able to use the platform even if it has no chambers or fingers at all.

## III.2 Level 1 — Platform concepts

### III.2.1 Organization & people

```
Company ──< Factory ──< Production Line / Area
User (account)  ↔  Employee (person, with employment history)
Role ──< Permissions
Shift (definition belongs to a Factory's shift pattern — Level 2)
```

- **Employee ≠ User.** Historical operators (codes 1–11) are Employees who may never get accounts. Historical records must preserve *the employee identity at production time* (Master Rules §12).
- Every operational record is scoped to a Factory (multi-factory requirement, Master Rules §29, §53.14).

### III.2.2 Product

```
Product Category ──< Product Family ──< Product ──< Product Variant
Mold / Tool  (a resource used to make Products — relation to Variant TBD)
Finish / Glaze  (an attribute dimension of Variant — TBD)
```

- The exact hierarchy is a §54 unknown (Part II: mold-vs-product ambiguity). The model commits only to: *categories are admin-defined* (Master Rules §15) and *historical code mappings are retained* so old data stays interpretable (Master Rules §14, §16).

### III.2.3 Production execution

```
Work Order (planned demand — no plant evidence yet, §54 unknown)
      ↓
Production Run / Batch (grouping — definition TBD with plant)
      ↓
Operation Execution Record  ←— the central concept
      • at a Process Stage (Level 2 configuration)
      • on Equipment (chamber, kiln, wagon…)
      • by Employee(s), in a Shift, at a Date/Time
      • consuming/producing Quantities in defined Units
      ↓
Allocation (links an execution to carriers/containers, e.g. setting → wagons)
```

- **Allocation is first-class** because the data proves one setting spans many wagons with partial fills (Master Rules §8): `Production Setting → Production Allocation → Wagon → Quantity/Packages`.
- This is exactly the generalization that frees the platform from the initial plant's vocabulary: a Dataset A row (`ChamberNo, LoadDateJalali, LoadTime, UnloadDateJalali, UnloadTime, loadFingerCount`) is *one factory's expression* of `ProcessOperation → Equipment → Input/Output Quantity → Duration`. The concrete mapping recipe lives in [Part V §V.4](#v4-worked-mapping-example-dataset-a--canonical-model).

### III.2.4 Quality & waste

```
Inspection (at a configurable point in the workflow)
      ↓
Quality Result = { Outcome → Quantity } over a configurable Outcome Set
      (e.g. initial plant: Grade 1, Waste — later: Grade 2, Rework, Hold, Broken…)
Waste Record (classified by configurable Waste Category, attributable to a Stage)
```

- Hardcoding "Grade1Count / WasteCount" columns is forbidden (Master Rules §10); the reference app's generated `grade2_count` column is an invented rule and is *not* carried forward.

### III.2.5 Measurements, analytics, events

```
Measurement (a reading: temperature point, humidity… defined per Equipment type — Level 2)
KPI Definition (Level 2) → KPI Value (computed, with lineage to source records)
Event / Alert (threshold breaches, baseline deviations — Master Rules §23)
Import Batch / Source Record Lineage (every historical record traceable — Master Rules §18)
```

## III.3 Level 2 — configuration the initial plant will need

| Configuration object | Initial plant values (Level 3) |
|---|---|
| Process stages & workflow | Forming → Finger/Tray handling → Dryer loading → Drying → Dryer unloading → Setting/Wagon arrangement → Kiln → Sorting/Grading → Waste classification (§5 — to be validated) |
| Equipment types + instances | Dryer chamber ×32; Kiln ×1 (20 temperature points); Wagons (numbered fleet); Finger cars (count/capacity unknown) |
| Shift pattern | 3 shifts (codes 1, 2, 3) |
| Quality outcome set | {Grade 1, Waste} at sorting; {Dryer waste} at drying |
| Units of measure | finger, column, package, piece — meanings pending plant validation |
| Counting rules | e.g. is `Total = Grade1 + Waste` enforced? (must NOT be assumed — §10) |
| Production rules | e.g. drying-overdue threshold (72 h in the reference app — factory-specific, configurable) |
| KPI definitions | Grade-1 yield %, waste rate %, drying duration, chamber utilization, throughput (§21) |

## III.4 Evidence mapping: frozen reference schema → target concepts

Every `app.*` table of the frozen reference implementation (`sql/init/00_schema.sql`) maps to a target concept. This table is the bridge for the future migration design — **it is not a migration script**.

| Frozen reference table | Target concept (level) | Notes |
|---|---|---|
| `app.config` | Deployment configuration (not domain) | Contains a JWT secret in-table — security lesson, see Appendix A |
| `app.shifts_definition` | Shift pattern (L2) | `CHECK shift_code IN (1,2,3)` hardcodes the pattern → becomes configuration |
| `app.firing_types`, `app.fuel_types` | Equipment/process parameter types (L2) | Kiln-specific lookup values |
| `app.categories` | Product Category (L1, admin-defined values L3) | 5 fixed rows today |
| `app.molds` | Mold/Tool (L1) | Mold-vs-product ambiguity unresolved |
| `app.glazes` | Finish/Glaze dimension (L2 attribute) | 24 code rows retained as historical mapping |
| `app.products` + trigger `compute_product_code_name` | Product/Variant (L1) | Code = category+mold+glaze+extra composition; composition rule is factory-specific → configuration |
| `app.product_category_assignments`, `app.extra_code_map` | Historical code mapping (migration layer) | Master Rules §14: keep old codes interpretable |
| `app.roles`, `app.users`, `app.user_credentials`, `app.login_sessions`, `app.pages`, `app.role_permissions`, `app.role_page_access` | User, Role, Permission (L1) | Concepts carry over; implementation does not (Django auth) |
| `app.dryer_loading`, `app.dryer_unloading` | Operation Execution Record at stages *Dryer loading / unloading* (L1) on Equipment *chamber* | `CHECK chamber_no BETWEEN 1 AND 32` → equipment configuration |
| `app.simple_dryer_readings`, `app.dryer_readings` (21 points) | Measurement against Equipment (L1) with configurable reading-point sets (L2) | Fixed reading-point columns → configuration |
| `app.setting_processes` | Operation Execution Record at stage *Setting* (L1) | Carries shift/supervisor/personnel context |
| `app.setting_wagons_data` | Allocation → Wagon (L1) | `CHECK wagon_order BETWEEN 1 AND 4` invents a 4-wagon limit; Dataset B does not prove such a limit → configuration, pending validation |
| `app.kiln_push_data` | Operation Execution Record at stage *Kiln* + Measurements | 18 named `temp_*` columns → configurable measurement-point set |
| `app.production_batches` | Batch (L1) — definition TBD | Reference app's invention; validate against plant practice before reuse |
| `app.warehouse_stock`, `app.warehouse_transactions` | Inventory concepts (L1) | Out of MVP focus; revisit in requirements phase |
| `app.packaging_records` | Inspection + Quality Result at stage *Sorting/Grading* (L1) with configurable Outcome Set (L2) | Generated `grade2_count` and `CHECK grade1+waste<=total` are invented rules → replaced by configurable outcome model |

## III.5 What this model deliberately does not decide

Blocked pending the Part II §II.7 open-questions checklist:

1. Product ↔ Family ↔ Variant ↔ Mold ↔ Glaze hierarchy shape.
2. Whether Setting, Batch, and Work Order are one, two, or three distinct concepts for this plant.
3. Units-of-measure semantics (finger, column, package) and conversion factors.
4. The linkage keys between drying, setting, and grading records (traceability chain).
5. Waste taxonomy (dryer waste vs sorting waste vs future categories).
6. Kiln process modeling (car sequencing, zones, firing programs).

---

# Part IV — Business Process Specification (As-Is)

> **Scope note:** This describes what the plant *currently records*, proven by the historical CSVs (`xls/`) and the frozen reference app. Recording practice is not necessarily the complete physical process — stages that generate no records (e.g. forming, clay preparation) are nearly invisible in the evidence and are flagged accordingly. It must be validated with plant operational staff before the workflow engine is designed (Master Rules §5).

## IV.1 As-is process flow

```
[Forming / shaping of clay product]          ← no records; existence implied (§5)
                 ↓
[Tray / Finger handling]                     ← no direct records; finger counts appear at dryer loading
                 ↓
(1) DRYER LOADING            evidence: Dataset A (xls/Dryer.csv), app.dryer_loading
                 ↓
(2) DRYING                   evidence: derived durations; dryer readings tables (21 points)
                 ↓
(3) DRYER UNLOADING          evidence: Dataset A unload columns, app.dryer_unloading
                 ↓
(4) SETTING / WAGON ARRANGEMENT
                             evidence: Dataset C (xls/Setting_Setting.csv) +
                                       Dataset B (xls/Setting_wagons.csv), app.setting_processes
                 ↓
(5) KILN PUSH / FIRING       evidence: xls/Kiln.csv (2,821 rows), app.kiln_push_data
                 ↓
(6) SORTING / GRADING / PACKAGING
                             evidence: Dataset D (xls/Packing.csv), app.packaging_records
                 ↓
[Warehouse / finished production]            ← reference app tables exist; no historical CSV
```

## IV.2 Stage descriptions (what is recorded, by whom, with what)

### Stage 1 — Dryer loading
- **Record:** one row per chamber load: `ChamberNo` (1–32), `LoadDateJalali` + `LoadTime`, loading operator code, product/mold code, `loadFingerCount` (typ. 4–8).
- **Actors:** loading operator; (shift + supervisor added by the reference app's `dryer_loading` table).
- **Evidence:** `xls/Dryer.csv` — 835 load/unload rows; e.g. chamber 10 loaded 1404-01-05 08:20 by operator 4, product 91000000, 8 fingers.

### Stage 2 — Drying
- **Record:** no direct "drying" record; duration is *derived* (unload − load). The reference app adds optional chamber temperature/humidity readings (`simple_dryer_readings`, `dryer_readings` with 21 fixed points) — no historical CSV counterpart supplied.
- **Business rule observed in app (not validated):** a chamber is "overdue" after 72 hours loaded (`api.dryer_chambers_status`). Factory-specific; must become configuration.

### Stage 3 — Dryer unloading
- **Record:** completion of the same Dataset A row: `UnloadDateJalali`, `UnloadTime`, unloading operator (column header `LoadOperatorCode_FK.1` — a raw-export artifact meaning *unload* operator). Example drying span: 1404-01-05 → 1404-01-09 (~4 days).
- **Data quality:** some rows have missing unload values (chamber still loaded, or unrecorded).

### Stage 4 — Setting / wagon arrangement
- **Record (context — Dataset C, 992 rows):** per setting: `date_jalali`, `shift` (1–3), `supervisorID` (1–2), `OperatorCode_FK`, `personnel_count`, `chamber_no`, `productName` (mold/product code), `fingers_count`, `columns_count`, `dryer_waste`, `ID` (e.g. `1404010718`).
- **Record (allocation — Dataset B, 2,481 rows):** per wagon within a setting: `SettingID`, `wagon_no`, `GlazeType`, `start_time`, `end_time`, `packages`.
- **Proven relationships (Master Rules §8, §9):**
  1. **One setting → many wagons.** `SettingID 1404010718` appears with wagon 75 (06:25–07:25, 64 packages) and wagon 41 (07:25–08:05, 64 packages), among others.
  2. **Partial wagon fills exist.** The same wagon number can appear twice within a setting with split quantities (e.g. 4 + 60 = 64 packages).
  3. **`ID`/`SettingID` is not unique.** Dataset C repeats IDs `1404010913`, `1404011009`, `1404011404`, `1404011612` on distinct records → the historical ID must not become a primary key; the true business key is unknown.
  4. **Dryer waste is recorded here**, at setting time (`dryer_waste`, e.g. 150), not in Dataset A.
- **Reference-app deviation:** `app.setting_wagons_data` enforces `wagon_order BETWEEN 1 AND 4` (max 4 wagons/setting). Dataset B is organized as repeated wagon rows per `SettingID`; a hard 4-wagon limit is an app assumption, not proven plant practice.

### Stage 5 — Kiln push / firing
- **Record:** per push event: Jalali date (format `1404.01.01`), time, shift, operator, product, incoming car/wagon id, fuel type, pushing duration (min), and a fixed set of ~18–20 temperature points (exhaust, preheat 1–2, thermostat, zones 00–15).
- **Evidence:** `xls/Kiln.csv` — 2,821 rows; `app.kiln_push_data`.
- **Unknowns:** exact kiln process, car sequencing, zone semantics, firing programs (§54).

### Stage 6 — Sorting / grading / packaging
- **Record:** per grading session: `date_jalali`, `shift`, `OperatorCode_FK`, `typeOfWorkers` + `workerscount`, `productName`, `GlazeType`, `wagon_no`, `TotalCount`, `Grade1Count`, `WasteCount`.
- **Evidence:** `xls/Packing.csv` — 2,065 rows; e.g. 1404/01/04, shift 1, wagon 75, product 91000000, glaze 91000001: total 1,128 → 1,000 Grade 1 + 128 waste.
- **Rules NOT to assume (Master Rules §10):** `TotalCount = Grade1Count + WasteCount` may not always hold; only Grade 1 and Waste are evidenced, but the model must support more outcomes. The reference app *invented* a derived Grade 2 — treated as a lesson, not a rule.

## IV.3 Cross-stage traceability (as-is)

The historical records connect stages only **weakly**, through shared reference values rather than explicit keys:

| Link | Connector present in data | Strength |
|---|---|---|
| Dryer load ↔ dryer unload | same row in Dataset A | Strong |
| Dryer record ↔ setting record | shared `chamber_no`, date, product code | Weak — no key; §54 unknown |
| Setting record ↔ wagon rows | `ID` = `SettingID` | Medium — key exists but duplicates occur |
| Wagon row ↔ kiln push | wagon/car number, date | Weak — no key |
| Wagon/kiln ↔ grading record | shared `wagon_no`, product, glaze, date | Weak — no key; §54 unknown |

**Consequence:** end-to-end batch traceability does **not** exist in the historical data. The new platform must (a) create explicit linkage for *future* records, and (b) treat reconstruction of *historical* linkage as a best-effort, flagged analytical exercise — never silently invented (Master Rules §1, §18).

## IV.4 Date/time conventions observed

| Source | Jalali format observed |
|---|---|
| Dataset A (`Dryer.csv`) | `1404-01-05` (dash) |
| `Kiln.csv` | `1404.01.01` (dot) |
| Dataset C (`Setting_Setting.csv`) | `1404/1/7` (slash, non-padded) |
| Dataset D (`Packing.csv`) | `1404/01/04` (slash, padded) |

Times are `HH:MM` text. Per Master Rules §20 the platform stores a canonical temporal representation internally, keeps the original Jalali text recoverable, and supports both calendars in the UI.

## IV.5 Open questions before the workflow engine is designed

See [Part II §II.7](#ii7-open-questions-checklist-must-be-answered-by-plant-staff) — the same checklist governs both parts. Items 1–8 gate the architecture/database phases; items 9–14 gate the historical migration design.

---

# Part V — Historical Data Architecture

> **New phase introduced by ADR-0003.** Before the production database is designed, the ~15 years of plant history must have a defined home. The old Excel structure is **never** forced into the new application (Master Rules §32); instead the original data is preserved verbatim and *mapped* into a clean, generic manufacturing model.

## V.1 The four layers

```
15+ years historical data (Excel exports, CSVs, legacy DBs)
        ↓
① RAW DATA LAYER            — immutable, verbatim capture
        ↓
② CLEANING / MAPPING LAYER  — parse, validate, map codes, resolve, audit
        ↓
③ CANONICAL MANUFACTURING MODEL — the generic domain model of Part III
        ↓
④ ANALYTICS DATA MODEL      — derived marts, KPIs, baselines (rebuildable)
```

### ① Raw Data Layer
- One staging record per source row, stored **verbatim** (original text, including unparsed Jalali dates, unpadded times, artifact columns like `Unnamed: 2` and `LoadOperatorCode_FK.1`).
- Immutable: source files and staging rows are never edited or overwritten (Master Rules §44).
- Full lineage on every row: source file, sheet, row number, import batch id, import timestamp, mapping version (Master Rules §18).

### ② Cleaning / Mapping Layer
- **Parsing:** a Jalali parser handling all four observed formats (`1404-01-05`, `1404.01.01`, `1404/1/7`, `1404/01/04`) plus `H:MM[:SS]` time text (e.g. `8:20:00`, and `PushingTime_min` values like `1:20:00` that are durations stored as time text).
- **Code mapping:** versioned mapping tables for mold/glaze/category/product/operator/supervisor codes; unmapped codes (e.g. product `90000001` in `Kiln.csv`) are routed to a review queue, never guessed.
- **Validation classes:** every staged row is classified — `Valid` / `Warning` / `Invalid` / `Duplicate` / `Unmapped` / `Needs Review` — and the classification is reportable (Master Rules §34–35).
- **Corrections with audit:** any fix stores original value, corrected value, reason, who, when. Duplicate `SettingID`s are resolved here by documented rule, not silently.

### ③ Canonical Manufacturing Model
- The Part III domain model, physically realized in the future database phase. Historical records land here marked `source = historical` with an FK back to their staging row; live records created by the application share the **same** model (Master Rules §53.21 — no separate "legacy tables").
- This is the only layer application features read and write.

### ④ Analytics Data Model
- Aggregates, marts, KPI series, baselines, trend tables — always **rebuildable** from layer ③; never an input to it. Dashboards, statistics, and ML consume this layer.
- Drill-down from any analytic figure to canonical records, and from there via lineage to the raw source row, must always be possible.

## V.2 Layer rules

1. Data flows downward only (①→②→③→④); no layer writes upstream.
2. Application UI and API touch layer ③ only; migration tooling touches ①–③; analytics reads ③ and materializes ④.
3. Re-running an import with a newer mapping version must be possible without data loss (staging is the durable source).
4. Every migration run produces a data-quality report: rows read / valid / warned / invalid / duplicate / unmapped, per file (Master Rules §37).

## V.3 Known inputs today

The currently exported slice (cataloged row-by-row in [Appendix B](./APPENDIX_B_DATA_ASSETS.md)): 9,194 transactional rows (Dryer 835, Setting_wagons 2,481, Setting_Setting 992, Packing 2,065, Kiln 2,821) plus reference files (Categories 5, Molds 3, Glaze 24, ProductName 4, Operators 10, Supervisors 2). The full ~15-year archive is not yet inventoried — open question II.7 #14.

## V.4 Worked mapping example (Dataset A → canonical model)

The plant-specific record:

```
ChamberNo, LoadDateJalali, LoadTime, UnloadDateJalali, UnloadTime, loadFingerCount, …
```

is evidence of a particular process, and maps conceptually to:

| Source field(s) | Canonical concept |
|---|---|
| `ChamberNo` | Equipment instance (type *dryer chamber*, factory configuration) |
| whole row | Operation Execution Record at stage *Drying* (load event → start, unload event → end) |
| `LoadDateJalali` + `LoadTime` | Operation start (canonical timestamp; original Jalali text preserved) |
| `UnloadDateJalali` + `UnloadTime` | Operation end |
| derived | Duration (drying time) |
| `loadFingerCount` | Input Quantity in unit *finger* (unit semantics pending II.7 #2) |
| `LoadOperatorCode_FK` / `….1` | Employee participation (load / unload roles) |
| `ProductCode_FK` | Product/Mold reference via versioned code mapping |

A brick factory with no chambers or fingers expresses its own stages, equipment types, and units through the same canonical concepts — zero schema change.

---

# Part VI — Architectural Principles

Binding on every subsequent phase (SRS, database, API, UI, implementation). Deviations require an ADR.

| # | Principle | Consequence |
|---|---|---|
| P1 | **Configuration over code.** Level-3 facts (32 chambers, 3 shifts, 4 wagons, 20 temp points, 72-h rule) live in configuration, never in code or schema constraints (Master Rules §27). | No factory constant may appear in a migration, model, or component. |
| P2 | **Evidence over assumption.** Every domain rule cites data, the frozen reference, or a plant answer; unknowns carry a `Needs plant validation` flag and block dependent design. | No invented business rules (the `grade2_count` lesson). |
| P3 | **One source of truth per artifact.** Product truth = this specification; schema truth = Django migrations (single lineage — unlike the frozen app's four divergent schema copies); decisions = ADRs. | Any duplicated definition is a defect. |
| P4 | **Canonical temporal core, Jalali-faithful edges.** Internal storage is canonical; original Jalali text is preserved and recoverable; UI supports both calendars (Master Rules §20). | The four-format parser is migration infrastructure, not UI code. |
| P5 | **Source data is immutable; corrections are audited.** Never overwrite raw inputs; every change is attributable (Master Rules §18, §44). | Layer ① append-only; correction log mandatory. |
| P6 | **API-first.** Every capability is exposed through the documented REST API before any UI consumes it; the UI is a client like any other (Master Rules §41). | Enables future PLC/SCADA/IoT and third-party integration. |
| P7 | **Multi-tenant from day one.** Company → Factory scoping on every operational record; roles are factory-aware (Master Rules §29, §42). | "Add a second factory" is a data operation, not a project. |
| P8 | **Analytics is a first-class citizen.** A feature is complete only when its data is analyzable (lineage, KPI hooks, layer-④ reachability) — not merely stored. | Analytics requirements reviewed in every feature spec. |
| P9 | **Configurable quality, workflow, and KPI models.** Outcome sets, process stages, and KPI definitions are administrator data (Master Rules §10, §21, §26). | No `grade1_count` columns; no hardcoded stage enums. |
| P10 | **Architecture changes only via ADR; AI implements, never re-architects.** | See Part VIII. |

Security baseline (lessons from Appendix A §4): real password verification, no secrets in the repository or in database tables, environment-based configuration, least-privilege database roles.

---

# Part VII — Roadmap

Refines the Master Rules §48 order by inserting explicit Historical Data, Configuration Model, and Workflow Engine phases before platform architecture (recorded in ADR-0003).

```
                    PRODUCT VISION
                          │
                          ▼
              BUSINESS & DOMAIN MODEL
                          │
                          ▼
               HISTORICAL DATA MODEL
                          │
                          ▼
                CONFIGURATION MODEL
                          │
                          ▼
                 WORKFLOW ENGINE
                          │
                          ▼
                PLATFORM ARCHITECTURE
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
          Database       API           UX
             │            │            │
             └────────────┼────────────┘
                          ▼
                    CORE PLATFORM
                          │
                          ▼
                  DATA / ANALYTICS
              ┌───────────┼───────────┐
              ▼           ▼           ▼
          Dashboards   Statistics   Reporting
                          │
                          ▼
                    AI / ML LAYER
                          │
                          ▼
                 DECISION SUPPORT
```

| Milestone | Deliverable | Gate to pass |
|---|---|---|
| **M0** | This specification v0.1 approved | Owner approval |
| **M1** | Plant validation round: Part II §II.7 answers recorded; glossary/domain model updated to v0.2 | All 14 checklist items answered or explicitly deferred |
| **M2** | Historical Data Architecture detailed spec: full 15-year archive inventory, profiling, mapping spec per file, DQ rules | Archive inventoried; mapping rules signed off |
| **M3** | Configuration Model spec: config schema for stages, equipment types, units, outcome sets, shift patterns, KPI definitions | Initial plant fully expressible as configuration |
| **M4** | Workflow Engine spec: stage transitions, record states, validation hooks | Current plant flow representable; second-factory thought experiment passes |
| **M5** | Platform architecture: SRS (functional + non-functional), ERD/database spec, API contract, UX blueprint | Consistency review against Parts II–VI |
| **M6** | Core platform implementation (Phase-1 scope per §49 MVP), driven through the Part VIII protocol | MVP criteria §I.4 demonstrated |
| **M7** | Data & analytics layer: dashboards, statistics, reporting; historical import executed with DQ report | §I.7 success criteria 2–3 |
| **M8** | AI/ML layer: forecasting, anomaly detection (architecture prepared earlier, implemented here) | Master Rules §24–25 scope |
| **M9** | Decision support: recommendations, optimization | Master Rules §2 "What should we do?" |

No milestone starts before its predecessor's gate is passed. Documentation phases M0–M5 produce no application code (ADR-0001).

---

# Part VIII — AI Collaboration Protocol

Purpose: prevent architecture drift when AI tools (Google AI Studio, coding agents, this assistant) contribute. The project remembers itself — the AI does not need to.

## VIII.1 Session rules

1. **Spec first.** Every AI session starts by supplying the current `docs/MASTER_SPECIFICATION.md` (plus relevant ADRs and appendices). Work requested without the spec attached is out of protocol.
2. **Scoped instructions.** AI tasks name the phase and the spec sections they implement, e.g.:
   > "Here is the approved domain model (Part III). Here is the approved database specification. Here is the API contract. Implement Phase 1 only. Do not modify architectural decisions."
3. **Never open-ended.** Prompts like "build me a manufacturing management system" are forbidden — they guarantee drift.

## VIII.2 What an AI may and may not do

| Allowed | Forbidden |
|---|---|
| Implement an approved spec section, verbatim in scope | Invent business rules, units, or quality outcomes |
| Flag ambiguities and propose ADR drafts for human decision | Alter architecture, schema, or API contract without an ADR |
| Refactor within an approved module boundary | Modify the frozen reference app or anything under `xls/` |
| Generate tests, docs, and migrations for approved designs | Resolve `Needs plant validation` items by assumption |

## VIII.3 Drift check

Every AI-produced deliverable is reviewed against the spec sections it cites. Output that cannot cite its governing section is rejected. Conflicts between output and spec are resolved in favor of the spec — or escalated to an ADR if the spec is wrong.

---

*End of Master Product & Architecture Specification v0.1. Amendments require a version bump and, for architectural changes, an ADR.*
