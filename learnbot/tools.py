"""
LangChain tools for LearnSphere — reads from real database.
"""

import json
import re
import uuid
from typing import Dict, Any
from langchain_core.tools import tool
from .database import get_db


def _parse_course_id(raw: Any) -> str:
    """Handle both plain string and dict input from LLM agent."""
    if isinstance(raw, dict):
        raw = raw.get("course_id", "")
    elif isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            parsed = json.loads(raw.replace("'", '"'))
            raw = parsed.get("course_id", raw)
        except Exception:
            match = re.search(
                r"['\"]course_id['\"]\s*:\s*['\"]([^'\"]+)['\"]", raw
            )
            if match:
                raw = match.group(1)
    return str(raw).strip().upper()


def _parse_student_course(student_raw: Any, course_raw: Any):
    """
    Parse student_id and course_id handling all possible
    formats the LLM agent might send.
    """
    student_id = str(student_raw).strip()
    course_id  = str(course_raw).strip()

    # Case 1 — student_raw is a dict object
    # e.g. {"student_id": "STU003", "course_id": "GEN401"}
    if isinstance(student_raw, dict):
        student_id = str(student_raw.get("student_id", "STU001")).strip()
        course_id  = str(student_raw.get("course_id",  course_raw)).strip()
        return student_id.upper(), course_id.upper()

    # Case 2 — student_raw is a stringified dict
    # e.g. "{'student_id': 'STU003', 'course_id': 'GEN401'}"
    if student_id.startswith("{"):
        try:
            # Replace single quotes with double for valid JSON
            parsed     = json.loads(student_id.replace("'", '"'))
            student_id = str(parsed.get("student_id", "STU001")).strip()
            course_id  = str(parsed.get("course_id",  course_raw)).strip()
            return student_id.upper(), course_id.upper()
        except json.JSONDecodeError:
            # Fallback — extract with regex
            sid_match = re.search(
                r"['\"]student_id['\"]\s*:\s*['\"]([^'\"]+)['\"]",
                student_id
            )
            cid_match = re.search(
                r"['\"]course_id['\"]\s*:\s*['\"]([^'\"]+)['\"]",
                student_id
            )
            if sid_match:
                student_id = sid_match.group(1).strip()
            if cid_match:
                course_id  = cid_match.group(1).strip()
            return student_id.upper(), course_id.upper()

    # Case 3 — course_raw is also a stringified dict
    # e.g. "{'course_id': 'GEN401'}"
    if course_id.startswith("{"):
        try:
            parsed    = json.loads(course_id.replace("'", '"'))
            course_id = str(parsed.get("course_id", course_id)).strip()
        except json.JSONDecodeError:
            match = re.search(
                r"['\"]course_id['\"]\s*:\s*['\"]([^'\"]+)['\"]",
                course_id
            )
            if match:
                course_id = match.group(1).strip()

    return student_id.upper(), course_id.upper()



# ── Tool 1 — get_course_info ──────────────────────────────────────

@tool
def get_course_info(course_id: str) -> Dict[str, Any]:
    """
    Retrieve course information from the LearnSphere catalog.

    Args:
        course_id: The unique course identifier (e.g. 'CS101', 'DS201')

    Returns:
        Dict with title, description, prerequisites, modules, duration

    Raises:
        ValueError: If course_id is not found in the catalog

    Example:
        get_course_info('CS101') -> {'title': 'Python Basics', ...}
    """
    course_id = _parse_course_id(course_id)

    with get_db() as conn:
        cur = conn.cursor()

        # Get course
        cur.execute("""
            SELECT course_id, title, description, duration, enrolled
            FROM courses
            WHERE course_id = ?
        """, (course_id,))
        row = cur.fetchone()

        if not row:
            # Return available courses instead of crashing
            cur.execute("SELECT course_id FROM courses")
            available = [r["course_id"] for r in cur.fetchall()]
            return {
                "error":     f"Course '{course_id}' not found.",
                "available": available,
                "message":   f"Available courses: {', '.join(available)}",
            }

        # Get modules
        cur.execute("""
            SELECT module_name FROM modules
            WHERE course_id = ?
            ORDER BY order_index
        """, (course_id,))
        modules = [r["module_name"] for r in cur.fetchall()]

        # Get prerequisites
        cur.execute("""
            SELECT p.prereq_id, c.title
            FROM prerequisites p
            JOIN courses c ON c.course_id = p.prereq_id
            WHERE p.course_id = ?
        """, (course_id,))
        prereqs_rows = cur.fetchall()
        prereqs = [r["title"] for r in prereqs_rows] if prereqs_rows else ["None"]

    return {
        "course_id":     dict(row)["course_id"],
        "title":         dict(row)["title"],
        "description":   dict(row)["description"],
        "duration":      dict(row)["duration"],
        "enrolled":      dict(row)["enrolled"],
        "prerequisites": prereqs,
        "modules":       modules,
    }


# ── Tool 2 — check_enrollment_status ─────────────────────────────

