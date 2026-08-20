CREATE FUNCTION app.record_login_attempt(
  p_username TEXT,
  p_success BOOLEAN,
  p_token_hash TEXT,
  p_ttl_minutes INTEGER
) RETURNS BIGINT AS $$
DECLARE
  v_user_id BIGINT;
  v_session_id BIGINT;
BEGIN
  SELECT user_id INTO v_user_id FROM app.users WHERE username = p_username AND is_active = TRUE;
  IF v_user_id IS NULL THEN
    RETURN NULL;
  END IF;
  IF p_success IS TRUE THEN
    PERFORM app.mark_successful_login(p_username);
    IF p_token_hash IS NOT NULL AND p_ttl_minutes IS NOT NULL THEN
      v_session_id := app.create_login_session(v_user_id, p_token_hash, p_ttl_minutes);
      UPDATE app.users SET last_login = NOW() WHERE user_id = v_user_id;
      RETURN v_session_id;
    ELSE
      UPDATE app.users SET last_login = NOW() WHERE user_id = v_user_id;
      RETURN NULL;
    END IF;
  ELSE
    PERFORM app.mark_failed_login(p_username);
    RETURN NULL;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION app.login(
  p_username TEXT,
  p_password TEXT,
  p_ttl_minutes INTEGER DEFAULT 60
) RETURNS TABLE(session_id BIGINT, user_id BIGINT, role_name TEXT) AS $$
DECLARE
  v_user_id BIGINT;
  v_role_name TEXT;
  v_hash TEXT;
  v_locked_until TIMESTAMPTZ;
  v_token_hash TEXT;
BEGIN
  SELECT u.user_id, r.role_name, c.password_hash, c.locked_until
  INTO v_user_id, v_role_name, v_hash, v_locked_until
  FROM app.users u
  LEFT JOIN app.roles r ON r.role_id = u.role_id
  JOIN app.user_credentials c ON c.user_id = u.user_id
  WHERE u.username = p_username AND u.is_active = TRUE;

  IF v_user_id IS NULL THEN
    PERFORM app.mark_failed_login(p_username);
    RETURN;
  END IF;

  IF v_locked_until IS NOT NULL AND v_locked_until > NOW() THEN
    RETURN;
  END IF;

  IF crypt(p_password, v_hash) = v_hash THEN
    v_token_hash := encode(gen_random_bytes(32), 'hex');
    session_id := app.create_login_session(v_user_id, v_token_hash, p_ttl_minutes);
    user_id := v_user_id;
    role_name := v_role_name;
    PERFORM app.mark_successful_login(p_username);
    UPDATE app.users SET last_login = NOW() WHERE user_id = v_user_id;
    RETURN NEXT;
    RETURN;
  ELSE
    PERFORM app.mark_failed_login(p_username);
    RETURN;
  END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

