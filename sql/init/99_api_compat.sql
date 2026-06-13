-- Switch to the right database context if needed
DO $$ 
BEGIN 
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'web_anon') THEN 
    CREATE ROLE web_anon NOLOGIN; 
  END IF; 
END 
$$;

-- 1. Enable pgcrypto for JWT
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. Create API schema
CREATE SCHEMA IF NOT EXISTS api;

-- 3. JWT Helper Functions
CREATE OR REPLACE FUNCTION api.sign(payload json, secret text, algorithm text DEFAULT 'HS256')
RETURNS text AS $$
DECLARE
  header json := json_build_object('typ', 'JWT', 'alg', algorithm);
  header_base64 text := translate(encode(convert_to(header::text, 'utf8'), 'base64'), '+/=', '-_');
  payload_base64 text := translate(encode(convert_to(payload::text, 'utf8'), 'base64'), '+/=', '-_');
  signature text := translate(encode(hmac(header_base64 || '.' || payload_base64, secret, 'sha256'), 'base64'), '+/=', '-_');
BEGIN
  RETURN header_base64 || '.' || payload_base64 || '.' || signature;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION api.login(username text, password text) RETURNS json AS $$
DECLARE
  _role text;
  _user_id bigint;
  result json;
BEGIN
  SELECT r.role_name, u.user_id INTO _role, _user_id
  FROM app.users u
  JOIN app.roles r ON u.role_id = r.role_id
  WHERE u.username = api.login.username;

  IF _role IS NULL THEN
    RETURN json_build_object('error', 'Invalid login credentials');
  END IF;

  -- Map to PostgREST roles
  IF _role NOT IN ('appuser', 'admin') THEN
     _role := 'appuser';
  END IF;

  result := json_build_object(
    'token', api.sign(
      json_build_object(
        'role', _role,
        'user_id', _user_id,
        'exp', extract(epoch from now())::integer + 3600*24
      ),
      current_setting('pgrst.jwt_secret')
    ),
    'user', json_build_object('username', username, 'role', _role, 'user_id', _user_id)
  );
  RETURN result;
EXCEPTION WHEN OTHERS THEN
  RETURN json_build_object('error', SQLERRM);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. CamelCase Views (for Dropdowns and Frontend Config)

-- Categories: CamelCase
CREATE OR REPLACE VIEW api.categories AS
SELECT
    category_id AS "CategoryID",
    category_code AS "CategoryCode",
    category_name AS "CategoryName",
    description AS "Description",
    is_active AS "IsActive"
FROM app.categories;

-- Molds: CamelCase
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

-- Glazes: CamelCase
CREATE OR REPLACE VIEW api.glazes AS
SELECT
    glaze_id AS "GlazeID",
    glaze_code AS "GlazeCode",
    glaze_name AS "GlazeName",
    is_self_colored AS "IsSelfColored",
    is_active AS "IsActive"
FROM app.glazes;

-- Shifts: CamelCase (for Admin)
CREATE OR REPLACE VIEW api.shifts AS
SELECT
    shift_id AS "ShiftID",
    shift_code AS "ShiftCode",
    shift_name AS "ShiftName",
    start_time AS "StartTime",
    end_time AS "EndTime",
    is_active AS "IsActive"
FROM app.shifts_definition;

-- FuelTypes: CamelCase
CREATE OR REPLACE VIEW api.fuel_types AS
SELECT
    fuel_type_id AS "FuelTypeID",
    fuel_name AS "FuelName",
    is_active AS "IsActive"
FROM app.fuel_types;

-- Roles: CamelCase
CREATE OR REPLACE VIEW api.roles AS
SELECT
    role_id AS "RoleID",
    role_name AS "RoleName",
    is_active AS "IsActive"
FROM app.roles;

-- Pages: CamelCase
CREATE OR REPLACE VIEW api.pages AS
SELECT
    page_id AS "PageID",
    page_key AS "PageKey",
    page_title AS "PageTitle",
    is_active AS "IsActive"
FROM app.pages;

