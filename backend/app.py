"""
NEXUS backend — Flask API for the AI Registration Assistant.

Routes:
  GET  /api/health              -> backend + Gen AI provider + ML model status
  GET  /api/courses             -> course catalog
  POST /api/students            -> upsert a student profile (incl. interests/skills)
  POST /api/eligibility         -> ML-scored eligibility check
  POST /api/register            -> register a student for a course
  GET  /api/dashboard           -> live stats + registration list + analytics
  GET  /api/receipt/<id>        -> PDF registration receipt (with embedded QR)
  GET  /api/qr/<id>.png         -> standalone QR code image
  GET  /api/verify/<id>         -> public verification page (what the QR opens)
  POST /api/chat                -> Gen AI chatbot / FAQ (rule-based fallback)
  POST /api/recommend           -> AI course recommendations (TF-IDF)
  POST /api/career/roadmap      -> AI career roadmap for a course
  POST /api/career/skill-gap    -> skill-gap analysis for a course
  POST /api/career/interview    -> AI interview prep questions
  POST /api/resume/analyze      -> AI resume analyzer
  POST /api/placement           -> ML placement-probability estimate
  GET  /api/badges/<roll>       -> achievement badges (earned + locked)

Run:
  pip install -r requirements.txt
  python app.py
  # serves the API AND the frontend/ folder at http://localhost:5000
"""
import io
import os
import random
from datetime import datetime

from flask import Flask, jsonify, request, send_file, send_from_directory, Response
from flask_cors import CORS
from fpdf import FPDF
from pypdf import PdfReader

import database
from courses import COURSES, COURSE_BY_ID
import ml_eligibility
import ai_assistant
import recommend
import career_ai
import resume_analyzer
import placement_model
import badges
import qr

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

database.init_db()


# ---------------------------------------------------------------- helpers
def gen_reg_id():
    return f"REG-{datetime.utcnow().year}-{random.randint(1000, 9999)}"


def today_str():
    return datetime.utcnow().strftime("%b %d, %Y")


import socket


