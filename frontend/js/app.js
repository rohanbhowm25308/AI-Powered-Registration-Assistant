/* ============ CONFIG ============ */
// Flask always serves the frontend AND the API from the same origin --
// whether that's http://127.0.0.1:5000 locally or a Render URL in
// production -- so API calls are always same-origin, relative paths.
const API_BASE = '';

let API_ONLINE = false;
let studentProfile = null;   // { name, roll, dept, sem, cgpa, backlog, interests }
let COURSES = [];
let charts = {};             // Chart.js instances, keyed by canvas id

/* ============ HELPERS ============ */
async function api(path, opts = {}) {
  const res = await fetch(API_BASE + path, {
    headers: opts.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${res.status})`);
  }
  return res.json();
}
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3200);
}
function currentLang() {
  const sel = document.getElementById('langSelect');
  return sel ? sel.value : 'en';
}

/* ============ HEALTH CHECK ============ */
async function checkHealth() {
  const dot = document.getElementById('statusDot');
  const label = document.getElementById('statusLabel');
  try {
    const health = await api('/api/health');
    API_ONLINE = true;
    dot.className = 'status-dot online';
    label.textContent = health.ai_provider ? `Backend online · ${health.ai_provider}` : 'Backend online';
  } catch (e) {
    API_ONLINE = false;
    dot.className = 'status-dot offline';
    label.textContent = 'Backend offline — start the Flask server';
  }
}

/* ============ NAV ============ */
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('view-' + btn.dataset.view).classList.add('active');
    if (btn.dataset.view === 'dashboard') renderDashboard();
    if (btn.dataset.view === 'register') renderCourses();
  });
});

/* ============ COURSES ============ */
async function loadCourses() {
  try {
    const data = await api('/api/courses');
    COURSES = data.courses;
  } catch (e) {
    COURSES = [
      { id: 'AIML', name: 'AI & Machine Learning', credits: 4, min_cgpa: 7.5, max_backlog: 0, last_date: 'Aug 10, 2026', seats: 60 },
      { id: 'DS', name: 'Data Science', credits: 4, min_cgpa: 7.0, max_backlog: 1, last_date: 'Aug 10, 2026', seats: 60 },
      { id: 'WEB', name: 'Web Development', credits: 3, min_cgpa: 6.0, max_backlog: 2, last_date: 'Aug 15, 2026', seats: 80 },
      { id: 'CYB', name: 'Cyber Security', credits: 4, min_cgpa: 7.0, max_backlog: 1, last_date: 'Aug 12, 2026', seats: 50 },
      { id: 'CLOUD', name: 'Cloud Computing', credits: 3, min_cgpa: 6.5, max_backlog: 1, last_date: 'Aug 12, 2026', seats: 55 },
    ];
  }
  renderRequirements();
  renderCourses();
}

/* ============ STUDENT DETAILS (chat tab) ============ */
document.getElementById('saveDetails').addEventListener('click', async () => {
  const name = document.getElementById('qName').value.trim();
  const roll = document.getElementById('qRoll').value.trim();
  if (!name || !roll) { addBotMsg("I'll need at least your <b>name</b> and <b>roll number</b> to save a profile."); return; }
  studentProfile = {
    name, roll,
    dept: document.getElementById('qDept').value,
    sem: document.getElementById('qSem').value,
    cgpa: parseFloat(document.getElementById('qCgpa').value) || 0,
    backlog: parseInt(document.getElementById('qBacklog').value) || 0,
    interests: document.getElementById('qInterests').value.trim(),
  };
  document.getElementById('eName').value = name;
  document.getElementById('eRoll').value = roll;
  document.getElementById('eDept').value = studentProfile.dept;
  document.getElementById('eSem').value = studentProfile.sem;
  document.getElementById('eCgpa').value = studentProfile.cgpa || '';
  document.getElementById('eBacklog').value = studentProfile.backlog || '';
  document.getElementById('recInterests').value = studentProfile.interests || '';
  document.getElementById('badgeRoll').value = roll;

  try {
    await api('/api/students', { method: 'POST', body: JSON.stringify(studentProfile) });
  } catch (e) { /* non-fatal */ }

  addBotMsg(`Saved, <b>${name}</b>. Your profile now powers the Eligibility, Recommend, Career Hub, and Badges tabs too.`);
});

/* ============ CHATBOT + VOICE ASSISTANT ============ */
const chatLog = document.getElementById('chatLog');
function addBotMsg(html) {
  const row = document.createElement('div');
  row.className = 'msg-row bot';
  const avatar = document.createElement('div');
  avatar.className = 'avatar bot-avatar';
  avatar.textContent = '✦';
  const bubble = document.createElement('div');
  bubble.className = 'msg bot';
  bubble.innerHTML = html;
  row.appendChild(avatar);
  row.appendChild(bubble);
  chatLog.appendChild(row);
  chatLog.scrollTop = chatLog.scrollHeight;
  return bubble;
}
function addUserMsg(text) {
  const row = document.createElement('div');
  row.className = 'msg-row user';
  const avatar = document.createElement('div');
  avatar.className = 'avatar user-avatar';
  avatar.textContent = (studentProfile && studentProfile.name) ? studentProfile.name[0].toUpperCase() : 'Y';
  const bubble = document.createElement('div');
  bubble.className = 'msg user';
  bubble.textContent = text;
  row.appendChild(avatar);
  row.appendChild(bubble);
  chatLog.appendChild(row);
  chatLog.scrollTop = chatLog.scrollHeight;
}

document.getElementById('chatSend').addEventListener('click', sendChat);
document.getElementById('chatInput').addEventListener('keydown', e => { if (e.key === 'Enter') sendChat(); });

function speak(text) {
  if (!('speechSynthesis' in window)) return;
  const plain = text.replace(/<[^>]+>/g, '');
  const utter = new SpeechSynthesisUtterance(plain);
  const langMap = { en: 'en-US', hi: 'hi-IN', es: 'es-ES', fr: 'fr-FR' };
  utter.lang = langMap[currentLang()] || 'en-US';
  speechSynthesis.cancel();
  speechSynthesis.speak(utter);
}

async function sendChat() {
  const input = document.getElementById('chatInput');
  const val = input.value.trim();
  if (!val) return;
  addUserMsg(val);
  input.value = '';

  const typing = addBotMsg('<span class="typing">thinking…</span>');
  try {
    const res = await api('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message: val, profile: studentProfile, lang: currentLang() }),
    });
    typing.innerHTML = res.reply;
    typing.classList.remove('typing');
    if (document.getElementById('voiceReplyToggle').checked) speak(res.reply);
  } catch (e) {
    typing.innerHTML = "I couldn't reach the assistant backend. Make sure the Flask server is running, or check your Gen AI API key in backend/.env.";
  }
  chatLog.scrollTop = chatLog.scrollHeight;
}

function setupChips() {
  const prompts = [
    'Which courses are available?', 'Can I register now?', 'What is the last date?',
    'Is my CGPA sufficient?', 'How many credits does AI & ML have?', 'Recommend a course for me',
  ];
  const wrap = document.getElementById('chatChips');
  wrap.innerHTML = '';
  prompts.forEach(p => {
    const el = document.createElement('div');
    el.className = 'chip';
    el.textContent = p;
    el.addEventListener('click', () => { document.getElementById('chatInput').value = p; sendChat(); });
    wrap.appendChild(el);
  });
}

// --- Voice input (Web Speech API) ---
let recognizer = null;
function setupVoiceInput() {
  const micBtn = document.getElementById('micBtn');
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    micBtn.title = 'Voice input not supported in this browser';
    micBtn.style.opacity = '0.4';
    micBtn.disabled = true;
    return;
  }
  recognizer = new SpeechRecognition();
  recognizer.continuous = false;
  recognizer.interimResults = false;

  const langMap = { en: 'en-US', hi: 'hi-IN', es: 'es-ES', fr: 'fr-FR' };

  micBtn.addEventListener('click', () => {
    recognizer.lang = langMap[currentLang()] || 'en-US';
    micBtn.classList.add('listening');
    try { recognizer.start(); } catch (e) { /* already started */ }
  });
  recognizer.addEventListener('result', (e) => {
    const transcript = e.results[0][0].transcript;
    document.getElementById('chatInput').value = transcript;
    sendChat();
  });
  recognizer.addEventListener('end', () => micBtn.classList.remove('listening'));
  recognizer.addEventListener('error', () => micBtn.classList.remove('listening'));
}

function onLanguageChanged(lang) {
  addBotMsg(I18N[lang] ? `${I18N[lang].tagline} 🌐` : 'Language updated.');
}

/* ============ ELIGIBILITY TAB ============ */
function renderRequirements() {
  const wrap = document.getElementById('reqList');
  wrap.innerHTML = '';
  COURSES.forEach(c => {
    const div = document.createElement('div');
    div.className = 'panel';
    div.style.padding = '14px 16px';
    div.innerHTML = `<div style="display:flex; justify-content:space-between; align-items:center;">
      <b style="font-family:'Space Grotesk',sans-serif;">${c.name}</b>
      <span style="font-family:'IBM Plex Mono',monospace; font-size:11.5px; color:var(--cyan);">${c.credits} CR</span>
      </div>
      <div style="color:var(--dim); font-size:12.5px; margin-top:6px;">Min CGPA <b style="color:var(--text)">${c.min_cgpa}</b> · Max backlogs <b style="color:var(--text)">${c.max_backlog}</b> · Closes ${c.last_date}</div>`;
    wrap.appendChild(div);
  });
}

document.getElementById('checkEligibility').addEventListener('click', async () => {
  const name = document.getElementById('eName').value.trim() || 'Student';
  const roll = document.getElementById('eRoll').value.trim();
  const dept = document.getElementById('eDept').value;
  const sem = document.getElementById('eSem').value;
  const cgpa = parseFloat(document.getElementById('eCgpa').value);
  const backlog = parseInt(document.getElementById('eBacklog').value) || 0;
  const box = document.getElementById('eligResult');

  if (isNaN(cgpa)) {
    box.className = 'result-box show not-eligible';
    box.innerHTML = 'Please enter a valid CGPA to check eligibility.';
    return;
  }
  studentProfile = { ...(studentProfile || {}), name, roll, dept, sem, cgpa, backlog };

  try {
    const res = await api('/api/eligibility', {
      method: 'POST', body: JSON.stringify({ name, roll, dept, sem, cgpa, backlog }),
    });
    if (res.eligible_courses.length > 0) {
      box.className = 'result-box show eligible';
      box.innerHTML = `✅ <b>${name}</b> is eligible for:<br>${res.eligible_courses.map(c => `&nbsp;&nbsp;• ${c.name} (${c.credits} credits) — <i>ML confidence ${(c.confidence * 100).toFixed(0)}%</i>`).join('<br>')}
        <span class="ml-tag">ML MODEL</span><br><br>CGPA: ${cgpa} · Backlogs: ${backlog}`;
    } else {
      box.className = 'result-box show not-eligible';
      box.innerHTML = `❌ <b>${name}</b> does not currently meet the requirements for any listed course. <span class="ml-tag">ML MODEL</span><br><br>CGPA: ${cgpa} · Backlogs: ${backlog}`;
    }
  } catch (e) {
    box.className = 'result-box show not-eligible';
    box.innerHTML = `Couldn't reach the eligibility engine (${e.message}). Is the Flask backend running?`;
  }
});

