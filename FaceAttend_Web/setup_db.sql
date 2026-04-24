-- ═══════════════════════════════════════════════════════════════
--  FaceAttend Pro  |  MySQL Database Setup Script
--  Run once:  mysql -u root -p < setup_db.sql
-- ═══════════════════════════════════════════════════════════════

-- Create the database
CREATE DATABASE IF NOT EXISTS faceattend
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE faceattend;

-- ── Students table ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    id          INT           NOT NULL,
    name        VARCHAR(120)  NOT NULL,
    roll        VARCHAR(30)   NOT NULL UNIQUE,
    registered  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Attendance table ─────────────────────────────────────────────
--   One row per student per day (UNIQUE constraint prevents duplicates)
CREATE TABLE IF NOT EXISTS attendance (
    id          INT           NOT NULL AUTO_INCREMENT,
    student_id  INT           NOT NULL,
    name        VARCHAR(120)  NOT NULL,
    time        TIME          NOT NULL,
    date        DATE          NOT NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY  uq_student_day (student_id, date),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ── Indexes for fast queries ─────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_attendance_date
    ON attendance (date);

CREATE INDEX IF NOT EXISTS idx_attendance_student
    ON attendance (student_id);


-- ── Verify ───────────────────────────────────────────────────────
SELECT 'Database setup complete!' AS status;
SHOW TABLES;
