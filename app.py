import io, re, sqlite3, json, shutil, subprocess, sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from matcher import extract_text, score_job, make_hr_email
from browser_apply import apply_to_job

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "data" / "applications.db"
DB_PATH.parent.mkdir(exist_ok=True)

st.set_page_config(page_title="QA Job Application Agent", page_icon="🧪", layout="wide")

@st.cache_resource
def install_browser():
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True
    )

install_browser()

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT, title TEXT, location TEXT, work_mode TEXT,
            portal TEXT, salary TEXT, description TEXT, job_url TEXT,
            match_score INTEGER, matched_skills TEXT, status TEXT DEFAULT 'Saved',
            added_at TEXT, applied_at TEXT, UNIQUE(company, title, job_url)
        )
    """)
    conn.commit()
    return conn

conn = db()

st.title("🧪 QA Job Application Agent")
st.caption("Resume matching, job tracking and cautious browser-assisted applications. Automation never bypasses logins, CAPTCHAs or portal restrictions.")

with st.sidebar:
    st.header("Your job preferences")
    experience = st.number_input("Years of experience", min_value=0.0, max_value=30.0, value=3.83, step=0.1)
    location_pref = st.text_input("Preferred location", "India")
    work_pref = st.selectbox("Work mode", ["Both", "Remote", "Office"])
    daily_target = st.number_input("Daily application target", min_value=1, max_value=100, value=20)
    st.markdown("---")
    st.write("**Target roles**")
    roles = ["QA Engineer", "Manual Tester", "Software Test Engineer", "Test Analyst", "QA Analyst", "API Tester"]
    st.write(", ".join(roles))
    st.markdown("---")
    st.caption("Portal imports should use permitted exports, alerts, APIs or job links. This app does not bypass logins, CAPTCHAs or portal restrictions.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["1. Resume", "2. Import jobs", "3. Match & apply", "4. Application tracker", "5. Candidate profile"])

with tab1:
    st.subheader("Upload your resume")
    uploaded = st.file_uploader("Upload PDF, DOCX or TXT", type=["pdf", "docx", "txt"])
    resume_text = ""
    if uploaded:
        try:
            resume_text = extract_text(uploaded.name, uploaded.getvalue())
            st.session_state["resume_text"] = resume_text
            resume_path = DB_PATH.parent / ("resume" + Path(uploaded.name).suffix.lower())
            resume_path.write_bytes(uploaded.getvalue())
            st.session_state["resume_path"] = str(resume_path)
            st.success(f"Resume read successfully ({len(resume_text)} characters).")
        except Exception as e:
            st.error(f"Could not read this file: {e}")
    elif "resume_text" in st.session_state:
        resume_text = st.session_state["resume_text"]
        saved_resume = list(DB_PATH.parent.glob("resume.*"))
        if saved_resume:
            st.session_state["resume_path"] = str(saved_resume[0])
        st.info("Using the resume text uploaded earlier in this session.")
    if resume_text:
        with st.expander("Preview extracted resume text"):
            st.text_area("Extracted text", resume_text, height=260)
        st.download_button("Download extracted resume text", resume_text, "resume_extracted.txt")
    else:
        st.info("Upload your latest resume to calculate meaningful match scores.")

with tab2:
    st.subheader("Import job openings")
    st.markdown("Upload a CSV with these columns: `company,title,location,work_mode,portal,salary,description,job_url`.")
    sample = pd.DataFrame([{
        "company":"Example Technologies", "title":"Manual QA Engineer",
        "location":"India", "work_mode":"Hybrid", "portal":"Naukri",
        "salary":"Negotiable",
        "description":"3-5 years QA experience. Manual testing, test case design, regression testing, SQL, API testing, Postman, Jira and Agile.",
        "job_url":"https://example.com/jobs/qa-001"
    }])
    st.download_button("Download sample jobs CSV", sample.to_csv(index=False), "sample_jobs.csv", "text/csv")
    jobs_file = st.file_uploader("Upload jobs CSV", type=["csv"], key="jobs_csv")
    if jobs_file:
        try:
            df = pd.read_csv(jobs_file).fillna("")
            required = {"company","title","description","job_url"}
            missing = required - set(df.columns)
            if missing:
                st.error("Missing required columns: " + ", ".join(sorted(missing)))
            else:
                for col in ["location","work_mode","portal","salary"]:
                    if col not in df.columns:
                        df[col] = ""
                st.dataframe(df.head(20), use_container_width=True)
                if st.button("Import these jobs"):
                    inserted = 0
                    for _, r in df.iterrows():
                        score, skills = score_job(str(r["description"]), st.session_state.get("resume_text", ""))
                        cur = conn.execute("""
                            INSERT OR IGNORE INTO jobs
                            (company,title,location,work_mode,portal,salary,description,job_url,match_score,matched_skills,status,added_at)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                        """, (str(r["company"]),str(r["title"]),str(r["location"]),str(r["work_mode"]),
                              str(r["portal"]),str(r["salary"]),str(r["description"]),str(r["job_url"]),
                              score, ", ".join(skills), "Saved", datetime.now().isoformat(timespec="seconds")))
                        inserted += cur.rowcount
                    conn.commit()
                    st.success(f"Imported {inserted} new jobs. Duplicate rows were skipped.")
        except Exception as e:
            st.error(f"Could not import CSV: {e}")

with tab3:
    st.subheader("Review job matches")
    rows = conn.execute("SELECT id,company,title,location,work_mode,portal,salary,description,job_url,match_score,matched_skills,status FROM jobs ORDER BY match_score DESC, id DESC").fetchall()
    if not rows:
        st.info("Import a jobs CSV to see matching results.")
    else:
        df = pd.DataFrame(rows, columns=["id","company","title","location","work_mode","portal","salary","description","job_url","match_score","matched_skills","status"])
        min_score = st.slider("Minimum match score", 0, 100, 35)
        filtered = df[df.match_score >= min_score]
        st.write(f"{len(filtered)} jobs meet your selected score.")
        for _, r in filtered.iterrows():
            with st.expander(f"{r['match_score']}% · {r['title']} — {r['company']} · {r['status']}"):
                st.write(f"**Location:** {r['location']} | **Mode:** {r['work_mode']} | **Portal:** {r['portal']}")
                st.write(f"**Salary:** {r['salary'] or 'Not listed'}")
                st.write(f"**Matched skills:** {r['matched_skills'] or 'No clear skill matches yet'}")
                st.write(str(r["description"])[:2500])
                if r["job_url"]:
                    st.markdown(f"[Open original job posting]({r['job_url']})")
                email = make_hr_email(r["company"], r["title"], experience, r["matched_skills"])
                st.text_area("Suggested HR message", email, height=180, key=f"email_{r['id']}")
                c1, c2, c3, c4 = st.columns(4)
                if c1.button("Mark as reviewed", key=f"review_{r['id']}"):
                    conn.execute("UPDATE jobs SET status='Reviewed' WHERE id=?", (int(r["id"]),)); conn.commit(); st.rerun()
                if c2.button("Mark as applied", key=f"apply_{r['id']}"):
                    today_count = conn.execute("SELECT COUNT(*) FROM jobs WHERE applied_at LIKE ?", (date.today().isoformat()+"%",)).fetchone()[0]
                    if today_count >= daily_target:
                        st.warning(f"Daily target of {daily_target} reached. Increase the target in the sidebar if appropriate.")
                    else:
                        conn.execute("UPDATE jobs SET status='Applied', applied_at=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), int(r["id"])))
                        conn.commit(); st.success("Recorded as applied. This does not submit anything to the job portal."); st.rerun()
                if c3.button("Reject job", key=f"reject_{r['id']}"):
                    conn.execute("UPDATE jobs SET status='Not relevant' WHERE id=?", (int(r["id"]),)); conn.commit(); st.rerun()
                if c4.button("Fill / apply", key=f"browser_apply_{r['id']}"):
                    profile_file = DB_PATH.parent / "candidate_profile.json"
                    if not profile_file.exists():
                        st.warning("Complete the Candidate profile tab first.")
                    elif not st.session_state.get("resume_path"):
                        st.warning("Upload your resume in the Resume tab first.")
                    else:
                        try:
                            cfg = json.loads(profile_file.read_text(encoding="utf-8"))
                            result = apply_to_job(r.to_dict(), st.session_state["resume_path"],
                                                  auto_submit=bool(cfg.get("auto_submit", False)),
                                                  allowed_domains=cfg.get("allowed_auto_submit_domains", []))
                            st.info(result.get("status", "Completed") + ": " + result.get("detail", ""))
                            if result.get("filled"):
                                st.write("Filled: " + ", ".join(result["filled"]))
                            if result.get("skipped"):
                                st.warning("Skipped: " + ", ".join(result["skipped"]))
                            if result.get("status") == "Submission attempted":
                                conn.execute("UPDATE jobs SET status='Submission attempted', applied_at=? WHERE id=?",
                                             (datetime.now().isoformat(timespec="seconds"), int(r["id"])))
                                conn.commit()
                        except Exception as e:
                            st.error(f"Application helper could not run: {e}")

with tab4:
    st.subheader("Application tracker")
    rows = conn.execute("SELECT company,title,location,portal,match_score,status,added_at,applied_at,job_url FROM jobs ORDER BY id DESC").fetchall()
    if rows:
        tracker = pd.DataFrame(rows, columns=["Company","Job title","Location","Portal","Match score","Status","Added at","Applied at","Job URL"])
        today_count = conn.execute("SELECT COUNT(*) FROM jobs WHERE applied_at LIKE ?", (date.today().isoformat()+"%",)).fetchone()[0]
        a,b,c = st.columns(3)
        a.metric("Jobs saved", len(tracker))
        b.metric("Applications recorded today", today_count)
        c.metric("Daily target", daily_target)
        st.dataframe(tracker, use_container_width=True, hide_index=True)
        st.download_button("Export tracker CSV", tracker.to_csv(index=False), "qa_job_application_tracker.csv", "text/csv")
    else:
        st.info("Your tracker is empty. Import jobs to get started.")

st.markdown("---")
st.caption("Privacy: your resume and tracker are processed locally by this app. Do not upload sensitive identity documents. Always verify job details and review messages before sending.")

with tab5:
    st.subheader("Candidate profile and browser automation")
    st.warning("Use truthful information only. Auto-submit is limited to employer/ATS domains you explicitly allow. LinkedIn, Naukri and Indeed pages are intentionally not auto-submitted by this generic helper. Never bypass CAPTCHAs or site restrictions.")
    profile_path = DB_PATH.parent / "candidate_profile.json"
    saved = json.loads(profile_path.read_text(encoding="utf-8")) if profile_path.exists() else {}
    with st.form("candidate_profile_form"):
        c1, c2 = st.columns(2)
        first_name = c1.text_input("First name", saved.get("first_name", ""))
        last_name = c2.text_input("Last name", saved.get("last_name", ""))
        email = c1.text_input("Email", saved.get("email", ""))
        phone = c2.text_input("Phone", saved.get("phone", ""))
        location = c1.text_input("City / location", saved.get("location", ""))
        experience_years = c2.text_input("Years of experience", str(saved.get("experience_years", "")))
        cover_note = st.text_area("Optional cover note (must be accurate)", saved.get("cover_note", ""))
        st.markdown("**Automatic submission settings**")
        auto_submit = st.checkbox("Enable automatic submission on explicitly allow-listed employer/ATS domains", value=bool(saved.get("auto_submit", False)))
        domains_text = st.text_input("Allowed domains (comma-separated, e.g. careers.example.com)", ", ".join(saved.get("allowed_auto_submit_domains", [])))
        consent = st.checkbox("I confirm these profile details are accurate and I authorize submissions only on the domains listed above.", value=bool(saved.get("consent", False)))
        save_profile = st.form_submit_button("Save candidate profile")
        if save_profile:
            try:
                years_value = float(experience_years) if experience_years.strip() else ""
                domains = [x.strip().lower() for x in domains_text.split(",") if x.strip()]
                if not all([first_name.strip(), last_name.strip(), email.strip(), phone.strip()]):
                    st.error("First name, last name, email and phone are required.")
                elif auto_submit and (not consent or not domains):
                    st.error("To enable auto-submit, confirm consent and add at least one allowed employer/ATS domain.")
                else:
                    profile = {"first_name": first_name.strip(), "last_name": last_name.strip(), "email": email.strip(),
                               "phone": phone.strip(), "location": location.strip(), "experience_years": years_value,
                               "cover_note": cover_note.strip(), "auto_submit": auto_submit,
                               "allowed_auto_submit_domains": domains, "consent": consent}
                    profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
                    st.success("Candidate profile saved locally.")
            except ValueError:
                st.error("Years of experience must be a number.")
    st.markdown("**One-time portal sign-in**")
    st.caption("This opens a persistent local Chromium profile so you can sign in yourself. No passwords are collected by this app.")
    login_url = st.text_input("Portal sign-in URL", placeholder="https://www.naukri.com/")
    if st.button("Open browser for manual sign-in"):
        st.code(f'python browser_apply.py --login "{login_url}"')
        st.info("Run this command in a separate terminal from the project folder. Sign in manually, then press Enter in that terminal to save the session.")

st.markdown("---")
st.caption("Privacy: resume, candidate profile, browser session and tracker are stored locally in the project data folder. Protect this folder and do not commit it to a public repository.")
