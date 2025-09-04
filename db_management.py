#!/usr/bin/env python3
"""
db_management.py
----------------
Generic PostgreSQL DB management module.
Provides CRUD utilities for any table.
Now includes SSH tunneling using Paramiko (no sshtunnel dependency).
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import paramiko
import socket
import threading


class Forwarder(threading.Thread):
    """
    Lightweight local port forwarder using Paramiko.
    Forwards localhost:local_port → remote_host:remote_port via SSH transport.
    """

    daemon = True

    def __init__(self, transport, local_port, remote_host, remote_port):
        super().__init__()
        self.transport = transport
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.sock = None
        self._stop = threading.Event()

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", self.local_port))
        self.sock.listen(1)

        while not self._stop.is_set():
            try:
                client, _ = self.sock.accept()
                chan = self.transport.open_channel(
                    "direct-tcpip",
                    (self.remote_host, self.remote_port),
                    client.getsockname(),
                )
                threading.Thread(target=self._pipe, args=(client, chan), daemon=True).start()
                threading.Thread(target=self._pipe, args=(chan, client), daemon=True).start()
            except Exception:
                break

    def _pipe(self, src, dst):
        try:
            while True:
                data = src.recv(1024)
                if not data:
                    break
                dst.sendall(data)
        except Exception:
            pass
        finally:
            src.close()
            dst.close()

    def stop(self):
        self._stop.set()
        if self.sock:
            self.sock.close()


class DBConnection:
    """
    Wrapper around psycopg2 connection and optional SSH tunnel.
    Behaves like a connection: exposes cursor(), commit(), rollback(), close().
    """

    def __init__(self, config: dict):
        self.config = config
        self.conn = None
        self.ssh_client = None
        self.forwarder = None
        self.local_port = None

    def connect(self):
        pg_cfg = self.config["postgres"]
        env_cfg = self.config["env"]

        ssh_host = env_cfg.get("SSH_HOST")
        ssh_port = env_cfg.get("SSH_PORT")
        ssh_user = env_cfg.get("SSH_USER")
        ssh_pass = env_cfg.get("SSH_PASS")

        if ssh_host and ssh_port and ssh_user:
            print(f"[INFO] Establishing SSH tunnel {ssh_user}@{ssh_host}:{ssh_port} → {pg_cfg['host']}:{pg_cfg['port']}")
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                ssh_host,
                port=int(ssh_port),
                username=ssh_user,
                password=ssh_pass,
            )
            self.local_port = 6543
            self.forwarder = Forwarder(
                self.ssh_client.get_transport(),
                self.local_port,
                pg_cfg["host"],
                int(pg_cfg["port"]),
            )
            self.forwarder.start()
            host = "127.0.0.1"
            port = self.local_port
        else:
            host = pg_cfg["host"]
            port = pg_cfg["port"]

        self.conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=pg_cfg["default_db"],
            user=env_cfg["DB_USER"],
            password=env_cfg["DB_PASS"],
            cursor_factory=RealDictCursor,
        )
        self.conn.autocommit = True
        return self.conn

    # proxy methods
    def cursor(self, cursor_factory=None):
        return self.conn.cursor(cursor_factory=cursor_factory or RealDictCursor)

    def commit(self):
        return self.conn.commit()

    def rollback(self):
        return self.conn.rollback()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
        if self.forwarder:
            self.forwarder.stop()
            self.forwarder = None
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None

    # context manager
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


# ---------------------------
# Utility functions
# ---------------------------

def table_exists(conn, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);",
            (table,),
        )
        return cur.fetchone()["exists"]


def create_table(conn, schema_sql: str):
    with conn.cursor() as cur:
        cur.execute(schema_sql)


def insert(conn, table: str, values: dict, id_column: str = None):
    cols, vals, placeholders = [], [], []
    for col, val in values.items():
        cols.append(col)
        vals.append(val)
        placeholders.append("%s")

    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
    with conn.cursor() as cur:
        if id_column:
            sql += f" RETURNING {id_column}"
            cur.execute(sql, vals if vals else None)
            row = cur.fetchone()
            return row[id_column]  # RealDictCursor
        else:
            cur.execute(sql, vals if vals else None)
            return None


def update(conn, table: str, values: dict, where: dict):
    set_clause = ", ".join([f"{k} = %s" for k in values.keys()])
    where_clause = " AND ".join([f"{k} = %s" for k in where.keys()])
    sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
    with conn.cursor() as cur:
        cur.execute(sql, list(values.values()) + list(where.values()))


def delete(conn, table: str, where: dict):
    where_clause = " AND ".join([f"{k} = %s" for k in where.keys()])
    sql = f"DELETE FROM {table} WHERE {where_clause}"
    with conn.cursor() as cur:
        cur.execute(sql, list(where.values()))


def select(conn, table: str, columns="*", where: dict = None, limit: int = None):
    # Normalize columns: list → comma-separated string
    if isinstance(columns, (list, tuple)):
        columns = ", ".join(columns)

    sql = f"SELECT {columns} FROM {table}"
    vals = []
    if where:
        where_clause = " AND ".join([f"{k} = %s" for k in where.keys()])
        sql += f" WHERE {where_clause}"
        vals.extend(where.values())
    if limit:
        sql += f" LIMIT {limit}"
    with conn.cursor() as cur:
        cur.execute(sql, vals if vals else None)
        return cur.fetchall()

