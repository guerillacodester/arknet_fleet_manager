#!/usr/bin/env python3
"""
geojson_uploader.py
-------------------
Interactive uploader for ordered GeoJSON routes.

Design:
- Inserts exactly ONE row per route into a table with columns:
    route TEXT NOT NULL,
    route_path TEXT
- route_path is a single long string: "lon lat, lon lat, ..."

Features:
- Reads SSH + DB credentials from .env and config.ini
- Creates SSH tunnel to VPS, connects to PostgreSQL
- Prompts for database, table, and GeoJSON file (tab completion)
- Ensures the table exists (creates a 2-column schema if missing)
- Accepts either:
    (a) processed *_ordered.geojson  -> { "route": "...", "route_data": [[lon,lat], ...] }
    (b) raw FeatureCollection         -> LineString / MultiLineString (flattened)
- Writes <input>_ordered.sql (single INSERT with the two columns)
- Graceful termination with Ctrl+C or Ctrl+X
"""

import os
import sys
import json
import psycopg2
import configparser
from dotenv import load_dotenv
from sshtunnel import SSHTunnelForwarder
import warnings

# ---------- Optional: Windows-friendly tab completion ----------
try:
    import readline  # macOS/Linux
except Exception:
    # Windows: provide fallback (pyreadline3)
    try:
        import pyreadline as readline  # type: ignore
    except Exception:
        readline = None  # no completion

# Suppress paramiko/cryptography TripleDES deprecation noise
warnings.filterwarnings(
    "ignore",
    message=".*TripleDES has been moved.*",
    category=DeprecationWarning
)

# ---------------- Graceful input ----------------
def safe_input(prompt: str) -> str:
    """Input wrapper that gracefully handles Ctrl+C and Ctrl+X."""
    try:
        s = input(prompt)
        if "\x18" in s:  # Ctrl+X (ASCII 24) typed into the prompt
            print("\n[INFO] Terminated by user (Ctrl+X). Exiting cleanly.")
            sys.exit(0)
        return s
    except KeyboardInterrupt:
        print("\n[INFO] Terminated by user (Ctrl+C). Exiting cleanly.")
        sys.exit(0)

# ---------------- Path completion ----------------
def _enable_path_completion():
    if readline is None:
        return
    import glob

    def complete_path(text, state):
        # Expand ~ and env vars; allow drilling into subfolders
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
        # On Windows pyreadline3 uses a different binding; this works for both
        readline.parse_and_bind("tab: complete")
        readline.set_completer(complete_path)
    except Exception:
        pass

# ---------------- Config ----------------
def load_config():
    load_dotenv()
    cfg = configparser.ConfigParser()
    if not os.path.exists("config.ini"):
        print("[ERROR] config.ini not found.")
        sys.exit(1)
    cfg.read("config.ini")

    # SSH
    ssh_host = os.getenv("SSH_HOST")
    ssh_port = int(os.getenv("SSH_PORT", "22"))
    ssh_user = os.getenv("SSH_USER")
    ssh_pass = os.getenv("SSH_PASS")

    # Postgres (remote endpoint behind SSH)
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_host = cfg.get("postgres", "host", fallback="127.0.0.1")
    db_port = int(cfg.get("postgres", "port", fallback="5432"))

    missing = [k for k, v in {
        "SSH_HOST": ssh_host, "SSH_USER": ssh_user, "SSH_PASS": ssh_pass,
        "DB_USER": db_user, "DB_PASS": db_pass
    }.items() if not v]
    if missing:
        print(f"[ERROR] Missing required .env keys: {', '.join(missing)}")
        sys.exit(1)

    return ssh_host, ssh_port, ssh_user, ssh_pass, db_user, db_pass, db_host, db_port

# ---------------- DB helpers ----------------
def connect_db(dbname, user, password, host, port):
    return psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)

def ensure_database(cur, conn, dbname):
    cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
    if cur.fetchone() is None:
        print(f"[INFO] Database '{dbname}' not found. Creating...")
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cur.execute(f"CREATE DATABASE {dbname}")
    else:
        print(f"[INFO] Database '{dbname}' exists.")

