CREATE FUNCTION app.compute_product_code_name() RETURNS trigger AS $$
DECLARE
  v_category_code TEXT;
  v_category_name TEXT;
  v_mold_code TEXT;
  v_mold_name TEXT;
  v_glaze_code TEXT;
  v_glaze_name TEXT;
  v_extra_name TEXT;
  v_extra_part TEXT;
BEGIN
  SELECT c.category_code, c.category_name, m.mold_code, m.mold_name, g.glaze_code, g.glaze_name
  INTO v_category_code, v_category_name, v_mold_code, v_mold_name, v_glaze_code, v_glaze_name
  FROM app.categories c, app.molds m, app.glazes g
  WHERE c.category_id = NEW.category_id AND m.mold_id = NEW.mold_id AND g.glaze_id = NEW.glaze_id;

  SELECT extra_name INTO v_extra_name
  FROM app.extra_code_map
  WHERE extra_code = NULLIF(TRIM(NEW.extra_code), '');

  v_extra_part := COALESCE(NULLIF(TRIM(NEW.extra_code), ''), '');

  NEW.product_code := v_category_code || '-' || v_mold_code || '-' || v_glaze_code || v_extra_part;

  IF v_extra_name IS NOT NULL THEN
    NEW.product_name := v_category_name || ' ' || v_mold_name || ' ' || v_glaze_name || ' ' || v_extra_name;
  ELSE
    IF TRIM(COALESCE(NEW.extra_code, '')) <> '' THEN
      NEW.product_name := v_category_name || ' ' || v_mold_name || ' ' || v_glaze_name || ' ' || TRIM(NEW.extra_code);
    ELSE
      NEW.product_name := v_category_name || ' ' || v_mold_name || ' ' || v_glaze_name;
    END IF;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_products_compute_code_name
BEFORE INSERT OR UPDATE OF category_id, mold_id, glaze_id, extra_code
ON app.products
FOR EACH ROW
EXECUTE FUNCTION app.compute_product_code_name();
