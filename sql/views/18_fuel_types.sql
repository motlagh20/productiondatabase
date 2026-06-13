CREATE VIEW app.fuel_types_view AS
SELECT fuel_type_id, fuel_name
FROM app.fuel_types
WHERE is_active = TRUE
ORDER BY fuel_name;

