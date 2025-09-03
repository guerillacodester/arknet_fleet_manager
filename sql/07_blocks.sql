CREATE TABLE IF NOT EXISTS public.blocks (
  block_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_id    uuid NOT NULL REFERENCES public.countries(country_id) ON DELETE CASCADE,
  route_id      uuid NOT NULL REFERENCES public.routes(route_id)     ON DELETE RESTRICT,
  service_id    uuid NOT NULL REFERENCES public.services(service_id) ON DELETE RESTRICT,
  start_time    time NOT NULL,
  end_time      time NOT NULL,
  break_minutes integer NOT NULL DEFAULT 0 CHECK (break_minutes BETWEEN 0 AND 180),
  notes         text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT blocks_time_range_chk CHECK (end_time > start_time),
  CONSTRAINT blocks_duration_chk CHECK (
    EXTRACT(EPOCH FROM (end_time - start_time)) BETWEEN 60 AND 43200
  ) -- max 12 hours
);

CREATE INDEX IF NOT EXISTS blocks_country_idx    ON public.blocks (country_id);
CREATE INDEX IF NOT EXISTS blocks_route_idx      ON public.blocks (route_id);
CREATE INDEX IF NOT EXISTS blocks_service_idx    ON public.blocks (service_id);
CREATE INDEX IF NOT EXISTS blocks_start_time_idx ON public.blocks (start_time);
