"""
Achievement badges — computed on the fly from the database, no extra
storage needed. Each badge is a pure function of what's already known
about a student, so badges stay correct even if data changes later.
"""
import database

BADGE_CATALOG = [
    {"id": "profile", "name": "First Steps", "icon": "🧭", "desc": "Saved your student profile"},
    {"id": "eligibility", "name": "Eligibility Checked", "icon": "✅", "desc": "Ran an eligibility check"},
    {"id": "registered", "name": "Registered", "icon": "🎓", "desc": "Registered for a course"},
    {"id": "multi_course", "name": "Multi-Course Learner", "icon": "📚", "desc": "Registered for 2+ courses"},
    {"id": "high_achiever", "name": "High Achiever", "icon": "🏆", "desc": "CGPA of 8.5 or above"},
    {"id": "clean_record", "name": "Clean Record", "icon": "✨", "desc": "Zero active backlogs"},
    {"id": "resume_ready", "name": "Resume Ready", "icon": "📄", "desc": "Ran the AI resume analyzer"},
    {"id": "career_planner", "name": "Career Planner", "icon": "🗺️", "desc": "Generated a career roadmap"},
]


def get_badges(roll):
    """Returns (earned_list, locked_list) for a given roll number."""
    if not roll:
        return [], BADGE_CATALOG

    conn = database.get_conn()
    student = conn.execute("SELECT * FROM students WHERE roll = ?", (roll,)).fetchone()
    reg_count = conn.execute("SELECT COUNT(*) c FROM registrations WHERE roll = ?", (roll,)).fetchone()["c"]
    elig_count = conn.execute("SELECT COUNT(*) c FROM eligibility_checks WHERE student_roll = ?", (roll,)).fetchone()["c"]
    resume_count = conn.execute(
        "SELECT COUNT(*) c FROM activity_log WHERE roll = ? AND action = 'resume_analyzed'", (roll,)
    ).fetchone()["c"]
    roadmap_count = conn.execute(
        "SELECT COUNT(*) c FROM activity_log WHERE roll = ? AND action = 'roadmap_generated'", (roll,)
    ).fetchone()["c"]
    conn.close()

    earned_ids = set()
    if student:
        earned_ids.add("profile")
        if student["cgpa"] is not None and student["cgpa"] >= 8.5:
            earned_ids.add("high_achiever")
        if student["backlog"] is not None and student["backlog"] == 0:
            earned_ids.add("clean_record")
    if elig_count > 0:
        earned_ids.add("eligibility")
    if reg_count >= 1:
        earned_ids.add("registered")
    if reg_count >= 2:
        earned_ids.add("multi_course")
    if resume_count > 0:
        earned_ids.add("resume_ready")
    if roadmap_count > 0:
        earned_ids.add("career_planner")

    earned = [b for b in BADGE_CATALOG if b["id"] in earned_ids]
    locked = [b for b in BADGE_CATALOG if b["id"] not in earned_ids]
    return earned, locked
