"""
help_routes.py
--------------
Provides CLI help menu for seed_routes.py
"""

def print_help():
    print("""
ArkNet Transit – Route Seeder
-----------------------------
Seeds the 'routes', 'shapes', and 'route_shapes' tables
from interactive prompts, CSV, or GeoJSON sources.

Usage:
  ./seed_routes.py [options]

Options:
  -h, --help       Show this help menu
  --csv            Batch import routes from CSV (path set in config.ini)
  --geojson        Batch import route shapes from GeoJSON (path set in config.ini)

Interactive mode (default):
  1. Select a country (must already be seeded in DB)
  2. Enter route details:
       - short_name (e.g., 1, 5A, 10B)
       - long_name (optional)
       - parishes served (optional, comma-separated)
       - active flag (default true)
       - validity dates (from / to)
  3. Optionally import geometry for this route from GeoJSON
  4. Confirm summary before commit
  5. Insert into DB and generate routes.sql

CSV mode:
  - Reads from path specified in [routes] section of config.ini
  - CSV must include headers:
      country_id, short_name, long_name, parishes,
      is_active, valid_from, valid_to

GeoJSON mode:
  - Reads from path specified in [routes] section of config.ini
  - GeoJSON must be a FeatureCollection where each Feature has:
      geometry: LineString (SRID 4326)
      properties.short_name (matches routes.short_name)
      properties.is_default (optional boolean)

Examples:
  ./seed_routes.py               # interactive seeding
  ./seed_routes.py --csv         # batch seed from CSV
  ./seed_routes.py --geojson     # batch import shapes from GeoJSON
""")
