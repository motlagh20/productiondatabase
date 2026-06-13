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

