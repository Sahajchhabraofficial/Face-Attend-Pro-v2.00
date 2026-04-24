"""
database.py — PostgreSQL Backend  |  FaceAttend Pro

Works with Render PostgreSQL using DATABASE_URL
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime

# ── Connection ─────────────────────────────────────────────────────
DATABASE_URL = "postgresql://postgresql_cn6z_user:n7pt3bNZ2R9BdAOudlEtRYtxtRwxQhdh@dpg-d7lm0vu8bjmc73afagng-a.ohio-postgres.render.com/postgresql_cn6z"

def _conn():
    return psycopg2.connect(DATABASE_URL, sslmode='require')


def _exec(sql, params=(), fetch="none"):
    con = _conn()
    cur = con.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(sql, params)

        if fetch == "one":
            return cur.fetchone()
        if fetch == "all":
            return cur.fetchall()

        con.commit()
        return True
    finally:
        cur.close()
        con.close()


# ════════════════════════════════════════════════════════════════════
#  STUDENT DATABASE
# ════════════════════════════════════════════════════════════════════
class StudentDB:

    def add_student(self, student_id, name, roll):
        _exec(
            "INSERT INTO students (id, name, roll, registered) "
            "VALUES (%s, %s, %s, %s)",
            (student_id, name, roll, datetime.now())
        )

    def get_students(self):
        rows = _exec("SELECT * FROM students ORDER BY id", fetch="all")
        return {
            str(r["id"]): {
                "name":       r["name"],
                "roll":       r["roll"],
                "registered": str(r["registered"]),
            }
            for r in (rows or [])
        }

    def get_student(self, student_id):
        row = _exec(
            "SELECT * FROM students WHERE id = %s",
            (int(student_id),), fetch="one"
        )
        if not row:
            return None
        return {
            "name":       row["name"],
            "roll":       row["roll"],
            "registered": str(row["registered"]),
        }

    def delete_student(self, student_id):
        _exec("DELETE FROM students WHERE id = %s", (int(student_id),))

    def roll_exists(self, roll):
        row = _exec(
            "SELECT id FROM students WHERE LOWER(roll) = LOWER(%s)",
            (roll,), fetch="one"
        )
        return row is not None

    def next_id(self):
        row = _exec("SELECT MAX(id) AS max_id FROM students", fetch="one")
        max_id = row["max_id"] if row and row["max_id"] is not None else 0
        return max_id + 1

    def total(self):
        row = _exec("SELECT COUNT(*) AS cnt FROM students", fetch="one")
        return row["cnt"] if row else 0


# ════════════════════════════════════════════════════════════════════
#  ATTENDANCE DATABASE
# ════════════════════════════════════════════════════════════════════
class AttendanceDB:

    def mark(self, student_id, name):
        """
        Mark attendance once per day (PostgreSQL version)
        """
        today = date.today()
        now   = datetime.now().strftime("%H:%M:%S")

        try:
            con = _conn()
            cur = con.cursor()

            cur.execute(
                "INSERT INTO attendance (student_id, name, time, date) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (student_id, date) DO NOTHING",
                (student_id, name, now, today)
            )

            affected = cur.rowcount
            con.commit()

            cur.close()
            con.close()

            return affected > 0
        except Exception as e:
            print("DB Error:", e)
            return False

    def get_today(self):
        return self.get_by_date(date.today().isoformat())

    def get_by_date(self, date_str):
        rows = _exec(
            "SELECT student_id, name, time, date "
            "FROM attendance WHERE date = %s ORDER BY time",
            (date_str,), fetch="all"
        )
        result = []
        for r in (rows or []):
            result.append([
                str(r["student_id"]),
                r["name"],
                str(r["time"]),
                str(r["date"])
            ])
        return result

    def get_all_dates(self):
        rows = _exec(
            "SELECT DISTINCT date FROM attendance ORDER BY date DESC",
            fetch="all"
        )
        return [str(r["date"]) for r in (rows or [])]

    def already_marked(self, student_id):
        row = _exec(
            "SELECT id FROM attendance "
            "WHERE student_id = %s AND date = %s",
            (student_id, date.today()), fetch="one"
        )
        return row is not None

    def today_count(self):
        row = _exec(
            "SELECT COUNT(*) AS cnt FROM attendance WHERE date = %s",
            (date.today(),), fetch="one"
        )
        return row["cnt"] if row else 0

    def attendance_rate(self, total_students):
        if total_students == 0:
            return 0
        return int(self.today_count() / total_students * 100)