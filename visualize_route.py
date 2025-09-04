#!/usr/bin/env python3
"""
visualize_route.py
------------------
CLI to visualize a route from a GeoJSON file or from the database.
"""

import argparse
import os
import json
import tempfile
from shapely import wkt
from shapely.geometry import mapping
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter

from load_routes import load_routes_from_geojson, load_geojson_from_db
from view_geojson import RouteMap
from load_config import load_config   # ✅ central config loader

def choose_file() -> str:
    """Prompt with TAB completion for file paths."""
    completer = PathCompleter(only_directories=False, expanduser=True)
    path = prompt("Enter path to .geojson file: ", completer=completer)
    return os.path.expanduser(path.strip())


def show_menu():
    """Interactive menu for visualization."""
    print("Choose visualization mode:")
    print("1) Load from GeoJSON file")
    print("2) Load from database")
    choice = input("Enter choice (1/2): ").strip()

    if choice == "1":
        path = choose_file()
        if not os.path.isfile(path):
            print(f"[ERROR] File not found: {path}")
            return
        records = load_routes_from_geojson(path)
        features = []
        for rec in records:
            geom = wkt.loads(rec["geom"])
            features.append({
                "type": "Feature",
                "geometry": mapping(geom),
                "properties": rec
            })
        geojson_data = {"type": "FeatureCollection", "features": features}
        route_id = os.path.splitext(os.path.basename(path))[0]

    elif choice == "2":
        short_name = input("Enter route short_name (e.g. 1, 1A): ").strip()
        config = load_config()   # ✅ use db_management config
        geojson_data = load_geojson_from_db(short_name, config)
        route_id = short_name

    else:
        print("[ERROR] Invalid choice.")
        return

    out_html = f"{route_id}_map.html"

    # Write temp GeoJSON to pass path into RouteMap
    with tempfile.NamedTemporaryFile("w", suffix=".geojson", delete=False) as tmp:
        json.dump(geojson_data, tmp)
        tmp_path = tmp.name

    rm = RouteMap(route_id=route_id)
    rm.generate(tmp_path, out_html)
    rm.clean_html(out_html)
    print(f"[OK] Map saved to {out_html}")


def cmd_help_visualization():
    print("""
Visualize Route CLI
-------------------
This tool lets you visualize transport routes from GeoJSON or directly
from the Postgres database.

Usage:
  visualize_route.py -h
  visualize_route.py

Options (when running without args):
  1) Visualize from file
     - Prompts for a .geojson file path (with TAB completion)
     - Uses load_routes_from_geojson()

  2) Visualize from database
     - Prompts for a route short_name (e.g. "1", "1A")
     - Queries the database via db_management + load_config

Examples:
  # Show help
  visualize_route.py -h

  # Launch interactive menu
  visualize_route.py
""")


def main():
    parser = argparse.ArgumentParser(add_help=True)
    args, unknown = parser.parse_known_args()

    if unknown or not vars(args):
        # no args → show menu
        show_menu()
    else:
        cmd_help_visualization()


if __name__ == "__main__":
    main()
