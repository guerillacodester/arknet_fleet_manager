CREATE TABLE IF NOT EXISTS public.vehicle_status_events (
  event_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id   uuid NOT NULL REFERENCES public.vehicles(vehicle_id) ON DELETE CASCADE,
  status       vehicle_status NOT NULL,
  at_time      timestamptz NOT NULL DEFAULT now(),
  reason       text,
  odometer_km  numeric,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS vstatus_vehicle_idx 
  ON public.vehicle_status_events (vehicle_id, at_time DESC);
