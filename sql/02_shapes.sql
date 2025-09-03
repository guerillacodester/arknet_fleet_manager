CREATE TABLE IF NOT EXISTS public.shapes (
  shape_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  geom       geometry(LINESTRING, 4326) NOT NULL,  -- WGS84, exact lon/lat as given
  -- length in metres, calculated by transforming to UTM zone 20N
  length_m   double precision GENERATED ALWAYS AS (
    ST_Length(ST_Transform(geom, 32620))
  ) STORED,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS shapes_gix ON public.shapes USING GIST (geom);
