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


def load_routes_from_geojson(path: str, target_short_name: str = None):
    """
    Load shapes from a GeoJSON file.
    If target_short_name is provided, filter by route short_name property.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = shape(feature["geometry"]).wkt  # store as WKT
        short_name = props.get("short_name")

        if target_short_name and short_name != target_short_name:
            continue

        records.append({
            "short_name": short_name,
            "geom": geom,
            "is_default": props.get("is_default", False),
        })
    return records
