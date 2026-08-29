-- 36_glaze.sql
-- Glaze dimension master (clean app core, ADR-0008).
-- A glaze is a named finish applied at Setting; it needs its own table with a
-- dedicated code, name, and formula/description (owner requirement 2026-08-29).
-- Replaces the legacy `glazes` scratch table (glaze_value/normalized/is_combined).

CREATE TABLE IF NOT EXISTS glaze (
    glaze_id      BIGSERIAL PRIMARY KEY,
    glaze_code    VARCHAR(20) NOT NULL UNIQUE,   -- short internal code, e.g. 'LAAB', 'AKHRA', 'MESHKII'
    glaze_name    VARCHAR(100) NOT NULL,          -- display name, e.g. 'لعاب سبز', 'اخرا'
    formula       TEXT,                            -- composition / formula (optional)
    description   TEXT,                            -- free-text notes
    is_combined   BOOLEAN NOT NULL DEFAULT FALSE, -- e.g. مولتی مشکی = combined finish
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_glaze_name ON glaze(glaze_name);

-- Seed with the distinct glazes observed in the historical Setting data, assigning
-- stable codes. Operator typos in the source (??, 20:45, س) are NOT seeded — they
-- belong to the ETL review layer (ADR-0008), not the clean master.
INSERT INTO glaze(glaze_code, glaze_name, is_combined, description) VALUES
    ('KHODRANG', 'خودرنگ', FALSE, 'بدون لعاب / رنگ طبیعی بدنه'),
    ('LAAB',     'لعاب',   FALSE, 'لعاب معمولی'),
    ('AKHRA',    'اخرا',   FALSE, 'لعاب اخرا (مترادف: اخراء)'),
    ('LAAB_SABZ','لعاب سبز', FALSE, 'لعاب سبز'),
    ('LAAB_MESHKI','لعاب مشکی', FALSE, 'لعاب مشکی'),
    ('MULTI_MESHKI','مولتی مشکی', TRUE, 'لعاب ترکیبی مشکی'),
    ('KOLAHK',   'کلاهک',  FALSE, 'کلاهک')
ON CONFLICT (glaze_code) DO NOTHING;
