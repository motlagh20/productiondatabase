-- =============================================================
-- Production Database – Complete Schema (Docker init)
-- Single source of truth for PostgreSQL 16
-- =============================================================

-- 0. Schemas & Extensions
CREATE SCHEMA IF NOT EXISTS app;
CREATE SCHEMA IF NOT EXISTS api;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
ALTER DATABASE appdb SET search_path TO app, public;

-- JWT secret stored as a table for easy access from functions
CREATE TABLE app.config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
INSERT INTO app.config(key, value) VALUES ('jwt_secret', 'mysecretpasswordforjwt1234567890ab')
ON CONFLICT (key) DO NOTHING;

-- =============================================================
-- 1. REFERENCE TABLES
-- =============================================================

CREATE TABLE app.firing_types (
  firing_type_id BIGSERIAL PRIMARY KEY,
  firing_name TEXT NOT NULL UNIQUE,
  description TEXT
);
CREATE INDEX firing_types_name_idx ON app.firing_types (firing_name);

CREATE TABLE app.shifts_definition (
  shift_id BIGSERIAL PRIMARY KEY,
  shift_code SMALLINT NOT NULL UNIQUE CHECK (shift_code IN (1,2,3)),
  shift_name TEXT NOT NULL,
  start_time TIME,
  end_time TIME,
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX shifts_definition_is_active_idx ON app.shifts_definition (is_active);

CREATE TABLE app.fuel_types (
  fuel_type_id BIGSERIAL PRIMARY KEY,
  fuel_name TEXT NOT NULL UNIQUE,
  is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX fuel_types_active_idx ON app.fuel_types (is_active);

-- =============================================================
-- 2. PRODUCT CATALOG
-- =============================================================

CREATE TABLE app.categories (
  category_id BIGSERIAL PRIMARY KEY,
  category_code TEXT NOT NULL UNIQUE,
  category_name TEXT NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX categories_code_idx ON app.categories (category_code);

CREATE TABLE app.molds (
  mold_id BIGSERIAL PRIMARY KEY,
  mold_code TEXT NOT NULL UNIQUE,
  mold_name TEXT NOT NULL,
  category_id BIGINT REFERENCES app.categories(category_id) ON UPDATE CASCADE ON DELETE SET NULL,
  width NUMERIC(10,2),
  length NUMERIC(10,2),
  height NUMERIC(10,2),
  pieces_per_press INTEGER DEFAULT 1,
  is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX molds_code_idx ON app.molds (mold_code);
CREATE INDEX molds_category_idx ON app.molds (category_id);

CREATE TABLE app.glazes (
  glaze_id BIGSERIAL PRIMARY KEY,
  glaze_code TEXT NOT NULL UNIQUE,
  glaze_name TEXT NOT NULL,
  is_self_colored BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX glazes_code_idx ON app.glazes (glaze_code);

CREATE TABLE app.products (
  product_id BIGSERIAL PRIMARY KEY,
  product_code TEXT UNIQUE NOT NULL,
  product_name TEXT NOT NULL,
  category_id BIGINT NOT NULL REFERENCES app.categories(category_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  mold_id BIGINT NOT NULL REFERENCES app.molds(mold_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  glaze_id BIGINT NOT NULL REFERENCES app.glazes(glaze_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  extra_code TEXT DEFAULT '',
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (category_id, mold_id, glaze_id, extra_code)
);
CREATE INDEX products_category_idx ON app.products (category_id);
CREATE INDEX products_mold_idx ON app.products (mold_id);
CREATE INDEX products_glaze_idx ON app.products (glaze_id);

CREATE TABLE app.product_category_assignments (
  product_id BIGINT NOT NULL REFERENCES app.products(product_id) ON DELETE CASCADE,
  category_id BIGINT NOT NULL REFERENCES app.categories(category_id) ON DELETE CASCADE,
  PRIMARY KEY (product_id, category_id)
);

CREATE TABLE app.extra_code_map (
  extra_code TEXT PRIMARY KEY,
  extra_name TEXT NOT NULL
);
CREATE INDEX extra_code_map_name_idx ON app.extra_code_map (extra_name);

-- =============================================================
-- 3. AUTH & RBAC
-- =============================================================

CREATE TABLE app.roles (
  role_id BIGSERIAL PRIMARY KEY,
  role_name TEXT NOT NULL UNIQUE,
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX roles_is_active_idx ON app.roles (is_active);

CREATE TABLE app.users (
  user_id BIGSERIAL PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role_id BIGINT NOT NULL REFERENCES app.roles(role_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  is_active BOOLEAN DEFAULT TRUE,
  last_login TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX users_role_id_idx ON app.users (role_id);
CREATE INDEX users_is_active_idx ON app.users (is_active);

CREATE TABLE app.user_credentials (
  credential_id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL UNIQUE REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
  password_hash TEXT NOT NULL,
  password_algorithm TEXT NOT NULL DEFAULT 'bcrypt',
  password_last_changed_at TIMESTAMPTZ DEFAULT NOW(),
  failed_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
  locked_until TIMESTAMPTZ,
  must_change_password BOOLEAN DEFAULT FALSE
);
CREATE INDEX user_credentials_user_id_idx ON app.user_credentials (user_id);
CREATE INDEX user_credentials_locked_until_idx ON app.user_credentials (locked_until);

CREATE TABLE app.login_sessions (
  session_id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
  session_token_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  ip_address TEXT,
  user_agent TEXT
);
CREATE INDEX login_sessions_user_id_idx ON app.login_sessions (user_id);
CREATE INDEX login_sessions_expires_at_idx ON app.login_sessions (expires_at);

CREATE TABLE app.pages (
  page_id BIGSERIAL PRIMARY KEY,
  page_key TEXT NOT NULL UNIQUE,
  page_name TEXT NOT NULL,
  page_title TEXT NOT NULL,
  description TEXT,
  is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX pages_is_active_idx ON app.pages (is_active);

CREATE TABLE app.role_permissions (
  permission_id BIGSERIAL PRIMARY KEY,
  role_id BIGINT NOT NULL REFERENCES app.roles(role_id) ON UPDATE CASCADE ON DELETE CASCADE,
  page_id BIGINT NOT NULL REFERENCES app.pages(page_id) ON UPDATE CASCADE ON DELETE CASCADE,
  can_view BOOLEAN DEFAULT FALSE,
  can_add BOOLEAN DEFAULT FALSE,
  can_edit BOOLEAN DEFAULT FALSE,
  can_delete BOOLEAN DEFAULT FALSE,
  UNIQUE (role_id, page_id)
);
CREATE INDEX role_permissions_role_id_idx ON app.role_permissions (role_id);
CREATE INDEX role_permissions_page_id_idx ON app.role_permissions (page_id);

-- Simple role-page access (used by api views)
CREATE TABLE app.role_page_access (
  role_id BIGINT NOT NULL REFERENCES app.roles(role_id) ON DELETE CASCADE,
  page_id BIGINT NOT NULL REFERENCES app.pages(page_id) ON DELETE CASCADE,
  PRIMARY KEY (role_id, page_id)
);

-- =============================================================
-- 4. DRYER OPERATIONS
-- =============================================================

CREATE TABLE app.dryer_loading (
  load_id BIGSERIAL PRIMARY KEY,
  chamber_no INTEGER NOT NULL CHECK (chamber_no BETWEEN 1 AND 32),
  load_date_jalali TEXT NOT NULL,
  shift_id BIGINT NOT NULL REFERENCES app.shifts_definition(shift_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  supervisor_id BIGINT NOT NULL REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  load_time TEXT NOT NULL,
  load_operator_id BIGINT NOT NULL REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  product_id BIGINT NOT NULL REFERENCES app.products(product_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  finger_count INTEGER NOT NULL CHECK (finger_count >= 0),
  load_timestamp TIMESTAMPTZ DEFAULT NOW(),
  is_unloaded BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (chamber_no, load_date_jalali, load_time)
);
CREATE INDEX dryer_loading_chamber_no_idx ON app.dryer_loading (chamber_no);
CREATE INDEX dryer_loading_timestamp_idx ON app.dryer_loading (load_timestamp);
CREATE INDEX dryer_loading_operator_idx ON app.dryer_loading (load_operator_id);
CREATE INDEX dryer_loading_is_unloaded_idx ON app.dryer_loading (is_unloaded);

CREATE TABLE app.dryer_unloading (
  unload_id BIGSERIAL PRIMARY KEY,
  load_id BIGINT NOT NULL UNIQUE REFERENCES app.dryer_loading(load_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  unload_date_jalali TEXT NOT NULL,
  shift_id BIGINT REFERENCES app.shifts_definition(shift_id) ON UPDATE CASCADE ON DELETE SET NULL,
  supervisor_id BIGINT REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE SET NULL,
  unload_time TEXT NOT NULL,
  unload_operator_id BIGINT NOT NULL REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  unloaded_finger_count INTEGER NOT NULL CHECK (unloaded_finger_count >= 0),
  dryer_waste INTEGER DEFAULT 0 CHECK (dryer_waste >= 0),
  drying_hours NUMERIC(10,2),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX dryer_unloading_load_id_idx ON app.dryer_unloading (load_id);

-- Simple dryer readings (by chamber, not linked to load)
CREATE TABLE app.simple_dryer_readings (
  reading_id BIGSERIAL PRIMARY KEY,
  chamber_no INTEGER NOT NULL CHECK (chamber_no BETWEEN 1 AND 32),
  record_date_jalali TEXT NOT NULL,
  record_time TEXT NOT NULL,
  temperature NUMERIC(10,2),
  humidity NUMERIC(10,2),
  recorded_by BIGINT REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE SET NULL,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX simple_dryer_readings_chamber_idx ON app.simple_dryer_readings (chamber_no);

-- Detailed dryer readings (linked to load, up to 21 points)
CREATE TABLE app.dryer_readings (
  reading_id BIGSERIAL PRIMARY KEY,
  load_id BIGINT NOT NULL REFERENCES app.dryer_loading(load_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  point_number INTEGER NOT NULL CHECK (point_number BETWEEN 1 AND 21),
  record_date_jalali TEXT,
  record_time TEXT NOT NULL,
  temperature NUMERIC(10,2),
  humidity NUMERIC(10,2),
  recorded_by BIGINT REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE SET NULL,
  notes TEXT,
  UNIQUE (load_id, point_number)
);

-- =============================================================
-- 5. SETTING (PRODUCTION LINE)
-- =============================================================

CREATE TABLE app.setting_processes (
  setting_id BIGSERIAL PRIMARY KEY,
  setting_date_jalali TEXT NOT NULL,
  shift_id BIGINT REFERENCES app.shifts_definition(shift_id) ON UPDATE CASCADE ON DELETE SET NULL,
  supervisor_id BIGINT REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE SET NULL,
  operator_id BIGINT REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE SET NULL,
  personnel_count INTEGER DEFAULT 0,
  chamber_no INTEGER NOT NULL,
  category_id BIGINT REFERENCES app.categories(category_id) ON UPDATE CASCADE ON DELETE SET NULL,
  fingers_count INTEGER DEFAULT 0,
  columns_count INTEGER DEFAULT 0,
  dryer_waste INTEGER DEFAULT 0,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX setting_processes_date_idx ON app.setting_processes (setting_date_jalali);
CREATE INDEX setting_processes_chamber_idx ON app.setting_processes (chamber_no);

CREATE TABLE app.setting_wagons_data (
  wagon_data_id BIGSERIAL PRIMARY KEY,
  setting_id BIGINT NOT NULL REFERENCES app.setting_processes(setting_id) ON UPDATE CASCADE ON DELETE CASCADE,
  wagon_order INTEGER NOT NULL CHECK (wagon_order BETWEEN 1 AND 4),
  wagon_no INTEGER NOT NULL,
  product_id BIGINT REFERENCES app.products(product_id) ON UPDATE CASCADE ON DELETE SET NULL,
  glaze_override TEXT,
  start_time TEXT,
  end_time TEXT,
  packages INTEGER DEFAULT 0 CHECK (packages >= 0),
  notes TEXT,
  UNIQUE (setting_id, wagon_order)
);
CREATE INDEX setting_wagons_data_setting_idx ON app.setting_wagons_data (setting_id);

-- =============================================================
-- 6. KILN
-- =============================================================

CREATE TABLE app.kiln_push_data (
  push_id BIGSERIAL PRIMARY KEY,
  push_date_jalali TEXT NOT NULL,
  push_time TEXT,
  shift_id BIGINT REFERENCES app.shifts_definition(shift_id) ON UPDATE CASCADE ON DELETE SET NULL,
  operator_id BIGINT REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE SET NULL,
  product_id BIGINT REFERENCES app.products(product_id) ON UPDATE CASCADE ON DELETE SET NULL,
  incoming_car_id INTEGER NOT NULL,
  fuel_type_id BIGINT REFERENCES app.fuel_types(fuel_type_id) ON UPDATE CASCADE ON DELETE SET NULL,
  pushing_time_min NUMERIC(10,2),
  temp_exhaust NUMERIC(10,2),
  temp_preheat01 NUMERIC(10,2),
  temp_preheat02 NUMERIC(10,2),
  temp_thermostat NUMERIC(10,2),
  temp_zone00 NUMERIC(10,2),
  temp_zone01 NUMERIC(10,2),
  temp_zone02 NUMERIC(10,2),
  temp_zone03 NUMERIC(10,2),
  temp_zone04 NUMERIC(10,2),
  temp_zone05 NUMERIC(10,2),
  temp_zone06 NUMERIC(10,2),
  temp_zone07 NUMERIC(10,2),
  temp_rapid01 NUMERIC(10,2),
  temp_rapid02 NUMERIC(10,2),
  temp_bottom_a NUMERIC(10,2),
  temp_bottom01 NUMERIC(10,2),
  temp_bottom_b NUMERIC(10,2),
  temp_bottom02 NUMERIC(10,2),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (push_date_jalali, incoming_car_id)
);
CREATE INDEX kiln_push_date_idx ON app.kiln_push_data (push_date_jalali);
CREATE INDEX kiln_push_operator_idx ON app.kiln_push_data (operator_id);

-- =============================================================
-- 7. WAREHOUSE & PACKAGING
-- =============================================================

CREATE TABLE app.production_batches (
  batch_id BIGSERIAL PRIMARY KEY,
  batch_number TEXT UNIQUE NOT NULL,
  product_id BIGINT NOT NULL REFERENCES app.products(product_id) ON UPDATE CASCADE ON DELETE RESTRICT,
  input_type TEXT NOT NULL CHECK (input_type IN ('RawTile', 'FiredTile')),
  input_batch_id BIGINT REFERENCES app.production_batches(batch_id),
  input_stock_id BIGINT,
  setting_date DATE NOT NULL,
  shift SMALLINT NOT NULL CHECK (shift IN (1,2,3)),
  setting_operator TEXT NOT NULL,
  quantity_input INTEGER NOT NULL CHECK (quantity_input >= 0),
  quantity_output INTEGER NOT NULL CHECK (quantity_output >= 0),
  waste_count INTEGER DEFAULT 0 CHECK (waste_count >= 0),
  wagon_numbers TEXT,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE app.warehouse_stock (
  stock_id BIGSERIAL PRIMARY KEY,
  batch_id BIGINT NOT NULL REFERENCES app.production_batches(batch_id),
  product_id BIGINT NOT NULL REFERENCES app.products(product_id),
  quantity INTEGER NOT NULL CHECK (quantity >= 0),
  entry_date DATE NOT NULL,
  location TEXT,
  is_available BOOLEAN DEFAULT TRUE,
  notes TEXT,
  UNIQUE (batch_id)
);

CREATE TABLE app.warehouse_transactions (
  transaction_id BIGSERIAL PRIMARY KEY,
  stock_id BIGINT NOT NULL REFERENCES app.warehouse_stock(stock_id),
  transaction_type TEXT NOT NULL CHECK (transaction_type IN ('Entry', 'Sale', 'ReturnToProduction')),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
  transaction_time TIME NOT NULL DEFAULT CURRENT_TIME,
  operator TEXT NOT NULL,
  related_batch_id BIGINT REFERENCES app.production_batches(batch_id),
  customer_name TEXT,
  invoice_number TEXT,
  notes TEXT
);

CREATE TABLE app.packaging_records (
  package_id BIGSERIAL PRIMARY KEY,
  package_date_jalali TEXT NOT NULL,
  shift_id BIGINT REFERENCES app.shifts_definition(shift_id),
  operator_id BIGINT REFERENCES app.users(user_id),
  type_of_workers TEXT,
  workers_count INTEGER CHECK (workers_count >= 0),
  product_id BIGINT NOT NULL REFERENCES app.products(product_id),
  wagon_no INTEGER,
  total_count INTEGER NOT NULL CHECK (total_count >= 0),
  grade1_count INTEGER NOT NULL CHECK (grade1_count >= 0),
  waste_count INTEGER DEFAULT 0 CHECK (waste_count >= 0),
  grade2_count INTEGER GENERATED ALWAYS AS (total_count - grade1_count - waste_count) STORED,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT,
  CHECK (grade1_count + waste_count <= total_count)
);

-- =============================================================
-- 8. APP-LEVEL FUNCTIONS & TRIGGERS
-- =============================================================

-- Auto-generate product code/name from category+mold+glaze+extra
CREATE OR REPLACE FUNCTION app.compute_product_code_name() RETURNS trigger AS $$
DECLARE
  v_cc TEXT; v_cn TEXT; v_mc TEXT; v_mn TEXT; v_gc TEXT; v_gn TEXT;
  v_en TEXT; v_ep TEXT;
BEGIN
  SELECT category_code, category_name INTO v_cc, v_cn FROM app.categories WHERE category_id = NEW.category_id;
  SELECT mold_code, mold_name INTO v_mc, v_mn FROM app.molds WHERE mold_id = NEW.mold_id;
  SELECT glaze_code, glaze_name INTO v_gc, v_gn FROM app.glazes WHERE glaze_id = NEW.glaze_id;

  SELECT extra_name INTO v_en FROM app.extra_code_map
  WHERE extra_code = NULLIF(TRIM(NEW.extra_code), '');

  v_ep := COALESCE(NULLIF(TRIM(NEW.extra_code), ''), '');

  IF NEW.product_code IS NULL OR NEW.product_code LIKE 'GEN%' OR NEW.product_code LIKE 'TMP%' THEN
    NEW.product_code := COALESCE(v_cc,'') || '-' || COALESCE(v_mc,'') || '-' || COALESCE(v_gc,'') || v_ep;
  END IF;

  IF v_en IS NOT NULL THEN
    NEW.product_name := TRIM(COALESCE(v_cn,'') || ' ' || COALESCE(v_mn,'') || ' ' || COALESCE(v_gn,'') || ' ' || v_en);
  ELSE
    IF v_ep <> '' THEN
      NEW.product_name := TRIM(COALESCE(v_cn,'') || ' ' || COALESCE(v_mn,'') || ' ' || COALESCE(v_gn,'') || ' ' || v_ep);
    ELSE
      NEW.product_name := TRIM(COALESCE(v_cn,'') || ' ' || COALESCE(v_mn,'') || ' ' || COALESCE(v_gn,''));
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_products_compute_code_name ON app.products;
CREATE TRIGGER trg_products_compute_code_name
BEFORE INSERT OR UPDATE OF category_id, mold_id, glaze_id, extra_code
ON app.products FOR EACH ROW
EXECUTE FUNCTION app.compute_product_code_name();

-- Mark dryer_loading as unloaded when unloading is inserted
CREATE OR REPLACE FUNCTION app.mark_loading_unloaded() RETURNS trigger AS $$
BEGIN
  UPDATE app.dryer_loading SET is_unloaded = TRUE WHERE load_id = NEW.load_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_unloading_sets_loading_unloaded ON app.dryer_unloading;
CREATE TRIGGER trg_unloading_sets_loading_unloaded
AFTER INSERT ON app.dryer_unloading FOR EACH ROW
EXECUTE FUNCTION app.mark_loading_unloaded();

-- Auth helper functions
CREATE OR REPLACE FUNCTION app.mark_failed_login(p_username TEXT) RETURNS VOID AS $$
DECLARE v_uid BIGINT; v_att INTEGER;
BEGIN
  SELECT user_id INTO v_uid FROM app.users WHERE username = p_username AND is_active = TRUE;
  IF v_uid IS NULL THEN RETURN; END IF;
  UPDATE app.user_credentials SET failed_attempts = failed_attempts + 1
  WHERE user_id = v_uid RETURNING failed_attempts INTO v_att;
  IF v_att >= 5 THEN
    UPDATE app.user_credentials SET locked_until = NOW() + INTERVAL '15 minutes' WHERE user_id = v_uid;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION app.mark_successful_login(p_username TEXT) RETURNS VOID AS $$
DECLARE v_uid BIGINT;
BEGIN
  SELECT user_id INTO v_uid FROM app.users WHERE username = p_username AND is_active = TRUE;
  IF v_uid IS NULL THEN RETURN; END IF;
  UPDATE app.user_credentials SET failed_attempts = 0, locked_until = NULL WHERE user_id = v_uid;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION app.create_login_session(p_user_id BIGINT, p_token_hash TEXT, p_ttl_minutes INTEGER) RETURNS BIGINT AS $$
DECLARE v_sid BIGINT;
BEGIN
  INSERT INTO app.login_sessions(user_id, session_token_hash, expires_at)
  VALUES (p_user_id, p_token_hash, NOW() + (p_ttl_minutes || ' minutes')::interval)
  RETURNING session_id INTO v_sid;
  RETURN v_sid;
END;
$$ LANGUAGE plpgsql;

-- Permission check
CREATE OR REPLACE FUNCTION app.has_permission(p_username TEXT, p_page_name TEXT, p_action TEXT) RETURNS BOOLEAN AS $$
DECLARE v_uid BIGINT; v_rid BIGINT; v_pid BIGINT; v_allowed BOOLEAN := FALSE;
BEGIN
  SELECT u.user_id, u.role_id INTO v_uid, v_rid FROM app.users u WHERE u.username = p_username AND u.is_active = TRUE;
  IF v_uid IS NULL THEN RETURN FALSE; END IF;
  SELECT page_id INTO v_pid FROM app.pages WHERE page_name = p_page_name AND is_active = TRUE;
  IF v_pid IS NULL THEN RETURN FALSE; END IF;
  IF p_action = 'view' THEN SELECT can_view INTO v_allowed FROM app.role_permissions WHERE role_id=v_rid AND page_id=v_pid;
  ELSIF p_action = 'add' THEN SELECT can_add INTO v_allowed FROM app.role_permissions WHERE role_id=v_rid AND page_id=v_pid;
  ELSIF p_action = 'edit' THEN SELECT can_edit INTO v_allowed FROM app.role_permissions WHERE role_id=v_rid AND page_id=v_pid;
  ELSIF p_action = 'delete' THEN SELECT can_delete INTO v_allowed FROM app.role_permissions WHERE role_id=v_rid AND page_id=v_pid;
  END IF;
  RETURN COALESCE(v_allowed, FALSE);
END;
$$ LANGUAGE plpgsql;

-- Helper: find or create product by category+mold+glaze+extra
CREATE OR REPLACE FUNCTION app.get_or_create_product(_cat BIGINT, _mold BIGINT, _glaze BIGINT, _extra TEXT) RETURNS BIGINT AS $$
DECLARE _pid BIGINT;
BEGIN
  SELECT product_id INTO _pid FROM app.products
  WHERE category_id=_cat AND mold_id=_mold AND glaze_id=_glaze AND extra_code=COALESCE(_extra,'')
  LIMIT 1;
  IF _pid IS NULL THEN
    INSERT INTO app.products (product_code, product_name, category_id, mold_id, glaze_id, extra_code, is_active)
    VALUES ('TMP-'||_cat||'-'||_mold||'-'||_glaze, 'محصول موقت', _cat, _mold, _glaze, COALESCE(_extra,''), TRUE)
    RETURNING product_id INTO _pid;
  END IF;
  RETURN _pid;
END;
$$ LANGUAGE plpgsql;

-- app.product_details: joined view for use in RPC functions
CREATE OR REPLACE VIEW app.product_details AS
SELECT p.product_id AS "ProductID",
  p.product_code, p.product_name,
  c.category_name, m.mold_name, g.glaze_name,
  p.category_id, p.mold_id, p.glaze_id, p.extra_code,
  p.is_active
FROM app.products p
LEFT JOIN app.categories c ON p.category_id = c.category_id
LEFT JOIN app.molds m ON p.mold_id = m.mold_id
LEFT JOIN app.glazes g ON p.glaze_id = g.glaze_id;

-- =============================================================
-- 9. API VIEWS (CamelCase for PostgREST)
-- =============================================================

CREATE OR REPLACE VIEW api.categories AS
SELECT category_id AS "CategoryID", category_code AS "CategoryCode",
       category_name AS "CategoryName", description AS "Description", is_active AS "IsActive"
FROM app.categories;

CREATE OR REPLACE VIEW api.molds AS
SELECT mold_id AS "MoldID", mold_code AS "MoldCode", mold_name AS "MoldName",
       category_id AS "CategoryID", width AS "Width", length AS "Length",
       height AS "Height", pieces_per_press AS "PiecesPerPress", is_active AS "IsActive"
FROM app.molds;

CREATE OR REPLACE VIEW api.glazes AS
SELECT glaze_id AS "GlazeID", glaze_code AS "GlazeCode", glaze_name AS "GlazeName",
       is_self_colored AS "IsSelfColored", is_active AS "IsActive"
FROM app.glazes;

CREATE OR REPLACE VIEW api.products AS
SELECT product_id AS "ProductID", product_code AS "ProductCode", product_name AS "ProductName",
       category_id AS "CategoryID", mold_id AS "MoldID", glaze_id AS "GlazeID",
       extra_code AS "ExtraCode", is_active AS "IsActive", created_at AS "CreatedAt"
FROM app.products;

CREATE OR REPLACE VIEW api.product_details AS
SELECT p.product_id AS "ProductID", p.product_code AS "ProductCode", p.product_name AS "ProductName",
       c.category_name AS "CategoryName", m.mold_name AS "MoldName",
       g.glaze_name AS "GlazeName", p.extra_code AS "ExtraCode", p.is_active AS "IsActive"
FROM app.products p
JOIN app.categories c ON p.category_id = c.category_id
JOIN app.molds m ON p.mold_id = m.mold_id
JOIN app.glazes g ON p.glaze_id = g.glaze_id;

CREATE OR REPLACE VIEW api.users AS
SELECT u.user_id AS "UserID", u.username AS "Username", u.full_name AS "FullName",
       u.is_active AS "IsActive", r.role_name AS "Role"
FROM app.users u LEFT JOIN app.roles r ON u.role_id = r.role_id;

CREATE OR REPLACE VIEW api.shifts AS
SELECT shift_id AS "ShiftID", shift_code AS "ShiftCode", shift_name AS "ShiftName",
       start_time AS "StartTime", end_time AS "EndTime", is_active AS "IsActive"
FROM app.shifts_definition;

CREATE OR REPLACE VIEW api.fuel_types AS
SELECT fuel_type_id AS "FuelTypeID", fuel_name AS "FuelName", is_active AS "IsActive"
FROM app.fuel_types;

CREATE OR REPLACE VIEW api.fuel_types_view AS SELECT * FROM api.fuel_types;

CREATE OR REPLACE VIEW api.roles AS
SELECT role_id AS "RoleID", role_name AS "RoleName", is_active AS "IsActive"
FROM app.roles;

CREATE OR REPLACE VIEW api.pages AS
SELECT page_id AS "PageID", page_key AS "PageKey", page_title AS "PageTitle", is_active AS "IsActive"
FROM app.pages;

CREATE OR REPLACE VIEW api.operators_dryer AS
SELECT u.user_id AS "OperatorCode", COALESCE(u.full_name, u.username) AS "OperatorName"
FROM app.users u JOIN app.roles r ON u.role_id = r.role_id
WHERE r.role_name IN ('Dryer','Operator') AND u.is_active = TRUE;

CREATE OR REPLACE VIEW api.operators_kiln AS
SELECT u.user_id AS "OperatorCode", COALESCE(u.full_name, u.username) AS "OperatorName"
FROM app.users u JOIN app.roles r ON u.role_id = r.role_id
WHERE r.role_name IN ('Kiln','Operator') AND u.is_active = TRUE;

CREATE OR REPLACE VIEW api.operators AS
SELECT u.user_id AS "OperatorCode", COALESCE(u.full_name, u.username) AS "OperatorName",
       r.role_name AS "RoleName"
FROM app.users u JOIN app.roles r ON u.role_id = r.role_id;

CREATE OR REPLACE VIEW api.shift_options AS
SELECT shift_id, shift_name FROM app.shifts_definition WHERE is_active = TRUE;

-- Dryer chamber status (32 chambers)
CREATE OR REPLACE VIEW api.dryer_chambers_status AS
SELECT s.i AS "ChamberNo",
  (dl.load_id IS NOT NULL) AS occupied,
  dl.load_date_jalali AS "LoadDateJalali", dl.load_time AS "LoadTime",
  COALESCE(u.full_name, u.username) AS "Operator",
  p.product_name AS "ProductName", c.category_name AS "CategoryName",
  m.mold_name AS "MoldName", dl.finger_count AS "FingerCount",
  CASE WHEN dl.load_id IS NOT NULL AND dl.load_timestamp IS NOT NULL
       AND (now() - dl.load_timestamp) > interval '72 hours' THEN TRUE ELSE FALSE END AS "Overdue"
FROM generate_series(1,32) s(i)
LEFT JOIN app.dryer_loading dl ON dl.chamber_no = s.i AND dl.is_unloaded = FALSE
LEFT JOIN app.products p ON dl.product_id = p.product_id
LEFT JOIN app.categories c ON p.category_id = c.category_id
LEFT JOIN app.molds m ON p.mold_id = m.mold_id
LEFT JOIN app.users u ON dl.load_operator_id = u.user_id;

CREATE OR REPLACE VIEW api.dryer_occupied AS
SELECT dl.chamber_no AS "ChamberNo",
  TRUE AS occupied,
  p.product_name AS "ProductName", dl.load_time AS "LoadTime",
  COALESCE(u.full_name, u.username) AS "Operator",
  p.category_id AS "CategoryID", p.mold_id AS "MoldID",
  c.category_name AS "CategoryName", m.mold_name AS "MoldName",
  dl.finger_count AS "FingerCount",
  dl.load_date_jalali AS "LoadDateJalali", dl.load_id AS "LoadID"
FROM app.dryer_loading dl
JOIN app.products p ON dl.product_id = p.product_id
LEFT JOIN app.categories c ON p.category_id = c.category_id
LEFT JOIN app.molds m ON p.mold_id = m.mold_id
LEFT JOIN app.users u ON dl.load_operator_id = u.user_id
WHERE dl.is_unloaded = FALSE;

CREATE OR REPLACE VIEW api.dryer_history AS
SELECT dl.load_id AS id, dl.chamber_no AS chamber, p.product_name AS product,
       dl.load_date_jalali AS date, dl.load_time AS time, dl.finger_count AS finger
FROM app.dryer_loading dl
LEFT JOIN app.products p ON dl.product_id = p.product_id
WHERE dl.is_unloaded = FALSE
ORDER BY dl.load_timestamp DESC LIMIT 20;

CREATE OR REPLACE VIEW api.dryer_unloading_history AS
SELECT du.unload_id AS id, dl.chamber_no AS chamber, p.product_name AS product,
       du.unload_date_jalali AS date, du.unload_time AS time,
       du.unloaded_finger_count AS finger, COALESCE(u.full_name, u.username) AS operator,
       du.dryer_waste AS waste
FROM app.dryer_unloading du
JOIN app.dryer_loading dl ON du.load_id = dl.load_id
LEFT JOIN app.products p ON dl.product_id = p.product_id
LEFT JOIN app.users u ON du.unload_operator_id = u.user_id
ORDER BY du.created_at DESC LIMIT 20;

CREATE OR REPLACE VIEW api.dryer_unload_history AS SELECT * FROM api.dryer_unloading_history;

CREATE OR REPLACE VIEW api.dryer_readings_recent AS
SELECT r.reading_id AS "ReadingID", r.chamber_no AS "ChamberNo",
       r.record_date_jalali AS "RecordDate", r.record_time AS "RecordTime",
       r.temperature AS "Temperature", r.humidity AS "Humidity",
       COALESCE(u.full_name, u.username) AS "Operator", r.notes AS "Notes"
FROM app.simple_dryer_readings r
LEFT JOIN app.users u ON r.recorded_by = u.user_id
ORDER BY r.reading_id DESC LIMIT 20;

CREATE OR REPLACE VIEW api.kiln_last_push_info AS
SELECT incoming_car_id AS "IncomingCarID", push_date_jalali, push_time
FROM app.kiln_push_data ORDER BY push_id DESC LIMIT 1;

CREATE OR REPLACE VIEW api.kiln_pushing_recent AS
SELECT k.push_id AS "push_id", k.push_date_jalali AS "push_date_jalali",
       k.push_time AS "push_time", k.shift_id AS "shift_id",
       k.operator_id AS "operator_id", COALESCE(u.full_name, u.username) AS "operator_name",
       p.product_name AS "product_name", k.incoming_car_id AS "incoming_car_id",
       f.fuel_name AS "fuel_name",
       COALESCE(k.push_date_jalali,'') || ' ' || COALESCE(k.push_time,'') AS "push_timestamp"
FROM app.kiln_push_data k
LEFT JOIN app.products p ON k.product_id = p.product_id
LEFT JOIN app.fuel_types f ON k.fuel_type_id = f.fuel_type_id
LEFT JOIN app.users u ON k.operator_id = u.user_id
ORDER BY k.push_id DESC LIMIT 20;

-- Access control views
CREATE OR REPLACE VIEW api.user_allowed_pages AS
SELECT u.user_id, p.page_key
FROM app.users u
JOIN app.roles r ON u.role_id = r.role_id
JOIN app.role_page_access rpa ON r.role_id = rpa.role_id
JOIN app.pages p ON rpa.page_id = p.page_id;

CREATE OR REPLACE VIEW api.role_allowed_pages AS
SELECT r.role_id, p.page_key, p.page_id, p.page_title,
  CASE WHEN rpa.page_id IS NOT NULL THEN TRUE ELSE FALSE END AS "Allowed"
FROM app.roles r CROSS JOIN app.pages p
LEFT JOIN app.role_page_access rpa ON r.role_id = rpa.role_id AND p.page_id = rpa.page_id;

-- Products with categories (M2M)
CREATE OR REPLACE VIEW api.products_with_categories AS
SELECT p.product_code AS "ProductCode", p.product_name AS "ProductName",
  COALESCE(json_agg(json_build_object('CategoryID',c.category_id,'CategoryName',c.category_name))
    FILTER (WHERE c.category_id IS NOT NULL), '[]') AS "Categories"
FROM app.products p
LEFT JOIN app.product_category_assignments pca ON p.product_id = pca.product_id
LEFT JOIN app.categories c ON pca.category_id = c.category_id
GROUP BY p.product_id, p.product_code, p.product_name;

-- =============================================================
-- 10. API RPC FUNCTIONS
-- =============================================================

-- JWT helpers
CREATE OR REPLACE FUNCTION api.sign(payload json, secret text, algorithm text DEFAULT 'HS256') RETURNS text AS $$
DECLARE
  header json := json_build_object('typ','JWT','alg',algorithm);
  h64 text := translate(encode(convert_to(header::text,'utf8'),'base64'),'+/=','-_');
  p64 text := translate(encode(convert_to(payload::text,'utf8'),'base64'),'+/=','-_');
  sig text := translate(encode(hmac(h64||'.'||p64,secret,'sha256'),'base64'),'+/=','-_');
BEGIN RETURN h64||'.'||p64||'.'||sig; END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Login
CREATE OR REPLACE FUNCTION api.login(p_username text, p_password text) RETURNS json AS $$
DECLARE _role text; _uid bigint; result json;
BEGIN
  SELECT r.role_name, u.user_id INTO _role, _uid
  FROM app.users u JOIN app.roles r ON u.role_id = r.role_id
  WHERE u.username = p_username;
  IF _role IS NULL THEN RETURN json_build_object('error','Invalid login credentials'); END IF;
  IF _role NOT IN ('appuser','admin') THEN _role := 'appuser'; END IF;
  result := json_build_object(
    'token', api.sign(json_build_object('role',_role,'user_id',_uid,'exp',extract(epoch from now())::integer+86400),
      (SELECT value FROM app.config WHERE key='jwt_secret')),
    'user', json_build_object('username',p_username,'role',_role,'user_id',_uid));
  RETURN result;
EXCEPTION WHEN OTHERS THEN RETURN json_build_object('error', SQLERRM);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Dryer loading
CREATE OR REPLACE FUNCTION api.create_dryer_loading_simple(
  chamber_no int, category_id int, mold_id int, finger_count int,
  load_date_jalali text, load_time text, operator_id int
) RETURNS json AS $$
DECLARE _pid bigint; _gid int; _id bigint; _occ int;
BEGIN
  SELECT 1 INTO _occ FROM app.dryer_loading WHERE chamber_no = create_dryer_loading_simple.chamber_no AND is_unloaded = FALSE LIMIT 1;
  IF _occ IS NOT NULL THEN RETURN json_build_object('error','Chamber is already occupied'); END IF;
  SELECT glaze_id INTO _gid FROM app.glazes WHERE glaze_code = 'UNK';
  IF _gid IS NULL THEN
    INSERT INTO app.glazes(glaze_code,glaze_name,is_self_colored,is_active) VALUES('UNK','نامشخص',FALSE,TRUE) RETURNING glaze_id INTO _gid;
  END IF;
  _pid := app.get_or_create_product(category_id, mold_id, _gid, '');
  INSERT INTO app.dryer_loading(chamber_no,product_id,finger_count,load_date_jalali,load_time,load_operator_id,shift_id,supervisor_id,is_unloaded)
  VALUES(chamber_no,_pid,finger_count,load_date_jalali,load_time,operator_id,
    COALESCE((SELECT shift_id FROM app.shifts_definition WHERE is_active=TRUE LIMIT 1),1),operator_id,FALSE)
  RETURNING load_id INTO _id;
  RETURN json_build_object('load_id',_id,'product_id',_pid);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION api.create_dryer_loading(
  chamber_no int, category_id int, mold_id int, finger_count int,
  load_date_jalali text, load_time text, operator_id int, notes text DEFAULT NULL
) RETURNS json AS $$
BEGIN RETURN api.create_dryer_loading_simple(chamber_no,category_id,mold_id,finger_count,load_date_jalali,load_time,operator_id); END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Dryer unloading
CREATE OR REPLACE FUNCTION api.create_dryer_unloading(
  load_id bigint DEFAULT NULL, unload_date_jalali text DEFAULT NULL,
  shift_id int DEFAULT NULL, supervisor_id int DEFAULT NULL,
  unload_time text DEFAULT NULL, unload_operator_id bigint DEFAULT NULL,
  unloaded_finger_count int DEFAULT NULL, dryer_waste int DEFAULT NULL
) RETURNS json AS $$
DECLARE _lid bigint; _uid bigint;
BEGIN
  IF create_dryer_unloading.load_id IS NOT NULL AND create_dryer_unloading.load_id > 0 THEN
    _lid := create_dryer_unloading.load_id;
  ELSE RETURN json_build_object('error','Load ID required'); END IF;
  INSERT INTO app.dryer_unloading(load_id,unload_date_jalali,unload_time,shift_id,unload_operator_id,unloaded_finger_count,dryer_waste)
  VALUES(_lid,unload_date_jalali,unload_time,shift_id,unload_operator_id,COALESCE(unloaded_finger_count,0),COALESCE(dryer_waste,0))
  RETURNING unload_id INTO _uid;
  RETURN json_build_object('unload_id',_uid);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Dryer reading
CREATE OR REPLACE FUNCTION api.create_dryer_reading_by_chamber(
  chamber_no int, record_date_jalali text, record_time text,
  temperature float DEFAULT NULL, humidity float DEFAULT NULL,
  recorded_by bigint DEFAULT NULL, notes text DEFAULT NULL
) RETURNS json AS $$
DECLARE _id bigint;
BEGIN
  INSERT INTO app.simple_dryer_readings(chamber_no,record_date_jalali,record_time,temperature,humidity,recorded_by,notes)
  VALUES(chamber_no,record_date_jalali,record_time,temperature,humidity,recorded_by,notes)
  RETURNING reading_id INTO _id;
  RETURN json_build_object('reading_id',_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Kiln push
CREATE OR REPLACE FUNCTION api.kiln_push(
  push_date_jalali text, push_time text, shift_id int, operator_id bigint,
  incoming_car_id text, fuel_type_id int DEFAULT NULL, product_id bigint DEFAULT 0,
  temp_exhaust float DEFAULT NULL, temp_preheat01 float DEFAULT NULL,
  temp_preheat02 float DEFAULT NULL, temp_thermostat float DEFAULT NULL,
  temp_zone00 float DEFAULT NULL, temp_zone01 float DEFAULT NULL,
  temp_zone02 float DEFAULT NULL, temp_zone03 float DEFAULT NULL,
  temp_zone04 float DEFAULT NULL, temp_zone05 float DEFAULT NULL,
  temp_zone06 float DEFAULT NULL, temp_zone07 float DEFAULT NULL,
  temp_rapid01 float DEFAULT NULL, temp_rapid02 float DEFAULT NULL,
  temp_bottom_a float DEFAULT NULL, temp_bottom01 float DEFAULT NULL,
  temp_bottom_b float DEFAULT NULL, temp_bottom02 float DEFAULT NULL,
  notes text DEFAULT NULL, push_timestamp text DEFAULT NULL
) RETURNS json AS $$
DECLARE _id bigint;
BEGIN
  INSERT INTO app.kiln_push_data(push_date_jalali,push_time,shift_id,operator_id,incoming_car_id,fuel_type_id,
    temp_exhaust,temp_preheat01,temp_preheat02,temp_thermostat,
    temp_zone00,temp_zone01,temp_zone02,temp_zone03,temp_zone04,temp_zone05,temp_zone06,temp_zone07,
    temp_rapid01,temp_rapid02,temp_bottom_a,temp_bottom01,temp_bottom_b,temp_bottom02,notes)
  VALUES(push_date_jalali,push_time,shift_id,operator_id,api.kiln_push.incoming_car_id::integer,fuel_type_id,
    temp_exhaust,temp_preheat01,temp_preheat02,temp_thermostat,
    temp_zone00,temp_zone01,temp_zone02,temp_zone03,temp_zone04,temp_zone05,temp_zone06,temp_zone07,
    temp_rapid01,temp_rapid02,temp_bottom_a,temp_bottom01,temp_bottom_b,temp_bottom02,notes)
  RETURNING push_id INTO _id;
  RETURN json_build_object('push_id',_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Setting batch create
CREATE OR REPLACE FUNCTION api.create_setting_batch(
  setting_date text, shift int, supervisor int, operator int,
  personnel_count int, chamber_no int, category_id int,
  fingers_count int, columns_count int, waste_count int, notes text
) RETURNS json AS $$
DECLARE _sid BIGINT; _cat INT;
BEGIN
  _cat := category_id;
  IF (_cat IS NULL OR _cat = 0) AND chamber_no > 0 THEN
    SELECT p.category_id INTO _cat FROM app.dryer_loading dl
    LEFT JOIN app.products p ON p.product_id = dl.product_id
    WHERE dl.chamber_no = create_setting_batch.chamber_no AND dl.is_unloaded = FALSE
    ORDER BY dl.load_timestamp DESC LIMIT 1;
  END IF;
  IF _cat IS NULL THEN _cat := 0; END IF;
  INSERT INTO app.setting_processes(setting_date_jalali,shift_id,supervisor_id,operator_id,
    personnel_count,chamber_no,category_id,fingers_count,columns_count,dryer_waste,notes)
  VALUES(setting_date,shift,supervisor,operator,personnel_count,chamber_no,_cat,fingers_count,columns_count,waste_count,notes)
  RETURNING setting_id INTO _sid;
  RETURN json_build_object('batch_id',_sid);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION api.add_setting_wagons(batch_id bigint, wagons json) RETURNS json AS $$
DECLARE w json; _pid BIGINT; _ins INT := 0;
BEGIN
  FOR w IN SELECT * FROM json_array_elements(wagons) LOOP
    IF (w->>'product_id') IS NOT NULL AND (w->>'product_id')::int > 0 THEN
      _pid := (w->>'product_id')::int;
    ELSE
      _pid := app.get_or_create_product((w->>'category_id')::int,(w->>'mold_id')::int,(w->>'glaze_id')::int,(w->>'extra_code')::text);
    END IF;
    INSERT INTO app.setting_wagons_data(setting_id,wagon_order,wagon_no,product_id,glaze_override,start_time,end_time,packages,notes)
    VALUES(batch_id,(w->>'wagon_order')::int,(w->>'wagon_no')::int,_pid,w->>'glaze_override',w->>'start_time',w->>'end_time',(w->>'packages')::int,w->>'notes');
    _ins := _ins + 1;
  END LOOP;
  RETURN json_build_object('inserted',_ins);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION api.get_setting_transactions(
  page int DEFAULT 1, per_page int DEFAULT 10, "order" text DEFAULT NULL,
  date text DEFAULT NULL, chamber text DEFAULT NULL
) RETURNS json AS $$
DECLARE _off int := (page-1)*per_page; _total int; _data json; _tp int;
BEGIN
  SELECT COUNT(*) INTO _total FROM app.setting_wagons_data w
  JOIN app.setting_processes s ON w.setting_id = s.setting_id
  WHERE (date IS NULL OR s.setting_date_jalali = date)
    AND (chamber IS NULL OR s.chamber_no::text = chamber);
  _tp := CEIL(_total::float / GREATEST(per_page,1));
  SELECT COALESCE(json_agg(t),'[]'::json) INTO _data FROM (
    SELECT s.setting_date_jalali AS "TransactionDate", sh.shift_name AS "Shift",
      u_sup.full_name AS "HeadShiftName", u_op.full_name AS "OperatorName",
      s.personnel_count AS "PersonCount", s.chamber_no AS "ChamberID_FK",
      pd.product_name AS "ProductName", pd.category_name AS "CategoryName",
      pd.mold_name AS "MoldName", pd.glaze_name AS "GlazeName",
      s.fingers_count AS "FingerCount", s.columns_count AS "ColumnCount",
      s.dryer_waste AS "RejectCount", w.wagon_no AS "WagonID_FK",
      w.start_time AS "WagonStartTime", w.end_time AS "WagonEndTime",
      w.packages AS "PacksLoaded", s.setting_id AS "SettingID"
    FROM app.setting_wagons_data w
    JOIN app.setting_processes s ON w.setting_id = s.setting_id
    LEFT JOIN app.shifts_definition sh ON s.shift_id = sh.shift_id
    LEFT JOIN app.users u_sup ON s.supervisor_id = u_sup.user_id
    LEFT JOIN app.users u_op ON s.operator_id = u_op.user_id
    LEFT JOIN app.product_details pd ON pd."ProductID" = w.product_id
    WHERE (get_setting_transactions.date IS NULL OR s.setting_date_jalali = get_setting_transactions.date)
      AND (get_setting_transactions.chamber IS NULL OR s.chamber_no::text = get_setting_transactions.chamber)
    ORDER BY s.setting_date_jalali DESC, w.start_time DESC
    LIMIT per_page OFFSET _off
  ) t;
  RETURN json_build_object('transactions',_data,'total_count',_total,'total_pages',_tp);
END;
$$ LANGUAGE plpgsql STABLE;

-- Unload + Setting combined
CREATE OR REPLACE FUNCTION api.unload_and_setting(
  chamber_no int, unload_date_jalali text, unload_time text,
  operator_id bigint, setting_operator_id bigint,
  unloaded_finger_count int, dryer_waste int, wagons json
) RETURNS json AS $$
DECLARE
  _load_id bigint; _unload_id bigint; _setting_id bigint;
  _cat_id bigint; _mold_id bigint; _glaze_id bigint; _loaded_fingers int;
  w json; _pid bigint; _shift_id bigint;
BEGIN
  -- Find active load for chamber
  SELECT dl.load_id, dl.product_id, dl.finger_count, dl.load_operator_id
  INTO _load_id, _cat_id, _loaded_fingers, operator_id
  FROM app.dryer_loading dl
  WHERE dl.chamber_no = unload_and_setting.chamber_no AND dl.is_unloaded = FALSE
  ORDER BY dl.load_timestamp DESC LIMIT 1;

  IF _load_id IS NULL THEN RETURN json_build_object('error','No active load for chamber'); END IF;

  -- Get product details for category/mold/glaze
  SELECT p.category_id, p.mold_id, p.glaze_id
  INTO _cat_id, _mold_id, _glaze_id
  FROM app.products p WHERE p.product_id = _cat_id;

  -- Default finger count
  IF unloaded_finger_count IS NULL OR unloaded_finger_count = 0 THEN
    unloaded_finger_count := _loaded_fingers;
  END IF;

  -- Create unload
  INSERT INTO app.dryer_unloading(load_id,unload_date_jalali,unload_time,unload_operator_id,unloaded_finger_count,dryer_waste)
  VALUES(_load_id,unload_date_jalali,unload_time,operator_id,unloaded_finger_count,COALESCE(dryer_waste,0))
  RETURNING unload_id INTO _unload_id;

  -- Get default shift
  SELECT shift_id INTO _shift_id FROM app.shifts_definition WHERE is_active=TRUE LIMIT 1;
  IF _shift_id IS NULL THEN _shift_id := 1; END IF;

  -- Create setting
  INSERT INTO app.setting_processes(setting_date_jalali,shift_id,supervisor_id,operator_id,
    personnel_count,chamber_no,category_id,fingers_count,columns_count,dryer_waste,notes)
  VALUES(unload_date_jalali,_shift_id,operator_id,setting_operator_id,0,
    unload_and_setting.chamber_no,_cat_id,unloaded_finger_count,0,COALESCE(dryer_waste,0),'')
  RETURNING setting_id INTO _setting_id;

  -- Insert wagons
  IF wagons IS NOT NULL THEN
    FOR w IN SELECT * FROM json_array_elements(wagons) LOOP
      _pid := app.get_or_create_product(
        COALESCE((w->>'category_id')::bigint, _cat_id),
        COALESCE((w->>'mold_id')::bigint, _mold_id),
        COALESCE((w->>'glaze_id')::bigint, _glaze_id),
        (w->>'extra_code')::text
      );
      INSERT INTO app.setting_wagons_data(setting_id,wagon_order,wagon_no,product_id,start_time,end_time,packages)
      VALUES(_setting_id,
        COALESCE((w->>'wagon_order')::int, 1),
        COALESCE((w->>'wagon_no')::int, 0),
        _pid,
        (w->>'start_time')::text,
        (w->>'end_time')::text,
        COALESCE((w->>'packages')::int, 0));
    END LOOP;
  END IF;

  RETURN json_build_object('success', TRUE, 'unload_id', _unload_id, 'setting_id', _setting_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Get setting details (for edit mode)
CREATE OR REPLACE FUNCTION api.get_setting_details(setting_id bigint) RETURNS json AS $$
DECLARE _s json; _w json;
BEGIN
  SELECT json_build_object(
    'SettingID', s.setting_id, 'SettingDateJalali', s.setting_date_jalali,
    'ChamberNo', s.chamber_no, 'CategoryID', s.category_id,
    'FingersCount', s.fingers_count, 'DryerWaste', s.dryer_waste,
    'OperatorID', s.operator_id, 'OperatorName', COALESCE(u.full_name, u.username),
    'SupervisorID', s.supervisor_id, 'ShiftID', s.shift_id
  ) INTO _s
  FROM app.setting_processes s
  LEFT JOIN app.users u ON u.user_id = s.operator_id
  WHERE s.setting_id = get_setting_details.setting_id;

  SELECT COALESCE(json_agg(json_build_object(
    'WagonID', w.wagon_data_id, 'WagonOrder', w.wagon_order, 'WagonNo', w.wagon_no,
    'ProductID', w.product_id, 'ProductName', p.product_name,
    'GlazeID', p.glaze_id, 'ExtraCode', p.extra_code,
    'StartTime', w.start_time, 'EndTime', w.end_time, 'Packages', w.packages
  )), '[]'::json) INTO _w
  FROM app.setting_wagons_data w
  LEFT JOIN app.products p ON p.product_id = w.product_id
  WHERE w.setting_id = get_setting_details.setting_id
  ORDER BY w.wagon_order;

  RETURN json_build_object('setting', _s, 'wagons', _w);
END;
$$ LANGUAGE plpgsql STABLE;

-- Update setting transaction
CREATE OR REPLACE FUNCTION api.update_setting_transaction(
  setting_id bigint, setting_date text DEFAULT NULL, unload_time text DEFAULT NULL,
  fingers_count int DEFAULT NULL, waste_count int DEFAULT NULL,
  wagons json DEFAULT NULL, shift int DEFAULT NULL,
  chamber_no int DEFAULT NULL, supervisor bigint DEFAULT NULL,
  operator bigint DEFAULT NULL, category_id bigint DEFAULT NULL
) RETURNS json AS $$
DECLARE w json; _pid bigint;
BEGIN
  UPDATE app.setting_processes SET
    setting_date_jalali = COALESCE(setting_date, setting_date_jalali),
    fingers_count = COALESCE(fingers_count, fingers_count),
    dryer_waste = COALESCE(waste_count, dryer_waste),
    shift_id = COALESCE(shift, shift_id),
    chamber_no = COALESCE(chamber_no, chamber_no),
    supervisor_id = COALESCE(supervisor, supervisor_id),
    operator_id = COALESCE(operator, operator_id),
    category_id = COALESCE(category_id, category_id)
  WHERE setting_id = update_setting_transaction.setting_id;

  IF wagons IS NOT NULL THEN
    DELETE FROM app.setting_wagons_data WHERE setting_id = update_setting_transaction.setting_id;
    FOR w IN SELECT * FROM json_array_elements(wagons) LOOP
      _pid := app.get_or_create_product(
        COALESCE(category_id, (w->>'category_id')::bigint, 0),
        COALESCE((w->>'mold_id')::bigint, 0),
        COALESCE((w->>'glaze_id')::bigint, 0),
        (w->>'extra_code')::text
      );
      INSERT INTO app.setting_wagons_data(setting_id,wagon_order,wagon_no,product_id,start_time,end_time,packages)
      VALUES(update_setting_transaction.setting_id,
        COALESCE((w->>'wagon_order')::int,1), COALESCE((w->>'wagon_no')::int,0),
        _pid, (w->>'start_time')::text, (w->>'end_time')::text, COALESCE((w->>'packages')::int,0));
    END LOOP;
  END IF;
  RETURN json_build_object('success', TRUE);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Product category management
CREATE OR REPLACE FUNCTION api.add_product_category(product_code text, category_id int) RETURNS json AS $$
DECLARE _pid bigint;
BEGIN
  SELECT product_id INTO _pid FROM app.products WHERE product_code = api.add_product_category.product_code;
  IF _pid IS NULL THEN RETURN json_build_object('error','Product not found'); END IF;
  INSERT INTO app.product_category_assignments(product_id,category_id) VALUES(_pid,category_id) ON CONFLICT DO NOTHING;
  RETURN json_build_object('success',true);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION api.remove_product_category(product_code text, category_id int) RETURNS json AS $$
DECLARE _pid bigint;
BEGIN
  SELECT product_id INTO _pid FROM app.products WHERE product_code = api.remove_product_category.product_code;
  DELETE FROM app.product_category_assignments WHERE product_id = _pid AND category_id = api.remove_product_category.category_id;
  RETURN json_build_object('success',true);
END;
$$ LANGUAGE plpgsql;

-- Role access management
CREATE OR REPLACE FUNCTION api.get_user_roles(user_id BIGINT) RETURNS JSON AS $$
DECLARE rid BIGINT;
BEGIN
  SELECT role_id INTO rid FROM app.users WHERE app.users.user_id = api.get_user_roles.user_id;
  IF rid IS NOT NULL THEN RETURN json_build_array(rid); ELSE RETURN '[]'::json; END IF;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION api.update_user_roles(user_id BIGINT, role_ids INTEGER[]) RETURNS JSON AS $$
BEGIN
  IF array_length(role_ids,1) > 0 THEN
    UPDATE app.users SET role_id = role_ids[1] WHERE app.users.user_id = api.update_user_roles.user_id;
  END IF;
  RETURN json_build_object('success',true);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION api.get_role_access(role_id INTEGER) RETURNS JSON AS $$
BEGIN
  RETURN (SELECT json_agg(json_build_object('PageID',p.page_id,'PageTitle',p.page_title,
    'Allowed', CASE WHEN rpa.page_id IS NOT NULL THEN true ELSE false END))
    FROM app.pages p LEFT JOIN app.role_page_access rpa ON p.page_id = rpa.page_id AND rpa.role_id = api.get_role_access.role_id);
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION api.update_role_access(role_id INTEGER, page_ids INTEGER[]) RETURNS JSON AS $$
BEGIN
  DELETE FROM app.role_page_access WHERE role_page_access.role_id = api.update_role_access.role_id;
  INSERT INTO app.role_page_access(role_id,page_id) SELECT api.update_role_access.role_id, unnest(page_ids);
  RETURN json_build_object('success',true);
END;
$$ LANGUAGE plpgsql;

-- Delete dryer load
CREATE OR REPLACE FUNCTION api.delete_dryer_load(load_id bigint) RETURNS json AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM app.dryer_unloading WHERE dryer_unloading.load_id = api.delete_dryer_load.load_id) THEN
    RETURN json_build_object('error','Cannot delete: unload record exists');
  END IF;
  DELETE FROM app.dryer_loading WHERE dryer_loading.load_id = api.delete_dryer_load.load_id;
  RETURN json_build_object('success', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================================
-- 11. INSTEAD-OF RULES for INSERT/UPDATE through views
-- =============================================================

-- Categories: auto-generate category_code on insert
CREATE OR REPLACE FUNCTION api.categories_insert() RETURNS trigger AS $$
BEGIN
  INSERT INTO app.categories(category_code, category_name, description, is_active)
  VALUES(
    COALESCE(NEW."CategoryCode", 'CAT-' || COALESCE((SELECT MAX(category_id)+1 FROM app.categories),1)),
    NEW."CategoryName", NEW."Description", COALESCE(NEW."IsActive", TRUE)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_api_categories_ins ON api.categories;
CREATE TRIGGER trg_api_categories_ins INSTEAD OF INSERT ON api.categories
FOR EACH ROW EXECUTE FUNCTION api.categories_insert();

-- Categories: update
CREATE OR REPLACE FUNCTION api.categories_update() RETURNS trigger AS $$
BEGIN
  UPDATE app.categories SET
    category_name = COALESCE(NEW."CategoryName", category_name),
    description = COALESCE(NEW."Description", description),
    is_active = COALESCE(NEW."IsActive", is_active)
  WHERE category_id = OLD."CategoryID";
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_api_categories_upd ON api.categories;
CREATE TRIGGER trg_api_categories_upd INSTEAD OF UPDATE ON api.categories
FOR EACH ROW EXECUTE FUNCTION api.categories_update();

-- Categories: delete
CREATE OR REPLACE FUNCTION api.categories_delete() RETURNS trigger AS $$
BEGIN
  UPDATE app.categories SET is_active = FALSE WHERE category_id = OLD."CategoryID";
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_api_categories_del ON api.categories;
CREATE TRIGGER trg_api_categories_del INSTEAD OF DELETE ON api.categories
FOR EACH ROW EXECUTE FUNCTION api.categories_delete();

-- =============================================================
-- 12. GRANTS
-- =============================================================

DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'web_anon') THEN
    CREATE ROLE web_anon NOLOGIN;
  END IF;
END $$;

GRANT USAGE ON SCHEMA api TO web_anon;
GRANT USAGE ON SCHEMA api TO appuser;
GRANT SELECT ON ALL TABLES IN SCHEMA api TO web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA api TO appuser;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO web_anon;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO appuser;

-- Write access for CRUD views
GRANT INSERT, UPDATE, DELETE ON api.categories TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.molds TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.glazes TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.products TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.shifts TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.fuel_types TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.roles TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.users TO appuser;

-- Grant on underlying tables for RPC SECURITY DEFINER functions
GRANT ALL ON ALL TABLES IN SCHEMA app TO appuser;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA app TO appuser;
