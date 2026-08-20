# Appendix A — Current System Inventory (Frozen Reference Implementation)

- **Project:** Manufacturing Analytics & Execution Platform
- **Document status:** Evidence record — findings of the full project review, preserved as permanent input to the new platform's design
- **Related decision:** [ADR-0002 — Freeze legacy app as reference](../adr/ADR-0002-freeze-legacy-app-as-reference.md)
- **Version:** 0.1
- **Date:** 2026-07-30

> Everything below describes the **frozen** legacy application. Nothing here is a defect ticket — per the freeze decision, these defects are deliberately *not* fixed. They are recorded as design lessons (Master Rules §51: the initial factory as a learning lab).

---

## 1. Two parallel backends

The repository contains **two independent backend implementations** of overlapping functionality:

| | Active stack | Legacy stack |
|---|---|---|
| Runtime | Docker: PostgreSQL 16-alpine + PostgREST + Nginx (`docker-compose.yml`) | Flask monolith `server.py` (~137 KB, ~3,200 lines) |
| Database | `appdb` (PostgreSQL), schemas `app` (tables) + `api` (views/RPC) | `kiln_monitoring.db` (SQLite, 200 KB); `production.db` (0 bytes) |
| Schema source | `sql/init/00_schema.sql` (executed by initdb) | root `schema.sql` + `CREATE TABLE` statements embedded in `server.py` |
| API style | PostgREST auto-CRUD on `api.*` views + RPC functions | Flask routes `/api/...` |
| Serving | Nginx serves `web/` and proxies `/api/` → PostgREST with rewrite rules translating legacy Flask paths | Flask serves everything on its own port |

The frontend (`web/app.js`) contains **fallback fetch chains** that try PostgREST-style endpoints first and fall back to Flask-style paths — evidence that the two stacks coexisted during a migration that was never completed.

## 2. Four divergent schema copies

The same domain schema exists in four places, none identical:

1. `sql/init/00_schema.sql` — canonical, actually executed at container init (28 `app.*` tables + `api` views/functions, 1,204 lines).
2. `sql/schema/` — modular per-table/function/view files (`tables/01…24`, `functions/`, plus `sql/views/`), partially out of sync with (1).
3. `xls/schema/` + `xls/init/` + `xls/views/` — an older copy of (2) with mapping seed scripts (`03_map_categories.sql`, `04_map_glazes.sql`, `05_map_molds.sql`).
4. Root `schema.sql` + `server.py` embedded DDL — the SQLite variant with its own table names and shapes.

**Lesson:** the new platform must have exactly one migration-managed schema source (Django migrations).

## 3. Hardcoded factory constants (violations of Master Rules §27)

| Constant | Where hardcoded |
|---|---|
| 32 dryer chambers | `app.dryer_loading CHECK (chamber_no BETWEEN 1 AND 32)`; chamber grids in `web/app.js` |
| 3 shifts | `app.shifts_definition CHECK (shift_code IN (1,2,3))` |
| Max 4 wagons per setting | `app.setting_wagons_data CHECK (wagon_order BETWEEN 1 AND 4)` — not proven by the historical data (Dataset B has unlimited wagon rows per setting) |
| 72-hour drying overdue rule | `api.dryer_chambers_status` view logic |
| 20 kiln temperature points | 20 fixed `temp_*` columns in `app.kiln_push_data` (mirroring the 18 temperature columns of `xls/Kiln.csv`) |
| 21 dryer reading points | fixed columns in `app.dryer_readings` |
| Grade 2 derivation | `app.packaging_records.grade2_count GENERATED ALWAYS AS (total_count - grade1_count - waste_count)` + `CHECK (grade1_count + waste_count <= total_count)` — an invented rule; Master Rules §10 forbids assuming it |
| Product code composition | trigger `compute_product_code_name` composes codes from category+mold+glaze+extra — factory-specific numbering baked into a trigger |

## 4. Security findings

Recorded for lessons only — the frozen app must not be exposed beyond a trusted network.

1. **Password-less login (PostgREST stack).** `api.login(p_username, p_password)` looks up the user **by username only and never checks `p_password`**, then signs and returns a valid JWT (`sql/init/00_schema.sql` ≈ line 734). This is despite a complete, unused `app.user_credentials` table with bcrypt hashes (pgcrypto) and a 5-attempt / 15-minute lockout design, and a fuller login flow in `sql/schema/functions/05_login_flow.sql` that is not the one installed by init.
2. **Mock login (Flask stack).** `server.py`'s login endpoint returns a hardcoded/mock token without real verification.
3. **Committed JWT secrets.** `postgrest.conf` (`"mysecretpasswordforjwt"`), `docker-compose.yml` (`PGRST_JWT_SECRET: "mysecretpasswordforjwt1234567890ab"`), and the `app.config` table (`key='jwt_secret'`) all contain plaintext secrets in version control.
4. **Anonymous role = application role.** PostgREST's `PGRST_DB_ANON_ROLE` is `appuser`, the same role that owns and can write the data — unauthenticated requests get full CRUD on every exposed `api` view.
5. **Committed database credentials** (`appuser/apppass`) in `docker-compose.yml`.

