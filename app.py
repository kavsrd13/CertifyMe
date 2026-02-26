"""
app.py — Microsoft Certification Learning Coach
Production-ready end-user interface.

Flow:
  1. Student enters topics + email + timeline
  2. Silent 3-step pipeline (Curator → Planner → Engagement)
  3. Review: Learning Path / Schedule / Reminders
  4. Human checkpoint: "I'm ready"
  5. Assessment (10 questions)
  6. Pass → Certification recommendation | Fail → Loop back
"""

import os, json, time, re
import streamlit as st
from dotenv import load_dotenv
from orchestration.workflow import (
    run_syllabus_agent,
    run_curator_agent,
    run_planner_agent,
    run_engagement_agent,
    run_assessment_agent,
    run_recommendation_agent,
)

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CertifyMe",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root{
  --bg:       #080C14;
  --surface:  #0F1623;
  --card:     rgba(255,255,255,0.04);
  --border:   rgba(255,255,255,0.08);
  --primary:  #5B6EF5;
  --p-glow:   rgba(91,110,245,.30);
  --accent:   #F0A500;
  --success:  #12B76A;
  --danger:   #F04438;
  --text:     #F2F4F7;
  --muted:    #8896AB;
  --r:        16px;
  --r-sm:     10px;
}

*{font-family:'Inter',sans-serif;box-sizing:border-box;}
.stApp{background:var(--bg);color:var(--text);}
header[data-testid="stHeader"]{background:transparent!important;}
.block-container{max-width:900px;padding-top:2rem;padding-bottom:4rem;}

/* ── sidebar ── */
section[data-testid="stSidebar"]{background:var(--surface)!important;border-right:1px solid var(--border)!important;}
section[data-testid="stSidebar"] *{color:var(--text)!important;}

/* ── inputs ── */
div[data-testid="stTextArea"] textarea,
div[data-testid="stTextInput"] input{
  background:var(--surface)!important;color:var(--text)!important;
  border:1px solid var(--border)!important;border-radius:var(--r-sm)!important;
  font-size:.95rem!important;}
div[data-testid="stTextArea"] textarea::placeholder,
div[data-testid="stTextInput"] input::placeholder{color:var(--muted)!important;}
div[data-testid="stTextArea"] label,
div[data-testid="stTextInput"] label{color:var(--muted)!important;font-size:.85rem!important;font-weight:500!important;}
div[data-testid="stSelectbox"] [data-baseweb="select"]>div{
  background:var(--surface)!important;border:1px solid var(--border)!important;
  border-radius:var(--r-sm)!important;color:var(--text)!important;}
