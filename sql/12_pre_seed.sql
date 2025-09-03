-- Unique indexes are enough for ON CONFLICT
CREATE UNIQUE INDEX IF NOT EXISTS routes_short_name_uidx   ON public.routes(short_name);
CREATE UNIQUE INDEX IF NOT EXISTS services_name_uidx       ON public.services(name);
CREATE UNIQUE INDEX IF NOT EXISTS depots_name_uidx         ON public.depots(name);

-- Optionally bind them as named constraints (nice for consistency)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='routes_short_name_uq') THEN
    ALTER TABLE public.routes ADD CONSTRAINT routes_short_name_uq UNIQUE USING INDEX routes_short_name_uidx;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='services_name_uq') THEN
    ALTER TABLE public.services ADD CONSTRAINT services_name_uq UNIQUE USING INDEX services_name_uidx;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='depots_name_uq') THEN
    ALTER TABLE public.depots ADD CONSTRAINT depots_name_uq UNIQUE USING INDEX depots_name_uidx;
  END IF;
END$$;