def get_lan_ip():
    """Best-effort LAN IP so QR codes work when scanned from a phone
    on the same network -- 127.0.0.1/localhost only means "this device"
    and is unreachable from anywhere else."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


_LAN_IP = get_lan_ip()


def verify_url(reg_id):
    host = request.host_url.rstrip("/")
    # Only substitute the LAN IP when we're being accessed via localhost/127.0.0.1
    # (pure local dev) -- in every real deployment (Render, etc.) request.host_url
    # is already the correct, publicly reachable address, so use it as-is.
    if "127.0.0.1" in host or "localhost" in host:
        host = f"http://{_LAN_IP}:5000"
    return f"{host}/api/verify/{reg_id}"


# ---------------------------------------------------------------- static frontend
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# ---------------------------------------------------------------- health
@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "ai_provider": ai_assistant.active_provider(),
        "ml_model_loaded": ml_eligibility.is_ml_model_loaded(),
        "placement_model_loaded": placement_model.is_model_loaded(),
    })


# ---------------------------------------------------------------- courses
@app.route("/api/courses")
def courses():
    return jsonify({"courses": COURSES})


# ---------------------------------------------------------------- students
@app.route("/api/students", methods=["POST"])
def create_student():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    roll = (data.get("roll") or "").strip()
    if not name or not roll:
        return jsonify({"error": "name and roll are required"}), 400

    database.upsert_student(
        name, roll, data.get("dept"), data.get("sem"),
        data.get("cgpa"), data.get("backlog"),
        interests=data.get("interests"), skills=data.get("skills"),
    )
    return jsonify({"status": "saved"})


# ---------------------------------------------------------------- eligibility (ML)
@app.route("/api/eligibility", methods=["POST"])
def check_eligibility():
    data = request.get_json(force=True) or {}
    try:
        cgpa = float(data.get("cgpa"))
    except (TypeError, ValueError):
        return jsonify({"error": "a valid cgpa is required"}), 400
    backlog = int(data.get("backlog") or 0)
    semester = int(data.get("sem") or 5)
    dept = data.get("dept") or "Computer Science"
    roll = (data.get("roll") or "").strip()

    predictions = ml_eligibility.predict_eligibility(cgpa, backlog, semester, dept)
    eligible = [p for p in predictions if p["eligible"]]

    if roll:
        database.log_eligibility_check(roll, cgpa, backlog, [p["id"] for p in eligible])

    return jsonify({
        "eligible_courses": eligible,
        "all_predictions": predictions,
        "ml_model_used": ml_eligibility.is_ml_model_loaded(),
    })


# ---------------------------------------------------------------- registration
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    roll = (data.get("roll") or "").strip()
    course_id = data.get("course_id")

    if not name or not roll:
        return jsonify({"error": "Save your student details (name + roll number) first."}), 400
    if course_id not in COURSE_BY_ID:
        return jsonify({"error": "Unknown course."}), 400

    course = COURSE_BY_ID[course_id]

    try:
        cgpa = float(data.get("cgpa") or 0)
    except (TypeError, ValueError):
        cgpa = 0.0
    backlog = int(data.get("backlog") or 0)

    if database.is_course_full(course_id, course["seats"]):
        return jsonify({"error": f"{course['name']} has no seats left."}), 409

    database.upsert_student(name, roll, data.get("dept"), data.get("sem"), cgpa, backlog)

    reg_id = gen_reg_id()
    reg_date = today_str()
    database.create_registration(reg_id, name, roll, course_id, course["name"], reg_date)

    return jsonify({
        "reg_id": reg_id, "name": name, "roll": roll,
        "course": course["name"], "course_id": course_id, "date": reg_date,
        "verify_url": verify_url(reg_id),
    })


# ---------------------------------------------------------------- dashboard / analytics
@app.route("/api/dashboard")
def dashboard():
    regs = database.get_all_registrations()
    by_course = {}
    for r in regs:
        by_course[r["course_id"]] = by_course.get(r["course_id"], 0) + 1

    busiest = None
    if by_course:
        busiest_id = max(by_course, key=by_course.get)
        busiest = COURSE_BY_ID.get(busiest_id, {}).get("name", busiest_id)

    return jsonify({
        "total_registrations": len(regs),
        "eligible_checks": database.count_eligibility_checks(),
        "by_course": [{"course_id": cid, "count": c} for cid, c in by_course.items()],
        "by_department": database.registrations_by_department(),
        "timeline": database.registrations_timeline(),
        "busiest_course": busiest,
        "registrations": [
            {"reg_id": r["reg_id"], "name": r["name"], "course": r["course_name"], "date": r["reg_date"]}
            for r in regs
        ],
    })


# ---------------------------------------------------------------- delete registrations
@app.route("/api/registrations/<reg_id>", methods=["DELETE"])
def delete_registration_route(reg_id):
    deleted = database.delete_registration(reg_id)
    if not deleted:
        return jsonify({"error": "Registration not found"}), 404
    return jsonify({"status": "deleted", "reg_id": reg_id})


@app.route("/api/registrations", methods=["DELETE"])
def delete_all_registrations_route():
    count = database.delete_all_registrations()
    return jsonify({"status": "cleared", "count": count})


# ---------------------------------------------------------------- receipt PDF (with embedded QR)
@app.route("/api/receipt/<reg_id>")
def receipt(reg_id):
    reg = database.get_registration(reg_id)
    if not reg:
        return jsonify({"error": "Registration not found"}), 404

    qr_buf = qr.make_qr_png(verify_url(reg_id), box_size=6)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(4, 6, 12)
    pdf.rect(0, 0, 210, 297, "F")

    pdf.set_text_color(79, 224, 255)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_xy(20, 25)
    pdf.cell(0, 10, "NEXUS -- Registration Receipt")

    pdf.set_draw_color(27, 39, 64)
    pdf.line(20, 38, 190, 38)

    rows = [
        ("Student Name", reg["name"]),
        ("Roll Number", reg["roll"] or "-"),
        ("Course", reg["course_name"]),
        ("Registration ID", reg["reg_id"]),
        ("Date", reg["reg_date"]),
    ]
    y = 55
    for label, value in rows:
        pdf.set_text_color(118, 136, 168)
        pdf.set_font("Helvetica", "", 12)
        pdf.set_xy(20, y)
        pdf.cell(60, 8, label)
        pdf.set_text_color(234, 241, 255)
        pdf.set_xy(90, y)
        pdf.cell(0, 8, str(value))
        y += 12

    pdf.image(qr_buf, x=140, y=y + 8, w=40)
    pdf.set_text_color(118, 136, 168)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(140, y + 50)
    pdf.multi_cell(40, 4, "Scan to verify this registration", align="C")

    pdf.set_text_color(118, 136, 168)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(20, 270)
    pdf.cell(0, 8, "This is a system-generated receipt from the AI Registration Assistant.")

    pdf_bytes = pdf.output()

    buf = io.BytesIO(bytes(pdf_bytes))
    buf.seek(0)
    return send_file(
        buf, mimetype="application/pdf",
        as_attachment=True, download_name=f"{reg_id}_receipt.pdf",
    )


# ---------------------------------------------------------------- QR code image + verification page
@app.route("/api/qr/<reg_id>.png")
def qr_image(reg_id):
    reg = database.get_registration(reg_id)
    if not reg:
        return jsonify({"error": "Registration not found"}), 404
    buf = qr.make_qr_png(verify_url(reg_id))
    return send_file(buf, mimetype="image/png")


@app.route("/api/verify/<reg_id>")
def verify(reg_id):
    reg = database.get_registration(reg_id)
    if not reg:
        html = """
        <body style="background:#04060c;color:#ff5d7a;font-family:sans-serif;
        display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
        <div style="text-align:center"><h1>Not found</h1>
        <p>No registration matches this code.</p></div></body>
        """
        return Response(html, mimetype="text/html"), 404

    html = f"""
    <body style="background:#04060c;color:#eaf1ff;font-family:sans-serif;
    display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
      <div style="text-align:center;background:#0a0f1c;border:1px solid #1b2740;
      border-radius:16px;padding:40px;max-width:360px;">
        <div style="width:56px;height:56px;border-radius:50%;margin:0 auto 16px;
        background:radial-gradient(circle at 30% 30%,#7ff3ff,#33d685 80%);
        display:flex;align-items:center;justify-content:center;font-size:26px;color:#04060c;">✓</div>
        <h2 style="font-family:sans-serif;">Registration Verified</h2>
        <p style="color:#7688a8;font-size:14px;">This is a genuine NEXUS registration record.</p>
        <div style="text-align:left;font-size:14px;margin-top:20px;">
          <p><b>Student:</b> {reg['name']}</p>
          <p><b>Course:</b> {reg['course_name']}</p>
          <p><b>Registration ID:</b> {reg['reg_id']}</p>
          <p><b>Date:</b> {reg['reg_date']}</p>
        </div>
      </div>
    </body>
    """
    return Response(html, mimetype="text/html")


# ---------------------------------------------------------------- chat (Gen AI / FAQ)
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    message = (data.get("message") or "").strip()
    profile = data.get("profile")
    lang = data.get("lang", "en")
    if not message:
        return jsonify({"error": "message is required"}), 400

    reply, provider = ai_assistant.chat_reply(message, profile, lang=lang)
    return jsonify({"reply": reply, "provider": provider})


# ---------------------------------------------------------------- AI course recommendation
@app.route("/api/recommend", methods=["POST"])
def recommend_route():
    data = request.get_json(force=True) or {}
    interests = (data.get("interests") or "").strip()
    if not interests:
        return jsonify({"error": "Describe your interests to get recommendations."}), 400
    cgpa = data.get("cgpa")
    backlog = data.get("backlog")
    try:
        cgpa = float(cgpa) if cgpa is not None else None
    except (TypeError, ValueError):
        cgpa = None

    results = recommend.recommend_courses(interests, cgpa=cgpa, backlog=backlog)
    return jsonify({"recommendations": results})


# ---------------------------------------------------------------- career roadmap
@app.route("/api/career/roadmap", methods=["POST"])
def roadmap_route():
    data = request.get_json(force=True) or {}
    course_id = data.get("course_id")
    profile = data.get("profile")
    lang = data.get("lang", "en")
    roll = (data.get("roll") or (profile or {}).get("roll") or "").strip()

    result, provider = career_ai.generate_roadmap(course_id, profile, lang=lang)
    if "error" in result:
        return jsonify(result), 400
    if roll:
        database.log_activity(roll, "roadmap_generated", course_id)
    result["provider"] = provider
    return jsonify(result)


# ---------------------------------------------------------------- skill-gap analysis
@app.route("/api/career/skill-gap", methods=["POST"])
def skill_gap_route():
    data = request.get_json(force=True) or {}
    course_id = data.get("course_id")
    skills = data.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    result = career_ai.analyze_skill_gap(course_id, skills)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ---------------------------------------------------------------- interview prep
@app.route("/api/career/interview", methods=["POST"])
def interview_route():
    data = request.get_json(force=True) or {}
    course_id = data.get("course_id")
    lang = data.get("lang", "en")

    result, provider = career_ai.generate_interview_prep(course_id, lang=lang)
    if "error" in result:
        return jsonify(result), 400
    result["provider"] = provider
    return jsonify(result)


# ---------------------------------------------------------------- resume analyzer
@app.route("/api/resume/analyze", methods=["POST"])
def resume_route():
    roll = None
    lang = "en"
    resume_text = ""

    if request.content_type and "multipart/form-data" in request.content_type:
        f = request.files.get("file")
        roll = (request.form.get("roll") or "").strip()
        lang = request.form.get("lang", "en")
        if not f:
            return jsonify({"error": "No file uploaded."}), 400
        if f.filename.lower().endswith(".pdf"):
            try:
                reader = PdfReader(f.stream)
                resume_text = "\n".join((page.extract_text() or "") for page in reader.pages)
            except Exception:
                return jsonify({"error": "Could not read this PDF. Try pasting the text instead."}), 400
        else:
            resume_text = f.read().decode("utf-8", errors="ignore")
    else:
        data = request.get_json(force=True) or {}
        resume_text = data.get("text", "")
        roll = (data.get("roll") or "").strip()
        lang = data.get("lang", "en")

    result = resume_analyzer.analyze_resume(resume_text, lang=lang)
    if "error" in result:
        return jsonify(result), 400

    if roll:
        database.log_activity(roll, "resume_analyzed", ",".join(result["skills_detected"][:10]))
        database.update_student_skills(roll, ",".join(result["skills_detected"]))

    return jsonify(result)


# ---------------------------------------------------------------- placement probability
@app.route("/api/placement", methods=["POST"])
def placement_route():
    data = request.get_json(force=True) or {}
    try:
        cgpa = float(data.get("cgpa"))
    except (TypeError, ValueError):
        return jsonify({"error": "a valid cgpa is required"}), 400
    backlog = int(data.get("backlog") or 0)
    semester = int(data.get("sem") or 6)
    dept = data.get("dept") or "Computer Science"
    course_id = data.get("course_id")
    skills_count = int(data.get("skills_count") or 0)

    if course_id not in COURSE_BY_ID:
        return jsonify({"error": "Unknown course."}), 400

    result = placement_model.predict_placement(cgpa, backlog, semester, dept, course_id, skills_count)
    return jsonify(result)


# ---------------------------------------------------------------- achievement badges
@app.route("/api/badges/<roll>")
def badges_route(roll):
    earned, locked = badges.get_badges(roll)
    return jsonify({"earned": earned, "locked": locked})


if __name__ == "__main__":
    print("=" * 50, flush=True)
    print("NEXUS backend starting...", flush=True)
    print("If you see this line, Python reached app.run().", flush=True)
    print("On this computer:  http://127.0.0.1:5000", flush=True)
    print(f"From your phone (same WiFi): http://{_LAN_IP}:5000", flush=True)
    print("QR codes will only scan successfully if your phone", flush=True)
    print("is on the SAME WiFi network as this computer.", flush=True)
    print("=" * 50, flush=True)
    app.run(debug=True, port=5000, use_reloader=False, host="0.0.0.0")