div[data-testid="stSelectbox"] [data-baseweb="select"] *{color:var(--text)!important;}
div[data-baseweb="menu"],div[data-baseweb="menu"] *{background:#111827!important;color:var(--text)!important;}

/* ── buttons ── */
div.stButton>button{
  background:linear-gradient(135deg,var(--primary),#7B8CFF)!important;
  color:#fff!important;border:none!important;border-radius:var(--r-sm)!important;
  font-weight:600!important;padding:.7rem 1.5rem!important;
  box-shadow:0 4px 24px var(--p-glow)!important;transition:all .2s!important;}
div.stButton>button:hover{transform:translateY(-1px)!important;box-shadow:0 8px 32px var(--p-glow)!important;}
div[data-testid="stFormSubmitButton"]>button{
  background:linear-gradient(135deg,var(--accent),#E07B00)!important;
  color:#fff!important;border:none!important;border-radius:var(--r-sm)!important;
  font-weight:600!important;padding:.7rem 1.5rem!important;}

/* ── progress ── */
div[data-testid="stProgress"]>div>div{
  background:linear-gradient(90deg,var(--primary),var(--accent))!important;border-radius:8px!important;}

/* ── radio ── */
div[data-testid="stRadio"]{
  background:var(--card)!important;border:1px solid var(--border)!important;
  border-radius:var(--r-sm)!important;padding:.5rem .8rem!important;}
div[data-testid="stRadio"] label,div[data-testid="stRadio"] label *{color:var(--text)!important;}

/* ── expander ── */
div[data-testid="stExpander"]{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:var(--r)!important;}
div[data-testid="stExpander"] summary{color:var(--text)!important;}

/* ── tabs ── */
div[data-testid="stTabs"] button{color:var(--muted)!important;font-weight:500!important;border-bottom:2px solid transparent!important;}
div[data-testid="stTabs"] button[aria-selected="true"]{color:var(--primary)!important;border-bottom-color:var(--primary)!important;}
div[data-testid="stTabs"] button:hover{color:var(--text)!important;}

/* ── cards ── */
.lc-card{
  background:var(--card);border:1px solid var(--border);border-radius:var(--r);
  padding:1.4rem 1.6rem;margin-bottom:.75rem;}
.lc-card h4{margin:0 0 .35rem;font-size:1rem;font-weight:600;color:var(--text);}
.lc-card p,.lc-card li{color:var(--muted);font-size:.9rem;line-height:1.65;margin:0;}
.lc-card ul{padding-left:1.1rem;margin:.4rem 0 0;}
.lc-card a{color:#818CF8;text-decoration:none;font-weight:500;}
.lc-card a:hover{text-decoration:underline;}

/* tag badge */
.tag{display:inline-block;background:rgba(91,110,245,.18);color:#A5B4FC;
     border:1px solid rgba(91,110,245,.3);border-radius:999px;
     padding:.18rem .7rem;font-size:.75rem;font-weight:600;margin-right:.35rem;}
.tag-success{background:rgba(18,183,106,.15);color:#6EE7B7;border-color:rgba(18,183,106,.3);}
.tag-warn{background:rgba(240,165,0,.15);color:#FCD34D;border-color:rgba(240,165,0,.3);}
.tag-danger{background:rgba(240,68,56,.15);color:#FCA5A5;border-color:rgba(240,68,56,.3);}

/* step indicator */
.step-row{display:flex;align-items:center;gap:.5rem;margin-bottom:1.6rem;}
.step-dot{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;
          justify-content:center;font-size:.75rem;font-weight:700;flex-shrink:0;}
.sd-done{background:var(--success);color:#fff;}
.sd-active{background:linear-gradient(135deg,var(--primary),var(--accent));color:#fff;box-shadow:0 0 12px var(--p-glow);}
.sd-idle{background:rgba(255,255,255,.06);color:var(--muted);border:1px solid var(--border);}
.step-lbl{font-size:.82rem;color:var(--muted);}
.step-sep{flex:1;height:1px;background:var(--border);}

/* verdict */
.v-pass{background:rgba(18,183,106,.1);border:1px solid rgba(18,183,106,.3);border-radius:var(--r);padding:2rem;text-align:center;}
.v-fail{background:rgba(240,68,56,.1);border:1px solid rgba(240,68,56,.25);border-radius:var(--r);padding:2rem;text-align:center;}
.score-num{font-size:3.8rem;font-weight:800;}
.score-pass{color:var(--success);}
.score-fail{color:var(--danger);}

/* module link card */
.mod-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r-sm);
          padding:.9rem 1.1rem;margin-bottom:.5rem;}
.mod-card a{color:#A5B4FC;font-weight:600;font-size:.93rem;}
.mod-card small{color:var(--muted);font-size:.8rem;}

/* question */
.q-text{color:var(--text);font-weight:600;font-size:.97rem;margin-bottom:.5rem;}

/* divider */
.div-line{border:none;border-top:1px solid var(--border);margin:1.5rem 0;}

/* week card */
.week-badge{display:inline-block;background:rgba(91,110,245,.2);color:#A5B4FC;
            border-radius:6px;padding:.2rem .6rem;font-size:.78rem;font-weight:700;margin-right:.5rem;}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_azure_ok():
    return bool(os.getenv("AZURE_OPENAI_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_DEPLOYMENT"))

def reset_all():
    for k in list(st.session_state.keys()):
        del st.session_state[k]

def step_bar(current: int):
    steps = ["Topics", "Learning Path", "Schedule", "Reminders", "Confirm", "Assessment", "Result"]
    html = '<div class="step-row">'
    for i, s in enumerate(steps, 1):
        cls = "sd-done" if i < current else ("sd-active" if i == current else "sd-idle")
        html += f'<div class="step-dot {cls}">{i}</div><div class="step-lbl">{s}</div>'
        if i < len(steps):
            html += '<div class="step-sep"></div>'
    st.markdown(html + "</div>", unsafe_allow_html=True)

def lc_card(title: str, body: str):
    st.markdown(f'<div class="lc-card"><h4>{title}</h4>{body}</div>', unsafe_allow_html=True)

# ── Sidebar: only progress ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='margin-bottom:.2rem'>
      <span style='font-size:1.15rem;font-weight:800;background:linear-gradient(135deg,#A5B4FC,#F0A500);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent'>CertifyMe</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    phase_now = st.session_state.get("phase", 0)
    labels = ["Enter Topics","Learning Path","Study Schedule","Reminders","Readiness Check","Assessment","Results"]
    progress_map = {0:0, 1:2, 2:4, 3:5, 4:6}
    done = progress_map.get(phase_now, 0)
    st.markdown("**Your Progress**")
    st.progress(done / len(labels))
    st.caption(f"Step {done} of {len(labels)}")
    st.write("")
    for i, lbl in enumerate(labels):
        icon  = "✅" if i < done else ("▶️" if i == done else "⬜")
        color = "#12B76A" if i < done else ("#A5B4FC" if i == done else "#475569")
        weight = "600" if i == done else "400"
        st.markdown(
            f"<div style='display:flex;gap:.5rem;align-items:center;margin:.18rem 0'>"
            f"<span>{icon}</span><span style='color:{color};font-size:.84rem;font-weight:{weight}'>{lbl}</span></div>",
            unsafe_allow_html=True)
    st.markdown("---")
    if st.button("↩ Start Over", use_container_width=True):
        reset_all(); st.rerun()

phase = st.session_state.get("phase", 0)

# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 0 — TOPIC INPUT
# ═════════════════════════════════════════════════════════════════════════════
if phase == 0:
    step_bar(1)

    st.markdown("""
    <div style='text-align:center;padding:1.2rem 0 1.8rem'>
      <div style='font-size:2rem;font-weight:800;letter-spacing:.04em;
                  background:linear-gradient(135deg,#A5B4FC,#F0A500);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  margin-bottom:.5rem'>CertifyMe</div>
      <h1 style='font-size:1.5rem;font-weight:600;color:#F2F4F7;margin:0'>
        Which Microsoft certification are you preparing for?
      </h1>
      <p style='color:#8896AB;margin:.5rem 0 0;font-size:.88rem'>
        Tell us the topics or exam you're targeting — we'll build your personalised study plan, 
        set up reminders, and assess your readiness.
      </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("input_form"):
        topics = st.text_area(
            "Topics you want to learn",
            placeholder="e.g. Azure Virtual Networks, Azure Storage, Identity and Access Management, Azure Security Centre",
            height=120,
        )
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input(
                "Your email (for study reminders)",
                placeholder="you@email.com",
            )
        with col2:
            timeline = st.text_input(
                "How long do you have?",
                placeholder="e.g. 4 weeks, 2 months",
            )
        st.write("")
        submitted = st.form_submit_button("Build My Learning Plan →", use_container_width=True)

    if submitted:
        if not topics.strip():
            st.warning("Please enter at least one topic.")
        elif not get_azure_ok():
            st.error("Service configuration error. Please contact your administrator.")
        else:
            st.session_state.update({
                "topics": topics.strip(),
                "email":  email.strip() or "not provided",
                "timeline": timeline.strip() or "flexible",
                "phase": 1,
            })
            st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 1 — SILENT PIPELINE
# ═════════════════════════════════════════════════════════════════════════════
elif phase == 1:
    step_bar(2)

    topics   = st.session_state["topics"]
    timeline = st.session_state["timeline"]

    st.markdown("""
    <div style='text-align:center;padding:1rem 0 1.6rem'>
      <h2 style='font-size:1.8rem;font-weight:700;color:#F2F4F7;margin:0'>Building your personalised plan…</h2>
      <p style='color:#8896AB;margin:.5rem 0 0'>This takes about 30–60 seconds.</p>
    </div>""", unsafe_allow_html=True)

    prog  = st.progress(0.0)
    label = st.empty()

    def update(pct, msg):
        prog.progress(pct, msg)
        label.markdown(
            f"<div style='text-align:center;color:#8896AB;font-size:.9rem;margin-top:.3rem'>{msg}</div>",
            unsafe_allow_html=True)

    # Step A: preprocess topics → structured syllabus (silent)
    update(0.08, "Understanding your topics…")
    try:
        syllabus, conv = run_syllabus_agent(
            f"Topics requested: {topics}. Timeline: {timeline}",
            f"Topics: {topics}. Preferred timeline: {timeline}.",
        )
        st.session_state["syllabus"] = syllabus
        st.session_state["conv"]     = conv
    except Exception as e:
        st.error(f"Could not process your topics. Please try again. ({e})")
        st.stop()

    # Step B: curate MS Learn paths
    update(0.35, "Finding the best Microsoft Learn resources for your topics…")
    mcp_msgs = []
    def mcp_cb(m): mcp_msgs.append(m)
    try:
        learning_paths, conv = run_curator_agent(
            st.session_state["syllabus"],
            st.session_state["conv"],
            mcp_progress_callback=mcp_cb,
        )
        st.session_state["learning_paths"] = learning_paths
        st.session_state["conv"]           = conv
    except Exception as e:
        st.error(f"Could not build learning paths. Please try again. ({e})")
        st.stop()

    # Step C: generate study plan
    update(0.62, "Creating your personalised schedule…")
    try:
        study_plan, conv = run_planner_agent(
            st.session_state["learning_paths"],
            st.session_state["conv"],
        )
        st.session_state["study_plan"] = study_plan
        st.session_state["conv"]       = conv
    except Exception as e:
        st.error(f"Could not generate study plan. Please try again. ({e})")
        st.stop()

    # Step D: engagement / reminders
    update(0.88, "Setting up your study reminders…")
    try:
        engagement, conv = run_engagement_agent(
            st.session_state["study_plan"],
            st.session_state["conv"],
        )
        st.session_state["engagement"] = engagement
        st.session_state["conv"]       = conv
    except Exception as e:
        st.error(f"Could not set up reminders. Please try again. ({e})")
        st.stop()

    update(1.0, "Done!")
    time.sleep(0.6)
    st.session_state["phase"] = 2
    st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 2 — REVIEW PLAN (3 tabs: Learning Path | Schedule | Reminders)
# ═════════════════════════════════════════════════════════════════════════════
elif phase == 2:
    step_bar(3)

    lp        = st.session_state.get("learning_paths", {})
    sp        = st.session_state.get("study_plan", {})
    eng       = st.session_state.get("engagement", {})
    syllabus  = st.session_state.get("syllabus", {})
    topics    = st.session_state.get("topics", "")

    st.markdown(f"""
    <div style='margin-bottom:1.4rem'>
      <h2 style='font-size:1.55rem;font-weight:700;color:#F2F4F7;margin:0'>Your personalised plan is ready</h2>
      <p style='color:#8896AB;margin:.35rem 0 0;font-size:.93rem'>
        Based on: <strong style='color:#A5B4FC'>{topics[:120]}{"…" if len(topics)>120 else ""}</strong>
      </p>
    </div>""", unsafe_allow_html=True)

    tab_lp, tab_sched, tab_remind = st.tabs(["📚  Learning Path", "📅  Study Schedule", "🔔  Reminders"])

    # ── Tab 1: Learning Path ──────────────────────────────────────────────────
    with tab_lp:
        st.write("")
        paths = lp.get("learning_paths", [])
        total_hrs = lp.get("total_curated_hours", "?")
        tips      = lp.get("tips", [])

        col_m1, col_m2 = st.columns([2, 1])
        with col_m1:
            st.markdown(f"**{len(paths)} topic areas · {total_hrs} hours of learning**")
        with col_m2:
            st.markdown("&nbsp;")

        st.write("")
        for path in paths:
            dom      = path.get("domain", "")
            priority = path.get("priority", "")
            modules  = path.get("modules", [])
            tag_cls  = "tag-success" if priority=="High" else ("tag-warn" if priority=="Medium" else "")
            st.markdown(
                f"<div style='margin:.9rem 0 .35rem'>"
                f"<span style='font-weight:600;color:#F2F4F7'>{dom}</span> "
                f"<span class='tag {tag_cls}'>{priority}</span></div>",
                unsafe_allow_html=True)
            for mod in modules:
                url   = mod.get("url", "#")
                title = mod.get("title", "")
                desc  = mod.get("description", "")
                hrs   = mod.get("duration_hours", "?")
                st.markdown(
                    f"""<div class="mod-card">
                      <a href="{url}" target="_blank">{title}</a><br/>
                      <small>⏱ {hrs} hr{'s' if hrs!=1 else ''}
                      {"&nbsp;·&nbsp;" + desc if desc else ""}</small>
                    </div>""",
                    unsafe_allow_html=True)
            st.markdown("<hr class='div-line'>", unsafe_allow_html=True)

        if tips:
            for tip in tips:
                st.info(f"💡 {tip}")

    # ── Tab 2: Study Schedule ─────────────────────────────────────────────────
    with tab_sched:
        st.write("")
        weeks    = sp.get("weeks", [])
        tot_wks  = sp.get("total_weeks", "?")
        daily    = sp.get("daily_hours", "?")
        kd       = sp.get("key_dates", {})

        c1, c2, c3 = st.columns(3)
        c1.metric("Duration", f"{tot_wks} weeks")
        c2.metric("Daily commitment", f"{daily} hr/day")
        c3.metric("Exam-ready by", kd.get("exam_ready_date", "—"))

        st.write("")
        for w in weeks:
            wnum = w.get("week", "")
            theme = w.get("theme", "")
            milestone = w.get("milestone", "")
            tasks = w.get("daily_tasks", [])
            checkpoint = w.get("checkpoint", "")

            with st.expander(f"Week {wnum} — {theme}", expanded=(wnum==1)):
                st.markdown(
                    f"<p style='color:#8896AB;font-size:.88rem;margin:0 0 .7rem'>"
                    f"🎯 <strong style='color:#F2F4F7'>Milestone:</strong> {milestone}</p>",
                    unsafe_allow_html=True)
                for t in tasks:
                    day  = t.get("day", "")
                    task = t.get("task", "")
                    dur  = t.get("duration_hours", "?")
                    st.markdown(
                        f"<div style='display:flex;gap:.7rem;margin:.3rem 0;align-items:flex-start'>"
                        f"<span style='color:#A5B4FC;font-weight:600;min-width:75px;font-size:.85rem'>{day}</span>"
                        f"<span style='color:#8896AB;font-size:.88rem'>{task} <em>({dur}h)</em></span></div>",
                        unsafe_allow_html=True)
                if checkpoint:
                    st.markdown(
                        f"<p style='color:#FCD34D;font-size:.83rem;margin:.6rem 0 0'>❓ Self-check: {checkpoint}</p>",
                        unsafe_allow_html=True)

        tips_sp = sp.get("success_tips", [])
        if tips_sp:
            st.write("")
            for t in tips_sp:
                st.success(f"✅ {t}")

    # ── Tab 3: Reminders ──────────────────────────────────────────────────────
    with tab_remind:
        st.write("")
        email   = st.session_state.get("email", "")
        strat   = eng.get("engagement_strategy", {})
        times   = strat.get("daily_reminder_times", [])
        habits  = strat.get("weekly_habits", [])
        acct    = strat.get("accountability_techniques", [])
        burnout = strat.get("burnout_prevention", [])
        checklist = eng.get("readiness_checklist", [])
        nudges  = eng.get("week_by_week_nudges", [])

        if email and email != "not provided":
            st.success(f"📧 Reminders will be sent to **{email}**")
        else:
            st.info("No email provided — reminders shown here for your reference.")

        st.write("")
        if times:
            lc_card("Daily Reminder Times",
                "<ul>" + "".join(f"<li>{t}</li>" for t in times) + "</ul>")

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if habits:
                lc_card("Weekly Study Habits",
                    "<ul>" + "".join(
                        f"<li><strong>{h.get('habit','')}</strong> — {h.get('description','')}</li>"
                        for h in habits) + "</ul>")
            if burnout:
                lc_card("Staying Energised",
                    "<ul>" + "".join(f"<li>{b}</li>" for b in burnout) + "</ul>")

        with col_r2:
            if acct:
                lc_card("Accountability Tips",
                    "<ul>" + "".join(f"<li>{a}</li>" for a in acct) + "</ul>")
            if checklist:
                lc_card("Pre-Assessment Checklist",
                    "<ul>" + "".join(f"<li>{c}</li>" for c in checklist) + "</ul>")

        if nudges:
            st.markdown("**Weekly encouragement**")
            for n in nudges:
                wk  = n.get("week", "")
                msg = n.get("motivational_message", "")
                man = n.get("focus_mantra", "")
                rew = n.get("reward_suggestion", "")
                with st.expander(f"Week {wk} — {man}"):
                    st.write(msg)
                    if rew:
                        st.caption(f"🎁 Reward: {rew}")

    # ── Checkpoint gate ───────────────────────────────────────────────────────
    st.markdown("<hr class='div-line'>", unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center;padding:1.2rem 1rem'>
      <h3 style='font-size:1.25rem;font-weight:700;color:#F2F4F7;margin:0 0 .4rem'>
        Finished reviewing your plan?
      </h3>
      <p style='color:#8896AB;font-size:.9rem;margin:0'>
        When you're ready, take the practice assessment to check your knowledge.
        It's a 10-question quiz — you need 70% to pass.
      </p>
    </div>""", unsafe_allow_html=True)

    c_l, c_mid, c_r = st.columns([1, 2, 1])
    with c_mid:
        if st.button("I'm ready — Start Assessment →", use_container_width=True):
            st.session_state["phase"] = 3
            st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 3 — ASSESSMENT
# ═════════════════════════════════════════════════════════════════════════════
elif phase == 3:
    step_bar(6)

    st.markdown("""
    <div style='margin-bottom:1.4rem'>
      <h2 style='font-size:1.55rem;font-weight:700;color:#F2F4F7;margin:0'>Knowledge Assessment</h2>
      <p style='color:#8896AB;margin:.35rem 0 0;font-size:.9rem'>
        10 questions · Answer all · Submit once · 70% to pass
      </p>
    </div>""", unsafe_allow_html=True)

    if "assessment" not in st.session_state:
        with st.spinner("Generating your assessment questions…"):
            try:
                assessment, conv = run_assessment_agent(st.session_state["conv"])
                st.session_state["assessment"] = assessment
                st.session_state["conv"] = conv
            except Exception as e:
                st.error(f"Could not generate assessment. Please try again. ({e})")
                st.stop()

    assessment = st.session_state["assessment"]
    questions  = assessment.get("questions", [])

    if not questions:
        st.error("No questions were generated. Please start over.")
        st.stop()

    # Progress indicator
    answered = sum(1 for q in questions if st.session_state.get(f"qans_{q['id']}", ""))
    st.progress(answered / len(questions), f"{answered}/{len(questions)} questions answered")
    st.write("")

    with st.form("quiz_form"):
        for q in questions:
            qid   = q["id"]
            diff  = q.get("difficulty", "")
            dom   = q.get("domain", "")
            d_col = {"Easy": "tag-success", "Medium": "tag-warn", "Hard": "tag-danger"}.get(diff, "")

            st.markdown(
                f"<div class='q-text'>Q{qid}. {q['question']}"
                f" <span class='tag {d_col}' style='float:right'>{diff}</span></div>",
                unsafe_allow_html=True)
            opts = q.get("options", {})
            st.radio(
                label=f"ans_{qid}",
                options=[f"{k}) {v}" for k, v in opts.items()],
                key=f"qans_{qid}",
                label_visibility="collapsed",
            )
            st.write("")

        st.markdown("---")
        done = st.form_submit_button("Submit Assessment →", use_container_width=True)

    if done:
        answers = {q["id"]: (st.session_state.get(f"qans_{q['id']}", "") or " ")[0]
                   for q in questions}
        st.session_state["student_answers"] = answers
        st.session_state["phase"] = 4
        st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
#  PHASE 4 — RESULTS  (Conditional branch: PASS → cert plan | FAIL → loop)
# ═════════════════════════════════════════════════════════════════════════════
elif phase == 4:
    step_bar(7)

    assessment = st.session_state["assessment"]
    answers    = st.session_state["student_answers"]

    if "recommendation" not in st.session_state:
        with st.spinner("Evaluating your answers…"):
            rec = run_recommendation_agent(assessment, answers, st.session_state["conv"])
            st.session_state["recommendation"] = rec

    rec     = st.session_state["recommendation"]
    verdict = rec.get("verdict", "FAIL")
    score   = rec.get("score_percent", 0)
    correct = rec.get("correct", 0)
    total   = rec.get("total", 10)
    rec_d   = rec.get("recommendation", {})
    strengths = rec.get("strength_domains", [])
    weaknesses = rec.get("weak_domains", [])

    # ── Verdict banner ────────────────────────────────────────────────────────
    c_l, c_mid, c_r = st.columns([1, 2, 1])
    with c_mid:
        if verdict == "PASS":
            st.markdown(f"""
            <div class="v-pass">
              <div class="score-num score-pass">{score}%</div>
              <h2 style='color:#12B76A;margin:.3rem 0'>Assessment Passed 🎉</h2>
              <p style='color:#A7F3D0'>{correct}/{total} correct answers</p>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="v-fail">
              <div class="score-num score-fail">{score}%</div>
              <h2 style='color:#F04438;margin:.3rem 0'>Keep Practising</h2>
              <p style='color:#FEE2E2'>{correct}/{total} correct &nbsp;·&nbsp; 70% needed to pass</p>
            </div>""", unsafe_allow_html=True)

    st.write("")

    # ── Detail columns ────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2, gap="large")

    with col_a:
        msg = rec_d.get("message", "")
        steps = rec_d.get("next_steps", [])
        if msg:
            lc_card("What to do next",
                f"<p>{msg}</p><ul>" + "".join(f"<li>{s}</li>" for s in steps) + "</ul>")

        if strengths:
            lc_card("Your strengths",
                "<ul>" + "".join(
                    f"<li><span class='tag tag-success'>✓</span> {s}</li>"
                    for s in strengths) + "</ul>")

    with col_b:
        if verdict == "PASS":
            booking = rec.get("exam_booking", {})
            url     = booking.get("url", "https://examregistration.microsoft.com/")
            tips    = booking.get("tips", [])
            provider= booking.get("provider", "Pearson VUE")
            lc_card("Book Your Certification Exam",
                f"<p>Provider: <strong>{provider}</strong></p>"
                f"<p><a href='{url}' target='_blank'>Register now →</a></p>"
                + ("<ul>" + "".join(f"<li>{t}</li>" for t in tips) + "</ul>" if tips else ""))
        else:
            if weaknesses:
                lc_card("Topics to revisit",
                    "<ul>" + "".join(
                        f"<li><span class='tag tag-danger'>!</span> {w}</li>"
                        for w in weaknesses) + "</ul>")

    # ── Answer review (collapsed) ─────────────────────────────────────────────
    st.write("")
    with st.expander("Review your answers"):
        for q in assessment.get("questions", []):
            qid      = q["id"]
            student  = answers.get(qid, "")
            correct_ = q.get("correct_answer", "")
            is_ok    = student == correct_
            icon     = "✅" if is_ok else "❌"
            st.markdown(f"**{icon} Q{qid}. {q['question']}**")
            if is_ok:
                st.success(f"Correct — {student})")
            else:
                st.error(f"Your answer: {student})  ·  Correct: {correct_})")
            st.caption(q.get("explanation", ""))
            st.write("")

    # ── Actions ───────────────────────────────────────────────────────────────
    st.markdown("<hr class='div-line'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        if st.button("↩ Start a new study plan", use_container_width=True):
            reset_all(); st.rerun()
    with c2:
        if verdict == "PASS":
            st.markdown(
                f"""<a href="https://examregistration.microsoft.com/" target="_blank">
                <button style="width:100%;background:linear-gradient(135deg,#12B76A,#059669);
                color:#fff;border:none;border-radius:10px;padding:.7rem;font-weight:600;
                font-size:.93rem;cursor:pointer">Register for the Certification Exam →</button></a>""",
                unsafe_allow_html=True)
        else:
            if st.button("📖 Revisit my plan and try again", use_container_width=True):
                weak = ", ".join(weaknesses)
                st.session_state["topics"] = (
                    st.session_state.get("topics", "") +
                    f" (focus especially on: {weak})")
                st.session_state["goals"] = (
                    f"Previous score: {score}%. Need to improve on: {weak}.")
                for k in ["phase","syllabus","learning_paths","study_plan",
                          "engagement","conv","assessment","recommendation","student_answers"]:
                    st.session_state.pop(k, None)
                st.rerun()