-- 5. snake_case Views (for Lists and Core Logic compatibility)

-- Users: CamelCase
CREATE OR REPLACE VIEW api.users AS
SELECT
    u.user_id AS "UserID",
    u.username AS "Username",
    u.full_name AS "FullName",
    u.is_active AS "IsActive",
    r.role_name AS "Role"
FROM app.users u
LEFT JOIN app.roles r ON u.role_id = r.role_id;

-- Products: CamelCase
CREATE OR REPLACE VIEW api.products AS
SELECT
    product_id AS "ProductID",
    product_code AS "ProductCode",
    product_name AS "ProductName",
    category_id AS "CategoryID",
    mold_id AS "MoldID",
    glaze_id AS "GlazeID",
    extra_code AS "ExtraCode",
    is_active AS "IsActive",
    created_at AS "CreatedAt"
FROM app.products;

-- Product Details: CamelCase
CREATE OR REPLACE VIEW api.product_details AS
SELECT
    p.product_id AS "ProductID",
    p.product_code AS "ProductCode",
    p.product_name AS "ProductName",
    c.category_name AS "CategoryName",
    m.mold_name AS "MoldName",
    g.glaze_name AS "GlazeName",
    p.extra_code AS "ExtraCode",
    p.is_active AS "IsActive"
FROM app.products p
JOIN app.categories c ON p.category_id = c.category_id
JOIN app.molds m ON p.mold_id = m.mold_id
JOIN app.glazes g ON p.glaze_id = g.glaze_id;

-- Products with Categories (Simulated M2M)
CREATE OR REPLACE VIEW api.products_with_categories AS
SELECT
    p.product_code AS "ProductCode",
    p.product_name AS "ProductName",
    COALESCE(
        json_agg(
            json_build_object(
                'CategoryID', c.category_id,
                'CategoryName', c.category_name
            )
        ) FILTER (WHERE c.category_id IS NOT NULL),
        '[]'
    ) AS "Categories"
FROM app.products p
LEFT JOIN app.product_category_assignments pca ON p.product_id = pca.product_id
LEFT JOIN app.categories c ON pca.category_id = c.category_id
GROUP BY p.product_id, p.product_code, p.product_name;

-- 6. Operational Views

-- Operators Dryer
CREATE OR REPLACE VIEW api.operators_dryer AS
SELECT
    u.user_id AS "OperatorCode",
    COALESCE(u.full_name, u.username) AS "OperatorName"
FROM app.users u
JOIN app.roles r ON u.role_id = r.role_id
WHERE r.role_name IN ('Dryer', 'Operator');

-- Operators Kiln
CREATE OR REPLACE VIEW api.operators_kiln AS
SELECT
    u.user_id AS "OperatorCode",
    COALESCE(u.full_name, u.username) AS "OperatorName"
FROM app.users u
JOIN app.roles r ON u.role_id = r.role_id
WHERE r.role_name IN ('Kiln', 'Operator');

-- Operators Generic (New)
CREATE OR REPLACE VIEW api.operators AS
SELECT
    u.user_id AS "OperatorCode",
    COALESCE(u.full_name, u.username) AS "OperatorName",
    r.role_name AS "RoleName"
FROM app.users u
JOIN app.roles r ON u.role_id = r.role_id;

-- Shift Options
CREATE OR REPLACE VIEW api.shift_options AS
SELECT
    shift_id,
    shift_name
FROM app.shifts_definition
WHERE is_active = true;

-- Kiln Last Push Info
CREATE OR REPLACE VIEW api.kiln_last_push_info AS
SELECT
    incoming_car_id AS "IncomingCarID",
    push_date_jalali,
    push_time
FROM app.kiln_push_data
ORDER BY push_id DESC
LIMIT 1;

