# config.py — Database Configuration
# ─────────────────────────────────────────────────────────────────
# Edit these values to match YOUR MySQL setup before running.
# ─────────────────────────────────────────────────────────────────

import os

DB_CONFIG = {
    "host": os.getenv("dpg-d7lm0vu8bjmc73afagng-a"),
    "user": os.getenv("postgresql_cn6z_user"),
    "password": os.getenv("n7pt3bNZ2R9BdAOudlEtRYtxtRwxQhdh"),
    "database": os.getenv("postgresql_cn6z"),
    "port":5432
}

# ─────────────────────────────────────────────────────────────────
# Connection pool size — how many parallel DB connections to allow.
# 5 is fine for local/school use. Increase for production.
# ─────────────────────────────────────────────────────────────────
POOL_SIZE = 5
