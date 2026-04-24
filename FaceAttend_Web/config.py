# config.py — Database Configuration
# ─────────────────────────────────────────────────────────────────
# Edit these values to match YOUR MySQL setup before running.
# ─────────────────────────────────────────────────────────────────

DB_CONFIG = {
    "host":     "localhost",   # MySQL server host
    "port":     3306,          # MySQL port (default 3306)
    "user":     "root",        # your MySQL username
    "password": "FaceAttendBy$ahaj",  # ← CHANGE THIS
    "database": "faceattend",  # DB name (will be created by setup_db.sql)
}

# ─────────────────────────────────────────────────────────────────
# Connection pool size — how many parallel DB connections to allow.
# 5 is fine for local/school use. Increase for production.
# ─────────────────────────────────────────────────────────────────
POOL_SIZE = 5