/* ============ RECOMMEND TAB ============ */
document.getElementById('getRecommendations').addEventListener('click', async () => {
  const interests = document.getElementById('recInterests').value.trim();
  const wrap = document.getElementById('recommendResults');
  if (!interests) { showToast('Describe your interests first.'); return; }
  wrap.innerHTML = '<div class="loading-line">Scoring courses against your interests…</div>';

  try {
    const res = await api('/api/recommend', {
      method: 'POST',
      body: JSON.stringify({
        interests,
        cgpa: studentProfile ? studentProfile.cgpa : null,
        backlog: studentProfile ? studentProfile.backlog : null,
      }),
    });
    wrap.innerHTML = '';
    res.recommendations.forEach((r, i) => {
      const card = document.createElement('div');
      card.className = 'rec-card' + (i === 0 ? ' top-pick' : '');
      card.innerHTML = `
        <div class="rec-head"><h3>${i === 0 ? '⭐ ' : ''}${r.name}</h3><span class="score">${r.overall_score.toFixed(0)}%</span></div>
        <div class="match-bar"><div class="match-bar-fill" style="width:${r.overall_score}%"></div></div>
        <div class="why">${r.why}</div>
        <span class="elig-tag ${r.eligible ? 'yes' : 'no'}">${r.eligible ? 'You\'re eligible' : 'Check eligibility first'}</span>
      `;
      wrap.appendChild(card);
    });
  } catch (e) {
    wrap.innerHTML = `<div class="loading-line">Couldn't get recommendations (${e.message}).</div>`;
  }
});

