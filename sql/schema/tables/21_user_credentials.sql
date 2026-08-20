CREATE TABLE app.user_credentials (
  credential_id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES app.users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
  password_hash TEXT NOT NULL,
  password_algorithm TEXT NOT NULL DEFAULT 'argon2id',
  password_last_changed_at TIMESTAMPTZ DEFAULT NOW(),
  failed_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
  locked_until TIMESTAMPTZ,
  must_change_password BOOLEAN DEFAULT FALSE,
  UNIQUE (user_id)
);

CREATE INDEX user_credentials_user_id_idx ON app.user_credentials (user_id);
CREATE INDEX user_credentials_locked_until_idx ON app.user_credentials (locked_until);

