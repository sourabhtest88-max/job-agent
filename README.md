# QA Job Application Agent — Version 2

Version 2 preserves the original Streamlit dashboard, resume parsing, CSV import, keyword matching, HR message drafting, duplicate prevention, SQLite tracker and CSV export. It adds a candidate profile and cautious Playwright browser assistance for employer/ATS application forms.

## Important portal and automation limits

- LinkedIn, Naukri and Indeed can be used as places where you find job links, but this generic helper intentionally does **not** automate submission on those portal domains. Follow each portal's current terms and use its own application flow.
- The browser helper is intended for employer career sites / ATS pages where automation is permitted. Website forms differ, so field detection is best-effort and must be checked.
- It does not bypass logins, CAPTCHAs, bot checks, queues, paywalls or other access controls. If a human verification or sign-in wall is detected, it stops.
- Auto-submit is OFF by default. To enable it, you must explicitly opt in, provide truthful candidate details, and allow-list exact employer/ATS domains in the Candidate profile tab. It submits only if required visible fields are populated and it finds exactly one clearly named submit button. Otherwise it leaves the page unsubmitted.
- A click is recorded as **Submission attempted**, not proof of successful application. Verify the employer confirmation page/email.
- Never enter fabricated answers. Questions not recognized by the helper must be completed manually. Do not store passwords in this app.

## 1. Install Python

Install Python 3.11+ from https://www.python.org/downloads/windows/ . During setup, check **Add python.exe to PATH**. Open a new PowerShell window after installation.

## 2. Install project dependencies

From this folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

If PowerShell blocks activation, run this once for the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. Start the dashboard

```powershell
python -m streamlit run app.py
```

## 4. Configure and use

1. Resume tab: upload your current PDF, DOCX or TXT resume. The file is saved locally under `data/` for form upload.
2. Candidate profile tab: enter your accurate name, email, phone, location and experience. Save the profile.
3. Import jobs tab: upload a CSV with `company,title,location,work_mode,portal,salary,description,job_url`.
4. Match & apply tab: inspect the match, original posting, and suggested HR note. Click **Fill / apply** to open the job page in Chromium and attempt safe field filling.
5. For a site that requires login, sign in manually once using the helper command shown in the Candidate profile tab. Run it from another PowerShell terminal in this project folder:

```powershell
python browser_apply.py --login "https://careers.example.com/"
```

The browser profile is stored locally in `data/browser_profile/`. Do not share it.
6. Auto-submit remains disabled unless you turn it on, confirm consent and add the employer/ATS domain to the allowlist. Start with one employer test page and verify the result.
7. Application tracker: review statuses and export the tracker CSV.

## CSV columns

All eight columns are supported: `company`, `title`, `location`, `work_mode`, `portal`, `salary`, `description`, `job_url`. Minimum required fields for import are `company`, `title`, `description`, `job_url`.

## Local data and privacy

SQLite tracker: `data/applications.db`  
Candidate profile: `data/candidate_profile.json`  
Resume copy: `data/resume.*`  
Persistent browser session: `data/browser_profile/`

These files can contain personal information and authenticated sessions. Keep them private, do not commit them to Git, and delete them from the machine when no longer needed. The app does not send your resume to a cloud service by default.

## Troubleshooting

- `python` not recognized: install Python and check **Add python.exe to PATH**, then reopen PowerShell.
- `playwright` not installed: activate `.venv`, run `python -m pip install -r requirements.txt`, then `python -m playwright install chromium`.
- Login/CAPTCHA detected: complete sign-in or verification manually; the helper will not bypass it.
- No form fields detected: the employer page uses a custom form. Complete it manually; the helper reports that it could not fill fields.
- No submission: confirm the domain is allow-listed, auto-submit is enabled, all required fields are complete, and the page has one unambiguous submit button. The app may still require manual completion.
