#!/usr/bin/env python3
"""
help_countries.py
-----------------
Provides help text for the seed_countries module.
Standardized with get_help_text() and print_help().
"""

def get_help_text() -> str:
    return """
===========================================
 ArkNet Seeder: Countries Table
===========================================

This tool seeds the `countries` table with ISO 3166-1 codes
and names from the configured CSV file.

Usage:
  python seed_countries.py

Behavior:
  - Creates the table if not present
  - If empty, seeds all countries
  - If populated, you will be prompted:
      [Y] Update existing countries
      [n] Do not update
      [S] Skip seeding entirely

Controls:
  Ctrl+C / Ctrl+X   Exit gracefully at any time
"""

def print_help():
    print(get_help_text())
