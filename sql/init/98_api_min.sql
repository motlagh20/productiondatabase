-- Minimal API setup for local use
CREATE SCHEMA IF NOT EXISTS api;

-- Seed essentials
INSERT INTO app.firing_types (firing_type_id, firing_name) VALUES (1, 'Default')
ON CONFLICT (firing_type_id) DO NOTHING;

INSERT INTO app.shifts_definition (shift_id, shift_code, shift_name, is_active)
VALUES (1, 1, 'Shift 1', TRUE)
ON CONFLICT (shift_id) DO NOTHING;

INSERT INTO app.roles (role_name, description) VALUES ('Operator','Default operator role')
ON CONFLICT (role_name) DO NOTHING;

INSERT INTO app.users (username, full_name, password_hash, role_id, is_active)
SELECT 'operator1','Operator One','x', r.role_id, TRUE
FROM app.roles r WHERE r.role_name='Operator'
ON CONFLICT (username) DO NOTHING;

-- CamelCase Views
CREATE OR REPLACE VIEW api.categories AS
SELECT
  category_id AS "CategoryID",
  category_code AS "CategoryCode",
  category_name AS "CategoryName",
  description AS "Description",
  is_active AS "IsActive"
FROM app.categories;

CREATE OR REPLACE VIEW api.molds AS
SELECT
  mold_id AS "MoldID",
  mold_code AS "MoldCode",
  mold_name AS "MoldName",
  category_id AS "CategoryID",
  width AS "Width",
  length AS "Length",
  height AS "Height",
  pieces_per_press AS "PiecesPerPress",
  is_active AS "IsActive"
FROM app.molds;

CREATE OR REPLACE VIEW api.glazes AS
SELECT
  glaze_id AS "GlazeID",
  glaze_code AS "GlazeCode",
  glaze_name AS "GlazeName",
  is_self_colored AS "IsSelfColored",
  is_active AS "IsActive"
FROM app.glazes;

CREATE OR REPLACE VIEW api.users AS
SELECT
  u.user_id AS "UserID",
  u.username AS "Username",
  u.full_name AS "FullName",
  u.is_active AS "IsActive",
  r.role_name AS "Role"
FROM app.users u
LEFT JOIN app.roles r ON u.role_id = r.role_id;

CREATE OR REPLACE VIEW api.operators_dryer AS
SELECT
  u.user_id AS "OperatorCode",
  COALESCE(u.full_name, u.username) AS "OperatorName"
FROM app.users u
JOIN app.roles r ON u.role_id = r.role_id
WHERE r.role_name IN ('Dryer', 'Operator') AND u.is_active = TRUE;

-- Occupancy View (Overdue simplified to FALSE)
CREATE OR REPLACE VIEW api.dryer_chambers_status AS
SELECT
  s.i AS "ChamberNo",
  (dl.load_id IS NOT NULL AND dl.is_unloaded = FALSE) AS occupied,
  dl.load_date_jalali AS "LoadDateJalali",
  dl.load_time AS "LoadTime",
  COALESCE(u.full_name, u.username) AS "Operator",
  p.product_name AS "ProductName",
  c.category_name AS "CategoryName",
  m.mold_name AS "MoldName",
  dl.finger_count AS "FingerCount",
  FALSE AS "Overdue"
FROM generate_series(1, 32) s(i)
LEFT JOIN app.dryer_loading dl ON dl.chamber_no = s.i AND dl.is_unloaded = FALSE
LEFT JOIN app.users u ON dl.load_operator_id = u.user_id
LEFT JOIN app.products p ON dl.product_id = p.product_id
LEFT JOIN app.categories c ON p.category_id = c.category_id
LEFT JOIN app.molds m ON p.mold_id = m.mold_id;

-- Helper: create or fetch product
CREATE OR REPLACE FUNCTION app.get_or_create_product(_category_id BIGINT, _mold_id BIGINT, _glaze_id BIGINT, _extra TEXT)
RETURNS BIGINT AS $$
DECLARE
  _pid BIGINT;
BEGIN
  SELECT product_id INTO _pid
  FROM app.products
  WHERE category_id = _category_id
    AND mold_id = _mold_id
    AND glaze_id = _glaze_id
    AND extra_code = COALESCE(_extra,'')
  LIMIT 1;

  IF _pid IS NULL THEN
    INSERT INTO app.products (product_code, product_name, category_id, mold_id, glaze_id, extra_code, is_active)
    VALUES (concat('TMP-',_category_id,'-',_mold_id,'-',_glaze_id), 'محصول موقت', _category_id, _mold_id, _glaze_id, COALESCE(_extra,''), TRUE)
    RETURNING product_id INTO _pid;
  END IF;
  RETURN _pid;
END;
$$ LANGUAGE plpgsql;

-- Dryer Loading RPC (simple)
CREATE OR REPLACE FUNCTION api.create_dryer_loading_simple(
  p_chamber_no INT,
  p_category_id INT,
  p_mold_id INT,
  p_finger_count INT,
  p_load_date_jalali TEXT,
  p_load_time TEXT,
  p_operator_id INT
) RETURNS JSON AS $$
DECLARE
  _pid BIGINT;
  _gid INT;
  _id BIGINT;
  _occupied INT;
BEGIN
  SELECT 1 INTO _occupied FROM app.dryer_loading dl WHERE dl.chamber_no = p_chamber_no AND dl.is_unloaded = FALSE LIMIT 1;
  IF _occupied IS NOT NULL THEN
    RETURN json_build_object('error', 'Chamber is already occupied');
  END IF;

  SELECT glaze_id INTO _gid FROM app.glazes WHERE glaze_code = 'UNK';
  IF _gid IS NULL THEN
    INSERT INTO app.glazes(glaze_code, glaze_name, is_self_colored, is_active)
    VALUES ('UNK', 'نامشخص', FALSE, TRUE)
    RETURNING glaze_id INTO _gid;
  END IF;

  _pid := app.get_or_create_product(p_category_id, p_mold_id, _gid, '');

  INSERT INTO app.dryer_loading(
    chamber_no, product_id, finger_count, load_date_jalali, load_time,
    load_operator_id, shift_id, supervisor_id, is_unloaded
  ) VALUES (
    p_chamber_no, _pid, p_finger_count, p_load_date_jalali, p_load_time,
    p_operator_id,
    COALESCE((SELECT shift_id FROM app.shifts_definition WHERE is_active = TRUE LIMIT 1), 1),
    p_operator_id,
    FALSE
  ) RETURNING load_id INTO _id;

  RETURN json_build_object('load_id', _id, 'product_id', _pid);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION api.create_dryer_loading(
  p_chamber_no INT,
  p_category_id INT,
  p_mold_id INT,
  p_finger_count INT,
  p_load_date_jalali TEXT,
  p_load_time TEXT,
  p_operator_id INT,
  p_notes TEXT DEFAULT NULL
) RETURNS JSON AS $$
DECLARE
  _r JSON;
BEGIN
  _r := api.create_dryer_loading_simple(p_chamber_no, p_category_id, p_mold_id, p_finger_count, p_load_date_jalali, p_load_time, p_operator_id);
  RETURN _r;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grants
GRANT USAGE ON SCHEMA api TO appuser;
GRANT SELECT ON ALL TABLES IN SCHEMA api TO appuser;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO appuser;
