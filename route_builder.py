#!/usr/bin/env python3
"""
route_builder.py
----------------
Interactive CLI that:
  1) Builds an ordered route (from raw FeatureCollection or *_ordered.geojson)
     - Saves <input>_ordered.geojson
     - Generates & cleans <input>_ordered.html
     - Prints termini
  2) Optionally uploads ONE row to PostgreSQL (via SSH):
       (route TEXT UNIQUE, route_path TEXT)
     where route_path is "lon lat, lon lat, ..."

Modules:
  - geo_math.py         (math helpers)
  - topology.py         (RouteTopology)
  - visualization.py    (RouteMap)
  - db_manager.py       (DBManager; ensures id UUID PK, route UNIQUE)
  - help_menu.py        (HelpMenu)
"""

from __future__ import annotations
import os
import sys
import json
from textwrap import dedent

# Local modules
from topology import RouteTopology, LonLat
from visualization import RouteMap
from db_manager import DBManager
from help_menu import HelpMenu

# ---------- Optional: Windows-friendly tab completion ----------
try:
    import readline  # macOS/Linux
except Exception:
    try:
        import pyreadline as readline  # type: ignore
    except Exception:
        readline = None


def _enable_path_completion():
    if readline is None:
        return
    import glob
    def complete_path(text, state):
        if not text:
            matches = glob.glob("*")
        else:
            expanded = os.path.expanduser(os.path.expandvars(text))
            if os.path.isdir(expanded):
                expanded = os.path.join(expanded, "")
            matches = glob.glob(expanded + "*")
        try:
            return matches[state]
        except IndexError:
            return None
    try:
        readline.set_completer_delims(' \t\n;')
        readline.parse_and_bind("tab: complete")
        readline.set_completer(complete_path)
    except Exception:
        pass


def safe_input(prompt: str) -> str:
    try:
        s = input(prompt)
        if "\x18" in s:  # Ctrl+X
            print("\n[INFO] Terminated by user (Ctrl+X). Exiting cleanly.")
            sys.exit(0)
        return s
    except KeyboardInterrupt:
        print("\n[INFO] Terminated by user (Ctrl+C). Exiting cleanly.")
        sys.exit(0)


def safe_input_default(prompt: str, default: str) -> str:
    s = safe_input(f"{prompt} [{default}]: ").strip()
    return s if s else default


def _load_segments(geojson_path: str):
    """Read FeatureCollection and return (route_id, segments[list[List[lon,lat]]])."""
    with open(geojson_path, "r", encoding="utf-8") as f:
        gj = json.load(f)

    route_id = "unknown"
    segments = []
    if gj.get("type") == "FeatureCollection":
        for feat in gj.get("features", []):
            props = (feat.get("properties") or {})
            if "route" in props:
                route_id = str(props["route"])
            geom = feat.get("geometry") or {}
            if geom.get("type") == "LineString":
                segments.append(geom.get("coordinates", []))
            elif geom.get("type") == "MultiLineString":
                segments.extend(geom.get("coordinates", []))
    return route_id, segments


def extract_route_from_geojson(geojson_path: str):
    """Support ordered geojson ({route, route_data}) or raw FeatureCollection."""
    with open(geojson_path, "r", encoding="utf-8") as f:
        gj = json.load(f)
    route_id = "unknown"
    coords = []
    if isinstance(gj, dict) and "route_data" in gj:
        route_id = str(gj.get("route", "unknown"))
        coords = gj.get("route_data") or []
    elif gj.get("type") == "FeatureCollection":
        from pathlib import Path
        route_id = Path(geojson_path).stem
        for feat in gj.get("features", []):
            props = (feat.get("properties") or {})
            if "route" in props:
                route_id = str(props["route"])
            geom = feat.get("geometry") or {}
            if geom.get("type") == "LineString":
                coords.extend(geom.get("coordinates", []))
            elif geom.get("type") == "MultiLineString":
                for seg in geom.get("coordinates", []):
                    coords.extend(seg)
    # coerce floats
    clean = []
    for pt in coords:
        try:
            lon, lat = float(pt[0]), float(pt[1])
            clean.append([lon, lat])
        except Exception:
            continue
    return route_id, clean