-- Kiln Pushing Recent
CREATE OR REPLACE VIEW api.kiln_pushing_recent AS
SELECT
    k.push_id AS "push_id",
    k.push_date_jalali AS "push_date_jalali",
    k.push_time AS "push_time",
    k.shift_id AS "shift_id",
    k.operator_id AS "operator_id",
    COALESCE(u.full_name, u.username) AS "operator_name",
    p.product_name AS "product_name",
    k.incoming_car_id AS "incoming_car_id",
    f.fuel_name AS "fuel_name",
    k.push_date_jalali || ' ' || k.push_time AS "push_timestamp"
FROM app.kiln_push_data k
LEFT JOIN app.products p ON k.product_id = p.product_id
LEFT JOIN app.fuel_types f ON k.fuel_type_id = f.fuel_type_id
LEFT JOIN app.users u ON k.operator_id = u.user_id
ORDER BY k.push_id DESC
LIMIT 20;

-- Dryer Occupied
CREATE OR REPLACE VIEW api.dryer_occupied AS
SELECT
    dl.chamber_no AS "ChamberNo",
    CASE WHEN dl.is_unloaded THEN false ELSE true END AS occupied,
    p.product_name AS "ProductName",
    dl.load_time AS "LoadTime",
    COALESCE(u.full_name, u.username) AS "Operator",
    p.category_id AS "CategoryID",
    p.mold_id AS "MoldID"
FROM app.dryer_loading dl
JOIN app.products p ON dl.product_id = p.product_id
LEFT JOIN app.users u ON dl.load_operator_id = u.user_id
WHERE dl.is_unloaded = false;

-- Dryer History
CREATE OR REPLACE VIEW api.dryer_history AS
SELECT
    dl.load_id AS id,
    dl.chamber_no AS chamber,
    p.product_name AS product,
    dl.load_date_jalali AS date,
    dl.load_time AS time,
    dl.finger_count AS finger
FROM app.dryer_loading dl
LEFT JOIN app.products p ON dl.product_id = p.product_id
WHERE dl.is_unloaded = false
ORDER BY dl.load_timestamp DESC
LIMIT 20;

-- Dryer Unloading History
CREATE OR REPLACE VIEW api.dryer_unloading_history AS
SELECT
    du.unload_id AS id,
    dl.chamber_no AS chamber,
    p.product_name AS product,
    du.unload_date_jalali AS date,
    du.unload_time AS time,
    du.finger_count AS finger,
    COALESCE(u.full_name, u.username) AS operator
FROM app.dryer_unloading du
JOIN app.dryer_loading dl ON du.load_id = dl.load_id
LEFT JOIN app.products p ON dl.product_id = p.product_id
LEFT JOIN app.users u ON du.unload_operator_id = u.user_id
ORDER BY du.unload_timestamp DESC
LIMIT 20;

CREATE OR REPLACE VIEW api.dryer_unload_history AS SELECT * FROM api.dryer_unloading_history;

-- Fuel Types View (Alias)
CREATE OR REPLACE VIEW api.fuel_types_view AS SELECT * FROM api.fuel_types;

-- Allowed Pages
CREATE OR REPLACE VIEW api.user_allowed_pages AS
SELECT
    u.user_id,
    p.page_key
FROM app.users u
JOIN app.roles r ON u.role_id = r.role_id
JOIN app.role_page_access rpa ON r.role_id = rpa.role_id
JOIN app.pages p ON rpa.page_id = p.page_id;

CREATE OR REPLACE VIEW api.role_allowed_pages AS
SELECT
    r.role_id,
    p.page_key,
    p.page_id,
    p.page_title,
    CASE WHEN rpa.page_id IS NOT NULL THEN true ELSE false END AS "Allowed"
FROM app.roles r
CROSS JOIN app.pages p
LEFT JOIN app.role_page_access rpa ON r.role_id = rpa.role_id AND p.page_id = rpa.page_id;

-- 7. RPC Functions

