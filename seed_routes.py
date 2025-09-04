#!/usr/bin/env python3
"""
seed_routes.py
--------------
Seeds the routes, shapes, and route_shapes tables interactively or
programmatically from a specified GeoJSON file.
Includes a -c smoketest mode to validate GeoJSON input without DB access.
"""

import sys
import os
import signal
import readline
from colorama import Fore, Style, init

# --- Imports (works standalone and as module) ---
try:
    from .db_management import DBConnection, table_exists, insert, select
    from .load_config import load_config
    from .load_routes import load_routes_from_geojson
    from .help_routes import print_help
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_management import DBConnection, table_exists, insert, select
    from load_config import load_config
    from load_routes import load_routes_from_geojson
    from help_routes import print_help

init(autoreset=True)

# ---------------------------
# Tab completion for paths (directories + .geojson only)
# ---------------------------
def _normalized_path(p: str) -> str:
    p_exp = os.path.expandvars(os.path.expanduser(p))
    if p_exp == "":
        p_exp = "." + os.sep
    return p_exp

def path_completer(text, state):
    text = _normalized_path(text)
    if text.endswith(os.sep) and os.path.isdir(text):
        dirname = text
        basename = ""
    else:
        dirname = os.path.dirname(text) or "." + os.sep
        basename = os.path.basename(text)

    try:
        entries = os.listdir(dirname)
    except Exception:
        entries = []

    def _starts_with(a: str, b: str) -> bool:
        if os.name == "nt":
            return a.lower().startswith(b.lower())
        return a.startswith(b)

    matches = []
    for entry in sorted(entries):
        if entry.startswith(".") and not basename.startswith("."):
            continue
        if not _starts_with(entry, basename):
            continue
        full = os.path.join(dirname, entry)
        if os.path.isdir(full):
            matches.append(os.path.normpath(full) + os.sep)
        elif entry.lower().endswith(".geojson"):
            matches.append(os.path.normpath(full))

    try:
        return matches[state]
    except IndexError:
        return None

try:
    readline.set_completer_delims(" \t\n;")
    readline.set_completer(path_completer)
    readline.parse_and_bind("tab: complete")
except Exception:
    pass

# ---------------------------
# Signals
# ---------------------------
def graceful_exit(sig, frame):
    print("\nExiting gracefully. Goodbye!")
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_exit)

