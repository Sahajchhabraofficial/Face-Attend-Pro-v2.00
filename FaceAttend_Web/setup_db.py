"""
setup_db.py — Automatic Database Setup
Run this INSTEAD of the mysql command:   python setup_db.py

It will:
  1. Connect to MySQL using your config.py credentials
  2. Create the 'faceattend' database if it doesn't exist
  3. Create both tables (students + attendance)
  4. Confirm everything is ready
"""

import sys

# ── Step 1: Check mysql-connector is installed ───────────────────
try:
    import mysql.connector
except ImportError:
    print("❌  mysql-connector-python is not installed.")
    print("    Run:  pip install mysql-connector-python")
    sys.exit(1)

# ── Step 2: Load config ──────────────────────────────────────────
try:
    from config import DB_CONFIG
except ImportError:
    print("❌  config.py not found. Make sure you're running this")
    print("    from inside the FaceAttend_Web folder.")
    sys.exit(1)

print("\n🚀  FaceAttend Pro — Automatic Database Setup")
print("─" * 46)

# ── Step 3: Connect WITHOUT specifying database first ────────────
# We connect to MySQL itself (no DB selected) to create the DB
connect_config = {
    "host":     DB_CONFIG["host"],
    "port":     DB_CONFIG.get("port", 3306),
    "user":     DB_CONFIG["user"],
    "password": DB_CONFIG["password"],
}

try:
    con = mysql.connector.connect(**connect_config)
    print(f"✅  Connected to MySQL at {connect_config['host']}")
except mysql.connector.Error as e:
    print(f"\n❌  Cannot connect to MySQL!")
    print(f"    Error: {e}")
    print(f"\n    Things to check:")
    print(f"    • Is MySQL running? Open 'Services' and look for MySQL")
    print(f"    • Is your password correct in config.py?")
    print(f"    • Is the host 'localhost' correct?")
    sys.exit(1)

cur = con.cursor()

# ── Step 4: Create database ──────────────────────────────────────
db_name = DB_CONFIG["database"]
try:
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    print(f"✅  Database '{db_name}' ready")
except Exception as e:
    print(f"❌  Could not create database: {e}")
    sys.exit(1)

cur.execute(f"USE `{db_name}`")

# ── Step 5: Create students table ────────────────────────────────
try:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id         INT          NOT NULL,
            name       VARCHAR(120) NOT NULL,
            roll       VARCHAR(30)  NOT NULL UNIQUE,
            registered DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("✅  Table 'students' ready")
except Exception as e:
    print(f"❌  Could not create students table: {e}")
    sys.exit(1)

# ── Step 6: Create attendance table ──────────────────────────────
try:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id         INT          NOT NULL AUTO_INCREMENT,
            student_id INT          NOT NULL,
            name       VARCHAR(120) NOT NULL,
            time       TIME         NOT NULL,
            date       DATE         NOT NULL,
            created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_student_day (student_id, date),
            FOREIGN KEY (student_id)
                REFERENCES students(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("✅  Table 'attendance' ready")
except Exception as e:
    print(f"❌  Could not create attendance table: {e}")
    sys.exit(1)

# ── Step 7: Create indexes ────────────────────────────────────────
for idx_sql in [
    "CREATE INDEX IF NOT EXISTS idx_att_date    ON attendance (date)",
    "CREATE INDEX IF NOT EXISTS idx_att_student ON attendance (student_id)",
]:
    try:
        cur.execute(idx_sql)
    except Exception:
        pass   # Indexes may already exist — that's fine

con.commit()
cur.close()
con.close()

# ── Done ─────────────────────────────────────────────────────────
print("\n" + "─" * 46)
print("🎉  Database setup complete!")
print(f"    Database : {db_name}")
print(f"    Tables   : students, attendance")
print(f"\n▶   Now run:  python app.py\n")
