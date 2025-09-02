#!/usr/bin/env python3
"""
geo_math.py
-----------
Math and geodesy helpers.
"""

from __future__ import annotations
import math
from typing import Iterable, Tuple, List


class GeoMath:
    """Geodesy utilities."""

    R_KM: float = 6371.0  # Earth radius (km)

    @staticmethod
    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Great-circle distance in kilometers between two lat/lon points.
        """
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlmb = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
        return GeoMath.R_KM * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

    @staticmethod
    def centroid(lonlat: Iterable[Tuple[float, float]]) -> Tuple[float, float]:
        """
        Arithmetic centroid of (lon, lat) iterable -> (lat, lon).
        """
        pts: List[Tuple[float, float]] = list(lonlat)
        if not pts:
            return (0.0, 0.0)
        sum_lon = sum(p[0] for p in pts)
        sum_lat = sum(p[1] for p in pts)
        return (sum_lat / len(pts), sum_lon / len(pts))
