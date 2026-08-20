CREATE VIEW app.shift_options AS
SELECT shift_id, shift_code, shift_name
FROM app.shifts_definition
WHERE is_active = TRUE
ORDER BY shift_code;

