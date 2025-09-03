CREATE TABLE IF NOT EXISTS public.block_breaks (
  block_id     uuid NOT NULL REFERENCES public.blocks(block_id) ON DELETE CASCADE,
  break_start  time NOT NULL,
  break_duration integer NOT NULL CHECK (break_duration BETWEEN 5 AND 120),
  reason       text,
  PRIMARY KEY (block_id, break_start)
);
