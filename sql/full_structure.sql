-- ================================
-- ArkNet Transit Master Schema
-- ================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ================================
-- ENUMS
-- ================================
CREATE TYPE vehicle_status AS ENUM (
  'available',
  'in_service',
  'maintenance',
  'retired'
);

-- ================================
-- COUNTRIES
-- ================================
CREATE TABLE countries (
  country_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  iso_code   text NOT NULL UNIQUE,
  name       text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ================================
-- ROUTES
-- ================================
CREATE TABLE routes (
  route_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_id uuid NOT NULL REFERENCES countries(country_id) ON DELETE CASCADE,
  short_name text NOT NULL,
  long_name  text,
  parishes   text,
  is_active  boolean NOT NULL DEFAULT true,
  valid_from date DEFAULT CURRENT_DATE,
  valid_to   date,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT routes_short_name_format_chk CHECK (short_name ~ '^[0-9]{1,2}[A-Z]?$')
);

CREATE UNIQUE INDEX routes_country_short_name_uidx
  ON routes (country_id, short_name);

-- ================================
-- SHAPES
-- ================================
CREATE TABLE shapes (
  shape_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  geom geometry(Linestring, 4326) NOT NULL
);

-- ================================
-- ROUTE_SHAPES
-- ================================
CREATE TABLE route_shapes (
  route_id   uuid NOT NULL REFERENCES routes(route_id) ON DELETE CASCADE,
  shape_id   uuid NOT NULL REFERENCES shapes(shape_id) ON DELETE CASCADE,
  variant_code text,
  is_default boolean NOT NULL DEFAULT false,
  PRIMARY KEY (route_id, shape_id)
);

-- ================================
-- SERVICES (calendar)
-- ================================
CREATE TABLE services (
  service_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_id uuid NOT NULL REFERENCES countries(country_id) ON DELETE CASCADE,
  name       text NOT NULL,
  mon boolean NOT NULL DEFAULT false,
  tue boolean NOT NULL DEFAULT false,
  wed boolean NOT NULL DEFAULT false,
  thu boolean NOT NULL DEFAULT false,
  fri boolean NOT NULL DEFAULT false,
  sat boolean NOT NULL DEFAULT false,
  sun boolean NOT NULL DEFAULT false,
  date_start date NOT NULL,
  date_end   date NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- ================================
-- FREQUENCIES
-- ================================
CREATE TABLE frequencies (
  frequency_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  service_id   uuid NOT NULL REFERENCES services(service_id) ON DELETE CASCADE,
  route_id     uuid NOT NULL REFERENCES routes(route_id) ON DELETE CASCADE,
  start_time   time NOT NULL,
  end_time     time NOT NULL,
  headway_s    integer NOT NULL CHECK (headway_s > 0)
);

-- ================================
-- BLOCKS (shifts)
-- ================================
CREATE TABLE blocks (
  block_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_id  uuid NOT NULL REFERENCES countries(country_id) ON DELETE CASCADE,
  route_id    uuid NOT NULL REFERENCES routes(route_id) ON DELETE CASCADE,
  service_id  uuid NOT NULL REFERENCES services(service_id) ON DELETE CASCADE,
  start_time  time NOT NULL,
  end_time    time NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- ================================
-- TRIPS
-- ================================
CREATE TABLE trips (
  trip_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  route_id   uuid NOT NULL REFERENCES routes(route_id) ON DELETE CASCADE,
  service_id uuid NOT NULL REFERENCES services(service_id) ON DELETE CASCADE,
  shape_id   uuid REFERENCES shapes(shape_id) ON DELETE SET NULL,
  trip_headsign text,
  direction_id  smallint CHECK (direction_id IN (0, 1)),
  block_id   uuid REFERENCES blocks(block_id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ================================
-- BLOCK_TRIPS
-- ================================
CREATE TABLE block_trips (
  block_id  uuid NOT NULL REFERENCES blocks(block_id) ON DELETE CASCADE,
  trip_id   uuid NOT NULL REFERENCES trips(trip_id) ON DELETE CASCADE,
  layover_minutes integer DEFAULT 0,
  PRIMARY KEY (block_id, trip_id)
);

-- ================================
-- BLOCK_BREAKS
-- ================================
CREATE TABLE block_breaks (
  break_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  block_id     uuid NOT NULL REFERENCES blocks(block_id) ON DELETE CASCADE,
  break_start  time NOT NULL,
  break_end    time NOT NULL,
  break_duration integer NOT NULL CHECK (break_duration > 0)
);

-- ================================
-- DEPOTS
-- ================================
CREATE TABLE depots (
  depot_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_id uuid NOT NULL REFERENCES countries(country_id) ON DELETE CASCADE,
  name       text NOT NULL,
  location   geometry(Point, 4326),
  capacity   integer CHECK (capacity IS NULL OR capacity >= 0),
  notes      text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX depots_country_name_uidx
  ON depots (country_id, name);

CREATE INDEX depots_loc_gix
  ON depots USING GIST (location);

-- ================================
-- VEHICLES
-- ================================
CREATE TABLE vehicles (
  vehicle_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_id         uuid NOT NULL REFERENCES countries(country_id) ON DELETE CASCADE,
  reg_code           text NOT NULL,
  home_depot_id      uuid REFERENCES depots(depot_id) ON DELETE SET NULL,
  preferred_route_id uuid REFERENCES routes(route_id) ON DELETE SET NULL,
  status             vehicle_status NOT NULL DEFAULT 'available',
  profile_id         text,
  notes              text,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT vehicles_reg_code_format_chk CHECK (reg_code ~ '^ZR[0-9]{2,3}$')
);

CREATE UNIQUE INDEX vehicles_country_reg_code_uidx
  ON vehicles (country_id, reg_code);

-- ================================
-- VEHICLE_ASSIGNMENTS
-- ================================
CREATE TABLE vehicle_assignments (
  assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id    uuid NOT NULL REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
  block_id      uuid NOT NULL REFERENCES blocks(block_id) ON DELETE CASCADE,
  assigned_at   timestamptz NOT NULL DEFAULT now()
);

-- ================================
-- VEHICLE_STATUS_EVENTS
-- ================================
CREATE TABLE vehicle_status_events (
  event_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  vehicle_id uuid NOT NULL REFERENCES vehicles(vehicle_id) ON DELETE CASCADE,
  status     vehicle_status NOT NULL,
  event_time timestamptz NOT NULL DEFAULT now(),
  notes      text
);

-- ================================
-- STOPS
-- ================================
CREATE TABLE stops (
  stop_id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_id uuid NOT NULL REFERENCES countries(country_id) ON DELETE CASCADE,
  code       text,
  name       text NOT NULL,
  location   geometry(Point, 4326) NOT NULL,
  zone_id    text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX stops_loc_gix
  ON stops USING GIST (location);

-- ================================
-- STOP_TIMES
-- ================================
CREATE TABLE stop_times (
  trip_id     uuid NOT NULL REFERENCES trips(trip_id) ON DELETE CASCADE,
  stop_id     uuid NOT NULL REFERENCES stops(stop_id) ON DELETE CASCADE,
  arrival_time time NOT NULL,
  departure_time time NOT NULL,
  stop_sequence integer NOT NULL,
  PRIMARY KEY (trip_id, stop_id, stop_sequence)
);

-- ================================
-- DRIVERS
-- ================================
CREATE TABLE drivers (
  driver_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  country_id  uuid NOT NULL REFERENCES countries(country_id) ON DELETE CASCADE,
  name        text NOT NULL,
  license_no  text UNIQUE NOT NULL,
  home_depot_id uuid REFERENCES depots(depot_id) ON DELETE SET NULL,
  employment_status text NOT NULL DEFAULT 'active',
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- ================================
-- DRIVER_ASSIGNMENTS
-- ================================
CREATE TABLE driver_assignments (
  assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  driver_id     uuid NOT NULL REFERENCES drivers(driver_id) ON DELETE CASCADE,
  block_id      uuid NOT NULL REFERENCES blocks(block_id) ON DELETE CASCADE,
  assigned_at   timestamptz NOT NULL DEFAULT now()
);

-- ================================
-- VIEWS
-- ================================
CREATE VIEW block_summary AS
SELECT b.block_id,
       b.start_time,
       b.end_time,
       SUM(bt.layover_minutes) AS total_layovers,
       SUM(bb.break_duration)  AS total_breaks
FROM blocks b
LEFT JOIN block_trips bt ON b.block_id = bt.block_id
LEFT JOIN block_breaks bb ON b.block_id = bb.block_id
GROUP BY b.block_id, b.start_time, b.end_time;
