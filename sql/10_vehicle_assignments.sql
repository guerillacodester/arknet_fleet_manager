CREATE TABLE IF NOT EXISTS public.vehicle_assignments (
  assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  duty_date     date NOT NULL,
  vehicle_id    uuid NOT NULL REFERENCES public.vehicles(vehicle_id) ON DELETE RESTRICT,
  block_id      uuid NOT NULL REFERENCES public.blocks(block_id)     ON DELETE RESTRICT,
  duty_part     text,                         -- e.g., 'A'/'B' for split shifts
  assigned_at   timestamptz NOT NULL DEFAULT now(),
  assigned_by   text,
  UNIQUE (duty_date, vehicle_id)
);
CREATE INDEX vehicle_assignments_date_idx    ON public.vehicle_assignments (duty_date);
CREATE INDEX vehicle_assignments_vehicle_idx ON public.vehicle_assignments (vehicle_id);
CREATE INDEX vehicle_assignments_block_idx   ON public.vehicle_assignments (block_id);
