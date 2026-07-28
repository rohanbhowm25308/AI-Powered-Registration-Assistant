"""
Runtime wrapper around the trained eligibility model.

If backend/models/eligibility_model.pkl exists (produced by train_model.py)
it's used for predictions. Otherwise this transparently falls back to the
same rule-based thresholds used to label the training data, so the API
works out of the box even before anyone has trained a model.
"""
import os
import joblib
import pandas as pd

from courses import COURSES, DEPARTMENTS

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "eligibility_model.pkl")
ENCODERS_PATH = os.path.join(os.path.dirname(__file__), "models", "encoders.pkl")

_model_bundle = None
_encoders = None
_load_attempted = False


def _load():
    global _model_bundle, _encoders, _load_attempted
    if _load_attempted:
        return
    _load_attempted = True
    if os.path.exists(MODEL_PATH) and os.path.exists(ENCODERS_PATH):
        _model_bundle = joblib.load(MODEL_PATH)
        _encoders = joblib.load(ENCODERS_PATH)


def is_ml_model_loaded():
    _load()
    return _model_bundle is not None


def _rule_based_confidence(cgpa, backlog, course):
    """Soft confidence score used when no trained model is available."""
    eligible = cgpa >= course["min_cgpa"] and backlog <= course["max_backlog"]
    cgpa_margin = cgpa - course["min_cgpa"]
    confidence = 0.5 + min(0.45, abs(cgpa_margin) * 0.15)
    if backlog > course["max_backlog"]:
        confidence = max(0.55, confidence - 0.1 * (backlog - course["max_backlog"]))
    confidence = max(0.05, min(0.99, confidence))
    return eligible, confidence


def predict_eligibility(cgpa, backlog, semester, department):
    """
    Returns a list of dicts, one per course:
    { id, name, credits, eligible, confidence }

    Each course is scored independently. If the trained model doesn't
    recognize a course (e.g. courses.py was updated but the model hasn't
    been retrained yet), that single course transparently falls back to
    rule-based scoring instead of failing the entire request.
    """
    _load()
    results = []

    dept_enc = None
    if _model_bundle is not None:
        dept_encoder = _encoders["department"]
        dept_safe = department if department in DEPARTMENTS else DEPARTMENTS[0]
        try:
            dept_enc = dept_encoder.transform([dept_safe])[0]
        except Exception:
            dept_enc = None

    for course in COURSES:
        used_ml = False
        if _model_bundle is not None and dept_enc is not None:
            try:
                model = _model_bundle["model"]
                feature_cols = _model_bundle["feature_cols"]
                course_encoder = _encoders["course_id"]
                course_enc = course_encoder.transform([course["id"]])[0]
                row = pd.DataFrame([{
                    "cgpa": cgpa, "backlog": backlog, "semester": semester,
                    "department_enc": dept_enc, "course_id_enc": course_enc,
                    "course_min_cgpa": course["min_cgpa"], "course_max_backlog": course["max_backlog"],
                }])[feature_cols]
                proba = model.predict_proba(row)[0]
                classes = list(model.classes_)
                p_eligible = proba[classes.index(1)] if 1 in classes else 0.0
                results.append({
                    "id": course["id"],
                    "name": course["name"],
                    "credits": course["credits"],
                    "eligible": bool(p_eligible >= 0.5),
                    "confidence": round(float(p_eligible if p_eligible >= 0.5 else 1 - p_eligible), 3),
                })
                used_ml = True
            except Exception:
                used_ml = False

        if not used_ml:
            eligible, confidence = _rule_based_confidence(cgpa, backlog, course)
            results.append({
                "id": course["id"],
                "name": course["name"],
                "credits": course["credits"],
                "eligible": eligible,
                "confidence": round(confidence, 3),
            })

    return results