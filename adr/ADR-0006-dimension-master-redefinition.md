# ADR-0006 — Dimension Master Redefinition (Composite Product + Cleaned Operators)

- **Status:** Proposed (for owner approval)
- **Date:** 2026-08-17
- **Deciders:** Project owner
- **Related:** MASTER_SPECIFICATION Part V (Historical Data Architecture), Master Rules §17 (source data), §32 (never rewrite source in place), P1 (config over code); [Appendix C §7](./APPENDIX_C_DATA_VS_SCHEMA.md) (normalized-design assessment); ADR-0004 (PMS donor), ADR-0005 (Setting 3-layer model)

## Context

The plant's native Excel workbooks (`xls/real data/`, the authoritative source) assign **opaque codes** to products and operators that are not self-describing and are internally inconsistent:

1. **Product codes are atomic and uninterpretable.** A fact row carries e.g. `productName = 90000001` — a bare code with no embedded meaning. Per the owner, the *real* product identity is **composite**: it is derived from **(mold type) + (glaze) + (specific attributes)**. `Molds.csv` is one input to this derivation, not the whole product. So the legacy code is a placeholder, not a definition.
2. **Glaze + product form the final name.** The final product name is typically a combination of `mold + glaze + specific attribute` — i.e. glaze and product are *independent dimensions* that together compose the finished product, not an isolated product code.
3. **Operator codes are inconsistent.** Due to file fragmentation and spelling errors across the workbooks, the same operator appears under different codes (e.g. orphan `140`, blank codes), and operator codes are not uniform across process files ([Appendix C §5](./APPENDIX_C_DATA_VS_SCHEMA.md)). The `Operators.csv` master (codes 1,2,4–11) does not cover all codes actually used.

The frozen reference app simply copied these opaque codes as-is (ADR-0002). The new platform must instead **redefine the dimension masters** during migration, with a controlled old→new code-mapping layer so historical rows stay traceable.

## Decision

### A. Product = composite entity, not an opaque code
- Model **three independent dimensions**: `molds` (mold type), `glazes` (glaze), and `product_attributes` (specific attributes), plus a `products` (finished product) table whose identity is **derived from the combination** `mold + glaze + attributes` (a deterministic naming/code rule, configured per plant per P1).
- Legacy atomic product codes (`90000001`, `90000002`, `99999999`, `93000000`, …) are **not** carried forward as product identity. They are retained only as a **legacy cross-reference** (`legacy_code`) on the new product, used solely for the migration mapping.
- The composite naming rule is **configuration, not code** (P1) — another plant defines its own composition rule.

### B. Glaze and product are independent composing dimensions
- `glazes` is a standalone dimension, referenced by the product-composition rule, not merged into a product code. A product's final name = function(mold, glaze, attributes).

### C. Operators: consolidate names first, then re-code
- Migration step order: (1) **collect & consolidate all operator names** across every workbook (dedupe + spelling normalization — e.g. resolve `140`/blank to the correct person); (2) assign **one canonical code per consolidated operator**; (3) build the `old_operator_code → new_operator_code` mapping.
- The `Operators.csv` master must be regenerated from the **consolidated, corrected** name set, not from the partial current file.

### D. Mandatory old→new mapping layer
- For **every** dimension (product, glaze, mold, operator, supervisor), the migration maintains an explicit `legacy_code → new_code` mapping table (versioned, Master Rules §18). No legacy code is silently dropped or guessed; unmappable codes route to a **review queue** (P2/P5: evidence over assumption; never invent).

### E. Source integrity
- The native workbooks are **never rewritten in place** (Master Rules §44/§32). If the owner chooses to *also* produce cleaned Excel files, those are **new artifacts**, not modifications of `xls/real data/`. The mapping tables are the authoritative bridge.

## Consequences

- **Positive:** the new platform gains **interpretable, re-definable** dimension masters (satisfying "comprehensive yet precise for this plant"); composite products are queryable by mold/glaze/attribute; operator analytics become consistent; historical rows remain traceable via the mapping layer.
- **Cost (accepted):** migration is no longer a straight copy — it requires a consolidation/cleaning pass and a mapping layer. This is the correct investment given the source's opacity and inconsistency.
- **Dependency:** the mapping tables must be built from the **authoritative workbooks** (`xls/real data/`), not from the `xls/*.csv` design prototype, because the prototype is a sample and may omit codes.
- **Out of scope here:** the exact composite naming formula — to be specified in the M2 mapping spec (config-driven).

## Validation

Grounded in owner's domain explanation (not inferred from data) and corroborated by the verified code gaps in [Appendix C §3/§5/§7.2](./APPENDIX_C_DATA_VS_SCHEMA.md) (unmapped product codes `90000001/2/99999999/93000000`, glaze `94000002/81000001`, operator `140`/blank, partitioned operator codes).
