"""
Trains a scikit-learn RandomForestClassifier that predicts whether a
student is eligible for a given course, using CGPA, backlogs, semester,
department, and the course's own requirements as features.

This is the "machine learning / data science" layer sitting behind the
Eligibility tab: instead of a flat if/else threshold, the API asks a
trained model for a probability, which is what gets shown to the
student as "ML confidence".

Usage:
    cd backend
    python data/generate_training_data.py     # build the dataset (once)
    python train_model.py                     # train + save the model
"""
import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder

from courses import DEPARTMENTS

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "student_eligibility_data.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "eligibility_model.pkl")
ENCODERS_PATH = os.path.join(os.path.dirname(__file__), "models", "encoders.pkl")


def main():
    if not os.path.exists(DATA_PATH):
        raise SystemExit(
            "No training data found. Run `python data/generate_training_data.py` first."
        )

    df = pd.read_csv(DATA_PATH)

    dept_encoder = LabelEncoder().fit(DEPARTMENTS)
    course_encoder = LabelEncoder().fit(df["course_id"].unique())

    df["department_enc"] = dept_encoder.transform(df["department"])
    df["course_id_enc"] = course_encoder.transform(df["course_id"])

    feature_cols = [
        "cgpa", "backlog", "semester",
        "department_enc", "course_id_enc",
        "course_min_cgpa", "course_max_backlog",
    ]
    X = df[feature_cols]
    y = df["eligible"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200, max_depth=8, min_samples_leaf=4, random_state=42
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Test accuracy: {acc:.3f}\n")
    print(classification_report(y_test, preds, target_names=["not_eligible", "eligible"]))

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "feature_cols": feature_cols}, MODEL_PATH)
    joblib.dump({"department": dept_encoder, "course_id": course_encoder}, ENCODERS_PATH)
    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved encoders to {ENCODERS_PATH}")


if __name__ == "__main__":
    main()
