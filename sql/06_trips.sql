CREATE TABLE IF NOT EXISTS public.trips (
  trip_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  route_id      uuid NOT NULL REFERENCES public.routes(route_id)     ON DELETE RESTRICT,
  service_id    uuid NOT NULL REFERENCES public.services(service_id) ON DELETE RESTRICT,
  shape_id      uuid NOT NULL REFERENCES public.shapes(shape_id)     ON DELETE RESTRICT,
  start_time    time NOT NULL,
  runtime_s     integer NOT NULL CHECK (runtime_s BETWEEN 60 AND 28800), -- 1 min to 8 hrs
  recovery_s    integer NOT NULL DEFAULT 0 CHECK (recovery_s BETWEEN 0 AND 3600),
  direction_id  smallint,              -- optional: 0 or 1 for direction
  trip_sequence integer,                -- ordering if needed
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS trips_route_idx       ON public.trips (route_id);
CREATE INDEX IF NOT EXISTS trips_service_idx     ON public.trips (service_id);
CREATE INDEX IF NOT EXISTS trips_shape_idx       ON public.trips (shape_id);
CREATE INDEX IF NOT EXISTS trips_start_time_idx  ON public.trips (start_time);