/* ============ CAREER HUB TAB ============ */
function courseNameById(id) {
  const c = COURSES.find(c => c.id === id);
  return c ? c.name : id;
}

document.getElementById('getRoadmap').addEventListener('click', async () => {
  const course_id = document.getElementById('careerCourse').value;
  const wrap = document.getElementById('careerResults');
  wrap.innerHTML = '<div class="loading-line">Building your roadmap…</div>';
  try {
    const res = await api('/api/career/roadmap', {
      method: 'POST',
      body: JSON.stringify({ course_id, profile: studentProfile, roll: studentProfile ? studentProfile.roll : '', lang: currentLang() }),
    });
    const stepsHtml = res.steps.map(s => `
      <div class="roadmap-step">
        <div class="phase-badge">${s.phase}</div>
        <div><div class="focus">${s.focus}</div><div class="detail">${s.detail}</div></div>
      </div>`).join('');
    wrap.innerHTML = `<div class="panel"><div class="eyebrow">Roadmap · ${res.course} <span class="ml-tag">${res.provider === 'rule_based' ? 'TEMPLATE' : 'GEN AI'}</span></div>${stepsHtml}</div>`;
  } catch (e) {
    wrap.innerHTML = `<div class="loading-line">Couldn't generate a roadmap (${e.message}).</div>`;
  }
});

