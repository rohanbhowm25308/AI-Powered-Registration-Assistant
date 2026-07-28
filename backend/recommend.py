"""
AI Course Recommendation — content-based filtering.

Turns each course's department/tags/skills/career-paths into a text
"profile" and the student's free-text interests into a query, then ranks
courses by TF-IDF cosine similarity (scikit-learn). Eligibility
(CGPA/backlogs) is blended in as a second factor so a great topical match
the student can't actually take yet still ranks lower than one they
qualify for.

Uses character n-grams (not whole-word tokens) specifically so common
typos ("machenical" vs "mechanical") still produce a strong match via
substring overlap, instead of falling back to an arbitrary default list.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from courses import COURSES


def _course_document(course):
    dept = course["department"]
    return " ".join([
        course["name"], course["name"],
        dept, dept, dept,  # weight department heavily -- "mechanical" should strongly surface Mechanical courses
        " ".join(course["tags"]) + " " + " ".join(course["tags"]),  # weight tags higher
        " ".join(course["skills_taught"]),
        " ".join(course["career_paths"]),
    ])


def recommend_courses(interests_text, cgpa=None, backlog=None, top_n=5):
    documents = [_course_document(c) for c in COURSES]
    query = interests_text.strip() or "general technology"

    # char_wb n-grams make this robust to typos/misspellings: "machenical"
    # and "mechanical" still share most of their 3-5 letter substrings.
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
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
            "department": course["department"],
            "match_score": round(float(sim) * 100, 1),
            "overall_score": round(score * 100, 1),
            "eligible": eligible,
            "career_paths": course["career_paths"],
            "why": _explain(interests_text, course, sim),
        })

    results.sort(key=lambda r: r["overall_score"], reverse=True)
    return results[:top_n]


def _explain(interests_text, course, sim):
    if sim < 0.08:
        return f"A broad option outside your stated interests — {', '.join(course['career_paths'][:2])}."
    query_lower = interests_text.lower()
    overlapping = [t for t in course["tags"] if t in query_lower]
    if overlapping:
        return f"Matches your interest in {', '.join(overlapping[:3])}. Leads to: {', '.join(course['career_paths'][:2])}."
    if course["department"].lower() in query_lower:
        return f"A {course['department']} course matching what you described. Leads to: {', '.join(course['career_paths'][:2])}."
    return f"Related to what you described. Leads to: {', '.join(course['career_paths'][:2])}."