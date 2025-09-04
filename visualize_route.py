#!/usr/bin/env python3
"""
visualize_route.py
------------------
Quick utility to render a route from a GeoJSON file into an interactive HTML map.
"""

import sys
import os
from visualization import RouteMap


def main():
    if len(sys.argv) < 2:
        print("Usage: ./visualize_route.py path/to/route.geojson [out.html]")
        sys.exit(1)

    geojson_path = sys.argv[1]
    if not os.path.isfile(geojson_path):
        print(f"[ERROR] File not found: {geojson_path}")
        sys.exit(1)

    out_html = sys.argv[2] if len(sys.argv) > 2 else "route_map.html"

    rm = RouteMap(route_id=os.path.splitext(os.path.basename(geojson_path))[0])
    rm.generate(geojson_path, out_html)
    rm.clean_html(out_html)

    print(f"[OK] Map saved to: {out_html}")


if __name__ == "__main__":
    main()
