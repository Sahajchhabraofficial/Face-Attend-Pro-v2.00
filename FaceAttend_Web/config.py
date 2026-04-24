import os

# ── PostgreSQL (Render) ─────────────────────────────

# This must match the Environment Variable name in Render
DATABASE_URL = os.getenv("DATABASE_URL")


# ── Optional Settings (you can keep or ignore) ──────

DEBUG = True
PORT = int(os.getenv("PORT", 10000))