document.getElementById('getSkillGap').addEventListener('click', async () => {
  const course_id = document.getElementById('careerCourse').value;
  const skills = document.getElementById('careerSkills').value;
  const wrap = document.getElementById('careerResults');
  wrap.innerHTML = '<div class="loading-line">Comparing your skills to the job requirements…</div>';
  try {
    const res = await api('/api/career/skill-gap', { method: 'POST', body: JSON.stringify({ course_id, skills }) });
    const rows = res.required_skills.map(s => {
      const has = res.have.includes(s);
      return `<div class="skillgap-bar-row"><div class="skill-name">${s}</div><div class="bar-track"><div class="bar-fill ${has ? 'have' : 'missing'}" style="width:${has ? 100 : 20}%"></div></div><div style="width:20px;">${has ? '✅' : '—'}</div></div>`;
    }).join('');
    wrap.innerHTML = `<div class="panel"><div class="eyebrow">Skill gap · ${res.course} (${res.coverage_pct}% covered)</div>${rows}<p style="color:var(--dim); font-size:13px; margin-top:12px;">${res.recommendation}</p></div>`;
  } catch (e) {
    wrap.innerHTML = `<div class="loading-line">Couldn't run skill-gap analysis (${e.message}).</div>`;
  }
});

document.getElementById('getInterview').addEventListener('click', async () => {
  const course_id = document.getElementById('careerCourse').value;
  const wrap = document.getElementById('careerResults');
  wrap.innerHTML = '<div class="loading-line">Preparing interview questions…</div>';
  try {
    const res = await api('/api/career/interview', { method: 'POST', body: JSON.stringify({ course_id, lang: currentLang() }) });
    const qs = res.questions.map((q, i) => `<div class="interview-q"><div class="qnum">${i + 1}</div><div>${q}</div></div>`).join('');
    wrap.innerHTML = `<div class="panel"><div class="eyebrow">Mock interview · ${res.course} <span class="ml-tag">${res.provider === 'rule_based' ? 'TEMPLATE' : 'GEN AI'}</span></div>${qs}</div>`;
  } catch (e) {
    wrap.innerHTML = `<div class="loading-line">Couldn't generate interview questions (${e.message}).</div>`;
  }
});

