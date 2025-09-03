CREATE TABLE IF NOT EXISTS public.route_shapes (
  route_id     uuid NOT NULL REFERENCES public.routes(route_id) ON DELETE RESTRICT,
  shape_id     uuid NOT NULL REFERENCES public.shapes(shape_id) ON DELETE CASCADE,
  variant_code text NOT NULL DEFAULT 'default',
  is_default   boolean NOT NULL DEFAULT false,
  PRIMARY KEY (route_id, shape_id),
  CONSTRAINT route_shapes_variant_format_chk CHECK (variant_code ~ '^[a-z0-9_\-]{1,32}$')
);

CREATE INDEX IF NOT EXISTS route_shapes_route_idx ON public.route_shapes (route_id);
CREATE INDEX IF NOT EXISTS route_shapes_shape_idx ON public.route_shapes (shape_id);