@tool
def check_enrollment_status(student_id: str, course_id: str = "") -> Dict[str, Any]:
    """
    Check a student's enrollment status for a specific course.

    Args:
        student_id: The student's unique ID (e.g. 'STU001') or a dictionary containing student_id and course_id.
        course_id:  The course identifier (e.g. 'CS101'). Optional if provided in student_id.

    Returns:
        Dict with active status, completion percentage, certificate date

    Example:
        check_enrollment_status('STU001', 'CS101') -> {'active': True, ...}
    """
    # Safe fallback inside the parser if course_id wasn't passed as a separate argument
    student_id, course_id = _parse_student_course(student_id, course_id)

    print(f"[TOOL] check_enrollment_status | student={student_id} course={course_id}")

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                e.active,
                e.completion_pct,
                e.certificate_date,
                e.enrolled_at,
                s.name  AS student_name,
                c.title AS course_title
            FROM enrollments e
            JOIN students s ON s.student_id = e.student_id
            JOIN courses  c ON c.course_id  = e.course_id
            WHERE e.student_id = ?
              AND e.course_id  = ?
        """, (student_id, course_id))
        row = cur.fetchone()

    if not row:
        return {
            "active":           False,
            "completion_pct":   0,
            "certificate_date": None,
            "message": (
                f"No enrollment found for student {student_id} "
                f"in course {course_id}."
            ),
        }

    row = dict(row)
    return {
        "active":           bool(row["active"]),
        "completion_pct":   row["completion_pct"],
        "certificate_date": row["certificate_date"],
        "enrolled_at":      row["enrolled_at"],
        "student_name":     row["student_name"],
        "course_title":     row["course_title"],
        "message": (
            f"{row['student_name']} is "
            f"{'actively enrolled' if row['active'] else 'not active'} "
            f"in {row['course_title']} "
            f"with {row['completion_pct']}% completion."
        ),
    }

# ── Tool 3 — create_support_ticket ───────────────────────────────

@tool
def create_support_ticket(
    issue_description: str,
    priority: str = "MED",
    student_id: str = "GUEST",
) -> Dict[str, Any]:
    """
    Create a support ticket for a student issue.
    student_id is optional — defaults to GUEST if not provided.

    Args:
        issue_description: Clear description of the problem (REQUIRED)
        priority:          Ticket priority — LOW, MED, HIGH (default MED)
        student_id:        Student unique ID (optional, default GUEST)

    Returns:
        Dict with ticket_id, priority, estimated_resolution, status

    Example:
        create_support_ticket('Cannot access course videos', 'HIGH')
    """
    # Handle dict input from agent
    if isinstance(issue_description, dict):
        data              = issue_description
        issue_description = data.get("issue_description", "No description")
        priority          = data.get("priority",          priority)
        student_id        = data.get("student_id",        student_id)

    # Sanitize priority
    priority = str(priority).strip().upper()
    if priority not in {"LOW", "MED", "HIGH"}:
        priority = "MED"

    resolution_time = {
        "LOW":  "5-7 business days",
        "MED":  "2-3 business days",
        "HIGH": "24 hours",
    }

    ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
    estimated = resolution_time[priority]

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO support_tickets
                (ticket_id, student_id, issue_description,
                 priority, status, estimated_resolution)
            VALUES (?, ?, ?, ?, 'Open', ?)
        """, (ticket_id, student_id, issue_description, priority, estimated))

    return {
        "ticket_id":            ticket_id,
        "student_id":           student_id,
        "issue_description":    issue_description,
        "priority":             priority,
        "estimated_resolution": estimated,
        "status":               "Open",
        "message": (
            f"Support ticket {ticket_id} created successfully. "
            f"Priority: {priority}. "
            f"Expected resolution: {estimated}. "
            f"Our team will contact you shortly."
        ),
    }


# ── Tool 4 — get_faq_answer ───────────────────────────────────────

@tool
def get_faq_answer(question: str) -> Dict[str, Any]:
    """
    Look up an answer from the LearnSphere FAQ knowledge base.

    Args:
        question: The student's question as a string

    Returns:
        Dict with answer, confidence score, and related articles

    Example:
        get_faq_answer('How do I reset my password?')
    """
    # Handle dict input
    if isinstance(question, dict):
        question = question.get("question", "")

    question = str(question).strip()
    if not question:
        return {
            "answer":           "Please provide a question.",
            "confidence":       0.0,
            "related_articles": [],
        }

    q_lower = question.lower()

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT keyword, answer, confidence, related_articles FROM faq")
        rows = cur.fetchall()

    # Find matching FAQ entry
    for row in rows:
        row = dict(row)
        if row["keyword"] in q_lower:
            related = row["related_articles"].split(",") if row["related_articles"] else []
            return {
                "answer":           row["answer"],
                "confidence":       row["confidence"],
                "related_articles": related,
            }

    # No match found
    return {
        "answer":           "I could not find a direct FAQ answer. A support ticket will be created for you.",
        "confidence":       0.0,
        "related_articles": ["Contact Support"],
    }