document.getElementById('getPlacement').addEventListener('click', async () => {
  const course_id = document.getElementById('careerCourse').value;
  const wrap = document.getElementById('careerResults');
  if (!studentProfile || studentProfile.cgpa === undefined) {
    showToast('Save your student profile first (Chat tab) so I know your CGPA.');
    return;
  }
  wrap.innerHTML = '<div class="loading-line">Estimating placement probability…</div>';
  const skillsCount = (document.getElementById('careerSkills').value.split(',').filter(s => s.trim()).length) || 0;
  try {
    const res = await api('/api/placement', {
      method: 'POST',
      body: JSON.stringify({
        cgpa: studentProfile.cgpa, backlog: studentProfile.backlog, sem: studentProfile.sem,
        dept: studentProfile.dept, course_id, skills_count: skillsCount,
      }),
    });
    const color = res.band === 'High' ? 'var(--ok)' : res.band === 'Moderate' ? 'var(--warn)' : 'var(--bad)';
    wrap.innerHTML = `<div class="panel"><div class="eyebrow">Placement probability · ${res.course}</div>
      <div class="placement-gauge">
        <div class="ring" style="background:conic-gradient(${color} ${res.probability_pct * 3.6}deg, var(--panel-2) 0deg); border:1px solid var(--line);">${res.probability_pct}%</div>
        <div class="band-label"><b>${res.band} likelihood</b>Based on CGPA, backlogs, course employability, and your skill count.<br><span class="ml-tag">${res.source === 'ml_model' ? 'ML MODEL' : 'FORMULA'}</span></div>
      </div></div>`;
  } catch (e) {
    wrap.innerHTML = `<div class="loading-line">Couldn't estimate placement probability (${e.message}).</div>`;
  }
});

/* ============ RESUME TAB ============ */
document.getElementById('analyzeResume').addEventListener('click', async () => {
  const text = document.getElementById('resumeText').value.trim();
  const fileInput = document.getElementById('resumeFile');
  const placeholder = document.getElementById('resumePlaceholder');
  const resultsWrap = document.getElementById('resumeResults');
  const roll = studentProfile ? studentProfile.roll : '';

  if (!text && !(fileInput.files && fileInput.files[0])) {
    showToast('Paste resume text or choose a file first.');
    return;
  }

  placeholder.style.display = 'block';
  placeholder.textContent = 'Analyzing…';
  resultsWrap.style.display = 'none';

  try {
    let res;
    if (fileInput.files && fileInput.files[0]) {
      const fd = new FormData();
      fd.append('file', fileInput.files[0]);
      fd.append('roll', roll);
      fd.append('lang', currentLang());
      res = await api('/api/resume/analyze', { method: 'POST', body: fd });
    } else {
      res = await api('/api/resume/analyze', { method: 'POST', body: JSON.stringify({ text, roll, lang: currentLang() }) });
    }

    placeholder.style.display = 'none';
    resultsWrap.style.display = 'block';
    const skillChips = res.skills_detected.length
      ? res.skills_detected.map(s => `<span class="skill-chip">${s}</span>`).join('')
      : '<span style="color:var(--dimmer); font-size:12.5px;">No specific skills detected — try adding more detail.</span>';
    const courseChips = res.matched_courses.map(c => `<span class="match-course-chip">${c.name}</span>`).join('');
    resultsWrap.innerHTML = `
      <div class="eyebrow">Skills detected <span class="ml-tag">${res.provider === 'rule_based' ? 'KEYWORD MATCH' : 'GEN AI'}</span></div>
      <div style="margin:10px 0 18px;">${skillChips}</div>
      <div class="eyebrow">Closest course fit</div>
      <div style="margin:10px 0 18px;">${courseChips || '<span style="color:var(--dimmer); font-size:12.5px;">No strong match yet.</span>'}</div>
      <div class="eyebrow">Review</div>
      <p style="font-size:13.5px; color:var(--text); line-height:1.6; margin-top:8px;">${res.summary}</p>
    `;
  } catch (e) {
    placeholder.style.display = 'block';
    placeholder.textContent = `Couldn't analyze this resume (${e.message}).`;
  }
});

/* ============ REGISTER TAB ============ */
let lastCourseCounts = {};

async function renderCourses() {
  try {
    const dash = await api('/api/dashboard');
    lastCourseCounts = {};
    dash.by_course.forEach(c => lastCourseCounts[c.course_id] = c.count);
  } catch (e) { /* ignore */ }

  const query = (document.getElementById('courseSearch')?.value || '').trim().toLowerCase();
  renderCourseGrid(query);
}

