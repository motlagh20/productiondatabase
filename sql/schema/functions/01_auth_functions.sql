CREATE FUNCTION app.set_password_changed_timestamp() RETURNS trigger AS $$
BEGIN
  IF NEW.password_hash <> OLD.password_hash THEN
    NEW.password_last_changed_at := NOW();
    NEW.must_change_password := FALSE;
    NEW.failed_attempts := 0;
    NEW.locked_until := NULL;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_credentials_pwchange
BEFORE UPDATE OF password_hash ON app.user_credentials
FOR EACH ROW
EXECUTE FUNCTION app.set_password_changed_timestamp();

CREATE FUNCTION app.mark_failed_login(p_username TEXT) RETURNS VOID AS $$
DECLARE
  v_user_id BIGINT;
  v_attempts INTEGER;
BEGIN
  SELECT user_id INTO v_user_id
  FROM app.users
  WHERE username = p_username AND is_active = TRUE;
  IF v_user_id IS NULL THEN
    RETURN;
  END IF;
  UPDATE app.user_credentials
  SET failed_attempts = failed_attempts + 1
  WHERE user_id = v_user_id
  RETURNING failed_attempts INTO v_attempts;
  IF v_attempts >= 5 THEN
    UPDATE app.user_credentials
    SET locked_until = NOW() + INTERVAL '15 minutes'
    WHERE user_id = v_user_id;
  END IF;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION app.mark_successful_login(p_username TEXT) RETURNS VOID AS $$
DECLARE
  v_user_id BIGINT;
BEGIN
  SELECT user_id INTO v_user_id
  FROM app.users
  WHERE username = p_username AND is_active = TRUE;
  IF v_user_id IS NULL THEN
    RETURN;
  END IF;
  UPDATE app.user_credentials
  SET failed_attempts = 0,
      locked_until = NULL
  WHERE user_id = v_user_id;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION app.create_login_session(p_user_id BIGINT, p_token_hash TEXT, p_ttl_minutes INTEGER)
RETURNS BIGINT AS $$
DECLARE
  v_session_id BIGINT;
BEGIN
  INSERT INTO app.login_sessions(user_id, session_token_hash, expires_at)
  VALUES (p_user_id, p_token_hash, NOW() + (p_ttl_minutes || ' minutes')::interval)
  RETURNING session_id INTO v_session_id;
  RETURN v_session_id;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION app.revoke_session(p_token_hash TEXT) RETURNS VOID AS $$
BEGIN
  UPDATE app.login_sessions
  SET revoked_at = NOW()
  WHERE session_token_hash = p_token_hash;
END;
$$ LANGUAGE plpgsql;

