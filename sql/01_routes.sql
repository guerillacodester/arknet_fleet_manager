CREATE TABLE IF NOT EXISTS public.routes (
  route_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_id   uuid NOT NULL REFERENCES public.countries(country_id) ON DELETE CASCADE,
  short_name   text NOT NULL,                -- '1','1A',...
  long_name    text,
  parishes     text,
  is_active    boolean NOT NULL DEFAULT true,
  valid_from   date DEFAULT CURRENT_DATE,
  valid_to     date,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT routes_short_name_format_chk CHECK (short_name ~ '^[0-9]{1,2}[A-Z]?$')
);

-- Ensure route short_names are unique *within a country*
CREATE UNIQUE INDEX IF NOT EXISTS routes_country_short_name_uidx
  ON public.routes (country_id, short_name);
