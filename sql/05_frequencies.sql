CREATE TABLE IF NOT EXISTS public.frequencies (
  service_id   uuid NOT NULL REFERENCES public.services(service_id) ON DELETE CASCADE,
  route_id     uuid NOT NULL REFERENCES public.routes(route_id)   ON DELETE RESTRICT,
  start_time   time NOT NULL,
  end_time     time NOT NULL,
  headway_s    integer NOT NULL,                   -- seconds between buses
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (service_id, route_id, start_time),
  CONSTRAINT frequencies_time_range_chk CHECK (end_time > start_time),
  CONSTRAINT frequencies_headway_bounds_chk CHECK (headway_s BETWEEN 60 AND 7200)
);

CREATE INDEX IF NOT EXISTS frequencies_route_idx   ON public.frequencies (route_id);
CREATE INDEX IF NOT EXISTS frequencies_service_idx ON public.frequencies (service_id);
