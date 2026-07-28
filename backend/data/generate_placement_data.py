"""
Generates a synthetic placement-outcome dataset used to train the
Placement Probability model.

Ground truth is a plausible formula combining CGPA, backlogs, the
course's employability index, and a student's skill count, plus noise
-- again standing in for real historical placement records, which
aren't available. Run:

    python data/generate_placement_data.py
"""
import csv
import os
import random
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from courses import COURSES, DEPARTMENTS

random.seed(7)
N_STUDENTS = 2000
OUT_PATH = os.path.join(os.path.dirname(__file__), "placement_data.csv")


def sample_student():
    cgpa = round(min(10.0, max(3.0, random.gauss(7.2, 1.2))), 2)
    backlog = max(0, int(random.gauss(0.8, 1.2)))
    semester = random.choice([5, 6, 7, 8])
    dept = random.choice(DEPARTMENTS)
    skills_count = max(0, int(random.gauss(4, 2)))
    return cgpa, backlog, semester, dept, skills_count


def placement_probability(cgpa, backlog, course, skills_count):
    score = (
        0.22 * cgpa
        - 0.35 * backlog
        + 2.6 * course["employability_index"]
        + 0.14 * min(skills_count, 8)
    )
    # squash to 0-1 with a logistic curve centered around a realistic pivot
    prob = 1 / (1 + pow(2.71828, -(score - 3.9) * 2.4))
    noisy = min(0.99, max(0.01, prob + random.gauss(0, 0.015)))
    return noisy


def main():
    rows = []
    for _ in range(N_STUDENTS):
        cgpa, backlog, semester, dept, skills_count = sample_student()
        course = random.choice(COURSES)
        prob = placement_probability(cgpa, backlog, course, skills_count)
        placed = int(random.random() < prob)
        rows.append({
            "cgpa": cgpa,
            "backlog": backlog,
            "semester": semester,
            "department": dept,
            "course_id": course["id"],
            "employability_index": course["employability_index"],
            "skills_count": skills_count,
            "placed": placed,
        })

    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
