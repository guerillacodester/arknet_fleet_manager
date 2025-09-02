#!/usr/bin/env python3
"""
help_menu.py
------------
Centralized help system for Route Builder CLI.

Keeps the entrypoint (route_builder.py) slim while still providing
a comprehensive help & usage overview.
"""

from textwrap import dedent


class HelpMenu:
    @staticmethod
    def show():
        print(dedent("""
        ==========================================================
                          ROUTE BUILDER – HELP
        ==========================================================

        Overview
        --------
        Route Builder is an interactive CLI tool that:
          1. Builds ordered routes from unordered QGIS/GeoJSON files
          2. Generates cleaned interactive HTML maps
          3. Uploads ordered routes to PostgreSQL via SSH tunnel

        Files Generated
        ---------------
          - <input>_ordered.geojson : compact ordered GeoJSON
          - <input>_ordered.html    : interactive Folium map
          - <input>_ordered.sql     : SQL insert dump (for backup/migration)

        Database Upload
        ---------------
          - Requires .env (SSH/DB credentials) + config.ini (DB host/port)
          - Inserts exactly ONE row into your chosen table:
                route TEXT NOT NULL,
                route_path TEXT
          - route_path is a long string of "lon lat, lon lat, ..." pairs

        Defaults
        --------
          - Default DB: arknettransit
          - Default Table: routes
          - Press Enter at prompts to accept defaults

        Interactive Controls
        --------------------
          - Tab       : file path auto-completion
          - Enter     : accept defaults
          - Ctrl+C    : exit gracefully
          - Ctrl+X    : exit gracefully

        Example Usage
        -------------
          $ python route_builder.py
          (follow interactive prompts)

          # To view help directly:
          $ python route_builder.py --help

        ==========================================================
        """))
