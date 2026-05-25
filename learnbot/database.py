"""
Database connection and table setup for LearnSphere.
Supports both SQLite (default) and PostgreSQL.
"""

import os
import sqlite3
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────
DB_TYPE = os.getenv("DB_TYPE", "sqlite")          # "sqlite" or "postgres"
SQLITE_PATH = os.getenv("SQLITE_PATH", "learnbot.db")
POSTGRES_URL = os.getenv("DATABASE_URL", "")


# ── SQLite connection ─────────────────────────────────────────────

@contextmanager
def get_sqlite_connection():
    """Get a SQLite connection as a context manager."""
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row    # returns rows as dicts
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── PostgreSQL connection ─────────────────────────────────────────

@contextmanager
def get_postgres_connection():
    """Get a PostgreSQL connection as a context manager."""
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        raise ImportError("Run: pip install psycopg2-binary")

    conn = psycopg2.connect(POSTGRES_URL)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Universal getter ──────────────────────────────────────────────

def get_db():
    """Returns the right connection based on DB_TYPE in .env"""
    if DB_TYPE == "postgres":
        return get_postgres_connection()
    return get_sqlite_connection()


# ── Create all tables ─────────────────────────────────────────────

def init_db():
    """
    Create all tables if they don't exist.
    Safe to run multiple times — uses IF NOT EXISTS.
    """
    with get_db() as conn:
        cur = conn.cursor()

        # Courses table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                course_id    TEXT PRIMARY KEY,
                title        TEXT NOT NULL,
                description  TEXT,
                duration     TEXT,
                enrolled     INTEGER DEFAULT 0,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Prerequisites table (many-to-many)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS prerequisites (
                course_id    TEXT NOT NULL,
                prereq_id    TEXT NOT NULL,
                PRIMARY KEY (course_id, prereq_id),
                FOREIGN KEY (course_id) REFERENCES courses(course_id),
                FOREIGN KEY (prereq_id) REFERENCES courses(course_id)
            )
        """)

        # Modules table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modules (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id    TEXT NOT NULL,
                module_name  TEXT NOT NULL,
                order_index  INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses(course_id)
            )
        """)

        # Students table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id   TEXT PRIMARY KEY,
                name         TEXT NOT NULL,
                email        TEXT UNIQUE NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Enrollments table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id       TEXT NOT NULL,
                course_id        TEXT NOT NULL,
                active           INTEGER DEFAULT 1,
                completion_pct   REAL DEFAULT 0.0,
                certificate_date TEXT,
                enrolled_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (student_id, course_id),
                FOREIGN KEY (student_id) REFERENCES students(student_id),
                FOREIGN KEY (course_id)  REFERENCES courses(course_id)
            )
        """)

        # Support tickets table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                ticket_id            TEXT PRIMARY KEY,
                student_id           TEXT,
                issue_description    TEXT NOT NULL,
                priority             TEXT DEFAULT 'MED',
                status               TEXT DEFAULT 'Open',
                estimated_resolution TEXT,
                created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at          TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(student_id)
            )
        """)

        # FAQ table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS faq (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword          TEXT UNIQUE NOT NULL,
                answer           TEXT NOT NULL,
                confidence       REAL DEFAULT 1.0,
                related_articles TEXT,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    print(f"[DB] Tables created successfully ({DB_TYPE}: {SQLITE_PATH if DB_TYPE == 'sqlite' else POSTGRES_URL})")


if __name__ == "__main__":
    init_db()
    print("[DB] Database initialized.")