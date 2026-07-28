"""
Trains a RandomForestClassifier that estimates placement probability
from CGPA, backlogs, semester, department, chosen course (via its
employability index), and detected skill count.

Usage:
    cd backend
    python data/generate_placement_data.py
    python train_placement_model.py
"""
import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.preprocessing import LabelEncoder

from courses import DEPARTMENTS

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "placement_data.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "placement_model.pkl")
ENCODERS_PATH = os.path.join(os.path.dirname(__file__), "models", "placement_encoders.pkl")


def main():
    if not os.path.exists(DATA_PATH):
        raise SystemExit("No placement data found. Run `python data/generate_placement_data.py` first.")

    df = pd.read_csv(DATA_PATH)
    dept_encoder = LabelEncoder().fit(DEPARTMENTS)
    course_encoder = LabelEncoder().fit(df["course_id"].unique())

    df["department_enc"] = dept_encoder.transform(df["department"])
    df["course_id_enc"] = course_encoder.transform(df["course_id"])

    feature_cols = [
        "cgpa", "backlog", "semester", "department_enc",
        "course_id_enc", "employability_index", "skills_count",
    ]
    X = df[feature_cols]
    y = df["placed"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=7, stratify=y)

    model = RandomForestClassifier(n_estimators=250, max_depth=9, min_samples_leaf=5, random_state=7)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    print(f"Test accuracy: {accuracy_score(y_test, preds):.3f}")
    print(f"Test ROC-AUC:  {roc_auc_score(y_test, proba):.3f}")

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "feature_cols": feature_cols}, MODEL_PATH)
    joblib.dump({"department": dept_encoder, "course_id": course_encoder}, ENCODERS_PATH)
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
