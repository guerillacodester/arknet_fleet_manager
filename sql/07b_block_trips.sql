CREATE TABLE IF NOT EXISTS public.block_trips (
  block_id   uuid NOT NULL REFERENCES public.blocks(block_id) ON DELETE CASCADE,
  trip_id    uuid NOT NULL REFERENCES public.trips(trip_id)  ON DELETE CASCADE,
  sequence   integer NOT NULL,
  layover_minutes integer DEFAULT 0 CHECK (layover_minutes BETWEEN 0 AND 120),
  PRIMARY KEY (block_id, sequence)
);
