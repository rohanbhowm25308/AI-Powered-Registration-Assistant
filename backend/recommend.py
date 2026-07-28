"""
AI Course Recommendation — content-based filtering.

Turns each course's tags/skills/career-paths into a text "profile" and
the student's free-text interests into a query, then ranks courses by
TF-IDF cosine similarity (scikit-learn). Eligibility (CGPA/backlogs) is
blended in as a second factor so a great topical match the student can't
actually take yet still ranks lower than one they qualify for.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from courses import COURSES


def _course_document(course):
    return " ".join([
        course["name"], course["name"],
        " ".join(course["tags"]) + " " + " ".join(course["tags"]),  # weight tags higher
        " ".join(course["skills_taught"]),
        " ".join(course["career_paths"]),
    ])


def recommend_courses(interests_text, cgpa=None, backlog=None, top_n=5):
    documents = [_course_document(c) for c in COURSES]
    query = interests_text.strip() or "general technology"

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(documents + [query])
    similarity = cosine_similarity(tfidf[-1], tfidf[:-1]).flatten()

    results = []
    for course, sim in zip(COURSES, similarity):
        eligible = True
        if cgpa is not None:
            eligible = cgpa >= course["min_cgpa"] and (backlog or 0) <= course["max_backlog"]

        # blend: topical match (70%) + eligibility bonus (30%) so eligible,
        # well-matched courses float to the top without hard-filtering others out
        score = 0.7 * float(sim) + (0.3 if eligible else 0.0)

        results.append({
            "id": course["id"],
            "name": course["name"],
            "credits": course["credits"],
            "match_score": round(float(sim) * 100, 1),
            "overall_score": round(score * 100, 1),
            "eligible": eligible,
            "career_paths": course["career_paths"],
            "why": _explain(interests_text, course, sim),
        })

    results.sort(key=lambda r: r["overall_score"], reverse=True)
    return results[:top_n]


def _explain(interests_text, course, sim):
    if sim < 0.05:
        return f"A broad option outside your stated interests — {', '.join(course['career_paths'][:2])}."
    overlapping = [t for t in course["tags"] if t in interests_text.lower()]
    if overlapping:
        return f"Matches your interest in {', '.join(overlapping[:3])}. Leads to: {', '.join(course['career_paths'][:2])}."
    return f"Related to what you described. Leads to: {', '.join(course['career_paths'][:2])}."
