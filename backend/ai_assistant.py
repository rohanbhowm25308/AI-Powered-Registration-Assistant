"""
Gen AI layer — one place that knows how to talk to OpenAI / Gemini / Groq.

Set GENAI_PROVIDER in backend/.env to "openai", "gemini", or "groq" and
provide the matching API key to get real LLM-generated replies. If no key
is configured, every feature in this file transparently falls back to a
rule-based / template implementation, so the whole app still works with
zero API keys (useful for demos / offline grading).

`generate()` is the shared primitive: every AI feature (chat, course
recommendations, career roadmap, skill-gap analysis, interview prep,
resume analysis) builds its own system prompt and calls this.
"""
import os
import re

import requests
from dotenv import load_dotenv

from courses import COURSES

load_dotenv()

GENAI_PROVIDER = os.getenv("GENAI_PROVIDER", "").lower().strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

LANGUAGE_NAMES = {
    "en": "English", "hi": "Hindi", "es": "Spanish",
    "fr": "French", "de": "German", "zh": "Chinese",
}


def active_provider():
    if GENAI_PROVIDER == "openai" and OPENAI_API_KEY:
        return "openai"
    if GENAI_PROVIDER == "gemini" and GEMINI_API_KEY:
        return "gemini"
    if GENAI_PROVIDER == "groq" and GROQ_API_KEY:
        return "groq"
    return "rule_based"


def course_catalog_text():
    lines = []
    for c in COURSES:
        lines.append(
            f"- {c['name']} ({c['id']}): {c['credits']} credits, "
            f"min CGPA {c['min_cgpa']}, max backlogs {c['max_backlog']}, "
            f"registration closes {c['last_date']}, {c['seats']} seats. "
            f"Skills taught: {', '.join(c['skills_taught'])}. "
            f"Career paths: {', '.join(c['career_paths'])}."
        )
    return "\n".join(lines)


# ---------------------------------------------------------------- provider calls
def _call_openai(system_prompt, user_message, max_tokens):
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.5,
            "max_tokens": max_tokens,
        },
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_gemini(system_prompt, user_message, max_tokens):
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    resp = requests.post(
        url,
        json={
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": max_tokens},
        },
        timeout=25,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_groq(system_prompt, user_message, max_tokens):
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.5,
            "max_tokens": max_tokens,
        },
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate(system_prompt, user_message, max_tokens=300, fallback=None):
    """
    Shared entry point for every AI feature. Tries the configured Gen AI
    provider; on any error (or if none is configured) returns `fallback`
    (a plain string, or a zero-arg callable that computes one) instead of
    raising, so callers never have to special-case "no API key".
    Returns (text, provider_used).
    """
    provider = active_provider()
    if provider != "rule_based":
        try:
            if provider == "openai":
                return _call_openai(system_prompt, user_message, max_tokens), provider
            if provider == "gemini":
                return _call_gemini(system_prompt, user_message, max_tokens), provider
            if provider == "groq":
                return _call_groq(system_prompt, user_message, max_tokens), provider
        except Exception as exc:
            # Log the real error so it shows up in server logs (e.g. Render's
            # Logs tab) instead of silently vanishing -- this is the only way
            # to actually diagnose "why did it fall back to rule-based".
            import traceback
            print(f"[ai_assistant] {provider} call failed: {exc}", flush=True)
            traceback.print_exc()

    if callable(fallback):
        fallback = fallback()
    return (fallback or "I don't have enough information to answer that right now."), "rule_based"


def lang_instruction(lang):
    if not lang or lang == "en":
        return ""
    name = LANGUAGE_NAMES.get(lang, lang)
    return f" Respond entirely in {name}, regardless of what language the question was asked in."


# ---------------------------------------------------------------- chat / FAQ
def _profile_context(profile):
    if not profile:
        return ""
    return (
        f"\n\nThe student's saved profile: name={profile.get('name')}, "
        f"cgpa={profile.get('cgpa')}, backlogs={profile.get('backlog')}, "
        f"department={profile.get('dept')}, semester={profile.get('sem')}."
    )


def _chat_system_prompt(profile, lang):
    return (
        "You are NEXUS, a knowledgeable, friendly AI assistant embedded in a college "
        "course registration portal. You can discuss: which courses fit the student, "
        "deadlines and credits, whether their CGPA/backlogs qualify them, study and time "
        "management advice for balancing multiple courses, what a course actually involves "
        "day-to-day, career direction, and general good-faith guidance for anything else a "
        "student might reasonably ask you as their registration assistant. Be genuinely "
        "helpful and specific rather than deflecting to 'check the X tab' unless that tab "
        "truly does the task better (e.g. resume upload, voice input). Keep replies focused "
        "(roughly 3-6 sentences unless more detail is clearly needed), use simple HTML like "
        "<b> tags for emphasis (no markdown), and never invent courses, deadlines, or "
        "numbers that aren't in the catalog below."
        + lang_instruction(lang)
        + "\n\nCourse catalog:\n" + course_catalog_text()
        + _profile_context(profile)
    )


