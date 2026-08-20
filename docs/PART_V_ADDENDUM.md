# Part V Addendum — Implementation Reference & Config-Driven Import

> **Appendix to MASTER_SPECIFICATION.md Part V (Historical Data Architecture).**
> Adds the approved design-donor reference (ADR-0004) and makes the Cleaning/Mapping Layer ② explicitly *config-driven* so the import is correct (the project's primary asset is historical data) yet re-definable per plant (Master Rules §27, §32).

## V.5 Implementation reference: PMS repository (per ADR-0004)

The repository **`github.com/motlagh20/PMS`** (React 19 + Vite + Express + Firestore) is the approved **design/UX donor** — harvested, not merged. See [ADR-0004](../adr/ADR-0004-pms-as-design-ux-donor.md).

### V.5.1 What is harvested (reference only)
- **Visual language** — modern RTL React + Tailwind + lucide-react + recharts; supersedes the frozen `web/` vanilla-JS design as the UI reference.
- **Import UX flow** — multi-source intake (local XLSX / CSV / Google Sheets via Drive picker), automatic Persian/English column-keyword mapping, row preview, progress, batched commit. This is the UX template for layer ② below.

### V.5.2 What is explicitly NOT harvested (anti-patterns)
- Firestore/NoSQL persistence — contradicts target stack I.3 (PostgreSQL) and P3.
- Factory-locked model (Set_1400, car1–car4, 18 hardcoded temp columns) — violates §32 and P1.
- **Fake fallback values** in PMS import (e.g. `fingerCount = 450 + i*20`, default temperatures). These fabricate data and violate **P2** (evidence over assumption) and **P5** (audited corrections). The new import MUST replace every fallback with an explicit **validation class** (Valid / Warning / Invalid / Duplicate / Unmapped / Needs Review) and a human review queue. Under no circumstance may an unmapped or empty field be silently filled with a synthetic number.

## V.6 Config-driven Cleaning/Mapping Layer (revision of V.2 ②)

To satisfy "comprehensive yet re-definable per plant," the cleaning/mapping layer is driven by **configuration data, not code**. For each source file/plant, an *import mapping definition* (itself versioned, Master Rules §18) declares:

| Config element | Example (this plant) | Lives in |
|---|---|---|
| Source → canonical field map | `ChamberNo` → Equipment instance (type *dryer chamber*) | config (L3 values) |
| Column-keyword aliases | `['شماره چمبر','chamber','chamber no']` → chamber field | config |
| Jalali format set | `-`, `.`, `/` (padded & unpadded) | config (shared) |
| Validation rules | `chamber_no` observed max = 34 (flag, do not hard-reject) | config |
| Code-mapping tables | mold/glaze/category/operator/supervisor versions | config + staging |
| Unmapped-code routing | `90000001`, `140`, `22` → review queue | config |
| Quality-class thresholds | empty-rate > X% → "not collected" flag | config |

A second plant expresses its own stages, equipment, units, and column vocabularies through the **same** config schema — zero code change (P1, Master Rules §27). The harvested PMS column-mapping *UX* is reused; the mapping *definitions* live in configuration, not in TypeScript string literals.

## V.8 Setting process — 3-layer model (per ADR-0005)

The `Setting` process record is **not** a single row. A chamber *loading* (`operation_id`, encodes date+chamber per owner) may *unload across two shifts* onto *multiple wagons*. Target layers: `setting_operations` (1 loading) → `setting_shift_unloads` (per-shift finger counts) → `setting_wagons` (wagons per shift). The `Setting_Setting.ID` ↔ `Setting_wagons.SettingID` header/detail link is preserved (verified 0 orphans). See [ADR-0005](../adr/ADR-0005-setting-three-layer-model.md) and [Appendix C §7](./APPENDIX_C_DATA_VS_SCHEMA.md) (confirmed domain rule).

## V.7 Reconciliation gates before M2 import execution

Per [Appendix C](./APPENDIX_C_DATA_VS_SCHEMA.md), the following are hard inputs to the M2 mapping spec:
1. Chamber observed max = **34** (not 32) — captured as observed bound, not enforced limit.
2. Shift values include **22** — must be validated/normalized, not silently dropped.
3. Unmapped codes (`140`, `22`, `90000001/2`, `99999999`, `93000000`, `81000001`, `94000002`) → review queue.
4. `Packing.csv` columns `typeOfWorkers`, `workerscount` are **100% empty** → treat as "not collected."
5. Operator codes are **process-partitioned** → resolve FKs per source file.
