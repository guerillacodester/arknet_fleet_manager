#!/usr/bin/env python3
"""
load_geojson.py
---------------
Utility for loading GeoJSON data.
"""

import json
from typing import Any, Dict


def load_geojson(path: str) -> Dict[str, Any]:
    """
    Load a GeoJSON file from disk and return the parsed JSON object.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