def write_ordered_geojson(out_path: str, route_id: str, ordered: list[LonLat]):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"route": route_id, "route_data": ordered}, f, indent=2)


def main() -> int:
    # --- Help flag ---
    if "--help" in sys.argv or "-h" in sys.argv:
        HelpMenu.show()
        return 0

    print(dedent("""
    Route Builder – Interactive Mode
    --------------------------------
    Steps:
      1) Build ordered route & HTML map
      2) Upload ONE row (route, route_path) to PostgreSQL (optional)

    Controls:
      - Tab-complete file paths
      - Press Enter to accept defaults
      - Ctrl+C or Ctrl+X to exit
    """))

    _enable_path_completion()

    # --- Input file ---
    while True:
        src = safe_input("Enter path to source GeoJSON (raw FeatureCollection or *_ordered.geojson): ").strip()
        if not src:
            print("[WARN] Path cannot be empty.")
            continue
        if not os.path.exists(src):
            print(f"[ERROR] File not found: {src}")
            continue
        break

    # Determine if already ordered
    already_ordered = False
    try:
        with open(src, "r", encoding="utf-8") as f:
            j = json.load(f)
        already_ordered = isinstance(j, dict) and "route_data" in j
    except Exception:
        pass

    if already_ordered:
        route_id, ordered = extract_route_from_geojson(src)
        out_geojson = src
        print(f"[INFO] Detected ordered file. Route '{route_id}', {len(ordered)} points.")
    else:
        route_id, segments = _load_segments(src)
        topo = RouteTopology()
        ordered = topo.build_ordered_route(segments)

        out_geojson = os.path.splitext(src)[0] + "_ordered.geojson"
        write_ordered_geojson(out_geojson, route_id, ordered)

        out_html = os.path.splitext(src)[0] + "_ordered.html"
        rmap = RouteMap(route_id=route_id)
        rmap.generate(ordered, out_html)
        rmap.clean_html(out_html)

        if ordered:
            start, end = RouteTopology.termini(ordered)
            print(f"[INFO] Processed {len(ordered)} points")
            print(f"[INFO] GeoJSON saved: {out_geojson}")
            print(f"[INFO] HTML map saved: {out_html}")
            print(f"Terminus 1: Lon={start[0]:.6f}, Lat={start[1]:.6f}")
            print(f"Terminus 2: Lon={end[0]:.6f}, Lat={end[1]:.6f}")
        else:
            print("[WARN] No route built.")

    # --- Upload? ---
    do_upload = safe_input_default("Upload to PostgreSQL now? (Y/n)", "Y")
    if do_upload.lower().startswith("n"):
        print("[INFO] Skipping upload. Done.")
        return 0

    # Ensure we have coordinates from ordered file
    route_id, coords = extract_route_from_geojson(out_geojson)
    if not coords:
        print("[ERROR] No coordinates available to upload.")
        return 1

    # Defaults from config.ini via DBManager
    dbm = DBManager()  # loads .env + config.ini (including default_db/default_table)
    dbname = safe_input_default("Database name", dbm.default_db)
    tablename = safe_input_default("Table name", dbm.default_table)

    # Upload via DBManager with existence check + prompt
    with dbm:
        dbm.ensure_database(dbname)
        dbm.ensure_table(dbname, tablename)

        exists = dbm.route_exists(dbname, tablename, route_id)
        print(f"[INFO] Route '{route_id}' exists in '{tablename}': {'Yes' if exists else 'No'}")

        if exists:
            choice = safe_input_default(
                f"Route '{route_id}' already exists. Update it? (Y/n)", "N"
            )
            if choice.lower().startswith("y"):
                dbm.upload_one_row(dbname, tablename, route_id, coords, allow_update=True)
            else:
                print("[INFO] Skipped updating existing route. Exiting.")
                return 0
        else:
            dbm.upload_one_row(dbname, tablename, route_id, coords)

        out_sql = os.path.splitext(out_geojson)[0] + "_ordered.sql"
        dbm.export_sql(out_sql, tablename, route_id, coords)

    print("[SUCCESS] Completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
