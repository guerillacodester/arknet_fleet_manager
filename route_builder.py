#!/usr/bin/env python3
"""
Route Builder (entrypoint)
--------------------------
1) Convert unordered route segments (from QGIS GeoJSON) into an ordered polyline.
2) Save compact JSON -> <input>_ordered.geojson
3) Print route termini
4) Generate interactive HTML map -> <input>_ordered.html
   - Basemap / No basemap (base layers)
   - Route (overlay)
   - All stops (overlay)
   - Cleaned HTML for accessibility/compliance
"""

from __future__ import annotations
import json, os, sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from textwrap import dedent
from typing import List, Tuple

from topology import RouteTopology, LonLat
from visualization import RouteMap


def _load_segments(geojson_path: str) -> Tuple[str, List[List[LonLat]]]:
    """
    Read a FeatureCollection of LineString/MultiLineString features and
    return (route_id, list-of-segments).
    """
    with open(geojson_path, "r", encoding="utf-8") as f:
        gj = json.load(f)

    route_id = "unknown"
    segments: List[List[LonLat]] = []

    if gj.get("type") == "FeatureCollection":
        for feat in gj.get("features", []):
            props = feat.get("properties", {}) or {}
            if "route" in props:
                route_id = str(props["route"])
            geom = feat.get("geometry", {}) or {}
            gtype = geom.get("type")
            if gtype == "LineString":
                segments.append(geom.get("coordinates", []))
            elif gtype == "MultiLineString":
                segments.extend(geom.get("coordinates", []))
    return route_id, segments


def main() -> int:
    parser = ArgumentParser(
        prog="route_builder.py",
        formatter_class=RawDescriptionHelpFormatter,
        description=dedent("""
            Build an ordered route from unordered QGIS/GeoJSON segments.

            Input:
              A GeoJSON file containing LineString or MultiLineString features.

            Output:
              - <input>_ordered.geojson (compact JSON: {"route": "<id>", "route_data": [[lon,lat], ...]})
              - <input>_ordered.html (interactive visualization with base/overlay toggles, cleaned HTML)
              - Printed summary with terminus coordinates
        """),
        epilog=dedent("""
            Example:
              python route_builder.py route_1.geojson

            This reads 'route_1.geojson', builds an ordered route,
            writes 'route_1_ordered.geojson' and 'route_1_ordered.html',
            and prints the start/stop termini.
        """),
    )
    parser.add_argument("geojson", help="Input route GeoJSON (FeatureCollection of LineString/MultiLineString)")
    args = parser.parse_args()

    if not os.path.exists(args.geojson):
        print(f"[ERROR] File not found: {args.geojson}")
        return 1

    route_id, segments = _load_segments(args.geojson)
    topo = RouteTopology()
    ordered: List[LonLat] = topo.build_ordered_route(segments)

    # Write compact JSON
    result = {"route": route_id, "route_data": ordered}
    out_geojson = os.path.splitext(args.geojson)[0] + "_ordered.geojson"
    with open(out_geojson, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # HTML map
    out_html = os.path.splitext(args.geojson)[0] + "_ordered.html"
    rmap = RouteMap(route_id=route_id)
    rmap.generate(ordered, out_html)
    rmap.clean_html(out_html)

    # Print summary + termini
    if ordered:
        start, end = topo.termini(ordered)
        print(f"[INFO] Processed {len(ordered)} points")
        print(f"[INFO] GeoJSON saved: {out_geojson}")
        print(f"[INFO] HTML map saved: {out_html}")
        print(f"Terminus 1: Lon={start[0]:.6f}, Lat={start[1]:.6f}")
        print(f"Terminus 2: Lon={end[0]:.6f}, Lat={end[1]:.6f}")
    else:
        print("[WARN] No route built.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
