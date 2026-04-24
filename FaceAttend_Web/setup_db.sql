-- ═══════════════════════════════════════════════════════════════
--  FaceAttend Pro  |  PostgreSQL Database Setup
-- ═══════════════════════════════════════════════════════════════

-- ── Students table ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    roll        TEXT UNIQUE NOT NULL,
    registered  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ── Attendance table ───────────────────────────────────────────
-- One row per student per day (prevents duplicates)
CREATE TABLE IF NOT EXISTS attendance (
    id          SERIAL PRIMARY KEY,
    student_id  INT NOT NULL,
    name        TEXT NOT NULL,
    time        TIME NOT NULL,
    date        DATE NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_student_day UNIQUE (student_id, date),
    CONSTRAINT fk_student FOREIGN KEY (student_id)
        REFERENCES students(id) ON DELETE CASCADE
);

-- ── Indexes for performance ─────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_attendance_date
    ON attendance (date);

CREATE INDEX IF NOT EXISTS idx_attendance_student
    ON attendance (student_id);

-- ── Verify ─────────────────────────────────────────────────────
SELECT 'Database setup complete!' AS status;