-- Kiln Push
CREATE OR REPLACE FUNCTION api.kiln_push(
    push_date_jalali text,
    push_time text,
    shift_id int,
    operator_id bigint,
    incoming_car_id text,
    fuel_type_id int DEFAULT NULL,
    product_id bigint DEFAULT 0,
    temp_exhaust float DEFAULT NULL,
    temp_preheat01 float DEFAULT NULL,
    temp_preheat02 float DEFAULT NULL,
    temp_thermostat float DEFAULT NULL,
    temp_zone00 float DEFAULT NULL,
    temp_zone01 float DEFAULT NULL,
    temp_zone02 float DEFAULT NULL,
    temp_zone03 float DEFAULT NULL,
    temp_zone04 float DEFAULT NULL,
    temp_zone05 float DEFAULT NULL,
    temp_zone06 float DEFAULT NULL,
    temp_zone07 float DEFAULT NULL,
    temp_rapid01 float DEFAULT NULL,
    temp_rapid02 float DEFAULT NULL,
    temp_bottom_a float DEFAULT NULL,
    temp_bottom01 float DEFAULT NULL,
    temp_bottom_b float DEFAULT NULL,
    temp_bottom02 float DEFAULT NULL,
    notes text DEFAULT NULL,
    push_timestamp text DEFAULT NULL
) RETURNS json AS $$
DECLARE
    _id bigint;
