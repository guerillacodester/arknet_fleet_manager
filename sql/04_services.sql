CREATE TABLE IF NOT EXISTS public.services (
  service_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_id   uuid NOT NULL REFERENCES public.countries(country_id) ON DELETE CASCADE,
  name         text NOT NULL,               -- 'Weekday','Saturday','Sunday'
  mon          boolean NOT NULL,
  tue          boolean NOT NULL,
  wed          boolean NOT NULL,
  thu          boolean NOT NULL,
  fri          boolean NOT NULL,
  sat          boolean NOT NULL,
  sun          boolean NOT NULL,
  date_start   date NOT NULL,
  date_end     date NOT NULL,
  is_current   boolean NOT NULL DEFAULT true,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT services_date_range_chk CHECK (date_end >= date_start)
);

-- Ensure service names are unique *within a country*
CREATE UNIQUE INDEX IF NOT EXISTS services_country_name_uidx
  ON public.services (country_id, name);
