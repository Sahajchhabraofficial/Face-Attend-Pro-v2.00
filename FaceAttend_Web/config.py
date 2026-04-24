import os

# ── PostgreSQL (Render) ─────────────────────────────

# This must match the Environment Variable name in Render
DATABASE_URL = os.getenv("postgresql://postgresql_cn6z_user:n7pt3bNZ2R9BdAOudlEtRYtxtRwxQhdh@dpg-d7lm0vu8bjmc73afagng-a.ohio-postgres.render.com/postgresql_cn6z")


# ── Optional Settings (you can keep or ignore) ──────

DEBUG = True
PORT = int(os.getenv("PORT", 10000))