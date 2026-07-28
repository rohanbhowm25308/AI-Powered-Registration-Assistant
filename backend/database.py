"""
Lightweight SQLite persistence layer (no ORM needed for this schema).
"""
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "nexus.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll TEXT UNIQUE NOT NULL,
            dept TEXT,
            sem TEXT,
            cgpa REAL,
            backlog INTEGER,
            interests TEXT,
            skills TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS eligibility_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_roll TEXT,
            cgpa REAL,
            backlog INTEGER,
            eligible_course_ids TEXT,
            checked_at TEXT
        );

        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reg_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            roll TEXT,
            course_id TEXT NOT NULL,
            course_name TEXT NOT NULL,
            reg_date TEXT NOT NULL,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll TEXT,
            action TEXT NOT NULL,
            meta TEXT,
            created_at TEXT
        );
    """)
    conn.commit()
    conn.close()


def upsert_student(name, roll, dept, sem, cgpa, backlog, interests=None, skills=None):
    conn = get_conn()
    existing = conn.execute("SELECT interests, skills FROM students WHERE roll = ?", (roll,)).fetchone()
    interests = interests if interests is not None else (existing["interests"] if existing else None)
    skills = skills if skills is not None else (existing["skills"] if existing else None)
    conn.execute("""
        INSERT INTO students (name, roll, dept, sem, cgpa, backlog, interests, skills, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(roll) DO UPDATE SET
            name=excluded.name, dept=excluded.dept, sem=excluded.sem,
            cgpa=excluded.cgpa, backlog=excluded.backlog,
            interests=excluded.interests, skills=excluded.skills
    """, (name, roll, dept, sem, cgpa, backlog, interests, skills, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def update_student_skills(roll, skills_csv):
    """Updates skills for an existing student; no-op if the roll isn't known yet
    (the resume analyzer can run before a profile is saved)."""
    conn = get_conn()
    conn.execute("UPDATE students SET skills = ? WHERE roll = ?", (skills_csv, roll))
    conn.commit()
    conn.close()


def get_student(roll):
    conn = get_conn()
    row = conn.execute("SELECT * FROM students WHERE roll = ?", (roll,)).fetchone()
    conn.close()
    return dict(row) if row else None


def log_eligibility_check(roll, cgpa, backlog, eligible_course_ids):
    conn = get_conn()
    conn.execute("""
        INSERT INTO eligibility_checks (student_roll, cgpa, backlog, eligible_course_ids, checked_at)
        VALUES (?, ?, ?, ?, ?)
    """, (roll, cgpa, backlog, ",".join(eligible_course_ids), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def create_registration(reg_id, name, roll, course_id, course_name, reg_date):
    conn = get_conn()
    conn.execute("""
        INSERT INTO registrations (reg_id, name, roll, course_id, course_name, reg_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (reg_id, name, roll, course_id, course_name, reg_date, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_registration(reg_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM registrations WHERE reg_id = ?", (reg_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_registrations():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM registrations ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_registration(reg_id):
    conn = get_conn()
    cur = conn.execute("DELETE FROM registrations WHERE reg_id = ?", (reg_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def delete_all_registrations():
    conn = get_conn()
    cur = conn.execute("DELETE FROM registrations")
    conn.commit()
    count = cur.rowcount
    conn.close()
    return count


def count_eligibility_checks():
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as c FROM eligibility_checks WHERE eligible_course_ids != ''").fetchone()
    conn.close()
    return row["c"]


def is_course_full(course_id, seat_limit):
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as c FROM registrations WHERE course_id = ?", (course_id,)).fetchone()
    conn.close()
    return row["c"] >= seat_limit


def log_activity(roll, action, meta=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO activity_log (roll, action, meta, created_at) VALUES (?, ?, ?, ?)",
        (roll, action, meta, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def registrations_by_department():
    conn = get_conn()
    rows = conn.execute("""
        SELECT COALESCE(s.dept, 'Unknown') as dept, COUNT(*) as c
        FROM registrations r LEFT JOIN students s ON r.roll = s.roll
        GROUP BY COALESCE(s.dept, 'Unknown')
    """).fetchall()
    conn.close()
    return [{"dept": r["dept"], "count": r["c"]} for r in rows]


def registrations_timeline():
    conn = get_conn()
    rows = conn.execute("""
        SELECT date(created_at) as day, COUNT(*) as c
        FROM registrations
        GROUP BY date(created_at)
        ORDER BY day ASC
    """).fetchall()
    conn.close()
    return [{"day": r["day"], "count": r["c"]} for r in rows]