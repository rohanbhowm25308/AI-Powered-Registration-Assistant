"""
Generates a synthetic student-eligibility dataset.

There's no real historical registration data to train on, so this script
builds a plausible one: for every (student, course) pair it labels
"eligible" using the same CGPA/backlog rules shown in the UI, then adds
realistic noise (borderline students who got manual approval/rejection,
measurement noise on CGPA) so the downstream model has to learn a soft
decision boundary rather than just memorizing a threshold.

Run:  python generate_training_data.py
Output: student_eligibility_data.csv (in this folder)
"""
import csv
import random
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from courses import COURSES, DEPARTMENTS

random.seed(42)
N_STUDENTS = 1500
OUT_PATH = os.path.join(os.path.dirname(__file__), "student_eligibility_data.csv")


def sample_student():
    cgpa = round(min(10.0, max(3.0, random.gauss(7.0, 1.3))), 2)
    backlog = max(0, int(random.gauss(1.0, 1.4)))
    semester = random.choice([3, 4, 5, 6, 7, 8])
    dept = random.choice(DEPARTMENTS)
    return cgpa, backlog, semester, dept


def label_eligibility(cgpa, backlog, course):
    """Rule-based ground truth with borderline noise, mimicking real
    admin overrides (e.g. a student 0.1 CGPA short who was let in anyway,
    or a clean-on-paper student rejected for an undisclosed reason)."""
    base_eligible = cgpa >= course["min_cgpa"] and backlog <= course["max_backlog"]

    cgpa_margin = cgpa - course["min_cgpa"]
    backlog_margin = course["max_backlog"] - backlog
    is_borderline = abs(cgpa_margin) < 0.3 or abs(backlog_margin) <= 0

    if is_borderline and random.random() < 0.12:
        return int(not base_eligible)
    return int(base_eligible)


def main():
    rows = []
    for _ in range(N_STUDENTS):
        cgpa, backlog, semester, dept = sample_student()
        for course in COURSES:
            eligible = label_eligibility(cgpa, backlog, course)
            rows.append({
                "cgpa": cgpa,
                "backlog": backlog,
                "semester": semester,
                "department": dept,
                "course_id": course["id"],
                "course_min_cgpa": course["min_cgpa"],
                "course_max_backlog": course["max_backlog"],
                "eligible": eligible,
            })

    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
