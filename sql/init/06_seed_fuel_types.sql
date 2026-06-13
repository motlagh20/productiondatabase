INSERT INTO app.fuel_types (fuel_name)
VALUES ('Gas'), ('Diesel')
ON CONFLICT (fuel_name) DO NOTHING;