function renderCourseGrid(query = '') {
  const grid = document.getElementById('courseGrid');
  grid.innerHTML = '';

  const filtered = COURSES.filter(c => {
    if (!query) return true;
    const haystack = [
      c.name, c.id,
      ...(c.tags || []),
      ...(c.skills_taught || []),
      ...(c.career_paths || []),
    ].join(' ').toLowerCase();
    return haystack.includes(query);
  });

  if (filtered.length === 0) {
    grid.innerHTML = `<p style="color:var(--dim); grid-column:1/-1; text-align:center; padding:30px;">No courses match "${query}".</p>`;
    return;
  }

  filtered.forEach(c => {
    const registeredCount = lastCourseCounts[c.id] || 0;
    const card = document.createElement('div');
    card.className = 'course-card';
    card.innerHTML = `
      <span class="tag">${c.id}</span>
      <h3>${c.name}</h3>
      <div class="meta">
        <span>Credits: <b>${c.credits}</b></span>
        <span>Min CGPA: <b>${c.min_cgpa}</b> · Max backlogs: <b>${c.max_backlog}</b></span>
        <span>Closes: <b>${c.last_date}</b></span>
        <span>Registered: <b>${registeredCount}</b> / ${c.seats}</span>
      </div>
      <button class="btn register-btn" data-course="${c.id}">Register</button>
    `;
    grid.appendChild(card);
  });
  grid.querySelectorAll('.register-btn').forEach(btn => {
    btn.addEventListener('click', () => handleRegister(btn.dataset.course));
  });
}

document.getElementById('courseSearch')?.addEventListener('input', (e) => {
  renderCourseGrid(e.target.value.trim().toLowerCase());
});

async function handleRegister(courseId) {
  if (!studentProfile || !studentProfile.name || !studentProfile.roll) {
    showToast('Save your student details first (Chat tab) or run an eligibility check with your name and roll number.');
    return;
  }
  try {
    const reg = await api('/api/register', {
      method: 'POST',
      body: JSON.stringify({
        name: studentProfile.name, roll: studentProfile.roll,
        dept: studentProfile.dept, sem: studentProfile.sem,
        cgpa: studentProfile.cgpa, backlog: studentProfile.backlog,
        course_id: courseId,
      }),
    });
    showConfirmation(reg);
    renderCourses();
  } catch (e) {
    showToast(e.message);
  }
}

/* ============ CONFIRMATION MODAL ============ */
const modal = document.getElementById('confirmModal');
let lastReg = null;
function showConfirmation(reg) {
  lastReg = reg;
  document.getElementById('mStudent').textContent = reg.name;
  document.getElementById('mCourse').textContent = reg.course;
  document.getElementById('mRegId').textContent = reg.reg_id;
  document.getElementById('mDate').textContent = reg.date;
  document.getElementById('mQr').src = `${API_BASE}/api/qr/${reg.reg_id}.png`;
  modal.classList.add('show');
}
document.getElementById('mClose').addEventListener('click', () => modal.classList.remove('show'));
document.getElementById('mDownload').addEventListener('click', () => {
  if (lastReg) downloadReceipt(lastReg.reg_id);
});

function downloadReceipt(regId) {
  window.open(`${API_BASE}/api/receipt/${regId}`, '_blank');
}

/* ============ DASHBOARD (stats, charts, badges) ============ */
function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function renderCharts(dash) {
  const style = getComputedStyle(document.documentElement);
  const cyan = '#4fe0ff', blue = '#3d6bf0', dim = '#7688a8', line = '#1b2740';
  Chart.defaults.color = dim;
  Chart.defaults.font.family = "'Inter', sans-serif";

  destroyChart('byCourse');
  const courseLabels = dash.by_course.map(c => courseNameById(c.course_id));
  charts.byCourse = new Chart(document.getElementById('chartByCourse'), {
    type: 'bar',
    data: { labels: courseLabels, datasets: [{ data: dash.by_course.map(c => c.count), backgroundColor: cyan, borderRadius: 6 }] },
    options: { plugins: { legend: { display: false } }, scales: { x: { grid: { color: line } }, y: { grid: { color: line }, beginAtZero: true, ticks: { precision: 0 } } } },
  });

  destroyChart('byDept');
  charts.byDept = new Chart(document.getElementById('chartByDept'), {
    type: 'doughnut',
    data: {
      labels: dash.by_department.map(d => d.dept),
      datasets: [{ data: dash.by_department.map(d => d.count), backgroundColor: [cyan, blue, '#7ff3ff', '#33d685', '#ffb84f'] }],
    },
    options: { plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12, font: { size: 11 } } } } },
  });

  destroyChart('timeline');
  charts.timeline = new Chart(document.getElementById('chartTimeline'), {
    type: 'line',
    data: {
      labels: dash.timeline.map(t => t.day),
      datasets: [{ data: dash.timeline.map(t => t.count), borderColor: cyan, backgroundColor: 'rgba(79,224,255,0.12)', fill: true, tension: 0.35, pointBackgroundColor: cyan }],
    },
    options: { plugins: { legend: { display: false } }, scales: { x: { grid: { color: line } }, y: { grid: { color: line }, beginAtZero: true, ticks: { precision: 0 } } } },
  });
}

