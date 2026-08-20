-- Master script to run all mapping scripts in order

-- First, ensure the schema exists
\i 00_schema.sql

-- Run the mapping scripts in order
\i 03_map_categories.sql
\i 04_map_glazes.sql
\i 05_map_molds.sql

-- Refresh any views that depend on these tables
-- (Add REFRESH MATERIALIZED VIEW commands here if needed)