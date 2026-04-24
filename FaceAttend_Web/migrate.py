"""
migrate.py — One-time migration from file storage → MySQL

Run AFTER setup_db.sql has been executed and config.py is filled in.

    python migrate.py

Imports:
  - data/students.json  → students table
  - data/attendance/*.csv → attendance table
"""

import json, csv, os, sys
from datetime import datetime
import mysql.connector
from config import DB_CONFIG

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
STUDENTS_FILE  = os.path.join(BASE_DIR, "data", "students.json")
ATTENDANCE_DIR = os.path.join(BASE_DIR, "data", "attendance")

def connect():
    return mysql.connector.connect(**DB_CONFIG)

def migrate_students(con):
    if not os.path.exists(STUDENTS_FILE):
        print("⚠  No students.json found — skipping students.")
        return 0

    with open(STUDENTS_FILE) as f:
        students = json.load(f)

    cur = con.cursor()
    count = 0
    for sid, s in students.items():
        try:
            cur.execute(
                "INSERT IGNORE INTO students (id, name, roll, registered) "
                "VALUES (%s, %s, %s, %s)",
                (int(sid), s["name"], s["roll"],
                 s.get("registered", datetime.now().isoformat())[:19])
            )
            if cur.rowcount:
                count += 1
                print(f"  ✅  Student  {sid}  {s['name']}")
            else:
                print(f"  ⏭   Skip (exists)  {sid}  {s['name']}")
        except Exception as e:
            print(f"  ❌  Error for {sid}: {e}")
    con.commit()
    cur.close()
    return count

def migrate_attendance(con):
    if not os.path.exists(ATTENDANCE_DIR):
        print("⚠  No attendance directory found — skipping.")
        return 0

    cur   = con.cursor()
    total = 0
    files = sorted([f for f in os.listdir(ATTENDANCE_DIR) if f.endswith(".csv")])

    for fname in files:
        date_str = fname.replace(".csv", "")
        path     = os.path.join(ATTENDANCE_DIR, fname)
        with open(path) as f:
            rows = list(csv.reader(f))

        day_count = 0
        for row in rows:
            if not row or len(row) < 3:
                continue
            sid, name, time = row[0], row[1], row[2]
            try:
                cur.execute(
                    "INSERT IGNORE INTO attendance "
                    "(student_id, name, time, date) VALUES (%s, %s, %s, %s)",
                    (int(sid), name, time, date_str)
                )
                if cur.rowcount:
                    day_count += 1
            except Exception as e:
                print(f"  ❌  {date_str} row {row}: {e}")
        con.commit()
        print(f"  📅  {date_str} → {day_count} records imported")
        total += day_count

    cur.close()
    return total


if __name__ == "__main__":
    print("\n🚀  FaceAttend — File → MySQL Migration\n" + "─" * 42)
    try:
        con = connect()
        print("✅  Connected to MySQL\n")
    except Exception as e:
        print(f"❌  Cannot connect to MySQL: {e}")
        print("    Check config.py credentials and run setup_db.sql first.")
        sys.exit(1)

    print("📂  Migrating students…")
    s_count = migrate_students(con)

    print(f"\n📂  Migrating attendance records…")
    a_count = migrate_attendance(con)

    con.close()
    print(f"\n{'─'*42}")
    print(f"✅  Migration complete!")
    print(f"    Students imported : {s_count}")
    print(f"    Attendance rows   : {a_count}")
    print(f"\nYou can now run:  python app.py\n")