async function renderDashboard() {
  let dash;
  try {
    dash = await api('/api/dashboard');
  } catch (e) {
    showToast("Couldn't load dashboard data — is the backend running?");
    return;
  }
  document.getElementById('statTotal').textContent = dash.total_registrations;
  document.getElementById('statEligible').textContent = dash.eligible_checks;
  document.getElementById('statCourses').textContent = dash.by_course.length;
  document.getElementById('statBusiest').textContent = dash.busiest_course || '—';

  if (dash.by_course.length || dash.by_department.length || dash.timeline.length) {
    try {
      renderCharts(dash);
    } catch (e) {
      console.error('Chart rendering failed:', e);
      document.querySelectorAll('.chart-grid canvas').forEach(c => {
        const msg = document.createElement('div');
        msg.style.cssText = 'color:var(--dim); font-size:12.5px; padding:20px; text-align:center;';
        msg.textContent = "Charts couldn't load (" + e.message + ")";
        c.replaceWith(msg);
      });
    }
  }

  const tbody = document.getElementById('regTableBody');
  tbody.innerHTML = '';
  if (!dash.registrations || dash.registrations.length === 0) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="6">No registrations yet — head to the Register tab.</td></tr>`;
    return;
  }
  dash.registrations.slice().reverse().forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td class="regid">${r.reg_id}</td><td>${r.name}</td><td>${r.course}</td><td>${r.date}</td>
      <td><button class="dl-btn" data-id="${r.reg_id}">Download PDF</button></td>
      <td><button class="dl-btn delete-reg-btn" data-id="${r.reg_id}" title="Delete this registration">✕</button></td>`;
    tbody.appendChild(tr);
  });
  tbody.querySelectorAll('.dl-btn:not(.delete-reg-btn)').forEach(btn => {
    btn.addEventListener('click', () => downloadReceipt(btn.dataset.id));
  });
  tbody.querySelectorAll('.delete-reg-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm(`Delete registration ${btn.dataset.id}? This can't be undone.`)) return;
      try {
        await api(`/api/registrations/${btn.dataset.id}`, { method: 'DELETE' });
        renderDashboard();
        renderCourses();
      } catch (e) {
        showToast("Couldn't delete: " + e.message);
      }
    });
  });
}

document.getElementById('clearAllRegs').addEventListener('click', async () => {
  if (!confirm('Clear ALL registrations? This deletes every registration in the system and cannot be undone.')) return;
  try {
    await api('/api/registrations', { method: 'DELETE' });
    renderDashboard();
    renderCourses();
    showToast('All registrations cleared.');
  } catch (e) {
    showToast("Couldn't clear registrations: " + e.message);
  }
});

document.getElementById('loadBadges').addEventListener('click', async () => {
  const roll = document.getElementById('badgeRoll').value.trim();
  const wrap = document.getElementById('badgeGrid');
  if (!roll) { showToast('Enter a roll number first.'); return; }
  wrap.innerHTML = '<div class="loading-line">Loading badges…</div>';
  try {
    const res = await api(`/api/badges/${encodeURIComponent(roll)}`);
    wrap.innerHTML = '';
    [...res.earned, ...res.locked].forEach(b => {
      const earned = res.earned.some(e => e.id === b.id);
      const card = document.createElement('div');
      card.className = 'badge-card' + (earned ? ' earned' : '');
      card.innerHTML = `<div class="icon">${b.icon}</div><div class="name">${b.name}</div><div class="desc">${b.desc}</div>`;
      wrap.appendChild(card);
    });
  } catch (e) {
    wrap.innerHTML = `<div class="loading-line">Couldn't load badges (${e.message}).</div>`;
  }
});

/* ============ INIT ============ */
(async function init() {
  setupChips();
  setupVoiceInput();
  addBotMsg(`Welcome! I'm your AI Registration Assistant, backed by a Flask API, ML models, and a Gen AI provider. Ask me anything, or use the quick prompts below.`);
  await checkHealth();
  await loadCourses();
})();