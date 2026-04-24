"""
database.py — MySQL Backend  |  FaceAttend Pro v2.0

Exact same public method signatures as the file-based prototype.
Only the internals changed — everything in app.py stays untouched.

Requires:  pip install mysql-connector-python
Setup:     mysql -u root -p < setup_db.sql
Config:    edit config.py with your credentials
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL")

def _conn():
    return psycopg2.connect(DATABASE_URL)

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
#  CONNECTION POOL  (shared by both classes)
# ════════════════════════════════════════════════════════════════════
_pool = None


def _get_pool():
    """Lazy-init a single connection pool for the whole app."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="faceattend_pool",
            pool_size=POOL_SIZE,
            **DB_CONFIG
        )
    return _pool


def _conn():
    """Grab a connection from the pool."""
    return _get_pool().get_connection()


def _exec(sql, params=(), fetch="none"):
    """
    Execute SQL and return results.
    fetch = 'one'  -> single dict or None
    fetch = 'all'  -> list of dicts
    fetch = 'none' -> lastrowid (for INSERT) or rowcount
    """
    con = _conn()
    cur = con.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        if fetch == "one":
            return cur.fetchone()
        if fetch == "all":
            return cur.fetchall()
        con.commit()
        return cur.lastrowid
    finally:
        cur.close()
        con.close()


# ════════════════════════════════════════════════════════════════════
#  STUDENT DATABASE
# ════════════════════════════════════════════════════════════════════
class StudentDB:
    """
    MySQL table: students
    Columns: id, name, roll, registered
    """

    def add_student(self, student_id, name, roll):
        _exec(
            "INSERT INTO students (id, name, roll, registered) "
            "VALUES (%s, %s, %s, %s)",
            (student_id, name, roll, datetime.now())
        )

    def get_students(self):
        """Returns {str_id: {name, roll, registered}, ...}"""
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
    """
    MySQL table: attendance
    Columns: id, student_id, name, time, date, created_at
    Unique constraint (student_id, date) prevents double-marking.
    """

    def mark(self, student_id, name):
        """
        Mark attendance for today.
        Returns True if newly marked, False if already marked.
        INSERT IGNORE silently skips duplicates (unique key on student_id+date).
        """
        today = date.today()
        now   = datetime.now().strftime("%H:%M:%S")
        try:
            con = _conn()
            cur = con.cursor()
            cur.execute(
                "INSERT IGNORE INTO attendance "
                "(student_id, name, time, date) VALUES (%s, %s, %s, %s)",
                (student_id, name, now, today)
            )
            affected = cur.rowcount
            con.commit()
            cur.close()
            con.close()
            return affected > 0
        except Exception:
            return False

    def get_today(self):
        return self.get_by_date(date.today().isoformat())

    def get_by_date(self, date_str):
        # Fetch raw values — format in Python to avoid % clashing with connector params
        rows = _exec(
            "SELECT student_id, name, time, date "
            "FROM attendance WHERE date = %s ORDER BY time",
            (date_str,), fetch="all"
        )
        result = []
        for r in (rows or []):
            # time comes back as timedelta from MySQL connector
            t = r["time"]
            if hasattr(t, "total_seconds"):
                total = int(t.total_seconds())
                h, rem = divmod(total, 3600)
                m, s   = divmod(rem, 60)
                time_str = f"{h:02d}:{m:02d}:{s:02d}"
            else:
                time_str = str(t)
            # date comes back as date object
            d = r["date"]
            date_out = d.isoformat() if hasattr(d, "isoformat") else str(d)
            result.append([str(r["student_id"]), r["name"], time_str, date_out])
        return result

    def get_all_dates(self):
        # Fetch raw date objects, convert to string in Python
        rows = _exec(
            "SELECT DISTINCT date FROM attendance ORDER BY date DESC",
            fetch="all"
        )
        result = []
        for r in (rows or []):
            d = r["date"]
            result.append(d.isoformat() if hasattr(d, "isoformat") else str(d))
        return result

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