BEGIN
    INSERT INTO app.kiln_push_data(
        push_date_jalali, push_time, shift_id, operator_id, incoming_car_id, fuel_type_id
    )
    VALUES (
        push_date_jalali, push_time, shift_id, operator_id, incoming_car_id, fuel_type_id
    )
    RETURNING push_id INTO _id;
    RETURN json_build_object('push_id', _id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Dryer Loading Simple (Complex Logic for Simple Form)
CREATE OR REPLACE FUNCTION api.create_dryer_loading_simple(
    chamber_no int,
    category_id int,
    mold_id int,
    finger_count int,
    load_date_jalali text,
    load_time text,
    operator_id int
) RETURNS json AS $$
DECLARE
    _pid bigint;
    _gid int;
    _id bigint;
    _occupied int;
BEGIN
    -- 1. Check occupancy
    SELECT 1 INTO _occupied FROM app.dryer_loading WHERE app.dryer_loading.chamber_no = api.create_dryer_loading_simple.chamber_no AND is_unloaded = false LIMIT 1;
    IF _occupied IS NOT NULL THEN
        RETURN json_build_object('error', 'Chamber is already occupied');
    END IF;

    -- 2. Find or Create Unknown Glaze
    SELECT glaze_id INTO _gid FROM app.glazes WHERE glaze_code = 'UNK';
    IF _gid IS NULL THEN
        INSERT INTO app.glazes(glaze_code, glaze_name, is_self_colored, is_active)
        VALUES ('UNK', 'نامشخص', false, true)
        RETURNING glaze_id INTO _gid;
    END IF;

    -- 3. Get or Create Product (Empty ExtraCode)
    _pid := app.get_or_create_product(category_id, mold_id, _gid, '');

    -- 4. Insert Loading
    INSERT INTO app.dryer_loading(
        chamber_no, product_id, finger_count, load_date_jalali, load_time,
        load_operator_id, shift_id, supervisor_id, is_unloaded
    ) VALUES (
        chamber_no, _pid, finger_count, load_date_jalali, load_time,
        operator_id, 
        (SELECT shift_id FROM app.shifts_definition WHERE is_active = true LIMIT 1), -- Default active shift
        operator_id, -- Default supervisor as operator
        false
    ) RETURNING load_id INTO _id;

    RETURN json_build_object('load_id', _id, 'product_id', _pid);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION api.create_dryer_loading(
    chamber_no int,
    category_id int,
    mold_id int,
    finger_count int,
    load_date_jalali text,
    load_time text,
    operator_id int,
    notes text DEFAULT NULL
) RETURNS json AS $$
DECLARE
  _r json;
BEGIN
  _r := api.create_dryer_loading_simple(chamber_no, category_id, mold_id, finger_count, load_date_jalali, load_time, operator_id);
  RETURN _r;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Dryer Unloading
CREATE OR REPLACE FUNCTION api.create_dryer_unloading(
    load_id bigint DEFAULT NULL,
    unload_date_jalali text DEFAULT NULL,
    shift_id int DEFAULT NULL,
    supervisor_id int DEFAULT NULL,
    unload_time text DEFAULT NULL,
    unload_operator_id bigint DEFAULT NULL,
    finger_count int DEFAULT NULL,
    dryer_waste int DEFAULT NULL
) RETURNS json AS $$
DECLARE
    _load_id bigint;
    _unload_id bigint;
BEGIN
    IF create_dryer_unloading.load_id IS NOT NULL AND create_dryer_unloading.load_id > 0 THEN
        _load_id := create_dryer_unloading.load_id;
    ELSE
         RETURN json_build_object('error', 'Load ID required');
    END IF;

    INSERT INTO app.dryer_unloading(load_id, unload_date_jalali, unload_time, shift_id, unload_operator_id, finger_count, waste_count)
    VALUES (_load_id, unload_date_jalali, unload_time, shift_id, unload_operator_id, finger_count, dryer_waste)
    RETURNING unload_id INTO _unload_id;

    UPDATE app.dryer_loading SET is_unloaded = true WHERE app.dryer_loading.load_id = _load_id;

    RETURN json_build_object('unload_id', _unload_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Dryer Reading Simple
CREATE OR REPLACE FUNCTION api.create_dryer_reading_by_chamber(
    chamber_no int,
    record_date_jalali text,
    record_time text,
    temperature float DEFAULT NULL,
    humidity float DEFAULT NULL,
    recorded_by bigint DEFAULT NULL,
    notes text DEFAULT NULL
) RETURNS json AS $$
DECLARE
    _id bigint;
BEGIN
    INSERT INTO app.simple_dryer_readings(
        chamber_no, record_date_jalali, record_time, temperature, humidity, recorded_by, notes
    ) VALUES (
        chamber_no, record_date_jalali, record_time, temperature, humidity, recorded_by, notes
    ) RETURNING reading_id INTO _id;
    RETURN json_build_object('reading_id', _id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Setting Batch Create
CREATE OR REPLACE FUNCTION api.create_setting_batch(
    setting_date text,
    shift int,
    supervisor int,
    operator int,
    personnel_count int,
    chamber_no int,
    category_id int,
    fingers_count int,
    columns_count int,
    waste_count int,
    notes text
) RETURNS json AS $$
DECLARE
    _sid BIGINT;
    _final_cat_id INT;
BEGIN
    _final_cat_id := category_id;
    
    -- Logic to find category from dryer loading if missing
    IF (_final_cat_id IS NULL OR _final_cat_id = 0) AND chamber_no > 0 THEN
        SELECT p.category_id INTO _final_cat_id
        FROM app.dryer_loading dl
        LEFT JOIN app.products p ON p.product_id = dl.product_id
        WHERE dl.chamber_no = api.create_setting_batch.chamber_no AND dl.is_unloaded = false
        ORDER BY dl.load_timestamp DESC
        LIMIT 1;
    END IF;
    
    IF _final_cat_id IS NULL THEN _final_cat_id := 0; END IF;

    INSERT INTO app.setting_processes(
        setting_date_jalali, shift_id, supervisor_id, operator_id,
        personnel_count, chamber_no, category_id, fingers_count, columns_count,
        dryer_waste, notes
    ) VALUES (
        setting_date, shift, supervisor, operator,
        personnel_count, chamber_no, _final_cat_id, fingers_count, columns_count,
        waste_count, notes
    ) RETURNING setting_id INTO _sid;
    
    RETURN json_build_object('batch_id', _sid);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION api.add_setting_wagons(
    batch_id bigint,
    wagons json
) RETURNS json AS $$
DECLARE
    w json;
    _pid BIGINT;
    _inserted INT := 0;
BEGIN
    FOR w IN SELECT * FROM json_array_elements(wagons)
    LOOP
        IF (w->>'product_id') IS NOT NULL AND (w->>'product_id')::int > 0 THEN
            _pid := (w->>'product_id')::int;
        ELSE
            _pid := app.get_or_create_product(
                (w->>'category_id')::int,
                (w->>'mold_id')::int,
                (w->>'glaze_id')::int,
                (w->>'extra_code')::text
            );
        END IF;

        INSERT INTO app.setting_wagons_data(
            setting_id, wagon_order, wagon_no, product_id,
            glaze_override, start_time, end_time, packages, notes
        ) VALUES (
            batch_id,
            (w->>'wagon_order')::int,
            (w->>'wagon_no')::int,
            _pid,
            w->>'glaze_override',
            w->>'start_time',
            w->>'end_time',
            (w->>'packages')::int,
            w->>'notes'
        );
        _inserted := _inserted + 1;
    END LOOP;
    
    RETURN json_build_object('inserted', _inserted);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION api.get_setting_transactions(
    page int DEFAULT 1,
    per_page int DEFAULT 10,
    "order" text DEFAULT NULL,
    date text DEFAULT NULL,
    chamber text DEFAULT NULL
) RETURNS json AS $$
DECLARE
    _offset int := (page - 1) * per_page;
    _total int;
    _data json;
    _total_pages int;
BEGIN
    -- Count total
    SELECT COUNT(*) INTO _total
    FROM app.setting_wagons_data w
    JOIN app.setting_processes s ON w.setting_id = s.setting_id
    WHERE (api.get_setting_transactions.date IS NULL OR s.setting_date_jalali = api.get_setting_transactions.date)
      AND (api.get_setting_transactions.chamber IS NULL OR s.chamber_no::text = api.get_setting_transactions.chamber);

    _total_pages := CEIL(_total::float / per_page);

    -- Get data
    SELECT COALESCE(json_agg(t), '[]'::json) INTO _data
    FROM (
        SELECT
            s.setting_date_jalali AS "TransactionDate",
            sh.shift_name AS "Shift",
            u_sup.full_name AS "HeadShiftName",
            u_op.full_name AS "OperatorName",
            s.personnel_count AS "PersonCount",
            s.chamber_no AS "ChamberID_FK",
            pd.product_name AS "ProductName",
            pd.category_name AS "CategoryName",
            pd.mold_name AS "MoldName",
            pd.glaze_name AS "GlazeName",
            s.fingers_count AS "FingerCount",
            s.columns_count AS "ColumnCount",
            s.dryer_waste AS "RejectCount",
            w.wagon_no AS "WagonID_FK",
            w.start_time AS "WagonStartTime",
            w.end_time AS "WagonEndTime",
            w.packages AS "PacksLoaded"
        FROM app.setting_wagons_data w
        JOIN app.setting_processes s ON w.setting_id = s.setting_id
        LEFT JOIN app.shifts_definition sh ON s.shift_id = sh.shift_id
        LEFT JOIN app.users u_sup ON s.supervisor_id = u_sup.user_id
        LEFT JOIN app.users u_op ON s.operator_id = u_op.user_id
        LEFT JOIN app.product_details pd ON pd.product_id = w.product_id
        WHERE (api.get_setting_transactions.date IS NULL OR s.setting_date_jalali = api.get_setting_transactions.date)
          AND (api.get_setting_transactions.chamber IS NULL OR s.chamber_no::text = api.get_setting_transactions.chamber)
        ORDER BY s.setting_date_jalali DESC, w.start_time DESC
        LIMIT per_page OFFSET _offset
    ) t;

    RETURN json_build_object(
        'transactions', _data,
        'total_count', _total,
        'total_pages', _total_pages
    );
END;
$$ LANGUAGE plpgsql STABLE;        WHERE (api.get_setting_transactions.date IS NULL OR s.setting_date_jalali = api.get_setting_transactions.date)
          AND (api.get_setting_transactions.chamber IS NULL OR s.chamber_no::text = api.get_setting_transactions.chamber)
        ORDER BY s.setting_date_jalali DESC, s.created_at DESC
        LIMIT per_page OFFSET _offset
    ) t;

    RETURN json_build_object(
        'total_count', _total,
        'total_pages', CEIL(_total::float / per_page),
        'transactions', COALESCE(_data, '[]'::json)
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- 11. Triggers for Product Auto-Generation
CREATE OR REPLACE FUNCTION app.generate_product_details()
RETURNS TRIGGER AS $$
DECLARE
  c_code TEXT; c_name TEXT;
  m_code TEXT; m_name TEXT;
  g_code TEXT; g_name TEXT;
BEGIN
  SELECT category_code, category_name INTO c_code, c_name FROM app.categories WHERE category_id = NEW.category_id;
  SELECT mold_code, mold_name INTO m_code, m_name FROM app.molds WHERE mold_id = NEW.mold_id;
  SELECT glaze_code, glaze_name INTO g_code, g_name FROM app.glazes WHERE glaze_id = NEW.glaze_id;
  
  -- Only update if not provided or looks like 'GEN%'
  IF NEW.product_code IS NULL OR NEW.product_code LIKE 'GEN%' THEN
      NEW.product_code := COALESCE(c_code,'') || COALESCE(m_code,'') || COALESCE(g_code,'') || COALESCE(NEW.extra_code,'');
  END IF;
  
  IF NEW.product_name IS NULL OR NEW.product_name = 'Generated Product' THEN
      NEW.product_name := TRIM(COALESCE(c_name,'') || ' ' || COALESCE(m_name,'') || ' ' || COALESCE(g_name,'') || ' ' || COALESCE(NEW.extra_code,''));
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_generate_product_details ON app.products;
CREATE TRIGGER trg_generate_product_details
BEFORE INSERT ON app.products
FOR EACH ROW
EXECUTE FUNCTION app.generate_product_details();

-- 12. Permissions
GRANT USAGE ON SCHEMA api TO web_anon;
GRANT USAGE ON SCHEMA api TO appuser;

GRANT SELECT ON ALL TABLES IN SCHEMA api TO web_anon;
GRANT SELECT ON ALL TABLES IN SCHEMA api TO appuser;

GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO web_anon;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA api TO appuser;

-- Allow inserts/updates through views
GRANT INSERT, UPDATE, DELETE ON api.products TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.categories TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.molds TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.glazes TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.shifts TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.fuel_types TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.roles TO appuser;
GRANT INSERT, UPDATE, DELETE ON api.users TO appuser;

CREATE OR REPLACE VIEW api.dryer_chambers_status AS
SELECT
    s.i AS "ChamberNo",
    CASE WHEN dl.load_id IS NOT NULL THEN true ELSE false END AS occupied,
    dl.load_date_jalali AS "LoadDateJalali",
    dl.load_time AS "LoadTime",
    COALESCE(u.full_name, u.username) AS "Operator",
    p.product_name AS "ProductName",
    c.category_name AS "CategoryName",
    m.mold_name AS "MoldName",
    dl.finger_count AS "FingerCount",
    CASE 
      WHEN dl.load_id IS NOT NULL AND dl.load_timestamp IS NOT NULL AND (now() - dl.load_timestamp) > interval '72 hours' THEN true 
      ELSE false 
    END AS "Overdue"
FROM generate_series(1, 32) s(i)
LEFT JOIN app.dryer_loading dl ON dl.chamber_no = s.i AND dl.is_unloaded = false
LEFT JOIN app.products p ON dl.product_id = p.product_id
LEFT JOIN app.categories c ON p.category_id = c.category_id
LEFT JOIN app.molds m ON p.mold_id = m.mold_id
LEFT JOIN app.users u ON dl.load_operator_id = u.user_id;
GRANT SELECT ON api.dryer_chambers_status TO appuser;
GRANT SELECT ON api.dryer_chambers_status TO web_anon;

CREATE OR REPLACE FUNCTION api.add_product_category(product_code text, category_id int)
RETURNS json AS $$
DECLARE _pid bigint;
BEGIN
    SELECT product_id INTO _pid FROM app.products WHERE product_code = api.add_product_category.product_code;
    IF _pid IS NULL THEN RETURN json_build_object('error', 'Product not found'); END IF;
    INSERT INTO app.product_category_assignments(product_id, category_id) VALUES (_pid, category_id) ON CONFLICT DO NOTHING;
    RETURN json_build_object('success', true);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION api.remove_product_category(product_code text, category_id int)
RETURNS json AS $$
DECLARE _pid bigint;
BEGIN
    SELECT product_id INTO _pid FROM app.products WHERE product_code = api.remove_product_category.product_code;
    DELETE FROM app.product_category_assignments WHERE product_id = _pid AND category_id = api.remove_product_category.category_id;
    RETURN json_build_object('success', true);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION api.get_user_roles(user_id BIGINT)
RETURNS JSON AS $$
DECLARE
  rid BIGINT;
BEGIN
  SELECT role_id INTO rid FROM app.users WHERE app.users.user_id = api.get_user_roles.user_id;
  IF rid IS NOT NULL THEN
    RETURN json_build_array(rid);
  ELSE
    RETURN '[]'::json;
  END IF;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION api.update_user_roles(user_id BIGINT, role_ids INTEGER[])
RETURNS JSON AS $$
DECLARE
  rid INTEGER;
BEGIN
  IF array_length(role_ids, 1) > 0 THEN
    rid := role_ids[1];
    UPDATE app.users SET role_id = rid WHERE app.users.user_id = api.update_user_roles.user_id;
  END IF;
  RETURN json_build_object('success', true);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION api.get_role_access(role_id INTEGER)
RETURNS JSON AS $$
BEGIN
  RETURN (
    SELECT json_agg(json_build_object(
      'PageID', p.page_id,
      'PageTitle', p.page_title,
      'Allowed', CASE WHEN rpa.page_id IS NOT NULL THEN true ELSE false END
    ))
    FROM app.pages p
    LEFT JOIN app.role_page_access rpa ON p.page_id = rpa.page_id AND rpa.role_id = api.get_role_access.role_id
  );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION api.update_role_access(role_id INTEGER, page_ids INTEGER[])
RETURNS JSON AS $$
BEGIN
  DELETE FROM app.role_page_access WHERE app.role_page_access.role_id = api.update_role_access.role_id;
  INSERT INTO app.role_page_access (role_id, page_id)
  SELECT api.update_role_access.role_id, unnest(page_ids);
  RETURN json_build_object('success', true);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE VIEW api.dryer_readings_recent AS
SELECT
  r.reading_id AS "ReadingID",
  r.chamber_no AS "ChamberNo",
  r.record_date_jalali AS "RecordDate",
  r.record_time AS "RecordTime",
  r.temperature AS "Temperature",
  r.humidity AS "Humidity",
  COALESCE(u.full_name, u.username) AS "Operator",
  r.notes AS "Notes"
FROM app.simple_dryer_readings r
LEFT JOIN app.users u ON r.recorded_by = u.user_id
ORDER BY r.reading_id DESC
LIMIT 20;
GRANT SELECT ON api.dryer_readings_recent TO appuser;
GRANT SELECT ON api.dryer_readings_recent TO web_anon;

-- Grant on underlying tables for RPCs and Views
GRANT ALL ON app.setting_processes TO appuser;
GRANT USAGE, SELECT ON SEQUENCE app.setting_processes_setting_id_seq TO appuser;
GRANT ALL ON app.setting_wagons_data TO appuser;
GRANT USAGE, SELECT ON SEQUENCE app.setting_wagons_data_wagon_data_id_seq TO appuser;
GRANT INSERT ON app.products TO appuser;
GRANT USAGE, SELECT ON SEQUENCE app.products_product_id_seq TO appuser;
GRANT ALL ON app.dryer_loading TO appuser;
GRANT USAGE, SELECT ON SEQUENCE app.dryer_loading_load_id_seq TO appuser;
GRANT ALL ON app.dryer_unloading TO appuser;
GRANT USAGE, SELECT ON SEQUENCE app.dryer_unloading_unload_id_seq TO appuser;
GRANT ALL ON app.kiln_push_data TO appuser;
