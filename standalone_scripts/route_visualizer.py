#!/usr/bin/env python3
"""
Route Visualizer (Folium)
-------------------------
Standalone tool to visualize GeoJSON route files with folium.
- Plots route points without unwanted lines
- Hover + cursor to inspect points
- Checkbox to hide/show basemap

Usage:
    python route_visualizer.py path/to/route.geojson
"""

import sys
import os
import json
import folium
from folium.plugins import MousePosition


def visualize_route(path: str):
    if not os.path.isfile(path):
        print(f"[ERROR] File not found: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    coords = []
    for feature in data.get("features", []):
        geom = feature.get("geometry", {})
        if geom.get("type") == "LineString":
            coords.extend(geom.get("coordinates", []))
        elif geom.get("type") == "MultiLineString":
            for seg in geom.get("coordinates", []):
                coords.extend(seg)

    if not coords:
        print("[ERROR] No coordinates found in file.")
        sys.exit(1)

    # Center map
    avg_lat = sum(lat for lon, lat in coords) / len(coords)
    avg_lon = sum(lon for lon, lat in coords) / len(coords)

    # Map with no default tiles
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=14, tiles=None)

    # Add toggleable basemap
    folium.TileLayer("OpenStreetMap", name="Basemap").add_to(m)
    # "No basemap" → empty transparent tile source
    folium.TileLayer(
        tiles="",
        name="No basemap",
        attr="No basemap"
    ).add_to(m)

    # Add route points (no lines)
    for i, (lon, lat) in enumerate(coords):
        folium.CircleMarker(
            location=[lat, lon],
            radius=3,
            color="red",
            fill=True,
            fill_opacity=0.8,
            popup=f"Point {i}<br>Lat={lat:.6f}<br>Lon={lon:.6f}"
        ).add_to(m)

    # Add mouse position tracker
    MousePosition(
        position="bottomright",
        separator=" | ",
        prefix="Coordinates:",
        lat_formatter="function(num) {return L.Util.formatNum(num, 6);}",
        lng_formatter="function(num) {return L.Util.formatNum(num, 6);}",
    ).add_to(m)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    # Save to script directory
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "route_visualizer_map.html")
    m.save(out_path)

    print(f"[INFO] Map saved to: {out_path}")
    print("[INFO] Open it in your browser to interact.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python route_visualizer.py path/to/route.geojson")
        sys.exit(1)

    visualize_route(sys.argv[1])
