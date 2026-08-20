# M0 — Architecture Sign-Off

> **Purpose:** This document is the gate checkpoint for milestone **M0** (specification approval before any platform code). It summarizes every decision, finding, and open item so the owner can approve the architecture in one pass.
> **Status:** ✅ **APPROVED by owner — 2026-08-17.** No application code has been written (ADR-0001 compliant). Proceed to M1 (plant validation) → M2 (historical data import spec) → platform build.

---

## 1. What was done (read-only, no source modified)

We profiled the **authoritative source workbooks** (`xls/real data/`, 22 files, Jalali years 1391–1404 incl. `Packing-All.xlsx`) and the owner's normalized `xls/*.csv` prototype, then froze findings as ADRs + Appendix C. All analysis was **read-only**; the source was never modified.

## 2. Architecture Decisions (ADRs 0001–0006)

| ADR | Decision | Status |
|---|---|---|
| 0001 | Documentation-first — no code until M0 + glossary approved | ✅ Compliant (0 app-code commits) |
| 0002 | Freeze legacy app as read-only reference | ✅ Frozen, 0 rows |
| 0003 | Consolidated Master Specification | ✅ Single spec of record |
| 0004 | PMS repo = design/UX donor (harvest, never merge code) | ✅ |
| 0005 | Setting 3-layer model → **4 layers** (op / shift-unload / wagon / `wagon_master`) | ✅ Updated (§14) |
| 0006 | Dimension redefinition — composite product, clean operators, review queues | ✅ Blueprints done |

## 3. Verified operational facts (owner-confirmed)

| Dimension | Rule | Out-of-range → |
|---|---|---|
| Chamber | **1–40** | flag (typo) |
| Shift | **1–3** = صبح/عصر/شب | flag |
| Wagon | **1–80** | flag (correct from ledgers) |
| Date | **Jalali canonical**; Gregorian = validation only | 2-digit yr → 13xx; 1397 missing 2 months |
| Time | **HH:MM** (no seconds) | strip `1900-01-03` cast; tolerate hour-only |
| Product | **composite** (type × glaze) | legacy codes → review queue |
| Kiln input | **خشت خام / سفال پخته** (≡ خام/شارژی) | canonical mapping |
| Kiln temp | 18 points (grew 1→18 over years) | **>1200 °C = typo** (×10 pattern) → flag |
| Dryer series | per-3h temp **+ humidity**, variable length | row-oriented, dynamic cols |

## 4. Data-model decisions (Appendix C §8–§15)

- **Row-oriented, not fixed-column** for kiln temps (§12), dryer temp/humidity (§13), setting wagons (§14) — because column counts grew/changing.
- **Setting = header + 1–N wagon rows**; wagon is a **cross-chamber/cross-shift continuous entity** → `wagon_master` layer (§14, ADR-0005).
- **Analytic columns EXCLUDED** from migration (`راندمان`, `Rand_*`, `Analyse`, `Tabarestan`, `Note`) — re-designed later from migrated facts (owner decision).
- **Config-driven bounds** (chamber 40 / shift 3 / wagon 80 / temp 1200), never hard-coded SQL CHECK (P1).
- **Migration is idempotent/upsert** → missing 1397 months & typo corrections imported post-build without duplication.

## 5. Migration blueprints (`xls/mapping/`, in git)

`operator_mapping_blueprint.csv`, `product_mapping_blueprint.csv` (Dryer/Kiln A–E+91xxxx **and** Packing 1–28 schemes, incl. 8 conflict resolutions §11.1), `glaze_mapping_blueprint.csv`. Cleaned workbooks in `xls/consolidated/` (git-ignored) + `REVIEW_*.txt` flag logs.

## 6. Open items — all NON-BLOCKING for M0

| # | Item | Status |
|---|---|---|
| 1 | 8 Packing product-code conflicts | ✅ Resolved (code 20 still REVIEW) |
| 2 | 1397 missing 2 months | ➜ Post-build re-import (idempotent) |
| 3 | Wagon/operator typos | ➜ Post-build from ledgers (flagged in `REVIEW_*.txt`) |
| 4 | Kiln temp vocabulary + 1200 °C bound | ✅ Resolved (§12.1) |
| 5 | Setting continuous-wagon + final audit | ✅ Resolved (§14, §15) |

## 7. ADR-0001 compliance check

- ✅ 24 commits, **all documentation/analysis** — no `server.py`/schema/import code added by this work.
- ✅ Pre-existing root `.py` files are the **frozen legacy app** (ADR-0002), not new code.
- ✅ Temp analysis scripts stayed in `%TEMP%` and were cleaned; nothing leaked into the repo.

## 8. Sign-off checklist

- [x] Owner approves operational bounds (chamber 40 / shift 3 / wagon 80 / temp 1200)
- [x] Owner approves Jalali-canonical date rule + 2-digit→13xx normalization
- [x] Owner approves composite-product redefinition + legacy-code review queues
- [x] Owner approves row-oriented models (kiln temps, dryer series, setting wagons + `wagon_master`)
- [x] Owner approves exclusion of analytic columns from raw migration
- [x] Owner accepts 2 post-build items (1397 completion, typo correction) as non-blocking

**APPROVED — 2026-08-17.** Upon sign-off → M1 (plant validation) → M2 (historical data import spec) → platform build.

---
*Generated 2026-08-17. Source of truth: `docs/APPENDIX_C_DATA_VS_SCHEMA.md` §1–§15, `adr/ADR-0001…0006`, `docs/MASTER_SPECIFICATION.md`.*
