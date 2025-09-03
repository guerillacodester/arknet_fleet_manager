CREATE TABLE public.stops (
  stop_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code         text UNIQUE,           -- e.g. "ZR1001A"
  name         text NOT NULL,         -- passenger-friendly stop name
  lat          numeric NOT NULL,
  lon          numeric NOT NULL,
  location_type smallint DEFAULT 0,   -- 0=stop, 1=station, 2=entrance
  parent_station uuid REFERENCES public.stops(stop_id),
  zone_id      text,
  created_at   timestamptz DEFAULT now()
);
