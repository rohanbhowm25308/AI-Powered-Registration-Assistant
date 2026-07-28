"""
AI Resume Analyzer.

Accepts raw resume text (already extracted client-side, or from an
uploaded .pdf/.txt handled in app.py). Always runs a fast keyword-based
skill extraction against the known skill vocabulary (deterministic,
works offline), then optionally asks the Gen AI provider for a short
qualitative summary and improvement tips layered on top.
"""
import re

from courses import ALL_KNOWN_SKILLS, COURSES
import ai_assistant as ai


def extract_skills(resume_text):
    text_low = resume_text.lower()
    found = []
    for skill in ALL_KNOWN_SKILLS:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text_low):
            found.append(skill)
    return sorted(set(found))


def _best_course_matches(skills, top_n=3):
    skills_low = {s.lower() for s in skills}
    scored = []
    for c in COURSES:
        taught_low = {s.lower() for s in c["skills_taught"]}
        overlap = len(skills_low & taught_low)
        scored.append((overlap, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for overlap, c in scored[:top_n] if overlap > 0] or [c for _, c in scored[:1]]


def _fallback_summary(skills, matches):
    if not skills:
        return ("I couldn't confidently detect specific technical skills in this resume. "
                "Consider explicitly listing tools, languages, and frameworks you've used.")
    lines = [f"Detected {len(skills)} technical skill(s): {', '.join(skills[:12])}."]
    if matches:
        lines.append(f"Closest course fit: {', '.join(c['name'] for c in matches)}.")
    lines.append("Tip: quantify your project impact (e.g. \"reduced load time by 30%\") to stand out.")
    return " ".join(lines)


def analyze_resume(resume_text, lang="en"):
    resume_text = (resume_text or "").strip()
    if not resume_text:
        return {"error": "No resume text provided."}

    skills = extract_skills(resume_text)
    matches = _best_course_matches(skills)

    system = (
        "You are a resume reviewer for engineering students. Given the raw resume "
        "text, write a 3-4 sentence review: what stands out, one weakness, and one "
        "concrete improvement. Be specific and encouraging, no markdown."
        + ai.lang_instruction(lang)
    )
    truncated = resume_text[:4000]
    summary, provider = ai.generate(
        system, truncated, max_tokens=220,
        fallback=lambda: _fallback_summary(skills, matches),
    )

    return {
        "skills_detected": skills,
        "matched_courses": [{"id": c["id"], "name": c["name"]} for c in matches],
        "summary": summary,
        "provider": provider,
    }
