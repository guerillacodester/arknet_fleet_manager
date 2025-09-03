#!/usr/bin/env python3
"""
Route Visualizer (Folium)
-------------------------
Standalone tool to visualize GeoJSON route files with folium.
- Plots route polyline(s) + points in separate overlays
- Hover + cursor to inspect points
- Checkbox to hide/show basemap
- Cleans up generated HTML (lang, title, charset, viewport)

Usage:
    python route_visualizer.py path/to/route.geojson
"""

import sys
import os
import json
import re
import folium
from folium.plugins import MousePosition


def visualize_route(path: str):
    if not os.path.isfile(path):
        print(f"[ERROR] File not found: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Collect route segments (avoid flattening into one list!)
    segments = []
    for feature in data.get("features", []):
        geom = feature.get("geometry", {})
        if geom.get("type") == "LineString":
            segments.append(geom.get("coordinates", []))
        elif geom.get("type") == "MultiLineString":
            segments.extend(geom.get("coordinates", []))

    if not segments:
        print("[ERROR] No coordinates found in file.")
        sys.exit(1)

    # Flatten all coords to compute map center
    all_coords = [pt for seg in segments for pt in seg]
    avg_lat = sum(lat for lon, lat in all_coords) / len(all_coords)
    avg_lon = sum(lon for lon, lat in all_coords) / len(all_coords)

    # Map with no default tiles
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=14, tiles=None)

    # Base layers
    folium.TileLayer("OpenStreetMap", name="Basemap", control=True).add_to(m)
    folium.TileLayer(tiles="", name="No basemap", attr="No basemap", control=True).add_to(m)

    # Overlay groups
    fg_line = folium.FeatureGroup(name="Route", show=True)
    fg_pts = folium.FeatureGroup(name="All stops", show=True)

    # Draw each segment separately
    for seg in segments:
        # Polyline (swap order → Folium wants (lat, lon))
        folium.PolyLine(
            [(lat, lon) for (lon, lat) in seg],
            color="blue", weight=3, opacity=0.7
        ).add_to(fg_line)

        # Points
        for i, (lon, lat) in enumerate(seg):
            folium.CircleMarker(
                location=[lat, lon],
                radius=3, color="red",
                fill=True, fill_opacity=0.8,
                popup=f"Lat={lat:.6f}<br>Lon={lon:.6f}"
            ).add_to(fg_pts)

    fg_line.add_to(m)
    fg_pts.add_to(m)

    # Mouse tracker
    MousePosition(
        position="bottomright",
        separator=" | ",
        prefix="Coordinates:",
        lat_formatter="function(num) {return L.Util.formatNum(num, 6);}",
        lng_formatter="function(num) {return L.Util.formatNum(num, 6);}",
    ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Save map
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "route_visualizer_map.html")
    m.save(out_path)

    # Clean HTML
    clean_html(out_path, title="Route Visualization")

    print(f"[INFO] Map saved to: {out_path}")
    print("[INFO] Open it in your browser to interact.")


def clean_html(path: str, title: str = "Route Map") -> None:
    """Post-process the HTML to fix common validator warnings."""
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    # Ensure <html lang="en">
    if not re.search(r'<html[^>]*\blang\s*=', html, flags=re.IGNORECASE):
        html = re.sub(r'<html([^>]*)>', r'<html\1 lang="en">', html, count=1, flags=re.IGNORECASE)

    # Ensure <title>
    if not re.search(r'<title>.*?</title>', html, flags=re.IGNORECASE | re.DOTALL):
        html = re.sub(r'<head[^>]*>', f'<head>\n<title>{title}</title>', html, count=1, flags=re.IGNORECASE)

    # Normalize charset
    html = re.sub(
        r'<meta[^>]*http-equiv\s*=\s*["\']content-type["\'][^>]*>',
        '<meta charset="utf-8">',
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'<meta\s+charset\s*=\s*["\'][^"\']*["\']\s*/?>',
        '<meta charset="utf-8">',
        html,
        flags=re.IGNORECASE,
    )

    # Fix viewport (remove user-scalable & maximum-scale)
    def _fix_viewport(tag_html: str) -> str:
        m = re.search(r'content\s*=\s*["\'](.*?)["\']', tag_html, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return tag_html
        content = m.group(1)
        parts = [p.strip() for p in re.split(r'\s*,\s*', content.replace('\n', ' '))]
        keep = [p for p in parts if not re.match(r'(?i)(user\s*-\s*scalable|max\s*-\s*scale)\s*=', p)]
        new_content = ', '.join(keep)
        start, end = m.span(1)
        return tag_html[:start] + new_content + tag_html[end:]

    html = re.sub(
        r'<meta\s+[^>]*name\s*=\s*["\']viewport["\'][^>]*\/?>',
        lambda m: _fix_viewport(m.group(0)),
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python route_visualizer.py path/to/route.geojson")
        sys.exit(1)

    visualize_route(sys.argv[1])
