"""
Runtime wrapper around the trained placement-probability model, with a
formula-based fallback (same shape as the label-generating formula used
in data/generate_placement_data.py) if no model has been trained yet.
"""
import os
import math
import joblib
import pandas as pd

from courses import COURSE_BY_ID, DEPARTMENTS

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "placement_model.pkl")
ENCODERS_PATH = os.path.join(os.path.dirname(__file__), "models", "placement_encoders.pkl")

_bundle = None
_encoders = None
_attempted = False


def _load():
    global _bundle, _encoders, _attempted
    if _attempted:
        return
    _attempted = True
    if os.path.exists(MODEL_PATH) and os.path.exists(ENCODERS_PATH):
        _bundle = joblib.load(MODEL_PATH)
        _encoders = joblib.load(ENCODERS_PATH)


def is_model_loaded():
    _load()
    return _bundle is not None


def _fallback_probability(cgpa, backlog, course, skills_count):
    score = (
        0.22 * cgpa - 0.35 * backlog
        + 2.6 * course["employability_index"]
        + 0.14 * min(skills_count, 8)
    )
    prob = 1 / (1 + math.exp(-(score - 3.9) * 2.4))
    return max(0.01, min(0.99, prob))


def predict_placement(cgpa, backlog, semester, department, course_id, skills_count=0):
    course = COURSE_BY_ID.get(course_id)
    if not course:
        return {"error": "Unknown course"}

    _load()
    prob = None
    source = None
    if _bundle is not None:
        try:
            dept_safe = department if department in DEPARTMENTS else DEPARTMENTS[0]
            dept_enc = _encoders["department"].transform([dept_safe])[0]
            course_enc = _encoders["course_id"].transform([course_id])[0]
            row = pd.DataFrame([{
                "cgpa": cgpa, "backlog": backlog, "semester": semester,
                "department_enc": dept_enc, "course_id_enc": course_enc,
                "employability_index": course["employability_index"], "skills_count": skills_count,
            }])[_bundle["feature_cols"]]
            prob = float(_bundle["model"].predict_proba(row)[0][1])
            source = "ml_model"
        except Exception:
            prob = None

    if prob is None:
        prob = _fallback_probability(cgpa, backlog, course, skills_count)
        source = "formula_fallback"

    band = "High" if prob >= 0.7 else "Moderate" if prob >= 0.45 else "Developing"
    return {
        "course": course["name"],
        "probability_pct": round(prob * 100, 1),
        "band": band,
        "source": source,
    }