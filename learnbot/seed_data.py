"""
Seed initial data into the database.
Run once to populate courses, students, enrollments, and FAQ.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from learnbot.database import init_db, get_db


def seed_courses():
    """Insert all courses, their modules and prerequisites."""
    courses = [
        {
            "course_id":   "CS101",
            "title":       "Python Basics",
            "description": "Introduction to Python programming for beginners",
            "duration":    "6 weeks",
            "enrolled":    1240,
            "prereqs":     [],
            "modules":     ["Variables", "Loops", "Functions", "OOP"],
        },
        {
            "course_id":   "DS201",
            "title":       "Data Science with Python",
            "description": "Hands-on data analysis using pandas, numpy, and matplotlib",
            "duration":    "8 weeks",
            "enrolled":    890,
            "prereqs":     ["CS101"],
            "modules":     ["Pandas", "NumPy", "Visualization", "Statistics"],
        },
        {
            "course_id":   "ML301",
            "title":       "Machine Learning Fundamentals",
            "description": "Core ML algorithms and model building",
            "duration":    "10 weeks",
            "enrolled":    560,
            "prereqs":     ["DS201"],
            "modules":     ["Regression", "Classification", "Clustering", "Neural Nets"],
        },
        {
            "course_id":   "GEN401",
            "title":       "Generative AI with LangChain",
            "description": "Build LLM-powered apps using LangChain and LangGraph",
            "duration":    "8 weeks",
            "enrolled":    320,
            "prereqs":     ["ML301"],
            "modules":     ["Prompt Engineering", "Agents", "RAG", "LangGraph"],
        },
    ]

    with get_db() as conn:
        cur = conn.cursor()
        for course in courses:
            # Insert course
            cur.execute("""
                INSERT OR IGNORE INTO courses
                    (course_id, title, description, duration, enrolled)
                VALUES (?, ?, ?, ?, ?)
            """, (
                course["course_id"],
                course["title"],
                course["description"],
                course["duration"],
                course["enrolled"],
            ))

            # Insert modules
            for i, module in enumerate(course["modules"]):
                cur.execute("""
                    INSERT OR IGNORE INTO modules
                        (course_id, module_name, order_index)
                    VALUES (?, ?, ?)
                """, (course["course_id"], module, i + 1))

            # Insert prerequisites
            for prereq in course["prereqs"]:
                cur.execute("""
                    INSERT OR IGNORE INTO prerequisites
                        (course_id, prereq_id)
                    VALUES (?, ?)
                """, (course["course_id"], prereq))

    print(f"[SEED] Inserted {len(courses)} courses")


def seed_students():
    """Insert sample students."""
    students = [
        ("STU001", "Ananya Sharma",   "ananya@example.com"),
        ("STU002", "Rahul Verma",     "rahul@example.com"),
        ("STU003", "Priya Nair",      "priya@example.com"),
        ("STU004", "Arjun Mehta",     "arjun@example.com"),
        ("STU005", "Kavya Reddy",     "kavya@example.com"),
    ]

    with get_db() as conn:
        cur = conn.cursor()
        for student_id, name, email in students:
            cur.execute("""
                INSERT OR IGNORE INTO students (student_id, name, email)
                VALUES (?, ?, ?)
            """, (student_id, name, email))

    print(f"[SEED] Inserted {len(students)} students")


def seed_enrollments():
    """Insert sample enrollments."""
    enrollments = [
        # (student_id, course_id, active, completion_pct, certificate_date)
        ("STU001", "CS101",  1, 85.0,  None),
        ("STU001", "DS201",  1, 40.0,  None),
        ("STU002", "CS101",  1, 100.0, "2026-04-15"),
        ("STU002", "ML301",  0, 10.0,  None),
        ("STU003", "GEN401", 1, 60.0,  None),
        ("STU003", "CS101",  1, 100.0, "2026-03-20"),
        ("STU004", "CS101",  1, 55.0,  None),
        ("STU004", "DS201",  1, 20.0,  None),
        ("STU005", "ML301",  1, 75.0,  None),
    ]

    with get_db() as conn:
        cur = conn.cursor()
        for student_id, course_id, active, pct, cert_date in enrollments:
            cur.execute("""
                INSERT OR IGNORE INTO enrollments
                    (student_id, course_id, active,
                     completion_pct, certificate_date)
                VALUES (?, ?, ?, ?, ?)
            """, (student_id, course_id, active, pct, cert_date))

    print(f"[SEED] Inserted {len(enrollments)} enrollments")


def seed_faq():
    """Insert FAQ entries."""
    faqs = [
        (
            "password",
            "Go to Settings > Security > Reset Password. Enter your registered email and check your inbox.",
            0.97,
            "Account Security,Login Issues",
        ),
        (
            "refund",
            "Refunds available within 7 days. Go to My Courses > Purchase History > Request Refund.",
            0.95,
            "Billing FAQ,Course Access",
        ),
        (
            "certificate",
            "Complete 100% of the course. Then go to My Courses > Completed > Download Certificate. If download fails, clear your browser cache and retry.",
            0.98,
            "Course Completion,Certificate Download",
        ),
        (
            "download",
            "If download fails: (1) Clear browser cache, (2) Use a different browser, (3) Disable VPN or ad-blocker, (4) Check internet connection.",
            0.95,
            "Download Issues,Browser Compatibility",
        ),
        (
            "billing",
            "For billing issues go to My Account > Billing History. For duplicate charges contact support@learnsphere.com with your invoice number.",
            0.94,
            "Billing FAQ,Payment Issues",
        ),
        (
            "email",
            "Go to Settings > Profile > Edit Email and verify the new address.",
            0.93,
            "Account Settings,Profile Management",
        ),
        (
            "access",
            "If you cannot access your course, clear browser cache. Check enrollment under My Courses. If payment failed go to Billing > Retry Payment.",
            0.90,
            "Course Access,Technical Issues",
        ),
        (
            "video",
            "If videos are not loading, check your internet connection and try a different browser. Disable VPN or ad-blocker.",
            0.92,
            "Video Playback,Technical Issues",
        ),
        (
            "login",
            "If you cannot log in, reset your password via Settings > Security > Reset Password.",
            0.95,
            "Login Issues,Account Security",
        ),
    ]

    with get_db() as conn:
        cur = conn.cursor()
        for keyword, answer, confidence, related in faqs:
            cur.execute("""
                INSERT OR IGNORE INTO faq
                    (keyword, answer, confidence, related_articles)
                VALUES (?, ?, ?, ?)
            """, (keyword, answer, confidence, related))

    print(f"[SEED] Inserted {len(faqs)} FAQ entries")


def seed_all():
    """Run all seed functions."""
    print("\n[SEED] Starting database seed...\n")
    init_db()
    seed_courses()
    seed_students()
    seed_enrollments()
    seed_faq()
    print("\n[SEED] Database seeded successfully!")
    print(f"[SEED] Database file: learnbot.db\n")


if __name__ == "__main__":
    seed_all()