def _rule_based_chat_reply(raw, profile):
    q = raw.lower()

    def course_list_html():
        return "<br>".join(f"<b>{c['name']}</b> ({c['credits']} credits, min CGPA {c['min_cgpa']})" for c in COURSES)

    if re.search(r"available|list|which courses|what courses|offer", q):
        return f"Here are the courses open for registration this semester:<br><br>{course_list_html()}"
    if re.search(r"last date|deadline|when.*close|close.*regist", q):
        return "<br>".join(f"<b>{c['name']}</b> — closes {c['last_date']}" for c in COURSES)
    if "credit" in q:
        hit = next((c for c in COURSES if c["name"].split(" ")[0].lower() in q or c["id"].lower() in q), None)
        if hit:
            return f"<b>{hit['name']}</b> carries <b>{hit['credits']} credits</b>."
        return "<br>".join(f"<b>{c['name']}</b>: {c['credits']} credits" for c in COURSES)
    if re.search(r"cgpa.*sufficient|is my cgpa|enough.*cgpa", q):
        if not profile or profile.get("cgpa") is None:
            return "I don't have your CGPA yet — save your student details first, or use the Eligibility tab."
        cgpa = float(profile.get("cgpa") or 0)
        backlog = int(profile.get("backlog") or 0)
        elig = [c for c in COURSES if cgpa >= c["min_cgpa"] and backlog <= c["max_backlog"]]
        if not elig:
            return f"With a CGPA of <b>{cgpa}</b> and {backlog} backlog(s), you don't currently meet the minimum for any listed course."
        return f"Yes — with a CGPA of <b>{cgpa}</b> you qualify for: {', '.join(c['name'] for c in elig)}."
    if re.search(r"can i register|register now|is registration open", q):
        return "Registration is currently <b>open</b> for all five courses. Head to the <b>Register</b> tab, pick a course, and confirm your details."
    if "recommend" in q or "suggest" in q:
        return "Try the <b>Recommend</b> tab — tell it your interests and it'll rank courses that fit, using CGPA and topic overlap."
    if "roadmap" in q or "career" in q:
        return "Check the <b>Career Hub</b> tab for a step-by-step roadmap, skill-gap analysis, and mock interview questions for any course."
    if "resume" in q:
        return "Paste or upload your resume in the <b>Resume</b> tab and I'll extract your skills and flag any gaps."
    if "eligib" in q:
        return "I can check that instantly — open the <b>Eligibility</b> tab and enter your CGPA and backlog count."
    if re.search(r"\bhi\b|hello|hey", q):
        return "Hi! I'm your registration assistant. Ask me about open courses, deadlines, credits, recommendations, or careers."
    if "thank" in q:
        return "Anytime — good luck with your registration!"
    try:
        num = float(q)
        if num <= 10:
            elig = [c for c in COURSES if num >= c["min_cgpa"]]
            return f"Assuming 0 backlogs, a CGPA of <b>{num}</b> qualifies for: {', '.join(c['name'] for c in elig) if elig else 'none of the listed courses yet'}."
    except ValueError:
        pass
    return ('I can help with course lists, deadlines, credits, eligibility, recommendations, career roadmaps, '
            'resume review, and interview prep. Try "which courses are available?" or "recommend a course for me".')


def chat_reply(message, profile=None, lang="en"):
    provider = active_provider()
    if provider != "rule_based":
        try:
            if provider == "openai":
                return _call_openai(_chat_system_prompt(profile, lang), message, 420), provider
            if provider == "gemini":
                return _call_gemini(_chat_system_prompt(profile, lang), message, 420), provider
            if provider == "groq":
                return _call_groq(_chat_system_prompt(profile, lang), message, 420), provider
        except Exception as exc:
            import traceback
            print(f"[ai_assistant] {provider} call failed: {exc}", flush=True)
            traceback.print_exc()
            fallback_reply = _rule_based_chat_reply(message, profile)
            # TEMPORARY diagnostic: shows the real error inline so it's visible
            # directly in the chat UI, not just server logs. Safe to remove
            # once the underlying issue is confirmed fixed.
            return (
                fallback_reply
                + f'<br><br><span style="opacity:0.6; font-size:12px;">'
                + f"⚠️ {provider} API call failed: {type(exc).__name__}: {exc}</span>",
                "rule_based (error)",
            )

    return _rule_based_chat_reply(message, profile), "rule_based"