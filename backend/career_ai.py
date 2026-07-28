"""
Career Hub features: AI career roadmap, skill-gap analysis, and AI
interview preparation. Each has an LLM-generated version (when a Gen AI
provider is configured) and a deterministic template fallback so the
feature always returns something useful.
"""
from courses import COURSE_BY_ID, CAREER_REQUIRED_SKILLS
import ai_assistant as ai


# ---------------------------------------------------------------- roadmap
def _roadmap_fallback(course):
    skills = course["skills_taught"]
    chunks = [skills[i:i + 2] for i in range(0, len(skills), 2)] or [[]]
    steps = []
    for i, chunk in enumerate(chunks, start=1):
        steps.append({
            "phase": f"Month {i}",
            "focus": " & ".join(chunk) if chunk else "Foundations",
            "detail": f"Build fundamentals in {', '.join(chunk) if chunk else 'core theory'} through guided coursework and a small project.",
        })
    steps.append({
        "phase": f"Month {len(chunks) + 1}",
        "focus": "Portfolio project",
        "detail": f"Ship one end-to-end project using {', '.join(skills[:3])} to show for {course['career_paths'][0]} applications.",
    })
    steps.append({
        "phase": f"Month {len(chunks) + 2}",
        "focus": "Job readiness",
        "detail": f"Polish your resume around this project, target roles like {', '.join(course['career_paths'])}, and start applying.",
    })
    return steps


def generate_roadmap(course_id, profile=None, lang="en"):
    course = COURSE_BY_ID.get(course_id)
    if not course:
        return {"error": "Unknown course"}, "rule_based"

    system = (
        "You are a career mentor. Produce a realistic month-by-month roadmap "
        f"for a student taking '{course['name']}' aiming for roles like "
        f"{', '.join(course['career_paths'])}. Return 4-6 short phases as plain "
        "text lines, each starting with 'Month N: Focus — one-sentence detail'. "
        "No markdown headers, no preamble." + ai.lang_instruction(lang)
    )
    user = f"Student profile: {profile or 'not provided'}. Course: {course['name']}."

    text, provider = ai.generate(system, user, max_tokens=350, fallback=None)
    if provider == "rule_based" or text is None:
        return {"course": course["name"], "career_paths": course["career_paths"], "steps": _roadmap_fallback(course)}, "rule_based"

    steps = []
    for line in text.strip().splitlines():
        line = line.strip("- ").strip()
        if not line:
            continue
        if ":" in line:
            phase, rest = line.split(":", 1)
            if "—" in rest:
                focus, detail = rest.split("—", 1)
            elif "-" in rest:
                focus, detail = rest.split("-", 1)
            else:
                focus, detail = rest, ""
            steps.append({"phase": phase.strip(), "focus": focus.strip(), "detail": detail.strip()})
    if not steps:
        steps = [{"phase": "Roadmap", "focus": "", "detail": text.strip()}]
    return {"course": course["name"], "career_paths": course["career_paths"], "steps": steps}, provider


# ---------------------------------------------------------------- skill gap
def analyze_skill_gap(course_id, known_skills):
    course = COURSE_BY_ID.get(course_id)
    if not course:
        return {"error": "Unknown course"}
    required = CAREER_REQUIRED_SKILLS.get(course_id, course["skills_taught"])
    known_norm = {s.strip().lower() for s in known_skills if s.strip()}

    have, missing = [], []
    for skill in required:
        (have if skill.lower() in known_norm else missing).append(skill)

    coverage = round(100 * len(have) / len(required), 1) if required else 0.0
    return {
        "course": course["name"],
        "required_skills": required,
        "have": have,
        "missing": missing,
        "coverage_pct": coverage,
        "recommendation": (
            f"You already cover {coverage:.0f}% of the skills {course['career_paths'][0]} roles expect. "
            f"Focus next on: {', '.join(missing[:3])}." if missing else
            f"You cover all the core skills tracked for {course['career_paths'][0]} roles — nice work."
        ),
    }


# ---------------------------------------------------------------- interview prep
_FALLBACK_QUESTIONS = {
    "AIML": [
        "Explain the bias-variance tradeoff in your own words.",
        "How would you handle an imbalanced dataset in a classification problem?",
        "Walk through how backpropagation updates weights in a neural network.",
        "What's the difference between overfitting and underfitting, and how do you detect each?",
        "Describe a project where you had to choose between two ML models. How did you decide?",
    ],
    "DS": [
        "How would you explain a p-value to a non-technical stakeholder?",
        "Walk through your process for cleaning a messy dataset.",
        "What's the difference between correlation and causation, with an example?",
        "How do you decide which chart type to use for a given dataset?",
        "Describe a time your analysis changed a decision someone was about to make.",
    ],
    "WEB": [
        "What happens, step by step, when you type a URL into the browser and hit enter?",
        "Explain the difference between props and state in a component-based framework.",
        "How would you optimize a web page that's loading slowly?",
        "What's a REST API, and how would you design one for a to-do list app?",
        "Describe how you'd debug a layout that looks broken only on mobile.",
    ],
    "CYB": [
        "Walk through the steps you'd take after discovering a suspicious login attempt.",
        "What's the difference between symmetric and asymmetric encryption?",
        "How would you explain the principle of least privilege to a new hire?",
        "Describe a common social engineering attack and how to defend against it.",
        "What's in your process for responsibly disclosing a vulnerability you found?",
    ],
    "CLOUD": [
        "Explain the difference between horizontal and vertical scaling.",
        "How would you design a CI/CD pipeline for a small web app?",
        "What's the difference between a container and a virtual machine?",
        "Describe how you'd troubleshoot a service that's intermittently down in production.",
        "How do you decide what to put behind a load balancer versus a single instance?",
    ],
}


def _interview_fallback(course):
    return _FALLBACK_QUESTIONS.get(course["id"], [
        f"Why are you interested in a career in {course['career_paths'][0]}?",
        f"Walk me through a project relevant to {course['name']}.",
        "What's a technical challenge you faced recently, and how did you solve it?",
    ])


def generate_interview_prep(course_id, lang="en"):
    course = COURSE_BY_ID.get(course_id)
    if not course:
        return {"error": "Unknown course"}, "rule_based"

    system = (
        f"You are a technical interviewer for {course['career_paths'][0]} roles. "
        "Produce exactly 5 realistic interview questions for a student who just "
        f"completed a course in {course['name']} (skills: {', '.join(course['skills_taught'])}). "
        "One question per line, no numbering, no preamble, no markdown."
        + ai.lang_instruction(lang)
    )
    text, provider = ai.generate(system, f"Course: {course['name']}", max_tokens=280, fallback=None)

    if provider == "rule_based" or not text:
        questions = _interview_fallback(course)
    else:
        questions = [q.strip("-• ").strip() for q in text.strip().splitlines() if q.strip()]
        if not questions:
            questions = _interview_fallback(course)

    return {"course": course["name"], "questions": questions[:6]}, provider
