CREATE TABLE IF NOT EXISTS public.depots (
  depot_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_id  uuid NOT NULL REFERENCES public.countries(country_id) ON DELETE CASCADE,
  name        text NOT NULL,
  location    geometry(POINT, 32620),   -- optional map location
  capacity    integer CHECK (capacity IS NULL OR capacity >= 0),
  notes       text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Unique depot names per country
CREATE UNIQUE INDEX IF NOT EXISTS depots_country_name_uidx
  ON public.depots (country_id, name);

CREATE INDEX IF NOT EXISTS
