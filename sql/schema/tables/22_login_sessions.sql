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

