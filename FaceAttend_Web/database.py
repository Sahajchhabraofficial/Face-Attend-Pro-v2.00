"""
database.py — PostgreSQL Backend | FaceAttend Pro v3.0
Works locally AND on Render.com

Uses psycopg2 with connection pooling.
Tables are auto-created on first run.
"""

import psycopg2
import psycopg2.pool
import psycopg2.extras
from datetime import date, datetime
from config import DATABASE_URL, LOCAL_DB, POOL_SIZE

# ════════════════════════════════════════════════════════════════════
#  CONNECTION POOL
# ════════════════════════════════════════════════════════════════════
_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        if DATABASE_URL:
            # Render — use the DATABASE_URL directly
            _pool = psycopg2.pool.ThreadedConnectionPool(
                1, POOL_SIZE,
                dsn=DATABASE_URL,
                sslmode="require"
            )
        else:
            # Local fallback
            _pool = psycopg2.pool.ThreadedConnectionPool(
                1, POOL_SIZE,
                host=LOCAL_DB["host"],
                port=LOCAL_DB["port"],
                user=LOCAL_DB["user"],
                password=LOCAL_DB["password"],
                dbname=LOCAL_DB["database"]
            )
    return _pool


def _conn():
    return _get_pool().getconn()


def _put(con):
    _get_pool().putconn(con)


def _exec(sql, params=(), fetch="none"):
    """
    Execute SQL safely.
    fetch = 'one'  -> single dict or None
    fetch = 'all'  -> list of dicts
    fetch = 'none' -> rowcount
    """
    con = _conn()
    try:
        with con.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
            con.commit()
            return cur.rowcount
    except Exception:
        con.rollback()
        raise
    finally:
        _put(con)


# ════════════════════════════════════════════════════════════════════
#  AUTO CREATE TABLES (runs on first startup)
# ════════════════════════════════════════════════════════════════════
def init_db():
    """Create tables if they don't exist. Called once on app start."""
    con = _conn()
    try:
        with con.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id         INTEGER      NOT NULL,
                    name       VARCHAR(120) NOT NULL,
                    roll       VARCHAR(30)  NOT NULL UNIQUE,
                    registered TIMESTAMP    NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id         SERIAL       PRIMARY KEY,
                    student_id INTEGER      NOT NULL,
                    name       VARCHAR(120) NOT NULL,
                    time       TIME         NOT NULL,
                    date       DATE         NOT NULL,
                    created_at TIMESTAMP    NOT NULL DEFAULT NOW(),
                    UNIQUE (student_id, date),
                    FOREIGN KEY (student_id)
                        REFERENCES students(id) ON DELETE CASCADE
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_att_date
                ON attendance (date)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_att_student
                ON attendance (student_id)
            """)
        con.commit()
        print("✅  Tables ready.")
    except Exception as e:
        con.rollback()
        print(f"❌  Table creation failed: {e}")
        raise
    finally:
        _put(con)


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
        rows = _exec(
            "SELECT * FROM students ORDER BY id",
            fetch="all"
        )
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
        row = _exec(
            "SELECT COALESCE(MAX(id), 0) AS max_id FROM students",
            fetch="one"
        )
        return (row["max_id"] if row else 0) + 1

    def total(self):
        row = _exec(
            "SELECT COUNT(*) AS cnt FROM students",
            fetch="one"
        )
        return row["cnt"] if row else 0


# ════════════════════════════════════════════════════════════════════
#  ATTENDANCE DATABASE
# ════════════════════════════════════════════════════════════════════
class AttendanceDB:

    def mark(self, student_id, name):
        """
        Mark attendance for today.
        Returns True if newly marked, False if already marked.
        INSERT ... ON CONFLICT DO NOTHING handles duplicates cleanly.
        """
        today = date.today()
        now   = datetime.now().strftime("%H:%M:%S")
        try:
            con = _conn()
            try:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO attendance (student_id, name, time, date)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (student_id, date) DO NOTHING
                        """,
                        (student_id, name, now, today)
                    )
                    affected = cur.rowcount
                con.commit()
                return affected > 0
            except Exception:
                con.rollback()
                return False
            finally:
                _put(con)
        except Exception:
            return False

    def get_today(self):
        return self.get_by_date(date.today().isoformat())

    def get_by_date(self, date_str):
        rows = _exec(
            "SELECT student_id, name, time, date "
            "FROM attendance WHERE date = %s "
            "ORDER BY time",
            (date_str,), fetch="all"
        )
        result = []
        for r in (rows or []):
            # Format time and date as clean strings
            t = r["time"]
            time_str = t.strftime("%H:%M:%S") if hasattr(t, "strftime") else str(t)
            d = r["date"]
            date_out = d.isoformat() if hasattr(d, "isoformat") else str(d)
            result.append([str(r["student_id"]), r["name"], time_str, date_out])
        return result

    def get_all_dates(self):
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
