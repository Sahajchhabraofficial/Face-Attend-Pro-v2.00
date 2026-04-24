# config.py — Database Configuration
# ─────────────────────────────────────────────────────────────────
# Edit these values to match YOUR MySQL setup before running.
# ─────────────────────────────────────────────────────────────────

import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

# ─────────────────────────────────────────────────────────────────
# Connection pool size — how many parallel DB connections to allow.
# 5 is fine for local/school use. Increase for production.
# ─────────────────────────────────────────────────────────────────
POOL_SIZE = 5
