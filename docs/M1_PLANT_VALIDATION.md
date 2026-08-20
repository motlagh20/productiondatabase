# M1 — Plant Validation Questionnaire

> **Purpose:** M0 froze the *data model* from the workbooks. M1 resolves the **domain unknowns** (Master Rules §54) with plant staff before M2 (historical-data import spec). Each item below lists: **what we observed**, **what we assumed**, **what we need confirmed**, and **priority** (P0 = blocks M2 import design if wrong; P1 = refines but non-blocking; P2 = post-build, from physical ledgers).
> **Status:** **P0 items ALL RESOLVED (2026-08-20)** — owner walked through all P0 with plant staff. P1/P2 remain as refinement / post-build items. Proceed to **M2 (historical-data import spec)**.

---

## A. Dimensions / Master data

### A1. Product code `20` (P0 — RESOLVED)
- **Observed:** Packing code `20` → 61× «پنجه ای سبز» + 2× «سفال مشکی» (type column mostly سفال).
- **Decision (owner 2026-08-20):** product code is **re-derived from (نوع محصول + شرح محصول)**, NOT from the legacy `کد محصول` column. Per owner rule, `شرح محصول` is the source of truth (if it says سفال → سفال; تیزه → تیزه; تیزه انتهایی پنجه ای → پنجه ای). Code `20` → **پنجه ای سبز** (per شرح). The 2 «سفال مشکی» rows are typos → REVIEW.
- **Implication:** Mapping blueprint must key on (type, description), not legacy code. Aligns with ADR-0006 composite product.

### A2. Glaze vocabulary (P0 — RESOLVED)
- **Observed:** glaze col is free-text. Full scan of all 22 workbooks found: خودرنگ, اخرا/اخراء, لعاب/تولید لعابدار, سبز (لعاب سبز/سفال سبز/تیزه سبز/پنجه ای سبز), مشکی (لعاب مشکی/مولتی مشکی/سفال مشکی), مولتی (مولتی مشکی + مولتی اخرا variants: سفال/تیزه/پنجه ای مولتی اخرا).
- **Decision (owner 2026-08-20):** glaze is an **independent dimension** kept as a **text column** (typo-fix only: اخراء→اخرا, س→سفال) — NO structural change to source. Glaze vocabulary table (`glaze_mapping_blueprint.csv`) is for **validation/lookup only**. «مولتی» = multi-color/combined (not a single color). Minimal-change-to-source principle applies.

### A3. «پنجه ای» product type (P0 — RESOLVED)
- **Observed:** codes 16/17/20 carry «پنجه ای» — a type **not present** in Dryer/Kiln (A–E + 91xxxxx) scheme.
- **Decision (owner 2026-08-20):** «پنجه ای» = **Ending ridge tile** = an **independent mold type** (3rd type after سفال=Tile, تیزه=Ridge tile). So mold types = {سفال, تیزه, پنجه ای}. Valid in composite product model (ADR-0006).

### A4. Operator master (P1)
- **Observed:** 15 distinct operator codes across files → recoded to 5 (global 1–5).
- **Assumed:** per-file codes are the same 5 people.
- **Need:** Confirm the 5-person roster; any operators missing from the workbooks?

---

## B. Dryer (خشک‌کن)

### B1. 50 numeric columns = per-3h temp + humidity series (P0 — RESOLVED)
- **Observed:** cols 0,3,6,…,150. Owner stated: every 3h, temp+humidity logged per chamber; **row above = temp, row below = humidity**; not all columns filled (chamber stay duration varies).
- **Confirmed (owner 2026-08-20, with screenshot):** Each chamber row has **1 metadata row + 2 parallel rows** (top = temp, bottom = humidity) on the left side; the **hour number (0,3,6…) sits in a header row above the data** (not in the data cells). Column count varies per chamber (observed 13 cols = 0–36h). Blank cells = not-logged (not zero). 
- **Model:** `dryer_readings(chamber_op_id, time_offset_hours, metric∈{temp,humidity}, value)` — row-oriented; hour parsed from header row (not hard-coded column index).

### B2. «فینگر» exact meaning (P0 — RESOLVED)
- **Observed:** `تعداد فینگر تولیدی` (Dryer), `تعداد فینگر` (Set).
- **Decision (owner 2026-08-20):** **Finger car** = a transport device that moves **trays (سینی)** of product. Process: pressed clay → placed on **8-slot trays** (8 wet bricks each) → trays accumulate on **elevator (الواتور)** → when full, **finger car** lifts trays and transfers them **into the chamber** for drying. So «تعداد فینگر» = number of finger-car loads/transfers in that operation. Validated: 4–8 plausible. Aligns with §13.

### B3. «نوع تولید» / «تعداد ستون» / «اپراتور بارگیری/تخلیه» (P1)
- **Observed:** these columns exist in Dryer but unmapped to a clear business concept.
- **Need:** What are they? (production type = product family? column = stacking column? load/unload operators = separate roles?)

---

## C. Kiln (کوره)

### C1. `input_type` semantics (P0 — RESOLVED)
- **Confirmed by owner:** خام/شارژی ≡ خشت خام/سفال پخته. Charged (شارژی) = already-fired ware re-sent to keep tunnel kiln running when no fresh production. Kiln-1404 renames to `incomingProduct_Type` with values {خشت خام, سفال پخته}. Frozen in §13. Action: none.

