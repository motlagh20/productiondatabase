# Migration Mapping Blueprints (`xls/mapping/`)

These files are the **migration mapping blueprints** — the concrete outputs of
[ADR-0006](../adr/ADR-0006-dimension-master-redefinition.md) (dimension-master
redefinition) and [Appendix C §8.7](../docs/APPENDIX_C_DATA_VS_SCHEMA.md)
(master-code evidence from the authoritative workbooks).

They translate the plant's **opaque/opaque legacy codes** (found in
`xls/real data/*.xls*`) into the **redefined, interpretable dimensions** of the
new platform. They are **inputs to the M2 import mapping spec**, not the data
source (the source stays in `xls/real data/`, never rewritten).

## Files

| File | Purpose | Status |
|---|---|---|
| `operator_mapping_blueprint.csv` | legacy operator code → canonical person (5 persons). Resolves the 1–15 code fragmentation. | **Needs owner review** on codes 4 & 5 (shared by two persons) |
| `product_mapping_blueprint.csv` | legacy product code (letter A–E / numeric 91xx–94xx) → composite `type × glaze` canonical product. | Draft; note A==92000001 collisions |
| `glaze_mapping_blueprint.csv` | legacy glaze text → canonical glaze dimension. | Draft; `س` and `10:25` flagged for review |

## Conventions
- `legacy_*` columns = values exactly as found in the source workbooks (read-only extraction).
- `canonical_*` / `new_code` = the proposed redefined identity (config-driven, per P1).
- `needs_review = YES` rows require an **owner decision** before the mapping is finalized (never auto-invented — P2/P5).
- These are **versioned artifacts** (Master Rules §18). When the owner confirms a row, set `needs_review` to empty and lock it.

## How to use
During M2 import, each fact row's legacy code is looked up here; unmapped rows
route to the review queue. The new platform stores the `canonical_*` identity
and keeps `legacy_*` only as a cross-reference.
