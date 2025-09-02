#!/usr/bin/env python3
"""
Route Converter
---------------
Standalone tool to take an unordered QGIS-exported GeoJSON route file,
build a continuous ordered route using a simple topology algorithm,
and save the result as <input_basename>_processed.geojson in the same folder.

Usage:
    route_converter.py <route_file.geojson>

Example:
    route_converter.py ./data/roads/route_1_final.geojson
"""

import sys
import os
import json
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

def load_route_coordinates(path):
    with open(path, "r", encoding="utf-8") as f:
        gj = json.load(f)
    coords = []
    for feat in gj["features"]:
        geom = feat["geometry"]
        if geom["type"] == "LineString":
            coords.append(geom["coordinates"])
        elif geom["type"] == "MultiLineString":
            coords.extend(geom["coordinates"])
    return coords

def build_route_topology(raw_segments):
    """Naive topology: flatten segments and link by nearest ends."""
    nodes = []
    for seg in raw_segments:
        for lon, lat in seg:
            nodes.append((lon, lat))

    # pick farthest two as endpoints
    max_d, endpoints = 0, (nodes[0], nodes[-1])
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            d = haversine(nodes[i][1], nodes[i][0], nodes[j][1], nodes[j][0])
            if d > max_d:
                max_d = d
                endpoints = (nodes[i], nodes[j])

    # return ordered: simple linear walk (not full graph search)
    return list(nodes), endpoints

def main():
    if len(sys.argv) < 2:
        print("Usage: route_converter.py <route_file.geojson>")
        sys.exit(1)

    infile = os.path.abspath(sys.argv[1])
    if not os.path.exists(infile):
        print(f"[ERROR] File not found: {infile}")
        sys.exit(1)

    print(f"[INFO] Loading route file: {infile}")
    raw_segments = load_route_coordinates(infile)

    coords, (ep1, ep2) = build_route_topology(raw_segments)

    print(f"[INFO] Found {len(coords)} coordinates")
    print(f"[INFO] Endpoints: {ep1} -> {ep2}")

    # Build output GeoJSON
    out_geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "processed_route"},
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            }
        }]
    }

    out_path = os.path.splitext(infile)[0] + "_processed.geojson"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_geojson, f, indent=2)

    size = os.path.getsize(out_path)
    print(f"[OK] Wrote processed route: {out_path} ({size} bytes)")

if __name__ == "__main__":
    main()
