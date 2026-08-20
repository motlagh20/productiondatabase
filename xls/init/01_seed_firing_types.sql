INSERT INTO app.firing_types (firing_type_id, firing_name, description)
VALUES
  (1, 'Single-Fired', 'پخت یک‌باره'),
  (2, 'Double-Fired', 'پخت دوباره')
ON CONFLICT DO NOTHING;

SELECT setval(
  pg_get_serial_sequence('app.firing_types','firing_type_id'),
  (SELECT COALESCE(MAX(firing_type_id),1) FROM app.firing_types)
);

