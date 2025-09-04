#!/usr/bin/env python3
"""
load_countries.py
-----------------
Reads countries.csv and returns list of dicts.
"""

import csv


def load_countries(file_path: str):
    countries = []
    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            iso_code = row.get("Code") or row.get("ISO") or row.get("iso_code")
            name = row.get("Name") or row.get("Country") or row.get("name")
            if iso_code and name:
                countries.append({"iso_code": iso_code.strip(), "name": name.strip()})
    return countries
