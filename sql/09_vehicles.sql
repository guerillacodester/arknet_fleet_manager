CREATE TABLE IF NOT EXISTS public.vehicles (
  vehicle_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_id         uuid NOT NULL REFERENCES public.countries(country_id) ON DELETE CASCADE,
  reg_code           text NOT NULL,                      -- e.g., 'ZR101', 'ZR1001'
  home_depot_id      uuid REFERENCES public.depots(depot_id)    ON DELETE SET NULL,
  preferred_route_id uuid REFERENCES public.routes(route_id)    ON DELETE SET NULL,
  status             vehicle_status NOT NULL DEFAULT 'available',
  profile_id         text,                                      -- simulator profile key (optional)
  notes              text,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT vehicles_reg_code_format_chk CHECK (reg_code ~ '^ZR[0-9]{2,3}$')
);

-- Unique vehicle reg_code per country
CREATE UNIQUE INDEX IF NOT EXISTS vehicles_country_reg_code_uidx
  ON public.vehicles (country_id, reg_code);
