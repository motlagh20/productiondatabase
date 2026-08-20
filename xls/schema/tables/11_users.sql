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

