# ADR-0001 — Documentation-First Development Order

- **Status:** Accepted
- **Date:** 2026-07-30
- **Deciders:** Project owner
- **Related:** Master Rules §46–§48, §58; [MASTER_SPECIFICATION.md Part I](../docs/MASTER_SPECIFICATION.md)

## Context

The Master Project Rules (§48) mandate a strict development order: charter → glossary → domain model → process model → requirements → architecture → database/ERD → migration design → API → UI/UX → implementation → analytics → AI/ML → testing → deployment. §58 states explicitly: "Do not begin full application generation until the appropriate specifications have been approved."

The existing codebase demonstrates the cost of skipping this order: an Excel-shaped schema, hardcoded factory constants, four divergent schema copies, and unresolved domain ambiguities baked into tables (see [Appendix A](../docs/APPENDIX_A_CURRENT_SYSTEM_INVENTORY.md)).

Key domain questions (Master Rules §54 — meaning of finger/package/column, mold-vs-product ambiguity, traceability links) remain unanswered and would otherwise become silent schema assumptions.

## Decision

Development follows the §48 phase order strictly. **No application code, scaffolding, schema design, or data import is written until the foundational documents (Phases 0–3) are reviewed and the glossary's open questions are resolved with plant staff.**

The foundational set produced under this decision: `docs/00_MASTER_PROJECT_RULES.md`, `docs/MASTER_SPECIFICATION.md` (consolidating the former charter, glossary, domain model, and process specification — ADR-0003), Appendices A–B, the ADRs, and the root README.

## Consequences

- **Positive:** domain ambiguities are surfaced and flagged (`Needs plant validation`) instead of being invented; the future schema is designed from the business domain, not from Excel columns (Master Rules §32); AI assistants have a binding in-repo source of truth (`docs/00_MASTER_PROJECT_RULES.md`).
- **Negative / accepted cost:** no visible feature progress until documentation phases are approved; plant-staff availability becomes the critical path.
- **Follow-up:** next milestones follow the roadmap in `docs/MASTER_SPECIFICATION.md` Part VII (M1 plant validation → M2 historical data spec → …) — only after the specification (M0) is approved.
