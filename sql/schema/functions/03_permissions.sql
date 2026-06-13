CREATE FUNCTION app.has_permission(p_username TEXT, p_page_name TEXT, p_action TEXT)
RETURNS BOOLEAN AS $$
DECLARE
  v_user_id BIGINT;
  v_role_id BIGINT;
  v_user_active BOOLEAN;
  v_page_id BIGINT;
  v_page_active BOOLEAN;
  v_allowed BOOLEAN := FALSE;
BEGIN
  SELECT u.user_id, u.role_id, u.is_active
  INTO v_user_id, v_role_id, v_user_active
  FROM app.users u
  WHERE u.username = p_username;
  IF v_user_id IS NULL OR v_user_active IS NOT TRUE THEN
    RETURN FALSE;
  END IF;
  SELECT p.page_id, p.is_active
  INTO v_page_id, v_page_active
  FROM app.pages p
  WHERE p.page_name = p_page_name;
  IF v_page_id IS NULL OR v_page_active IS NOT TRUE THEN
    RETURN FALSE;
  END IF;
  IF p_action = 'view' THEN
    SELECT rp.can_view INTO v_allowed
    FROM app.role_permissions rp
    WHERE rp.role_id = v_role_id AND rp.page_id = v_page_id;
  ELSIF p_action = 'add' THEN
    SELECT rp.can_add INTO v_allowed
    FROM app.role_permissions rp
    WHERE rp.role_id = v_role_id AND rp.page_id = v_page_id;
  ELSIF p_action = 'edit' THEN
    SELECT rp.can_edit INTO v_allowed
    FROM app.role_permissions rp
    WHERE rp.role_id = v_role_id AND rp.page_id = v_page_id;
  ELSIF p_action = 'delete' THEN
    SELECT rp.can_delete INTO v_allowed
    FROM app.role_permissions rp
    WHERE rp.role_id = v_role_id AND rp.page_id = v_page_id;
  ELSE
    RETURN FALSE;
  END IF;
  RETURN COALESCE(v_allowed, FALSE);
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION app.require_permission(p_username TEXT, p_page_name TEXT, p_action TEXT)
RETURNS VOID AS $$
BEGIN
  IF NOT app.has_permission(p_username, p_page_name, p_action) THEN
    RAISE EXCEPTION 'permission denied for user %, page %, action %', p_username, p_page_name, p_action
      USING ERRCODE = '42501';
  END IF;
END;
$$ LANGUAGE plpgsql;

