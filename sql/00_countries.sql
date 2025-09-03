CREATE TABLE countries (
    country_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    iso_code   text NOT NULL UNIQUE,   -- e.g. 'BB', 'JM', 'TT'
    name       text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
