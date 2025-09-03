CREATE TABLE public.stop_times (
  trip_id     uuid NOT NULL REFERENCES public.trips(trip_id) ON DELETE CASCADE,
  stop_id     uuid NOT NULL REFERENCES public.stops(stop_id) ON DELETE RESTRICT,
  stop_sequence integer NOT NULL,          -- order along the trip
  arrival_time interval NOT NULL,          -- offset from trip start
  departure_time interval NOT NULL,        -- offset from trip start
  timepoint smallint DEFAULT 1,            -- 1=fixed, 0=approx
  PRIMARY KEY (trip_id, stop_sequence)
);
