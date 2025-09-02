#!/usr/bin/env python3
"""
db_manager.py
-------------
Database + SSH tunnel management for Route Builder.

- Reads SSH/DB creds from .env and host/port/defaults from config.ini
- Opens/closes SSH tunnel
- Ensures database + table:
      id UUID PRIMARY KEY (with DEFAULT when possible)
      route TEXT UNIQUE NOT NULL
      route_path TEXT
- Checks if a route exists
- Inserts OR updates ONE row per route (prompt controlled by caller)
- Exports matching SQL

Note on UUID default:
  We try to enable a server-side default using an extension:
    1) CREATE EXTENSION IF NOT EXISTS pgcrypto;   --> gen_random_uuid()
    2) otherwise CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; --> uuid_generate_v4()
  If neither extension can be enabled, we still create the table (without a default),
  and we will INSERT an explicit uuid4() from Python instead.
"""

from __future__ import annotations
import os
import sys
import uuid
import configparser
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from sshtunnel import SSHTunnelForwarder
import warnings

# Silence cryptography TripleDES deprecation warnings surfaced via paramiko
warnings.filterwarnings(
    "ignore",
    message=".*TripleDES has been moved.*",
    category=DeprecationWarning
)

# Paramiko 4.x compatibility shim for sshtunnel (DSSKey removed upstream)
try:
    import paramiko  # noqa
    if not hasattr(paramiko, "DSSKey"):
        paramiko.DSSKey = None  # type: ignore
except Exception:
    pass