# ---------------------------
# Country selection
# ---------------------------
def choose_country(db):
    countries = select(db, "countries", ["country_id", "iso_code", "name"])
    normalized = [
        {"id": row["country_id"], "iso": row["iso_code"], "name": row["name"]}
        for row in countries
    ]

    country_id = None
    while not country_id:
        user_input = input("Enter country ISO code, name, or fragment: ").strip()
        for row in normalized:
            if user_input.upper() == row["iso"].upper():
                country_id = row["id"]
                print(f"Selected: {row['iso']} – {row['name']}")
                break
        if country_id:
            break
        for row in normalized:
            if user_input.lower() == row["name"].lower():
                country_id = row["id"]
                print(f"Selected: {row['iso']} – {row['name']}")
                break
        if country_id:
            break
        matches = [row for row in normalized if user_input.lower() in row["name"].lower()]
        if matches:
            print("\nMatches found:")
            for idx, row in enumerate(matches, start=1):
                print(f"[{idx}] {row['iso']} – {row['name']}")
            choice = input("Select by number or re-enter: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(matches):
                row = matches[int(choice) - 1]
                country_id = row["id"]
                print(f"Selected: {row['iso']} – {row['name']}")
            else:
                print("Invalid choice, try again.")
        else:
            print("No matches found. Try again.")
    return country_id

# ---------------------------
# Seeder
# ---------------------------
def seed_routes(interactive: bool = True, geojson_mode: bool = False, geojson_path: str = None):
    config = load_config()
    db = DBConnection(config)
    db.connect()

    if not table_exists(db, "routes"):
        print(Fore.RED + "[ERROR]" + Style.RESET_ALL + " Table 'routes' does not exist. Run migrations first.")
        return

    if interactive:
        print(Fore.CYAN + "\nArkNet Transit – Route Seeder\n" + "-" * 40 + Style.RESET_ALL)

        country_id = choose_country(db)

        short_name = input("Enter route short name (e.g., 1, 5A, 10B): ").strip().upper()
        long_name = input("Enter route long name [optional]: ").strip() or None
        parishes = input("Enter parishes served [optional, comma-separated]: ").strip() or None
        is_active = input("Is this route active? [Y/n]: ").strip().lower() != "n"
        valid_from = input("Enter valid_from date [default = today]: ").strip() or None
        valid_to = input("Enter valid_to date [optional, blank if none]: ").strip() or None

        geojson_path = input("Enter path to GeoJSON file (Tab-complete supported): ").strip()
        geojson_path = _normalized_path(geojson_path)
        if not os.path.isfile(geojson_path):
            print(Fore.RED + "[ERROR]" + Style.RESET_ALL + f" File not found: {geojson_path}")
            return

        geom_records = load_routes_from_geojson(geojson_path, short_name)
        if not geom_records:
            print(Fore.RED + "[ERROR]" + Style.RESET_ALL + f"No geometry found for {short_name}")
            return

        print("\nSummary:\n---------")
        print(f"Country ID: {country_id}")
        print(f"Route short name: {short_name}")
        print(f"Route long name: {long_name}")
        print(f"Parishes: {parishes}")
        print(f"Active: {is_active}")
        print(f"Valid from: {valid_from}")
        print(f"Valid to: {valid_to}")
        print(f"Geometry: {len(geom_records)} record(s) from {geojson_path}")
        if input("Proceed with insertion into DB? [Y/n]: ").strip().lower() == "n":
            print("Aborted.")
            return

        # --- Insert (with duplicate check) ---
        route_id = None
        existing = select(
            db,
            "routes",
            columns="route_id",
            where={"country_id": country_id, "short_name": short_name}
        )
        if existing and len(existing) > 0:
            route_id = existing[0]["route_id"]
            print(Fore.YELLOW + f"[WARN] Route {short_name} already exists for this country. Using existing route_id." + Style.RESET_ALL)
        else:
            route_id = insert(
                db, "routes",
                {
                    "country_id": country_id,
                    "short_name": short_name,
                    "long_name": long_name,
                    "parishes": parishes,
                    "is_active": is_active,
                    "valid_from": valid_from,
                    "valid_to": valid_to,
                },
                id_column="route_id"
            )
        if not route_id:
            print(Fore.RED + "[ERROR]" + Style.RESET_ALL + f" Failed to get route_id for {short_name}")
            return

        for geom in geom_records:
            shape_id = insert(db, "shapes", {"geom": geom["geom"]}, id_column="shape_id")
            insert(
                db, "route_shapes",
                {
                    "route_id": route_id,
                    "shape_id": shape_id,
                    "variant_code": geom.get("variant_code"),
                    "is_default": geom.get("is_default", False),
                }
            )
        print(Fore.GREEN + "[OK]" + Style.RESET_ALL + f" Route {short_name} inserted/updated.")

    elif geojson_mode:
        if not geojson_path or not os.path.isfile(geojson_path):
            print(Fore.RED + "[ERROR]" + Style.RESET_ALL + " A valid GeoJSON file path is required in --geojson mode.")
            return
        records = load_routes_from_geojson(geojson_path)
        for rec in records:
            route_id = None
            existing = select(
                db,
                "routes",
                columns="route_id",
                where={"country_id": rec.get("country_id"), "short_name": rec["short_name"]}
            )
            if existing and len(existing) > 0:
                route_id = existing[0]["route_id"]
                print(Fore.YELLOW + f"[WARN] Route {rec['short_name']} already exists for this country. Using existing route_id." + Style.RESET_ALL)
            else:
                route_id = insert(
                    db, "routes",
                    {
                        "country_id": rec.get("country_id"),
                        "short_name": rec["short_name"],
                        "long_name": rec.get("long_name"),
                        "parishes": rec.get("parishes"),
                        "is_active": rec.get("is_active", True),
                        "valid_from": rec.get("valid_from"),
                        "valid_to": rec.get("valid_to"),
                    },
                    id_column="route_id"
                )
            if not route_id:
                print(Fore.RED + "[ERROR]" + Style.RESET_ALL + f" Failed to get route_id for {rec['short_name']}")
                continue

            shape_id = insert(db, "shapes", {"geom": rec["geom"]}, id_column="shape_id")
            insert(
                db, "route_shapes",
                {
                    "route_id": route_id,
                    "shape_id": shape_id,
                    "variant_code": rec.get("variant_code"),
                    "is_default": rec.get("is_default", False),
                }
            )
        print(Fore.GREEN + "[OK]" + Style.RESET_ALL + f" Imported {len(records)} route(s).")

# ---------------------------
# CLI entrypoint
# ---------------------------
def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print_help()
            return
        elif sys.argv[1] == "--geojson":
            if len(sys.argv) < 3:
                print(Fore.RED + "[ERROR]" + Style.RESET_ALL + " Usage: ./seed_routes.py --geojson <path>")
                return
            seed_routes(interactive=False, geojson_mode=True, geojson_path=sys.argv[2])
            return
        elif sys.argv[1] == "-c":
            if len(sys.argv) < 3:
                print(Fore.RED + "[ERROR]" + Style.RESET_ALL + " Usage: ./seed_routes.py -c <path>")
                return
            geojson_path = _normalized_path(sys.argv[2])
            if not os.path.isfile(geojson_path):
                print(Fore.RED + "[ERROR]" + Style.RESET_ALL + f" File not found: {geojson_path}")
                return
            records = load_routes_from_geojson(geojson_path)
            print(Fore.CYAN + f"[SMOKETEST] Loaded {len(records)} feature(s) from {geojson_path}" + Style.RESET_ALL)
            if records:
                first = records[0].copy()
                first.pop("geom", None)
                print("First record:", first)
            return

    seed_routes(interactive=True)

if __name__ == "__main__":
    main()
