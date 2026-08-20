INSERT INTO app.shifts_definition (shift_code, shift_name, start_time, end_time)
VALUES
  (1, 'صبح', '06:00', '14:00'),
  (2, 'عصر', '14:00', '22:00'),
  (3, 'شب',  '22:00', '06:00')
ON CONFLICT DO NOTHING;

