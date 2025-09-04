#!/usr/bin/env python3
"""
visualization.py
----------------
Interactive map generation (Folium) + post-generation HTML cleanup.
"""

from __future__ import annotations
from typing import List, Tuple
import re
import json
from geo_math import GeoMath

LonLat = Tuple[float, float]


class RouteMap:
    """Create and sanitize interactive HTML maps."""

    def __init__(self, route_id: str = "route"):
        self.route_id = route_id

    def generate(self, geojson_path: str, out_html: str) -> None:
        """
        Create Folium map with:
          - Base layers: Basemap (default) / No basemap (toggle)
          - Overlays: Route segments (blue polylines), All vertices (red points)
        """
        import folium
        from folium.plugins import MousePosition

        # Load GeoJSON
        with open(geojson_path, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)

        features = geojson_data.get("features", [])
        if not features:
            return

        # Compute centroid from all coordinates
        all_coords: List[LonLat] = []
        for feat in features:
            geom = feat.get("geometry", {})
            if geom.get("type") == "LineString":
                all_coords.extend(geom.get("coordinates", []))

        lat_c, lon_c = GeoMath.centroid(all_coords)

        # Base map
        m = folium.Map(location=[lat_c, lon_c], zoom_start=14, tiles=None)

        # Basemap ON by default
        folium.TileLayer("OpenStreetMap", name="Basemap", control=True, show=True).add_to(m)

        # No basemap OFF by default
        folium.TileLayer(tiles="", name="No basemap", attr="No basemap", control=True, show=False).add_to(m)

        # Overlays
        fg_line = folium.FeatureGroup(name="Route", show=True)
        fg_pts = folium.FeatureGroup(name="All points", show=True)

        # Draw each LineString separately
        for feat in features:
            geom = feat.get("geometry", {})
            if geom.get("type") == "LineString":
                coords = geom.get("coordinates", [])

                # Polyline (blue)
                folium.PolyLine(
                    [(lat, lon) for lon, lat in coords],
                    color="blue",
                    weight=3,
                    opacity=0.7,
                    popup=f"Route {self.route_id}",
                ).add_to(fg_line)

                # Points (red)
                for i, (lon, lat) in enumerate(coords):
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=3,
                        color="red",
                        fill=True,
                        fill_opacity=0.8,
                        popup=f"Point {i}<br>Lat={lat:.6f}<br>Lon={lon:.6f}",
                    ).add_to(fg_pts)

        fg_line.add_to(m)
        fg_pts.add_to(m)

        # Mouse position display
        MousePosition(
            position="bottomright",
            separator=" | ",
            prefix="Coordinates:",
            lat_formatter="function(num) {return L.Util.formatNum(num, 6);}",
            lng_formatter="function(num) {return L.Util.formatNum(num, 6);}",
        ).add_to(m)

        # Layer control
        folium.LayerControl(collapsed=False).add_to(m)
        m.save(out_html)

    # --- HTML cleaner --------------------------------------------------------

    def clean_html(self, path: str) -> None:
        """
        Fix common validator warnings:
          - Ensure <html lang="en">
          - Ensure <title>
          - Use <meta charset="utf-8"> (replace any http-equiv variant)
          - Remove 'maximum-scale' & 'user-scalable' from viewport (robust across whitespace/newlines)
        """
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()

        # Ensure <html lang="en">
        if not re.search(r'<html[^>]*\blang\s*=', html, flags=re.IGNORECASE):
            html = re.sub(r'<html([^>]*)>', r'<html\1 lang="en">', html, count=1, flags=re.IGNORECASE)

        # Ensure <title>
        if not re.search(r'<title>.*?</title>', html, flags=re.IGNORECASE | re.DOTALL):
            html = re.sub(
                r'<head[^>]*>', f'<head>\n<title>Route {self.route_id}</title>',
                html, count=1, flags=re.IGNORECASE
            )

        # Normalize charset
        html = re.sub(
            r'<meta[^>]*http-equiv\s*=\s*["\']content-type["\'][^>]*>',
            '<meta charset="utf-8">', html, flags=re.IGNORECASE,
        )
        html = re.sub(
            r'<meta\s+charset\s*=\s*["\'][^"\']*["\']\s*/?>',
            '<meta charset="utf-8">', html, flags=re.IGNORECASE,
        )

        # Fix viewport
        def _fix_viewport_tag(tag_html: str) -> str:
            m = re.search(r'content\s*=\s*["\'](.*?)["\']', tag_html, flags=re.IGNORECASE | re.DOTALL)
            if not m:
                return tag_html
            content = m.group(1)
            parts = [p.strip() for p in re.split(r'\s*,\s*', content.replace('\n', ' '))]
            keep = []
            for p in parts:
                if re.match(r'(?i)user\s*-\s*scalable\s*=', p):
                    continue
                if re.match(r'(?i)maximum\s*-\s*scale\s*=', p):
                    continue
                if p:
                    keep.append(p)
            new_content = ', '.join(keep)
            start, end = m.span(1)
            return tag_html[:start] + new_content + tag_html[end:]

        html = re.sub(
            r'<meta\s+[^>]*name\s*=\s*["\']viewport["\'][^>]*\/?>',
            lambda m: _fix_viewport_tag(m.group(0)),
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