def ensure_table(cur, tablename):
    """
    Ensure a 2-column schema:
      route TEXT NOT NULL,
      route_path TEXT
    If the table already exists with extra columns (e.g., id), the INSERT using
    explicit column list (route, route_path) will still work.
    """
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {tablename} (
            route TEXT NOT NULL,
            route_path TEXT
        )
    """)
    print(f"[INFO] Table '{tablename}' is ready (columns: route, route_path).")

# ---------------- GeoJSON parsing ----------------
def extract_route_from_geojson(geojson_path):
    """
    Supports two input formats:

    (A) Processed ordered file:
        { "route": "<id>", "route_data": [[lon,lat], ...] }

    (B) Raw FeatureCollection (QGIS):
        LineString or MultiLineString -> flattened coordinates
        Route id taken from feature properties['route'] if present, else file stem.
    """
    with open(geojson_path, "r", encoding="utf-8") as f:
        gj = json.load(f)

    route_id = "unknown"
    coords = []

    # (A) Ordered format
    if isinstance(gj, dict) and "route_data" in gj:
        route_id = str(gj.get("route", "unknown"))
        coords = gj.get("route_data") or []

    # (B) FeatureCollection
    elif gj.get("type") == "FeatureCollection":
        from pathlib import Path
        route_id = Path(geojson_path).stem  # default fallback
        for feat in gj.get("features", []):
            props = feat.get("properties", {}) or {}
            if "route" in props:
                route_id = str(props["route"])
            geom = feat.get("geometry", {}) or {}
            gtype = geom.get("type")
            if gtype == "LineString":
                coords.extend(geom.get("coordinates", []))
            elif gtype == "MultiLineString":
                for seg in geom.get("coordinates", []):
                    coords.extend(seg)

    # Filter out bad points and coerce to [lon, lat] floats
    clean = []
    for pt in coords:
        try:
            lon, lat = float(pt[0]), float(pt[1])
            clean.append([lon, lat])
        except Exception:
            continue

    return route_id, clean

# ---------------- Upload + SQL export ----------------
def coords_to_long_string(coords):
    """Return 'lon lat, lon lat, ...' string."""
    return ", ".join(f"{lon} {lat}" for lon, lat in coords)

def upload_route_row(cur, tablename, route_id, coords):
    if not coords:
        print("[WARN] No coordinates found, nothing to upload.")
        return
    coord_str = coords_to_long_string(coords)
    sql = f"INSERT INTO {tablename} (route, route_path) VALUES (%s, %s)"
    cur.execute(sql, (route_id, coord_str))
    print(f"[INFO] Inserted route '{route_id}' with {len(coords)} points into {tablename}")

def export_sql(out_path, tablename, route_id, coords):
    if not coords:
        print("[WARN] No coordinates found, skipping SQL export.")
        return
    coord_str = coords_to_long_string(coords)
    # Escape single quotes for a valid SQL literal
    route_sql = route_id.replace("'", "''")
    coord_sql = coord_str.replace("'", "''")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(
            f"INSERT INTO {tablename} (route, route_path) "
            f"VALUES ('{route_sql}', '{coord_sql}');\n"
        )
    print(f"[INFO] SQL dump written: {out_path}")

# ---------------- Main ----------------
def main():
    print("""
GeoJSON Uploader – Interactive Mode
-----------------------------------
This script will:
  1. Connect to PostgreSQL via SSH
  2. Ensure database and table exist
  3. Upload ONE row: (route, route_path) where route_path="lon lat, lon lat, ..."
  4. Export an SQL dump mirroring the insert

Exit anytime with Ctrl+C or Ctrl+X
    """)

    _enable_path_completion()
    ssh_host, ssh_port, ssh_user, ssh_pass, db_user, db_pass, db_host, db_port = load_config()

    tunnel = None
    conn = None
    try:
        # SSH tunnel
        print(f"[INFO] Opening SSH tunnel to {ssh_host}...")
        tunnel = SSHTunnelForwarder(
            (ssh_host, ssh_port),
            ssh_username=ssh_user,
            ssh_password=ssh_pass,
            remote_bind_address=(db_host, db_port)
        )
        tunnel.start()
        local_port = tunnel.local_bind_port
        print(f"[INFO] Tunnel established on localhost:{local_port}")

        # Connect to maintenance DB to ensure target DB exists
        conn = connect_db("postgres", db_user, db_pass, "127.0.0.1", local_port)
        cur = conn.cursor()

        # DB name
        while True:
            dbname = safe_input("Enter database name: ").strip()
            if dbname:
                try:
                    ensure_database(cur, conn, dbname)
                    break
                except Exception as e:
                    print(f"[ERROR] {e}")
            else:
                print("[WARN] Database name cannot be empty.")

        # Reconnect to chosen DB
        conn.close()
        conn = connect_db(dbname, db_user, db_pass, "127.0.0.1", local_port)
        cur = conn.cursor()

        # Table name
        while True:
            tablename = safe_input("Enter table name: ").strip()
            if tablename:
                try:
                    ensure_table(cur, tablename)  # ensures (route TEXT, route_path TEXT)
                    break
                except Exception as e:
                    print(f"[ERROR] {e}")
            else:
                print("[WARN] Table name cannot be empty.")

        # GeoJSON path
        while True:
            geojson_file = safe_input("Enter path to GeoJSON file: ").strip()
            if not geojson_file:
                print("[WARN] Path cannot be empty.")
                continue
            if not os.path.exists(geojson_file):
                print(f"[ERROR] File not found: {geojson_file}")
                continue
            route_id, coords = extract_route_from_geojson(geojson_file)
            if not coords:
                print("[ERROR] No coordinates found in GeoJSON, try another file.")
                continue
            break

        # Insert one row
        upload_route_row(cur, tablename, route_id, coords)
        conn.commit()

        # Export matching SQL
        out_sql = os.path.splitext(geojson_file)[0] + "_ordered.sql"
        export_sql(out_sql, tablename, route_id, coords)

        print("[SUCCESS] Upload complete.")

    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        try:
            if tunnel:
                tunnel.stop()
        except Exception:
            pass

if __name__ == "__main__":
    main()
