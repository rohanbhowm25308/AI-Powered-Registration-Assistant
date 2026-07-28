# NEXUS — AI Registration Assistant

A full-stack AI-powered course registration platform for students: eligibility
prediction, personalized course recommendations, a career hub (roadmaps,
skill-gap analysis, interview prep, placement probability), a resume analyzer,
a voice-enabled multilingual chatbot, QR-verified PDF receipts, an analytics
dashboard, and achievement badges — all backed by a real Flask API, SQLite
database, two trained scikit-learn models, and a pluggable Gen AI provider.

## Feature map

| Feature                        | Where it lives                                            |
|---------------------------------|------------------------------------------------------------|
| AI Eligibility Prediction       | `ml_eligibility.py` — trained RandomForestClassifier       |
| AI Course Recommendation        | `recommend.py` — TF-IDF content-based ranking              |
| AI Career Roadmap               | `career_ai.py` — Gen AI + template fallback                |
| Skill Gap Analysis              | `career_ai.py` — required vs. known skills                 |
| AI Interview Preparation        | `career_ai.py` — Gen AI + curated question bank             |
| Placement Probability           | `placement_model.py` — trained RandomForestClassifier      |
| AI Resume Analyzer              | `resume_analyzer.py` — keyword extraction + Gen AI review   |
| AI FAQ Chatbot                  | `ai_assistant.py` — same chat endpoint, rule-based FAQ core |
| Voice Assistant                 | `frontend/js/app.js` — Web Speech API (mic + speak-aloud)   |
| Multi-language Support          | `frontend/js/i18n.js` + `lang_instruction()` in the backend |
| Registration Analytics Dashboard| `/api/dashboard` + Chart.js in `app.js`                     |
| PDF Registration Receipt        | `app.py` `/api/receipt` — FPDF, with embedded QR code       |
| QR Code Verification            | `qr.py` + `/api/verify/<reg_id>` public verification page   |
| Achievement Badges              | `badges.py` — computed live from the database               |
| Live Background                 | `frontend/js/particles.js` — animated neural network canvas |

## Project structure

```
nexus/
├── frontend/                     Plain HTML / CSS / JavaScript — no build step
│   ├── index.html                All tabs: Chat, Eligibility, Recommend,
│   │                              Career Hub, Resume, Register, Dashboard
│   ├── css/style.css
│   ├── js/
│   │   ├── particles.js          Animated neural-network background
│   │   ├── i18n.js               Multi-language UI strings + switcher
│   │   └── app.js                Talks to every API route, voice I/O, charts
│   └── assets/logo.svg           App icon / favicon
│
└── backend/                      Python / Flask / ML / Gen AI
    ├── app.py                    Flask API — every route below
    ├── database.py                SQLite persistence (students, registrations,
    │                              eligibility checks, activity log)
    ├── courses.py                 Single source of truth: course rules, tags,
    │                              skills taught, career paths, employability
    ├── ai_assistant.py            Gen AI layer (OpenAI / Gemini / Groq) +
    │                              rule-based fallback used by every AI feature
    ├── ml_eligibility.py          Eligibility ML runtime (+ threshold fallback)
    ├── train_model.py             Trains the eligibility model
    ├── placement_model.py         Placement-probability ML runtime
    ├── train_placement_model.py   Trains the placement model
    ├── recommend.py               TF-IDF course recommendation engine
    ├── career_ai.py               Roadmap, skill-gap, interview prep
    ├── resume_analyzer.py         Resume skill extraction + AI review
    ├── badges.py                  Achievement badge catalog + evaluation
    ├── qr.py                      QR code generation for verification
    ├── data/
    │   ├── generate_training_data.py   Synthetic eligibility dataset
    │   └── generate_placement_data.py  Synthetic placement dataset
    ├── models/                    Trained model + encoder files land here
    ├── requirements.txt
    └── .env.example               Copy to .env and add a Gen AI API key
```

## 1. Set up the backend

