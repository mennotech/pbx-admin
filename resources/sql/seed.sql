INSERT OR IGNORE INTO servers (id, slug, display_name, upstream_base_url, enabled)
VALUES
  ('pbx-alpha', 'alpha', 'Alpha PBX', 'https://pbx-alpha.internal', 1),
  ('pbx-beta', 'beta', 'Beta PBX', 'https://pbx-beta.internal', 1);

-- Replace emails with your Access identities.
INSERT OR IGNORE INTO user_server_access (user_email, server_id, role)
VALUES
  ('admin@example.com', 'pbx-alpha', 'admin'),
  ('admin@example.com', 'pbx-beta', 'admin');