## 5. API surface inventory

### PostgREST (active) — schema `api`
- **Views (read):** `users_overview`, `role_page_permissions`, `shift_options`, `user_options`, `dryer_chambers_status`, `dryer_occupied`, `dryer_history`, `dryer_unload_history`, `dryer_readings_recent`, `kiln_pushing_recent`, `kiln_last_push_info`, `operators_dryer`, `operators_kiln`, `fuel_types`, `role_allowed_pages`, `user_allowed_pages`, plus master-data views (categories, molds, glazes, products…) defined in `00_schema.sql`.
- **RPC functions:** `api.login`, `api.sign` (in-database HMAC JWT via pgcrypto), `api.create_dryer_loading_simple`, dryer unload/readings writers, kiln push writer, setting/wagons writers, packaging writer, admin CRUD helpers (full list in `sql/init/00_schema.sql` and `sql/schema/functions/`).
- **Nginx** (`nginx.conf`) rewrites legacy Flask-style paths (e.g. `/api/dryer/...`) onto these views/RPCs.

### Flask (legacy) — `server.py`
- Persian-labeled endpoints covering login, dryer loading/unloading/readings, kiln pushing, settings/wagons, packaging, admin (users/roles/pages), reports — all against SQLite. Superseded but still runnable via `dev_server.py`.

## 6. Frontend inventory

- `web/index.html` + `web/app.js` (single-page, vanilla JS): Persian/RTL UI with fa/en i18n string tables; pages for dryer dashboard (32-chamber grid), loading/unloading, readings, kiln pushing, setting/wagons (max-4 wagon form), packaging, admin (users, roles, pages, categories, molds, glazes, products).
- `web/design-standards.css` + root `DESIGN_STANDARDS.md`, `DESIGN_README.md`, `DESIGN_SUMMARY.md`, `IMPLEMENTATION_GUIDE.md`, `QUICK_REFERENCE.md`: a documented design system (colors, typography, RTL rules) — reusable **as reference** for the future React UI's Persian/RTL requirements.
- Client-side quirks: fallback fetch chains to both backends; client-side Jalali handling; 24-hour time normalization helpers.

## 7. Root utility scripts (SQLite era, superseded)

`add_products.py`, `check_specific_tables.py`, `cleanup_duplicates.py`, `debug_db.py`, `debug_users.py`, `dev_server.py`, `fix_db.py`, `init_db_script.py`, `inspect_db.py`, `inspect_prof_db.py` — one-off maintenance/debug scripts against the SQLite files. Frozen with the rest.

Binary/archive artifacts also present: `postgrest.zip`, `PROFESSIONAL_SETUP.rar`, `kiln_monitoring.db`, `production.db` (empty), and the source `.docx` of the Master Rules.

## 8. Confirmed data-quality issues in `xls/` (evidence, not defects to fix)

| Issue | Evidence |
|---|---|
| Duplicate business IDs | `Setting_Setting.csv` repeats `ID` values `1404010913`, `1404011009`, `1404011404`, `1404011612` |
| Three Jalali date separators + inconsistent padding | `1404-01-05` (Dryer), `1404.01.01` (Kiln), `1404/1/7` (Setting_Setting), `1404/01/04` (Packing) |
| Missing values | e.g. `Packing.csv` first data row has empty `typeOfWorkers`, `workerscount`; Dryer rows with missing unload data |
| Export artifacts | `Glaze.csv`/`Molds.csv` contain a pandas `Unnamed: 2` column; `Dryer.csv` header `LoadOperatorCode_FK.1` actually means *unload* operator |
| Times as text, inconsistent padding | `8:20:00` vs `06:25:00`; kiln `PushingTime_min` holds `1:20:00` (a duration in a time-like format) |
| Code ambiguity | `productName` columns hold mold-family codes (`91000000`) and, in `Kiln.csv`, also `90000001` — a value absent from every reference CSV |
| Split/partial wagon fills | same wagon repeated within a `SettingID` with split package counts (4 + 60 = 64) |

These are the concrete inputs for the future migration/staging design (Master Rules §19, §33–35). Full per-file catalog: [Appendix B](./APPENDIX_B_DATA_ASSETS.md).

## 9. Gap analysis vs Master Rules (summary)

| Master Rules requirement | Frozen app status |
|---|---|
| §27 no hardcoded factory constants | Violated throughout (§3 above) |
| §32 never copy Excel structure | Violated — `app.*` tables mirror CSV columns nearly 1:1 |
| §20 canonical temporal representation | Violated — Jalali dates/times stored as TEXT |
| §17–19 historical import subsystem with lineage | Absent — only 3 master-data mapping seeds in `xls/init/`; no importer for the transactional CSVs |
| §21–25 analytics, baselines, statistics | Absent — zero analytic capability |
| §29 multi-company/multi-factory | Absent — single implicit factory |
| §42 security/roles | Designed but not enforced (password-less login) |
| §45 target stack | Different stack (PostgREST + vanilla JS vs Django + React) |

**Conclusion recorded:** the current app is valuable as *domain evidence* and a working UI prototype of the plant's recording practices, and unsuitable as a foundation for the platform — hence the freeze (ADR-0002).
