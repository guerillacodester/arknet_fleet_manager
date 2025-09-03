CREATE TABLE public.drivers (
  driver_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  staff_code  text UNIQUE NOT NULL,     -- e.g. employee number
  full_name   text NOT NULL,
  home_depot_id uuid REFERENCES public.depots(depot_id),
  license_expiry date,
  status      text CHECK (status IN ('active','leave','retired')),
  created_at  timestamptz DEFAULT now()
);
