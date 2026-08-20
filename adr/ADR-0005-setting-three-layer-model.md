# ADR-0005 — Setting Model: 3-Layer Operation / Shift-Unload / Wagon

- **Status:** Proposed (for owner approval)
- **Date:** 2026-08-15
- **Deciders:** Project owner (confirmed the multi-shift chamber domain rule)
- **Related:** MASTER_SPECIFICATION Part V (Historical Data Architecture), Master Rules §32 (never rewrite source), P1 (config over code); [Appendix C §7](./APPENDIX_C_DATA_VS_SCHEMA.md) (normalized-design assessment); ADR-0004 (PMS donor)

## Context

The owner designed `xls/Setting_Setting.csv` + `xls/Setting_wagons.csv` as a **header/detail pair** for the *Setting* (kiln-charge preparation) process, as a normalized-design prototype. Inspection (Appendix C §7) found `Setting_Setting.ID` is **duplicated 122 times** (e.g. `1404010913` appears 3×).

The owner clarified the domain rule: `ID` encodes `YYYY+MM+DD+chamber_no` — it identifies **one chamber loading**. That loading's **unloading can span two shifts** (afternoon begins, morning completes), producing per-shift finger counts (3 then 4), and the fingers are placed on **multiple wagons** (3). So the repeated ID is **one operation split across multiple unload rows**, not dirty data.

The frozen app modeled this as two flat tables (`setting_processes` + `setting_wagons_data`) with a `CHECK wagon_order BETWEEN 1 AND 4` limit (ADR-0002 §3) — which both invents a 4-wagon cap and cannot express a multi-shift unload. The prototype's duplication exposes the same modeling gap.

## Decision

Model the Setting process as **three explicit layers** instead of one header table + one wagon table:

| Layer | Grain | Key | Source |
|---|---|---|---|
| `setting_operations` | one chamber loading | `operation_id` (= the `ID`, a **batch key**, *not* a surrogate PK) | `Setting_Setting.csv` grouped by `ID` |
| `setting_shift_unloads` | one unloading shift within an operation | composite `(operation_id, shift)` or surrogate + `sub_id` | each `Setting_Setting` row (one per shift) |
| `setting_wagons` | one wagon within a shift-unload | composite `(operation_id, shift, wagon_no)` | `Setting_wagons.csv` (already FK → `ID`) |
| **`wagon_master`** (added 2026-08-17) | **the wagon entity itself**, spanning chambers & shifts | `wagon_no` | all `Setting_wagons.csv` rows + workbook `Data` repeating blocks (Appendix C §14) |

Rules:
1. `Setting_Setting.ID` is treated as a **batch/operation key**, never as a unique surrogate. The true per-row key is **composite** `(ID, shift, wagon_no)` or a generated `sub_id` per `ID`.
2. **No "wagon ≤ 4" limit** — wagon count is observed per operation (data shows it is unbounded), captured as configuration per Master Rules §32/P1.
3. The header/detail FK (`Setting_wagons.SettingID → Setting_Setting.ID`) is **preserved** — verified 0 orphans in the prototype (Appendix C §7.1).
4. Any operation whose unload spans shifts is **kept as multiple rows** under the same `operation_id`; aggregation (`SUM(fingers)` across shifts/wagons) is a query, never a destructive merge.
5. **Wagon is a continuous entity (Appendix C §14):** the same `wagon_no` may appear under **multiple operation_ids** (filled across different dryer chambers, and/or completed across shifts). The migration must **aggregate** a wagon's loads into one `wagon_master` record — never treat each appearance as independent. This is why `wagon_master` is a separate layer above `setting_wagons`.

## Consequences

- **Positive:** faithfully preserves the real operation ("7 fingers across 3 wagons over 2 shifts") with no fidelity loss; removes the frozen app's false 4-wagon constraint; gives the migration a clean, normalized target that matches the owner's intent.
- **Needs companion work (tracked in Appendix C §7.2):** (a) `Setting_Setting.ID` duplicates must be resolvable by the composite key during staging; (b) dimension masters (`Operators`, `Molds`/`ProductName`, `Glaze`) must be completed to cover all fact codes before FK enforcement; (c) an explicit rule resolving the single `productName` column across the two product masters.
- **Supersedes** the frozen 2-table Setting model for the new platform; does not alter the CSV prototype (which remains a valid design demo).

## Validation

Reproducible: the 122 duplicate IDs in `xls/Setting_Setting.csv` and the 0-orphan `Setting_wagons.SettingID` linkage were verified by direct inspection (Appendix C §7). The domain rule was confirmed by the owner, not inferred from data.