```bash
cd backend
python -m venv venv && source venv/bin/activate     # optional but recommended
pip install -r requirements.txt
```

## 2. Train the ML models (data science layer)

Two features are backed by trained **scikit-learn RandomForestClassifiers**,
not fixed thresholds: Eligibility Prediction and Placement Probability. Since
there's no real historical data to train on, each has a script that builds a
realistic synthetic dataset (rules + noise) so the model learns a soft
decision boundary instead of memorizing an if/else:

```bash
# Eligibility model (~95% test accuracy)
python data/generate_training_data.py
python train_model.py

# Placement model
python data/generate_placement_data.py
python train_placement_model.py
```

Both steps are optional — if skipped, the API automatically falls back to
rule-based/formula scoring, so the app still works. Pre-trained models are
already included in `models/`, so you can skip this step entirely and just run
the server.

## 3. (Optional) Connect a Gen AI provider

Powers the chatbot, career roadmap, interview prep, and resume review with
real LLM output instead of templates.

```bash
cp .env.example .env
```

Edit `.env` and set **one** provider:

```
GENAI_PROVIDER=openai   # or: gemini | groq
OPENAI_API_KEY=sk-...
```

Leave `GENAI_PROVIDER` blank to run entirely on the built-in rule-based /
template fallback — every AI feature still returns a real, useful answer with
zero API keys configured.

## 4. Run the server

```bash
python app.py
```

This starts the API **and** serves the frontend at the same address:

```
http://localhost:5000
```

If you'd rather serve `frontend/` separately (e.g. VS Code's "Live Server" or
`python -m http.server`), `frontend/js/app.js` auto-detects that and points
its API calls at `http://localhost:5000` instead.

## API reference

| Method | Route                       | Purpose                                          |
|--------|------------------------------|---------------------------------------------------|
| GET    | `/api/health`                | Backend + Gen AI provider + ML model status        |
| GET    | `/api/courses`               | Course catalog                                     |
| POST   | `/api/students`              | Save/update a student profile (incl. interests/skills) |
| POST   | `/api/eligibility`           | ML-scored eligibility check                        |
| POST   | `/api/recommend`             | AI course recommendations (TF-IDF)                 |
| POST   | `/api/career/roadmap`        | AI career roadmap                                  |
| POST   | `/api/career/skill-gap`      | Skill-gap analysis                                  |
| POST   | `/api/career/interview`      | AI interview prep questions                        |
| POST   | `/api/resume/analyze`        | AI resume analyzer (text or PDF/TXT upload)          |
| POST   | `/api/placement`             | ML placement-probability estimate                   |
| POST   | `/api/register`              | Register a student for a course                    |
| GET    | `/api/dashboard`             | Live stats + charts data + registration list         |
| GET    | `/api/receipt/<reg_id>`      | PDF receipt download (QR embedded)                   |
| GET    | `/api/qr/<reg_id>.png`       | Standalone QR code image                            |
| GET    | `/api/verify/<reg_id>`       | Public verification page (what the QR opens)         |
| GET    | `/api/badges/<roll>`         | Achievement badges (earned + locked)                 |
| POST   | `/api/chat`                  | Gen AI chatbot / FAQ (rule-based fallback)           |

Every AI route accepts an optional `"lang"` field (`en` / `hi` / `es` / `fr`)
to get replies in that language when a Gen AI provider is configured.

## Notes

- Database: `backend/nexus.db` (SQLite) is created automatically on first run.
- Retrain either model any time — it overwrites the matching `.pkl` files.
- All course rules (credits, min CGPA, backlog limits, tags, skills taught,
  career paths, employability index) live in **one place**: `backend/courses.py`.
  Change them there and the UI, ML training labels, recommendations, skill-gap
  analysis, and chatbot knowledge all stay in sync.
- Voice input/output uses the browser's built-in Web Speech API — no extra
  backend or API key required, but browser support varies (best in Chrome).
