# Appendix C — Data-vs-Schema Reconciliation (Frozen Reference vs Historical CSVs)

- **Project:** Manufacturing Analytics & Execution Platform
- **Document status:** Evidence annex — reconciling the frozen reference schema's documented constraints against the *actual* values found in `xls/*.csv`. Findings here are inputs to the historical-import design (Master Rules §17–19, §33–37) and corroborate ADR-0002 and Architectural Principle P1.
- **Version:** 0.1
- **Date:** 2026-08-15
- **Method:** read-only profiling of every `xls/*.csv` (utf-8-sig encoding, stdlib, no writes to source) and direct inspection of `sql/init/00_schema.sql` constraint clauses. Row counts and distinct values are empirically verified, not estimated.

> Companion to [Appendix A](./APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md) (review of the frozen app's code) and [Appendix B](./APPENDIX_B_DATA_ASSETS.md) (catalog of the data assets). This appendix answers one question: **when the frozen app's own schema is checked against the plant's real exported data, what happens?**

---

## 1. The frozen app contains none of the historical data

The frozen legacy app's SQLite file `kiln_monitoring.db` (200 KB) was opened read-only and contains **only seed/master data** — reference tables (Categories 9, Glazes 4, Molds 1, Products 4, Users 4, Roles 4, Shifts 3) and a near-empty `SettingWagons` (5 rows), `DryerLoading` (4), `DryerUnloading` (3). All transactional tables (`DryerReadings`, `KilnPushData`, `PackagingRecords`, `Warehouse*`) are **0 rows**.

**Consequence:** although Appendix A §8 catalogued the data-quality issues *in the CSVs*, the frozen app never actually ingested them. None of the 9,242 transactional rows in `xls/` exist in any database of the frozen reference. The historical archive is still entirely in the CSVs — reinforcing the M2→M4 migration requirement (Roadmap Part VII).

---

## 2. Constraint-vs-data conflicts (the core finding)

Every hardcoded factory constant in the frozen schema was tested against the real CSV values. **Three of them are contradicted by the plant's own data.**

| Frozen constraint (source) | Plant data reality (verified) | Verdict |
|---|---|---|
| Frozen constraint (source) | Plant data reality (verified) | Verdict |
|---|---|---|
| `CHECK (chamber_no BETWEEN 1 AND 32)` — `sql/.../14_dryer_loading.sql:3`, `00_schema.sql:201,238` | Authoritative workbooks: **40 chambers** in Dryer (range 1–40); Setting `شماره چمبر` reaches up to 75 in some Set files | **CONFLICT** — the frozen `32` is wrong; real chamber count is **40** (owner-confirmed). Values >40 are user-typo candidates to flag, not a higher real maximum |
| `CHECK (shift_code IN (1,2,3))` — `00_schema.sql:33` | Setting/Packing shift ∈ {1,2}; **3 shifts confirmed** (صبح/عصر/شب). The earlier "shift 22" was a CSV-prototype artifact, not a real value | **CONFLICT (bound)** — 3 shifts is correct; the frozen model's bound is fine, but the value must not be a hard-coded constant (P1) |
| `CHECK (wagon_order BETWEEN 1 AND 4)` — `00_schema.sql:288` | Workbooks: wagon **serial 1–80** (owner-confirmed). Values >80 (e.g. 190, 465) are user-typo candidates to flag | **CONFLICT** — the 4-wagon limit is an app assumption; real wagon range is 1–80, values beyond are flagged for review (ADR-0006 §8.4) |

**Interpretation (corrected 2026-08-17):** the frozen app's integrity constraints are *inconsistent with the plant's recorded reality*, but the earlier figures (chamber 34, shift 22) were **wrong** — they came from the `xls/*.csv` *prototype*, which is a sample, not the source. Verified against the authoritative workbooks (`xls/real data/`): **chamber = 40, shift = 3 (صبح/عصر/شب), wagon = 80**. Out-of-range values (chamber >40, wagon >80) are **user typos to flag for review**, not higher real maxima. This is the strongest motivation for Principle P1 (**configuration over code**) — a Level-3 fact (number of chambers) must never be a code/schema constant.

---

## 3. Referential-integrity gaps discovered (PROTOTYPE CSV — superseded)

> **Note (2026-08-17):** the rows below were observed in the `xls/*.csv` *prototype* (a sample, not the source). The authoritative workbooks (`xls/real data/`) now supersede them — e.g. the prototype's `Packing.shift = 22` does **not** exist in `Packing-All.xlsx` (real shift is 1–3, see §11). Kept here as a record of the prototype's gaps; verify against the workbooks before acting.

Beyond the constraint conflicts, the transactional data contains codes absent from every reference file:

| Field | Orphan / unmapped value(s) | Reference set checked against |
|---|---|---|
| `Setting_Setting.OperatorCode_FK` | **`140`** — not in `Operators.csv` (valid codes: 1,2,4–11) | `xls/Operators.csv` |
| `Packing.shift` *(prototype only)* | **`22`** — not in {1,2,3} | shift definition |
| `Kiln.productName` | **`90000001`, `90000002`, `99999999`** — 0 of 3 match any reference (Mold/Product) | `xls/Molds.csv`, `xls/ProductName.csv` |
| `Packing.productName` *(prototype only)* | **`93000000`** — not in ProductName/Mold refs | `xls/ProductName.csv`, `xls/Molds.csv` |
| `Packing.GlazeType` *(prototype only)* | **`81000001`** — not in `Glaze.csv` | `xls/Glaze.csv` |
| `Kiln.GlazeType` | **`94000002`** — not in `Glaze.csv` | `xls/Glaze.csv` |

These are **open questions for plant staff** (glossary II.7 #5/#8), not invented rules. The import design (Part V layer ②) must route them to a review queue, never guess.

---

## 4. Column-completeness findings (PROTOTYPE CSV — superseded)

> **Note (2026-08-17):** observed in the `xls/*.csv` *prototype*. The real `Packing-All.xlsx` (§11) shows `تعداد درجه 2` is ~99.9% empty (rarely collected) and `نوع کارگران` is ~48% empty with stray date values — not the 100%-empty columns reported below. Verify against the workbooks.

Two columns are structurally unpopulated in the export — they were never collected, not merely missing occasionally:

| File | Column | Empty | Note |
|---|---|---|---|
| `Packing.csv` *(prototype)* | `typeOfWorkers` | **100%** (2065/2065) | drop or mark "not collected" |
| `Packing.csv` *(prototype)* | `workerscount` | **100%** (2065/2065) | drop or mark "not collected" |
| `Setting_Setting.csv` | `columns_count` | **76.2%** (756/992) | mostly uncollected; keep nullable |
| `Setting_Setting.csv` | `fingers_count` | 1.3% | minor |
| `Setting_Setting.csv` | `dryer_waste` | 3.5% | minor |

---

## 5. Operator-code partitioning (new observation)

Operator codes are **process-scoped**, not a single global pool:

| File | Codes observed | Overlap |
|---|---|---|
| `Dryer.csv` (load/unload) | 4, 5, 8 | — |
| `Kiln.csv` | 4, 5, 7, 8 | shares 4,5,8 with Dryer |
| `Packing.csv` | 1, 2 | distinct from above |
| `Setting_Setting.csv` | 9, 10, 11 (+ orphan 140) | distinct from above |

Either the `Operators.csv` master is incomplete, or codes are reused per process. **Needs plant validation** (glossary II.7 #5). Implication for import: operator FKs must be resolved per source file, not assumed globally.

---

## 6. Summary for the migration design

1. The frozen app is **evidence only** — it holds zero historical rows; the archive lives in `xls/`.
2. Three frozen constraints (`chamber 1–32`, `shift 1–3`, `wagon ≤ 4`) are **disproven by the data** → must become configuration (P1). Verified real bounds (2026-08-17, against authoritative workbooks): **chamber = 40, shift = 3 (صبح/عصر/شب), wagon = 80**. Out-of-range values are **user-typo candidates** to flag for review, not higher real maxima.
3. Unmapped codes from the `xls/*.csv` prototype (`140`, `90000001/2`, `99999999`, `93000000`, `81000001`, `94000002`) require a **review queue**, not guesses. (The earlier "shift 22" was a CSV-prototype artifact, not a real plant value.)
4. Two `Packing.csv` columns are 100% empty → treat as "not collected".
5. Operator codes are process-partitioned → resolve FKs per source file (§8).

All figures above are reproducible from `xls/*.csv` by direct count; no value was estimated.

---

## 7. Assessment of the *intended* normalized CSV design (the owner's optimization)

**Context change (2026-08-15):** the `xls/*.csv` files are **not** raw exports. Per the owner they are an *intentional relational/normalized design* — sample data demonstrating an optimized schema: one shared `Operators.csv` master referenced by all fact files; `Setting_Setting.csv` + `Setting_wagons.csv` as header/detail pair; and `Molds`/`ProductName`/`Glaze` as separated dimension tables. The CSVs are a **design prototype**, not a 1:1 extraction. This section assesses the *design*, not row-count parity with the source `.xlsm`.

### 7.1 What is correct and well-designed
- **Shared operator master** — `Operators.csv` (10 codes) is referenced as FK by Dryer/Kiln/Packing/Setting. In 3 of 4 fact files every used code exists in the master. ✅ Right idea (matches L1/L2 + config-driven intent).
- **Setting header/detail cross-reference** — `Setting_wagons.SettingID → Setting_Setting.ID`. Verified: **0 orphan detail rows**, and every header has at least one wagon row. The 1:N relationship is structurally sound. ✅
- **Separated dimensions** — `Molds` / `ProductName` / `Glaze` as independent lookup tables. ✅ Aligns with the spec's dimension modeling.

### 7.2 Issues that break the design even at the *prototype* level
1. **`Setting_Setting.ID` is duplicated (122 dups, e.g. `1404010913` appears 3×).** It cannot serve as a simple PK. See §7.3 — this is **domain-meaningful**, not dirty data, but the *key model* must change (composite/surrogate).
2. **Dimension masters are incomplete** — fact files reference codes absent from every master: `Setting_Setting.OperatorCode_FK ∈ {140, ''}`, `productName ∈ {90000001,90000002,99999999,93000000}`, `GlazeType ∈ {94000002,81000001}`. An FK built on these would break. Masters must *fully cover* the fact codes before import.
3. **Two product masters, one fact column** — `Molds` and `ProductName` both exist, but fact tables carry a single `productName`. Resolution rule (e.g. code-prefix → which master) is unspecified.

### 7.3 Domain example — why the repeated Setting ID is correct (confirmed by owner)
`Setting_Setting.ID` encodes **`YYYY` + `MM` + `DD` + `chamber_no`** (e.g. `1404010913` = 1404/01/09, chamber 13). A chamber's *loading* is one operation, but its *unloading* can span **two shifts**: the afternoon shift begins unloading (3 fingers), the morning shift completes it (4 fingers); the unloaded fingers are placed on **3 different wagons**.

→ The repeated ID is **one loading operation split across multiple unloading shifts/rows**, not a data error. This is a **domain rule the import must understand**, and it dictates the key model:
- `Setting_Setting.ID` is a **batch/operation key** (identifies "that chamber loading"), **not** a surrogate PK.
- The true record key must be **composite**: `(ID, shift, wagon_no)` (or a per-ID `sub_id`/`seq`).
- Target model → **three layers** (see ADR-0005): `setting_operations` (the loading, keyed by ID) → `setting_shift_unloads` (per-shift finger counts 3 & 4) → `setting_wagons` (the wagons, FK to shift). This preserves "7 fingers across 3 wagons over 2 shifts" without losing fidelity.

### 7.4 Conclusion
The owner's optimization direction is **correct and aligns with the spec**; the prototype only needs (a) a composite/surrogate key for Setting, (b) complete dimension masters, and (c) an explicit product-master resolution rule. None of these are schema violations of the source — they are *design refinements* to make the prototype import-ready.

All checks in §7 reproducible from `xls/*.csv` by direct FK/count inspection; no value estimated.

---

## 8. Dimension-master redefinition strategy (owner decision, ADR-0006)

The legacy workbooks assign **opaque, non-self-describing codes** to products and operators, and those codes are internally inconsistent. Per the owner (confirmed 2026-08-17), the migration must **redefine** the dimension masters rather than copy the legacy codes. Full rationale in [ADR-0006](../adr/ADR-0006-dimension-master-redefinition.md).

### 8.1 Product is composite, not an opaque code
- Fact rows carry atomic codes like `productName = 90000001` with no embedded meaning. The *real* product identity is **derived from `mold type + glaze + specific attributes`**. `Molds.csv` is one input, not the whole product.
- Target: independent dimensions `molds`, `glazes`, `product_attributes`, and a `products` table whose identity is a **configured composition rule** (mold + glaze + attributes). Legacy atomic codes are kept only as a `legacy_code` cross-reference for the mapping, never as product identity.

### 8.2 Glaze + product compose the final name
- `glazes` is a standalone dimension; the final product name = function(mold, glaze, attributes). Glaze and product are **independent composing dimensions**, not a single merged code.

### 8.3 Operators: consolidate names, then re-code
- Fragmentation + spelling errors across workbooks caused inconsistent operator codes (orphan `140`, blanks, partitioned codes — §5). Migration order: **(1)** collect & consolidate all operator names (dedupe + spelling normalization), **(2)** assign one canonical code per consolidated operator, **(3)** build `old_operator_code → new_operator_code` mapping. The `Operators.csv` master must be regenerated from the consolidated set.

### 8.4 Mandatory old→new mapping layer
- For **every** dimension (product, glaze, mold, operator, supervisor): an explicit `legacy_code → new_code` mapping table (versioned, Master Rules §18). Unmappable codes → review queue (P2/P5: never invent).

### 8.5 Source & extraction rules
- Mapping tables are built from the **authoritative workbooks** (`xls/real data/`), **not** the `xls/*.csv` prototype (the prototype is a sample and may omit codes).
- Native workbooks are **never rewritten in place** (§44/§32). Any cleaned Excel output is a *new artifact*, not a modification of source.

### 8.6 Implication for the prototype's "dimension gaps"
The §7.2 findings (unmapped `90000001/2/99999999/93000000`, glaze `94000002/81000001`, operator `140`/blank) are **expected** under this strategy: they are legacy opaque codes that will be *resolved by the redefinition + mapping layer*, not patched in the CSV. The CSV prototype's incomplete masters are therefore acceptable as a design demo; the authoritative masters come from the workbooks via §8.3–8.4.

### 8.7 Evidence — master extraction from the authoritative workbooks (2026-08-17)

All codes below were extracted read-only from `xls/real data/*.xls*` (Dryer/Kiln `CODE`/`DataSet` sheets; Set `Data` sheet). They **confirm ADR-0006** and expose why the `xls/*.csv` prototype masters are not authoritative.

**Product is composite (mold/type + glaze/color).** The workbooks' `CODE` sheet carries both single-letter composite codes and numeric composite codes, all self-describing:
- Letter codes: `A`=تیزه-سفال خودرنگ مخلوط, `B`=تیزه-سفال اخرا مخلوط, `C`=تیزه-سفال سبز مخلوط, `D`=تیزه-سفال نوک‌مدادی مخلوط, `E`=تیزه-سفال بیرنگ مخلوط.
- Numeric codes: `91000001..91000005` = سفال {خودرنگ/اخرا/سبز/نوک‌مدادی/بیرنگ}; `92000001..92000005` = تیزه {خودرنگ/اخرا/سبز/نوک‌مدادی/بیرنگ}; `93100001`=سفال نیمه‌خودرنگ; `94000002`=بخته دو‌باررفته.
- The Set `Data` sheet shows the **underlying independent dimensions**: `محصول` ∈ {سفال 16182, تیزه 386, آجر 24, اجر 8} and `لعاب/خودرنگ` ∈ {خودرنگ 7506, سفال 134, لعاب 3, آجر 2, اخرا 1, س 1}. i.e. **product type × glaze status** are the real composing dimensions; the numeric/letter codes are their pre-composed names. (`اجر` is a spelling variant of `آجر` → normalization candidate per §8.3.)

**Prototype master is NOT the source.** Compared with `xls/*.csv`:
- Prototype `Molds.csv`+`ProductName.csv` codes `{11000001,21000001,31000001,53000001,81000000,91000000,92000000}` → **0 of them exist in the workbooks**. Conversely every real product code (`91000001..94000002`, `A`–`E`) is **absent from the prototype**. The prototype masters are synthetic samples, not derived from source.
- Prototype `Operators.csv` codes `{1,2,4,5,6,7,8,9,10,11}`; real operator codes `{1..15}`. Real has **3, 12, 13, 14, 15** missing from the prototype.

**Operator fragmentation (exactly the §8.3 problem).** The same person carries multiple codes across sheets:
| Operator name | Legacy codes seen |
|---|---|
| سید حسین جلالی | 1, 4 |
| وحید عموزاد | 2, 5 |
| حسن یخکشی | 5, 7 |
| رجب علی پناه | 4, 8 |
| عسگری قاسمی | 3, 6 |

Only **5 distinct operator names** exist, but they are spread over 15 codes (plus blanks). Migration must consolidate to 5 canonical persons and re-code 1:1 (§8.3), building `old_operator_code → new_operator_code`.

**Conclusion:** the workbook extraction is the only valid basis for dimension redefinition (§8.5). The `xls/*.csv` prototype masters must be discarded as dimension sources; the composite product rule and the 5-operator consolidation are concrete, source-verified inputs to the M2 mapping spec.

All codes above reproducible by re-running the read-only extraction over `xls/real data/`; no value estimated.

### 8.8 Product codes — per-file consistent, but stray non-standard codes in facts (2026-08-17)

Unlike operators, the product `CODE`/`DataSet` lookup is **identical across every file** (A–E letter codes + `91000001..91000005`/`92000001..92000005`/`93100001`/`94000002`). No per-file reversal exists, so no per-file realignment is needed for products.

However, scanning every fact row found **5 distinct non-standard product codes**, all in 2 Kiln files, totalling **7 rows** out of 15 years of data:

| Code | Count | File | Diagnosis |
|---|---|---|---|
| `90000001` | 3 | Kiln-1399 | **unmapped** — absent from the CODE lookup; not a typo of any standard code |
| `9100000` | 1 | Kiln-1399 | **typo** of `91000001` (one digit short) |
| `80` | 1 | Kiln-1399 | **unmapped / data error** — far outside the code scheme |
| `910000001` | 1 | Kiln-1403 | **typo** of `91000001` (one digit long) |
| `940000002` | 1 | Kiln-1403 | **typo** of `94000002` (one digit long) |

**Handling (per ADR-0006 §8.4, P2/P5):**
- Typos (`9100000`, `910000001`, `940000002`) → auto-correct to the nearest standard code during staging (3 rows).
- Unmapped (`90000001`, `80`) → **review queue**, never invented (4 rows).
- Set files carry no product *code* at all — only a free-text `محصول` column (سفال/تیزه/آجر; `اجر` is a spelling variant of `آجر`). These map to the **product-type** dimension, not to a code, and feed the composite product rule (§8.1).

**Conclusion:** product coding is already globally consistent; the only cleanup is 7 stray fact rows in two Kiln files. The composite product rule (§8.1) remains the authoritative redefinition; the `xls/mapping/product_mapping_blueprint.csv` maps the standard codes to `type × glaze` canonical products.

All figures reproducible by re-running the read-only scan over `xls/real data/`; no value estimated.

### 8.9 Glaze column — free-text, normalized; cleaning complete (2026-08-17)

The glaze dimension is a **free-text column** (`لعاب/خودرنگ`) present only in the Set family's `Data` sheet (not in Dryer/Kiln). It is not a coded lookup — values are entered as text and vary by file:

| Value | Seen in | Notes |
|---|---|---|
| `خودرنگ` | all Set | dominant (no glaze applied) |
| `لعاب`, `لعاب اخرا`, `لعاب مشکی`, `مولتی مشکی` | 1403–1404 | real glaze variants |
| `اخرا`, `اخراء` (misspelling) | 1399–1402 | `اخراء` is a typo of `اخرا` |
| `آجر`, `کلاهک`, `سفال` | 1404 | product-like glaze notes |
| `س` | 1404 | typo of `سفال` |
| `19:45`, `10:25`, `15:10` | 1399–1400 | **time-like garbage** — wrong column entry |

**Cleaned workbooks (`xls/consolidated/`, source never touched):**
- Spelling normalized: `اخراء`→`اخرا` (×33), `س`→`سفال` (×1).
- Time-like garbage (`19:45`, `10:25`×2, `15:10`) blanked and logged to `REVIEW_glaze_strays.txt` for owner decision (never invented).
- Verified: zero stray glaze values remain in any Set file after cleaning.

### 8.10 Dimension-cleaning status — all three dimensions done (2026-08-17)

| Dimension | Coding pattern | Cleaned action | Review queue |
|---|---|---|---|
| **Operator** | per-file reversed (Kiln-1404 swapped 4↔5 etc.) | re-coded to global 1=سیدحسین,2=وحید,3=عسگری,4=رجب,5=حسن; **names untouched** | `REVIEW_operator_mismatches.txt` (33 blank high codes) |
| **Product** | globally consistent, 7 stray fact rows | 3 typos auto-corrected; 2 unmapped (`90000001`,`80`) blanked | `REVIEW_product_strays.txt` |
| **Glaze** | free-text, per-file variant spellings | `اخراء`→`اخرا`, `س`→`سفال`; time-like garbage blanked | `REVIEW_glaze_strays.txt` |

All three cleaned workbooks live in `xls/consolidated/` (git-ignored local artifact, per owner: workbooks are design references, never committed). The authoritative source in `xls/real data/` is untouched. These cleaned workbooks are the verified basis for the M2 import mapping spec (ADR-0006).

### 9. Operational columns — chamber / shift / wagon (2026-08-17, owner-confirmed)

Verified against the authoritative workbooks (`xls/real data/`), not the CSV prototype. Owner confirmed the real bounds; out-of-range values are user-typo candidates to **flag for review**, never higher real maxima.

| Column | Source sheet(s) | Verified range | Out-of-range rule |
|---|---|---|---|
| **شماره چمبر** (chamber) | Dryer `Data Entry`, Set `Data` | **1–40** (40 chambers, owner-confirmed) | `>40` → flag (user typo) |
| **شیفت** (shift) | Set `Data` | **1–3** = صبح / عصر / شب (owner-confirmed) | not in {1,2,3} → flag |
| **شماره واگن** (wagon) | Kiln `Input` (واگن ورودی/خروجی), Set `Data`, **Packing `شماره واگن`** | **1–80** (owner-confirmed serial) | `>80` → flag (user typo; Packing shows up to 1464 but these are typos per owner, to be corrected from physical ledgers) |

**Findings:**
- Earlier claims (Appendix C §2, prior draft) of "chamber 34" and "shift 22" were **wrong** — they derived from the `xls/*.csv` *prototype* (a sample), not the source. The real chamber count is **40**, shifts are **3**, wagon serial tops at **80**.
- Wagon values >80 found: Kiln `واگن ورودی` = 190 (×3 files), 465 (×1); Set `شماره واگن` = 81/82/83 (a handful of rows). All flagged for owner review.
- Chamber values >40 found in Set `شماره چمبر` up to 75 — flagged for owner review (likely typo, since real chamber count is 40).
- **Column-name caution:** two Set columns are easily misread:
  - `تعداد خشت داخل چمبر` = *brick count* (0–15120), **not** a chamber number.
  - Kiln `دمای واگن 44` = *wagon temperature* (≈130), **not** a wagon serial — exclude from wagon-range analysis.

**Implication for schema (P1):** `chamber_no`, `shift_code`, `wagon_no` must be **configuration-driven bounds** (default 40 / 3 / 80), never hard-coded SQL `CHECK` constants. The import's validation stage routes out-of-range rows to the review queue (ADR-0006 §8.4), it does not reject or invent.

All ranges reproducible by re-running the read-only scan over `xls/real data/`; no value estimated.

### 10. Date / time columns — mixed formats, Excel cast traps (2026-08-17)

Verified against the authoritative workbooks. Date and time are stored in **three different Jalali text formats** plus a Gregorian datetime, and Excel's type-casting produces traps the import must handle.

**Jalali date — three distinct formats (per file / per family):**

| Format | Example | Seen in |
|---|---|---|
| Dot (`YY.M.D`) | `98.1.2`, `1400.12.26` | Dryer-1398, Kiln-1398/1399, Set-1399, Kiln-1401/1402/1403/1404, Set-1400 |
| Slash (`YYYY/M/D`) | `1399/1/2`, `1404/1/5` | Dryer-1399, Set-1401 → 1404 |
| Dash / ISO (`YYYY-M-D`) | `1400-01-01` | Dryer-1400 → 1404 |

→ The import needs a **3-way Jalali parser** (dot / slash / dash); the format is **not stable across years**, so it cannot be hard-coded per file.

**Gregorian datetime — present but NOT canonical:**
- Dryer carries `تاریخ و زمان بارگیری میلادی` / `تخلیه میلادی` as `YYYY-MM-DD HH:MM:SS` (e.g. `2025-03-25 08:20:00`). Per owner (2026-08-17): the **Jalali date is the system-of-record**; the Gregorian column was only added for easier time arithmetic in Excel. Use Gregorian **only to cross-validate** the Jalali date, never as the stored canonical time.

**Time-of-day columns (separate from date):**
- Kiln `ساعت` / `PushingTime_min`: `HH:MM:SS` (e.g. `22:10:00`). **Trap:** some cells cast to `1900-01-03 00:00:00` (Excel's epoch base for a time with no date) — the import must read these as *time-only*, stripping the bogus 1900-01-03 date.
- Set `زمان شروع` / `زمان پایان`: `HH:MM` **or just `HH`** (e.g. `20`, `16:5`) — zero-padding and minute-omission must be tolerated.
- Dryer `مدت زمان`: free-text `N days, H:MM:SS` (e.g. `3 days, 0:00:00`) — parse as an interval, not a timestamp.

**Year normalization (owner rule 2026-08-17):**
- All years must be stored **fully qualified (13xx)** — e.g. `98` → `1398`. 2-digit years are prevalent (≈69k rows in Packing `تاریخ بسته بندی` alone). The system-of-record base is **1391–1399** (and onward); years 91–99 must be migrated as **1391…1399**.
- **Data gap:** year **1397 is missing 2 months** (only months 1–10 present); to be completed later from physical ledgers.

**Design rules (P1, corrected 2026-08-17):**
1. **Jalali date is canonical** — store as the system-of-record `DATE`/timestamp. Gregorian is a *validation-only* helper column, not the stored truth.
2. **Time-of-day: keep `HH:MM` only** — drop seconds (owner: seconds not needed). Store separately from date when source has no date (Kiln/Set time columns).
3. **Normalize 2-digit years → 13xx** at ingest; never store a bare 2-digit year.
4. The Jalali parser must accept dot / slash / dash formats and the `1900-01-03` Excel-time trap; unparseable values → review queue (never invented).
5. `Rand_Tize` / `Rand_sofal` sheets are analytic rollups (monthly `میانگین سال` headers like `خرداد`), **not** transaction rows — exclude from Fact loading.

All formats reproducible by re-running the read-only scan over `xls/real data/`; no value estimated.

### 11. Packing — authoritative source added (2026-08-17)

The owner added `Packing-All.xlsx` (93,389 rows, all years) to `xls/real data/` — the true source, replacing the earlier `xls/Packing.csv` *prototype* (which was a sample and had wrong figures: e.g. it implied "shift 22", which does not exist — real shift is 1–3).

**Sheet1 columns:** `تاریخ بسته بندی, ماه, روز, شیفت, کنترلر, نوع کارگران, تعداد کارگران, نوع محصول, کد محصول, شرح محصول, شماره واگن, تعداد کل محصول, درجه 1, درجه 2, ضایعات, راندمان`. A `Legend` sheet maps economic codes / input products.

**Findings:**
- **Shift = 1–3** (distinct=3) — confirms §9; no "22".
- **Wagon = 1–1464** in this file, but per owner the real range is **1–80**; **757 rows >80 are user typos** → flag for correction from physical ledgers (same rule as §9).
- **Product code (1–28, 19 distinct) is internally inconsistent** — 8 codes map to *multiple* names, e.g. `code 4 → {تیزه خودرنگ, سفال خودرنگ}`, `code 03 → {56, اخرا, خودرنگ, سفال خودرنگ}`, `code 16 → {4 variants}`. This is exactly the **opaque-legacy-code** problem ADR-0006 targets → these rows go to the product review queue; the new platform redefines product as composite (type × glaze), not by these codes.
- **Product coding differs from Dryer/Kiln** (which use A–E + 91xxxxx). Packing uses a **separate legacy scheme** (1–28) — the migration mapping must reconcile both schemes to the canonical product (ADR-0006).
- **`نوع محصول`** has Arabic/Farsi spelling variants (`تيزه` vs `تیزه`) — apply Ye/Kaf normalization (see memory: legacy normalization rule).
- **`تعداد درجه 2`** is ~99.9% empty (only 132/93,389 filled) — treat as "rarely collected", not a hard requirement.
- **`نوع کارگران`** has stray date-like values (`95/04/31`) mixed with real categories — flag for review.

**Year coverage (normalized):** 1391–1404 all present with 12 months **except 1397 (months 1–10 only — 2 months missing)** and 1404 (partial, months 1–3). 1390 has a single stray row. ~69k rows use 2-digit years (e.g. `98.1.2`) and must be normalized to 13xx.

**Implication:** Packing is the **richest operational transaction set** and must drive the packing Fact table; its legacy product/wagon codes feed the ADR-0006 review queues, and the 1397 gap is a known data-completion task (owner: fill from physical ledgers later).

#### 11.1 Packing product-code conflict resolution (2026-08-17)

The 8 conflicting codes were dissected by frequency + the `نوع محصول` column (99% reliable). The conflicts are **typos / spelling variants**, not genuinely distinct products:

| Code | Dominant name (count) | Stray names | Canonical → | Note |
|---|---|---|---|---|
| `03` | سفال خودرنگ (48,080) | اخرا(4), `56`(1) | `P-SOFAL-KHODRANG` | type=سفال → collides with `91000001` |
| `04` | تیزه خودرنگ (2,192) | — | `P-TIZEH-KHODRANG` | type=تیزه → collides with `A`/`92000001` |
| `4` | تیزه خودرنگ (1,052) | سفال خودرنگ(9, typo) | `P-TIZEH-KHODRANG` | same canonical as `04` |
| `01` | سفال اخرا (501) | اخرا/اخراء (typos) | `P-SOFAL-AKHRA` | normalize spelling اخراء→اخرا |
| `02` | تیزه اخرا (39) | اخرا (typo) | `P-TIZEH-AKHRA` | normalize |
| `16` | تیزه پنجه ای خودرنگ (2,608) | سفال خودرنگ(20, typo) | `P-TIZEH-PANJEH-KHODRANG` | **new type پنجه ای** not in Dryer/Kiln scheme |
| `17` | تیزه پنجه ای اخرا (28) | پنجه ای اخراء(typo) | `P-TIZEH-PANJEH-AKHRA` | new type |
| `20` | پنجه ای سبز (61) | سفال مشکی(2, typo) | `P-PANJEH-SABZ` | **type ambiguous** (type col mostly سفال) → REVIEW |

**Resolution rules applied:**
1. Decide canonical product **by `نوع محصول`**, not by the noisy free-text name.
2. Apply Ye/Kaf + اخراء→اخرا normalization to names.
3. Multiple legacy codes converging on the same (type×glaze) canonical → **expected collisions** (e.g. `03`≈`91000001`, `04`/`4`/`A`/`92000001` all = تیزه خودرنگ). The new platform stores the canonical product, dropping the legacy code.
4. Two **new product types** surface from Packing that the Dryer/Kiln scheme never had: **پنجه ای** (codes 16/17/20). These must be added to the product-type vocabulary (config-driven).
5. `20` (پنجه ای سبز) has an **ambiguous type column** (mostly سفال) → flagged REVIEW before finalizing.

The full `legacy → canonical` map is in `xls/mapping/product_mapping_blueprint.csv` (now covers Dryer/Kiln A–E + 91xxxxx **and** Packing 1–28 schemes).

All figures reproducible by re-running the read-only scan over `xls/real data/`; no value estimated.

### 12. Kiln temperature columns — schema grew over time (2026-08-17)

Verified against the authoritative workbooks. The number of temperature columns **expanded with the plant's instrumentation**, so the schema must be **row-oriented**, not a fixed 18-column block.

**Kiln-1404 (latest): 18 `temp_*` columns, all fully populated (2,840 rows):**

| Group | Columns | Approx. range (°C) |
|---|---|---|
| Exhaust | `temp_exhaust` | ~190 |
| Preheat | `temp_preheat01`, `temp_preheat02` | 400–520 |
| Thermostat | `temp_termostat` | ~740 |
| **Zones** | `temp_Zone00` … `temp_Zone07` | 760–950 (8 zones) |
| Rapid | `temp_rapid01`, `temp_Rapid02` | 570–610 |
| Bottom | `temp_bottomA`, `temp_bottom01`, `temp_bottomB`, `temp_bottom02` | 350–560 |

**Earlier years — far fewer columns:**
- Kiln-1398 → 1403 (`Input` sheet): only `دمای اگزوز` (~7,700 rows) is populated; `دمای واگن 44` is populated only in 1398/1399; `دمای لوله باتوم` / `دمای لوله خشک کن` are **0% filled** in every year.
- Localized names (`دمای اگزوز`) in 1398–1403 switch to English `temp_*` keys in 1404 — **naming also changed**, not just count.

**Implications for schema (P1 / ADR-0001):**
1. **Do NOT hard-code 18 temperature columns.** The source had 1 (exhaust-only) for years, then 18. A fixed column block breaks on older years.
2. Model temperatures **row-oriented**: a `kiln_temperature_readings` child table keyed by `(kiln_record_id, zone_key, reading_type)` — each zone/temperature point becomes a row, so adding zones later needs no schema change.
3. Build the zone/reading vocabulary (exhaust, preheat01, Zone00…07, rapid01, bottomA, …) as **configuration** (Appendix B §3 style), not code.
4. Packing/Set carry `راندمان` (efficiency, 0–1 ratio) — a different measure, not a kiln temperature; keep separate.

#### 12.1 Temperature vocabulary + plausibility bound (2026-08-17)

**Reading vocabulary (from Kiln-1404, 18 points, 6 groups):**

| Group (config key) | Source columns | Typical avg (°C) |
|---|---|---|
| `exhaust` | `temp_exhaust` | ~190 |
| `preheat` | `temp_preheat01`, `temp_preheat02` | 400–540 |
| `thermostat` | `temp_termostat` | ~750 |
| `zone` | `temp_Zone00` … `temp_Zone07` (8 zones) | 770–950 |
| `rapid` | `temp_rapid01`, `temp_Rapid02` | 570–600 |
| `bottom` | `temp_bottomA`, `temp_bottom01`, `temp_bottomB`, `temp_bottom02` | 325–550 |

**Plausibility bound (owner rule):** the kiln's maximum tolerance is **1100–1200 °C**. Any reading **> 1200 °C** is a **typo / sensor fault** → flag for review (same class as wagon>80, chamber>40). Verified: only **10 of 2,840** rows (0.35%) exceed 1200 °C. **Pattern:** every over-limit value is ~**×10 its normal** (an extra-zero typo) — e.g. `temp_Zone01 = 9930` vs avg 932 (≈993×10), `temp_Zone05 = 8981` vs 898×10, `temp_preheat02 = 5756` vs 575×10. Suggested (not auto-applied — P2/P5) correction: divide by 10 and re-validate; final call stays with plant staff via the review queue. These 10 belong in the temperature review queue, never auto-corrected or invented.

**Implication:** the temperature import stage needs (a) a **config vocabulary** mapping each `temp_*` column to a `(group, reading_type)` pair, and (b) a **plausibility max (1200 °C)** that routes out-of-range readings to review. Both are data/config, not code.

All figures reproducible by re-running the read-only scan over `xls/real data/`; no value estimated.

### 13. Additional operational columns — dryer humidity series, kiln input-type, Set_1398 (2026-08-17)

A full column census (all 22 workbooks, all sheets) surfaced columns the earlier per-family scans missed.

**Dryer — humidity/temperature time series (51 numeric cols):**
- Headers `0, 3, 6, … 150` (every 3 hours) — **51 columns**. Per owner: every 3h the **dryer temperature AND humidity** of each chamber are logged. In the source file **each chamber row carries two data rows: the upper row = temperature, the lower row = humidity**.
- **Column count is variable** — not all 51 are populated in every file, because the **retention time in the chamber varies** (set by expert judgment, may change later). The import must do **dynamic column discovery** (read only populated series columns), never hard-code 51.
- Model **row-oriented** like kiln temps: a `dryer_readings` child table keyed by `(dryer_record_id, reading_index, measure)` where `measure ∈ {temp, humidity}` — preserves the per-3h rhythm and the variable length.

**Kiln — input type (raw vs recharge):**
- Column `خام` (Kiln-1398→1403) records the **input material type**: `خام` (= un-fired green ware) is the norm; `شارژی` (= already-fired ware sent through again to keep the tunnel kiln fed when there is no production) appears once (Kiln-1403, 1 row).
- **Kiln-1404 renamed** the column to **`incomingProduct_Type`** with values **`خشت خام`** (≡ خام) and **`سفال پخته`** (≡ شارژی).
- Import maps both eras to a canonical `input_type ∈ {خشت_خام, سفال_پخته}`. This is a **new Fact dimension** for the kiln table (ADR-0001: not hard-coded).

**Set — `سرشیفت` = shift supervisor** (distinct from `نام اپراتور`/operator). Treat as a separate personnel column.

**Set_1398.xls — legacy .xls format (gap closed):**
- `openpyxl` cannot read `.xls`; this file was invisible to the earlier scan. Read via `xlrd`. Structure matches other Set files (same columns; `Data` sheet = 5,978 rows). No new schema elements — the analysis gap was **format access**, not structure.
- The `Note` sheet contains MojiBake text (e.g. `نéضت âرèآé…`) — a stray note, not transaction data; ignore for Fact loading.
- `Data` sheet has **repeated column groups** (واگن/لعاب/زمان/بسته/خشت appear multiple times) — likely multiple loadings per chamber row; the import must de-duplicate/realign by the repeating block, not assume a single occurrence.

All figures reproducible by re-running the read-only scan over `xls/real data/`; no value estimated.

### 14. Setting (ستینگ) — continuous wagon model (2026-08-17)

Per owner's process description, the setting stage loads dried bricks from a dryer chamber onto wagons, and **a wagon is a continuous entity that spans chambers and shifts**:

- When a dryer chamber opens, **all** its dried bricks go to setting and are laid onto wagons.
- A wagon may already be **partly filled from a previous chamber** (not yet complete) → the new chamber **completes** it.
- From one chamber you can get: a fully-filled wagon, **and** a partially-filled wagon; the partial wagon carries over to the next chamber's setting.
- The unload + wagon-fill may **not finish in one shift** → continued in the next shift.

**Workbook evidence:** the Set `Data` sheet is **NOT one row per chamber**. It carries **repeating wagon blocks** — Set_1404 has **4 identical block groups** (cols 12–19, 20–27, 28–35, 36–43), each a `{شماره واگن, لعاب/خودرنگ, زمان شروع/پایان, کارکرد, تعداد بسته, تعداد خشت, تعداد کل سفال}` group, followed by summary cols (ضایعات ماشین آلات, ضایعات خشک کن, صحت اعداد, تعداد کل خشت بسته بندی شده, تعداد خشت داخل چمبر). The earlier-seen "two Set CSV files" correspond to **these two phases within one sheet**: (a) chamber-unload, (b) wagon-fill.

**Direct confirmation — the `xls/` prototype CSVs already model this:**
- `xls/Setting_Setting.csv` (992 rows) = the **header** op: `date_jalali, shift, supervisorID, OperatorCode_FK, personnel_count, chamber_no, productName, fingers_count, columns_count, dryer_waste, ID`.
- `xls/Setting_wagons.csv` (2,481 rows) = the **child wagon rows**: `SettingID, wagon_no, GlazeType, start_time, end_time, packages` — where `SettingID` is the FK to `Setting_Setting.ID`.
- Max **4 wagons per SettingID** (matches the 4 repeating blocks in the workbook `Data` sheet). Avg ~2.5 wagons/op. The separate wagon table is exactly what makes a wagon **cross-chamber/cross-shift** (one `wagon_no` can appear under multiple `SettingID`s → aggregate).
- Setting product codes seen here: `91000000` (943, ≈ سفال خودرنگ / common code), `81000000` (32), `92000000` (17) — to be added to the product blueprint (§11.1 scheme).

**Implications for schema (P1 / ADR-0001):**
1. **Setting Fact = header + child wagon rows.** One setting operation (chamber, date, shift, operator, supervisor, product, finger/column counts) parents **1–N wagon-load rows** (one per repeating block). Do NOT model setting as a single flat row.
2. **Wagon is cross-chamber / cross-shift.** The same `شماره واگن` can appear in multiple setting rows (filled across chambers/shifts). The import must **aggregate** a wagon's loads (union of its block rows) into one wagon entity — never treat each appearance as independent.
3. **Repeating-block parsing, not fixed columns.** Because the block count varies (1–4+ per chamber), parse by the repeating `{شماره واگن … تعداد کل سفال}` pattern; the block width is the unit, not a hard-coded column index.
4. **Shift boundary:** setting rows may span shifts; the `شیفت` on the header is the *starting* shift — continuation in the next shift is a separate row (or a `continued_from` link). Keep shift as an attribute, not an implicit grain.
5. Column `[0]` `پ` (likely MojiBake of پرسنل/پالت) and `کارکرد` (machine runtime) need normalization; ignore the `Note`-style MojiBake in analysis sheets.

All figures reproducible by re-running the read-only scan over `xls/real data/`; no value estimated.

### 15. Final column audit + analytic-column exclusion (2026-08-17)

A full pass over all 22 workbooks (every sheet, openpyxl + xlrd for `.xls`) listed every **data** column (analytic sheets excluded). Result: all operational dimensions are covered by §8–§14. No uncovered operational column remains.

**Per-family data-column inventory (analytic sheets removed):**
- **Dryer (17):** operator load/unload, loading/discharge dates (Jalali+Gregorian), produced fingers, chamber, month, duration, operator name/code, product name/code, production type, notes.
- **Kiln (61):** 18 `temp_*` readings, `خام`/`incomingProduct_Type` (input type), push time, operator, date/hour, product type/name, operator/product code, **`IncomingCarID` = same as wagon number** (owner: it IS the wagon no, just renamed in 1404), `شماره پوشینگ`, `واگن ورودی/خروجی`, plus a stray `#VALUE!` cell (Excel error → ignore).
- **Packing (20):** packing date, grade 1/2, waste, workers, total product, efficiency, day, description, wagon, shift, month, input product, product type, worker type, economic code, product code, controller.
- **Set (35):** date, package/brick/total, column/finger/personnel, efficiencies (3 kinds), shift-start/end, supervisor, wagon, chamber, shift, glaze, product, operator, waste, runtime, `پ` (MojiBake of پرسنل/پالت), plus repeated wagon blocks (§14).

**Analytic columns EXCLUDED from migration (owner decision):** the `راندمان` rollups, `Rand_Tize`/`Rand_sofal`, `Analyse`/`Analyse1`, `Tabarestan`, `Note`, `Access`, `error`, `Backupmnu`/`backup` sheets. These are derived/summary views and will be **re-designed later from the migrated fact data**, not carried over as raw columns. The migration's job is the **operational transactions** only.

**Resolved naming notes:**
- `IncomingCarID` (Kiln-1404) ≡ wagon number — maps to the existing `wagon_no` dimension, not a new field.
- `#VALUE!` (Kiln-1403) and `پ` (Set MojiBake) are data-quality noise → ignore / normalize at ingest.

**Status: data profiling complete — ready for M0 architecture sign-off.** All operational facts, bounds, typo/flag rules, and the row-oriented models (kiln temps, dryer temp+humidity, setting header+wagon) are frozen in §8–§15 and the migration blueprints.

All figures reproducible by re-running the read-only scan over `xls/real data/`; no value estimated.