class DBManager:
    """Context-managed SSH + Postgres helper."""

    def __init__(self, default_db: str | None = None, default_table: str | None = None):
        load_dotenv()
        cfg = configparser.ConfigParser()
        if not os.path.exists("config.ini"):
            print("[ERROR] config.ini not found.")
            sys.exit(1)
        cfg.read("config.ini")

        # SSH (.env)
        self.ssh_host = os.getenv("SSH_HOST")
        self.ssh_port = int(os.getenv("SSH_PORT", "22"))
        self.ssh_user = os.getenv("SSH_USER")
        self.ssh_pass = os.getenv("SSH_PASS")

        # DB server (as seen from SSH host)
        self.db_user = os.getenv("DB_USER")
        self.db_pass = os.getenv("DB_PASS")
        self.db_host = cfg.get("postgres", "host", fallback="127.0.0.1")
        self.db_port = int(cfg.get("postgres", "port", fallback="5432"))

        # Defaults from config.ini
        self.default_db = default_db or cfg.get("postgres", "default_db", fallback="arknettransit")
        self.default_table = default_table or cfg.get("postgres", "default_table", fallback="routes")

        missing = [k for k, v in {
            "SSH_HOST": self.ssh_host, "SSH_USER": self.ssh_user, "SSH_PASS": self.ssh_pass,
            "DB_USER": self.db_user, "DB_PASS": self.db_pass
        }.items() if not v]
        if missing:
            print(f"[ERROR] Missing required .env keys: {', '.join(missing)}")
            sys.exit(1)

        self._tunnel = None
        self._local_port = None
        self._conn = None  # psycopg2 connection (opened as needed)

        # whether the table's id column has a server-side DEFAULT
        self._id_has_default: bool = False
        # which UUID function is available ('gen_random_uuid', 'uuid_generate_v4', or None)
        self._uuid_func: str | None = None

    # ---------- context management ----------
    def __enter__(self) -> "DBManager":
        self.open_tunnel()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    # ---------- tunnel / connection ----------
    def open_tunnel(self):
        print(f"[INFO] Opening SSH tunnel to {self.ssh_host}...")
        self._tunnel = SSHTunnelForwarder(
            (self.ssh_host, self.ssh_port),
            ssh_username=self.ssh_user,
            ssh_password=self.ssh_pass,
            remote_bind_address=(self.db_host, self.db_port),
        )
        self._tunnel.start()
        self._local_port = self._tunnel.local_bind_port
        print(f"[INFO] Tunnel established on localhost:{self._local_port}")

    def connect(self, dbname: str):
        self.close_conn()
        self._conn = psycopg2.connect(
            dbname=dbname,
            user=self.db_user,
            password=self.db_pass,
            host="127.0.0.1",
            port=self._local_port,
        )
        return self._conn

    def close_conn(self):
        try:
            if self._conn:
                self._conn.close()
        except Exception:
            pass
        finally:
            self._conn = None

    def close(self):
        self.close_conn()
        try:
            if self._tunnel:
                self._tunnel.stop()
        except Exception:
            pass
        finally:
            self._tunnel = None
            self._local_port = None

    # ---------- ensure objects ----------
    @staticmethod
    def _is_safe_identifier(name: str) -> bool:
        # letters, digits, underscore only (basic safety for CREATE DATABASE)
        import re
        return bool(re.fullmatch(r"[A-Za-z0-9_]+", name))

    def ensure_database(self, dbname: str):
        if not self._is_safe_identifier(dbname):
            raise ValueError("Unsafe database name. Use letters, numbers, underscore only.")
        conn = self.connect("postgres")
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
        if cur.fetchone() is None:
            print(f"[INFO] Database '{dbname}' not found. Creating...")
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))
        else:
            print(f"[INFO] Database '{dbname}' exists.")
        self.close_conn()

    def _detect_uuid_function(self, conn) -> str | None:
        cur = conn.cursor()
        cur.execute("SELECT extname FROM pg_extension WHERE extname IN ('pgcrypto','uuid-ossp')")
        exts = {row[0] for row in cur.fetchall()}
        if "pgcrypto" in exts:
            return "gen_random_uuid"
        if "uuid-ossp" in exts:
            return "uuid_generate_v4"
        return None

    def _try_enable_uuid_extensions(self, conn):
        cur = conn.cursor()
        # Try pgcrypto first
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            conn.commit()
        except Exception:
            conn.rollback()
        # Then try uuid-ossp
        try:
            cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
            conn.commit()
        except Exception:
            conn.rollback()

    def ensure_table(self, dbname: str, tablename: str):
        """
        Ensure schema:
          id UUID PRIMARY KEY [DEFAULT gen_random_uuid()|uuid_generate_v4()],
          route TEXT UNIQUE NOT NULL,
          route_path TEXT
        """
        conn = self.connect(dbname)
        cur = conn.cursor()

        # best effort to enable extension(s)
        self._try_enable_uuid_extensions(conn)
        self._uuid_func = self._detect_uuid_function(conn)

        # Build CREATE TABLE with or without UUID default
        if self._uuid_func == "gen_random_uuid":
            id_col = sql.SQL("id UUID PRIMARY KEY DEFAULT gen_random_uuid()")
        elif self._uuid_func == "uuid_generate_v4":
            id_col = sql.SQL('id UUID PRIMARY KEY DEFAULT uuid_generate_v4()')
        else:
            id_col = sql.SQL("id UUID PRIMARY KEY")

        ddl = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {table} (
                {idcol},
                route TEXT UNIQUE NOT NULL,
                route_path TEXT
            )
        """).format(
            table=sql.Identifier(tablename),
            idcol=id_col
        )
        cur.execute(ddl)
        conn.commit()

        # detect if id column has a default now
        cur.execute("""
            SELECT column_default
            FROM information_schema.columns
            WHERE table_name=%s AND column_name='id'
        """, (tablename,))
        row = cur.fetchone()
        self._id_has_default = bool(row and row[0])

        print(f"[INFO] Table '{tablename}' is ready "
              f"(id UUID{' DEFAULT' if self._id_has_default else ''}, route UNIQUE, route_path).")

        self.close_conn()

    # ---------- existence / upload / export ----------
    def route_exists(self, dbname: str, tablename: str, route_id: str) -> bool:
        """Return True if a route already exists in the table."""
        conn = self.connect(dbname)
        cur = conn.cursor()
        cur.execute(
            sql.SQL("SELECT 1 FROM {table} WHERE route=%s LIMIT 1")
               .format(table=sql.Identifier(tablename)),
            (route_id,)
        )
        found = cur.fetchone() is not None
        self.close_conn()
        return found

    @staticmethod
    def coords_to_long_string(coords):
        return ", ".join(f"{lon} {lat}" for lon, lat in coords)

    def upload_one_row(self, dbname: str, tablename: str, route_id: str, coords, allow_update=False):
        """
        Insert a new route or update an existing one (when allow_update=True).
        If the table lacks a server-side UUID default, we will generate a UUID client-side.
        """
        if not coords:
            print("[WARN] No coordinates found, nothing to upload.")
            return

        coord_str = self.coords_to_long_string(coords)
        conn = self.connect(dbname)
        cur = conn.cursor()

        try:
            if allow_update:
                # Overwrite the entire cell as requested
                cur.execute(
                    sql.SQL("UPDATE {table} SET route_path=%s WHERE route=%s")
                       .format(table=sql.Identifier(tablename)),
                    (coord_str, route_id)
                )
                print(f"[INFO] Updated route '{route_id}' with {len(coords)} points in {tablename}")
            else:
                if self._id_has_default:
                    cur.execute(
                        sql.SQL("INSERT INTO {table} (route, route_path) VALUES (%s, %s)")
                           .format(table=sql.Identifier(tablename)),
                        (route_id, coord_str)
                    )
                else:
                    # No default on id: generate uuid client-side
                    new_id = str(uuid.uuid4())
                    cur.execute(
                        sql.SQL("INSERT INTO {table} (id, route, route_path) VALUES (%s, %s, %s)")
                           .format(table=sql.Identifier(tablename)),
                        (new_id, route_id, coord_str)
                    )
                print(f"[INFO] Inserted new route '{route_id}' with {len(coords)} points into {tablename}")

            conn.commit()
        finally:
            self.close_conn()

    def export_sql(self, out_path: str, tablename: str, route_id: str, coords):
        """
        Write a portable SQL file.
        - If the table has a UUID DEFAULT, we only write (route, route_path).
        - If not, we write (id, route, route_path) with a generated UUID.
        """
        if not coords:
            print("[WARN] No coordinates found, skipping SQL export.")
            return
        route_sql = route_id.replace("'", "''")
        coord_sql = self.coords_to_long_string(coords).replace("'", "''")

        with open(out_path, "w", encoding="utf-8") as f:
            if self._id_has_default:
                f.write(
                    f'INSERT INTO "{tablename}" (route, route_path) '
                    f"VALUES ('{route_sql}', '{coord_sql}');\n"
                )
            else:
                gen_id = str(uuid.uuid4())
                f.write(
                    f'INSERT INTO "{tablename}" (id, route, route_path) '
                    f"VALUES ('{gen_id}', '{route_sql}', '{coord_sql}');\n"
                )
        print(f"[INFO] SQL dump written: {out_path}")
