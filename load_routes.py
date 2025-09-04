"""
load_routes.py
--------------
Helpers to load route data from CSV or GeoJSON for seeding.
"""

import csv
import json
from typing import List, Dict, Any
from shapely.geometry import shape


def load_routes_from_csv(path: str) -> List[Dict[str, Any]]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                "country_id": row.get("country_id"),
                "short_name": row.get("short_name"),
                "long_name": row.get("long_name"),
                "parishes": row.get("parishes"),
                "is_active": row.get("is_active", "true").lower() in ("true", "1", "yes", "y"),
                "valid_from": row.get("valid_from"),
                "valid_to": row.get("valid_to"),
            })
    return records


import json
from shapely.geometry import shape

def load_routes_from_geojson(path: str, target_short_name: str | None = None):
    """
    Load shapes from a GeoJSON file.

    Behaviour:
    - If features contain properties.short_name: filter by target_short_name (case-insensitive).
    - If features DO NOT contain short_name: treat the file as a single-route file and
      return ALL LineString/MultiLineString geometries, assigning short_name = target_short_name.
    - Accepts LineString and MultiLineString only.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    # Detect whether the file carries short_name metadata at all
    has_short_name = any("short_name" in (feat.get("properties") or {}) for feat in features)

    records = []
    for feat in features:
        props = feat.get("properties") or {}
        geom = shape(feat.get("geometry"))

        if geom.geom_type not in ("LineString", "MultiLineString"):
            # ignore non-path geometry
            continue

        short = props.get("short_name")
        # Filtering logic
        if target_short_name:
            if has_short_name:
                # File has explicit short_name per feature: match it
                if not short:
                    continue
                if str(short).upper() != str(target_short_name).upper():
                    continue
            else:
                # File has NO short_name anywhere: treat all features as the target route
                short = target_short_name

        rec = {
            "short_name": str(short) if short is not None else None,
            "geom": geom.wkt,  # WKT for insertion into PostGIS
            # Optional props if present (harmless if missing)
            "variant_code": props.get("variant_code") or props.get("variant"),
            "is_default": bool(props.get("is_default", False)),
            "long_name": props.get("long_name"),
            "parishes": props.get("parishes"),
            "is_active": props.get("is_active", True),
            "valid_from": props.get("valid_from"),
            "valid_to": props.get("valid_to"),
        }
        records.append(rec)

    return records

