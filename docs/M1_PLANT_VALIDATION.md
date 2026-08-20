# M1 — Plant Validation Questionnaire

> **Purpose:** M0 froze the *data model* from the workbooks. M1 resolves the **domain unknowns** (Master Rules §54) with plant staff before M2 (historical-data import spec). Each item below lists: **what we observed**, **what we assumed**, **what we need confirmed**, and **priority** (P0 = blocks M2 import design if wrong; P1 = refines but non-blocking; P2 = post-build, from physical ledgers).
> **Status:** Draft for owner to walk through with plant staff.

---

## A. Dimensions / Master data

### A1. Product code `20` (P0)
- **Observed:** Packing code `20` → 61× «پنجه ای سبز» + 2× «سفال مشکی» (type column mostly سفال).
- **Assumed:** canonical `P-PANJEH-SABZ`.
- **Need:** Is code 20 really «پنجه ای سبز» or «سفال مشکی»? (type column contradicts name).
- **Owner call needed.**

### A2. Glaze vocabulary (P0)
- **Observed:** glaze col is free-text. Normalized: اخراء→اخرا, س→سفال. Other values: خودرنگ (dominant), لعاب, اخرا.
- **Assumed:** these 4 cover the glaze domain.
- **Need:** Full glaze list — any other glaze types exist (محروقی، لعاب‌دار variants, etc.)? Is «س» always «سفال»?

### A3. «پنجه ای» product type (P0)
- **Observed:** codes 16/17/20 carry «پنجه ای» — a type **not present** in Dryer/Kiln (A–E + 91xxxxx) scheme.
- **Assumed:** new composite type = پنجه ای × {خودرنگ، اخرا، سبز}.
- **Need:** Confirm «پنجه ای» is a real mold/type and how it maps to Dryer/Kiln product codes (or if it's Packing-only).

### A4. Operator master (P1)
- **Observed:** 15 distinct operator codes across files → recoded to 5 (global 1–5).
- **Assumed:** per-file codes are the same 5 people.
- **Need:** Confirm the 5-person roster; any operators missing from the workbooks?

---

## B. Dryer (خشک‌کن)

### B1. 50 numeric columns = per-3h temp + humidity series (P0)
- **Observed:** cols 0,3,6,…,150. Owner stated: every 3h, temp+humidity logged per chamber; **row above = temp, row below = humidity**; not all columns filled (chamber stay duration varies).
- **Assumed:** row-oriented `dryer_readings(time_offset, metric∈{temp,humidity}, value)`.
- **Need:** Confirm (a) 3-hour cadence, (b) row-above=temp / row-below=humidity layout, (c) blank cols = not-yet-logged (not missing data).

### B2. «فینگر» exact meaning (P0)
- **Observed:** `تعداد فینگر تولیدی` (Dryer), `تعداد فینگر` (Set). Spec previously «not defined».
- **Assumed:** a carrying unit (tray-rack) of dried bricks loaded into a chamber column.
- **Need:** Exact physical definition + typical capacity (so we can validate finger counts as plausible).

### B3. «نوع تولید» / «تعداد ستون» / «اپراتور بارگیری/تخلیه» (P1)
- **Observed:** these columns exist in Dryer but unmapped to a clear business concept.
- **Need:** What are they? (production type = product family? column = stacking column? load/unload operators = separate roles?)

---

## C. Kiln (کوره)

### C1. `input_type` semantics (P0 — confirmed, document)
- **Confirmed by owner:** خام/شارژی ≡ خشت خام/سفال پخته. Charged (شارژی) = already-fired ware re-sent to keep tunnel kiln running when no fresh production.
- **Action:** none — frozen in §13.

### C2. Temperature point vocabulary (P1)
- **Observed:** 1404 has 18 `temp_*` (exhaust, preheat 1–2, thermostat, zone 00–07, rapid 1–2, bottom A/01/B/02). Earlier years only `دمای اگزوز`.
- **Assumed:** row-oriented `kiln_temperature_readings(zone, value)`; >1200 °C = typo (×10 pattern).
- **Need:** Confirm the 18-zone list is complete & stable; confirm 1100–1200 °C is the true max tolerance.

### C3. «شماره پوشینگ» / «زمان پوشینگ» / «دمای لوله باتوم» / «دمای لوله خشک کن» (P1)
- **Observed:** present in Kiln `Input`.
- **Need:** What is «پوشینگ» (push event id? sequence?) and the two «لوله» (pipe) temperatures — are they distinct readings or duplicates of zone temps?

### C4. Fuel type (P2)
- **Spec mentions** fuel type on push events; **not seen** in workbooks.
- **Need:** Is fuel recorded anywhere, or dropped in later years?

---

## D. Setting (ستینگ)

### D1. 4-layer model (P0 — confirmed, document)
- **Confirmed by owner:** wagon is continuous across chambers/shifts; one chamber unload → 1–N wagons; partial wagon completed from prior chamber; unload may span shifts.
- **Frozen:** `setting_operations` + `setting_shift_unloads` + `setting_wagons` + `wagon_master` (ADR-0005).
- **Action:** none.

### D2. «تعداد ستون» / «کارکرد» / «ضایعات خشک کن» / «صحت اعداد وارد شده» (P1)
- **Observed:** in Set `Data`.
- **Need:** Definitions — column count (stacking?), کارکرد (machine runtime min?), dryer waste (units?), number-validation flag (auto or manual?).

### D3. MojiBake column `پ` (P1)
- **Observed:** `Data[0]` = `پ` (likely MojiBake of پرسنل/پالت).
- **Need:** What is this column really? (personnel count? pallet count?)

---

## E. Packing (بسته‌بندی)

### E1. Grade 2 definition (P0)
- **Observed:** `تعداد درجه 2` is **99.9% empty** in Packing-All.
- **Assumed:** grade 2 is not routinely recorded (spec derived it as total−grade1−waste — an assumption).
- **Need:** Is grade 2 real (rarely used) or always derived? Affects quality model.

### E2. «نوع کارگران» contains garbage (P1)
- **Observed:** column holds worker-type text **but also** stray dates like `95/04/31`.
- **Need:** What is this column's true meaning? (worker category vs. a mislabeled date column?)

### E3. «کنترلر» / «کد اقتصادی» / «شرح محصول» (P1)
- **Observed:** present in Packing-All.
- **Need:** Definitions — controller (who?), economic code (customer/tax id?), product description (free text vs. canonical).

### E4. Wagon traceability across stages (P0)
- **Observed:** `wagon_no` appears in Setting, Kiln (`واگن ورودی/خروجی`, `IncomingCarID`), and Packing.
- **Assumed:** same `wagon_no` space = one continuous entity (ADR-0005 `wagon_master`).
- **Need:** Confirm Packing `شماره واگن` refers to the **same** wagon as Setting/Kiln (so we can trace brick flow chamber→setting→kiln→packing).

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