### C2. Temperature point vocabulary (P0 — RESOLVED)
- **Observed:** 1404 has 18 `temp_*` (exhaust, preheat 1–2, thermostat, zone 00–07, rapid 1–2, bottom A/01/B/02). Earlier years only `دمای اگزوز`.
- **Confirmed (owner 2026-08-20):** the 18-zone list is **complete & final**: exhaust=اگزوز, preheat01/02=پیش‌گرما یک/دو, thermostat=ترموستات, zone00-07=زون ۰۰-۰۷, rapid01/02=راپید یک/دو, bottomA/01/B/02=باتوم A/۰۱/B/۰۲. Max tolerance **1100–1200 °C**; >1200 = typo/sensor fault → flag (×10 pattern observed). Row-oriented model confirmed.

### C3. «شماره پوشینگ» / «زمان پوشینگ» / «دمای لوله باتوم» / «دمای لوله خشک کن» (P1)
- **Observed:** present in Kiln `Input`.
- **Need:** What is «پوشینگ» (push event id? sequence?) and the two «لوله» (pipe) temperatures — are they distinct readings or duplicates of zone temps?

### C4. Fuel type (P2)
- **Spec mentions** fuel type on push events; **not seen** in workbooks.
- **Need:** Is fuel recorded anywhere, or dropped in later years?

---

## D. Setting (ستینگ)

### D1. 4-layer model (P0 — RESOLVED)
- **Confirmed by owner:** wagon is continuous across chambers/shifts; one chamber unload → 1–N wagons; partial wagon completed from prior chamber; unload may span shifts. Frozen: `setting_operations` + `setting_shift_unloads` + `setting_wagons` + `wagon_master` (ADR-0005). Action: none.

### D2. «تعداد ستون» / «کارکرد» / «ضایعات خشک کن» / «صحت اعداد وارد شده» (P1)
- **Observed:** in Set `Data`.
- **Need:** Definitions — column count (stacking?), کارکرد (machine runtime min?), dryer waste (units?), number-validation flag (auto or manual?).

### D3. MojiBake column `پ` (P1)
- **Observed:** `Data[0]` = `پ` (likely MojiBake of پرسنل/پالت).
- **Need:** What is this column really? (personnel count? pallet count?)

---

## E. Packing (بسته‌بندی)

### E1. Grade 2 definition (P0 — RESOLVED)
- **Observed:** `تعداد درجه 2` is **99.9% empty** in Packing-All.
- **Decision (owner 2026-08-20):** **درجه ۲ ≡ ضایعات** (same concept). Migration rule: **carry the value if present, leave blank if absent** (no structural change — minimal-change principle). Later, grade-2/waste can be **derived** from grade-1 + total. Owner also noted **numerical errors are frequent** in the data → a post-import QA/validation pass is needed (tracked as P2, not blocking M0/M2).

### E2. «نوع کارگران» contains garbage (P1)
- **Observed:** column holds worker-type text **but also** stray dates like `95/04/31`.
- **Need:** What is this column's true meaning? (worker category vs. a mislabeled date column?)

### E3. «کنترلر» / «کد اقتصادی» / «شرح محصول» (P1)
- **Observed:** present in Packing-All.
- **Need:** Definitions — controller (who?), economic code (customer/tax id?), product description (free text vs. canonical).

### E4. Wagon traceability across stages (P0 — RESOLVED)
- **Observed:** `wagon_no` appears in Setting (`Setting_wagons`), Kiln (`واگن ورودی/خروجی`, `IncomingCarID`), and Packing (`شماره واگن` — confirmed present in Packing-All.xlsx Sheet1 header, index 10).
- **Confirmed (owner 2026-08-20):** the **same wagon number = one physical unit** across Setting → Kiln → Packing. Full brick-flow traceability is possible. Aligns with ADR-0005 `wagon_master` (cross-chamber/cross-shift/cross-stage continuous entity).

---

## F. Cross-cutting / data-quality (post-build, P2)

| Item | Action | Who |
|---|---|---|
| 1397 missing 2 months | Re-import after ledger completion (idempotent) | Owner |
| Wagon >80 typos (757 Packing rows) | Correct from ledgers, flag in `REVIEW_*.txt` | Owner |
| Operator code typos | Correct from ledgers | Owner |
| Kiln temp >1200 (10 rows, ×10) | Flag; ÷10 suggested, owner confirms | Owner |
| Set_1398.xls MojiBake in Note sheet | Ignore (analytic note, not data) | — |

---

## G. Validation method
1. Owner walks section **A, B1, B2, C2, E1, E4** (P0) with plant staff — these block M2 import if wrong.
2. P1 items refine the schema but don't block; collect when convenient.
3. P2 items are post-build ledger corrections (already non-blocking for M0).
4. Record answers in this doc; once P0 resolved → **M2 historical-data import spec** can be written.

---
*Generated 2026-08-17 (M1 draft). Source: Appendix C §1–§15, ADR-0005, MASTER_SPECIFICATION §54 unknowns, workbook profiling.*
