#!/usr/bin/env python3
"""
load_config.py
--------------
Reads .env and config.ini, returns as dict.
"""

import os
from dotenv import load_dotenv
import configparser


def load_config():
    load_dotenv()
    config = configparser.ConfigParser()
    config.read("config.ini")

    # Collect all env variables we might care about
    env_vars = {
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASS": os.getenv("DB_PASS"),
        "SSH_HOST": os.getenv("SSH_HOST"),
        "SSH_PORT": os.getenv("SSH_PORT"),
        "SSH_USER": os.getenv("SSH_USER"),
        "SSH_PASS": os.getenv("SSH_PASS"),
    }

    return {
        "postgres": {
            "host": config.get("postgres", "host"),
            "port": config.get("postgres", "port"),
            "default_db": config.get("postgres", "default_db"),
        },
        "files": {
            "countries": config.get("files", "countries"),
        },
        "env": env_vars,
    }
