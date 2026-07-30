#  NEXUS — AI-Powered Registration Assistant

A full-stack, AI-powered college course registration platform — not just a form, but a real assistant. It predicts eligibility with a trained machine learning model, recommends courses based on what you're actually interested in, builds AI career roadmaps and mock interview questions, reviews your resume for skill gaps, estimates placement probability, and lets you register, search, and manage courses across **89 courses spanning 5 departments** — all wrapped in a live, chat-first interface with voice input, multi-language support, and QR-verified receipts.

**🔗 [Live Demo](https://ai-powered-registration-assistant.onrender.com/)** · **📦 [GitHub Repository](https://github.com/rohanbhowm25308/AI-Powered-Registration-Assistant)**

> ⚠️ Hosted on Render's free tier — the first request after inactivity can take 30-60 seconds to wake the server up. Give it a moment.

---

##  Features

| Feature | How it works |
|---|---|
|  **89 Courses, 5 Departments** | Computer Science, Electronics, Mechanical, Civil, and Information Technology — real credits, CGPA/backlog requirements, and career paths for each |
|  **AI Eligibility Prediction** | A trained `RandomForestClassifier` (scikit-learn) scores your real eligibility — not just a fixed if/else |
|  **Placement Probability** | A second trained model estimates your placement odds based on CGPA, backlogs, and course employability data |
|  **AI Course Recommendations** | TF-IDF + cosine similarity matches your stated interests against every course's tags, skills, and career paths — typo-tolerant |
|  **Career Hub** | AI-generated career roadmaps, skill-gap analysis, and mock interview questions for any course |
|  **Resume Analyzer** | Upload or paste a resume (PDF/TXT) — extracts skills, flags gaps, and gives AI-written feedback |
|  **AI Chatbot** | Powered by Groq (Llama), grounded in the real course catalog — asks and answers naturally, with a rule-based fallback if no API key is set |
|  **Voice Input & Output** | Talk to the assistant and have it talk back, via the Web Speech API |
|  **Multi-language UI** | English, Hindi, Spanish, and French |
|  **Course Search** | Instantly filter all 89 courses by name, code, skill, or career path |
|  **QR-Verified PDF Receipts** | Every registration generates a real PDF receipt with an embedded, scannable QR code linking to a public verification page |
|  **Achievement Badges** | Earn badges for milestones — profile saved, eligibility checked, registered, resume analyzed, and more |
|  **Live Analytics Dashboard** | Real-time charts (Chart.js) for registrations by course, by department, and over time |
|  **Full Registration Management** | Delete individual registrations or clear all, with confirmation prompts |

---

##  Tech Stack

**Backend:** Python, Flask, scikit-learn, pandas, SQLite, Groq API (Gen AI), FPDF2 (PDF generation), qrcode
**Frontend:** Vanilla HTML, CSS, JavaScript — no framework, no build step, no bundler
**ML:** Two independently trained `RandomForestClassifier` models (eligibility + placement), trained on realistic synthetic data generated from rule-based criteria plus noise
**Deployment:** Render (Gunicorn WSGI server)

---

##  Running it locally

```bash
git clone https://github.com/rohanbhowm25308/AI-Powered-Registration-Assistant.git
cd AI-Powered-Registration-Assistant/backend

python -m venv venv
source venv/bin/activate      # or venv\Scripts\activate on Windows

pip install -r requirements.txt

cp .env.example .env
# then edit .env and add GENAI_PROVIDER=groq + your GROQ_API_KEY
# (optional — the app works without it, just with simpler chat replies)

python app.py
```

Then open **http://127.0.0.1:5000**.

Pre-trained ML models are already included in `backend/models/` — no training required to run it, though the scripts to regenerate and retrain them (`data/generate_training_data.py`, `train_model.py`, etc.) are included if you want to.

---

##  Project Structure

```
AI-Powered-Registration-Assistant/
├── frontend/          Plain HTML/CSS/JS — chat, eligibility, recommend,
│                       career hub, resume, register, dashboard
└── backend/           Flask API, ML models, Gen AI integration,
                        course catalog, SQLite database
```

---

##  Developed by

**Rohan Bhowmik** —  Aspiring Developer in AI/ML, Data Science and Web Development

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/rohan-bhowmik-b014473a1)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/rohanbhowm25308)
[![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white)](https://www.instagram.com/rohan_._.bhowmik.84)

---

### ⭐ If you like this project, consider giving it a star — it genuinely helps!
