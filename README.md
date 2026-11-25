# QA Job Application Agent — Version 1

A beginner-friendly local dashboard for resume parsing, job-description matching, duplicate prevention, HR message drafting and application tracking.

## Important scope

This starter version does **not** scrape Naukri, LinkedIn or Indeed, log in to accounts, bypass CAPTCHAs, or submit applications. Import job details from permitted CSV exports, job alerts, official APIs where available, or job links you collect. Review each job and submit through the portal yourself.

The matching score is a simple keyword-based baseline, not an AI hiring prediction. We can add an LLM-based analysis step after the basic workflow works.

## 1. Install Python

Install Python 3.11 or newer from https://www.python.org/downloads/ . During Windows installation, select **Add Python to PATH**.

## 2. Open the project folder

Open Command Prompt or PowerShell in this folder.

## 3. Create a virtual environment

Windows:
```powershell
py -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4. Install packages

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Start the app

```bash
streamlit run app.py
```

The app should open in your browser at `http://localhost:8501`.

## 6. Use the app

1. Open the Resume tab and upload your PDF, DOCX or TXT resume.
2. Open Import jobs and download the sample CSV to see the required format.
3. Replace the sample rows with real job postings you are permitted to collect.
4. Upload the CSV and click Import these jobs.
5. Open Match & review, inspect each job and use the original job link.
6. Edit the suggested HR message and attach your resume when applying.
7. Record the result in the tracker.

## CSV columns

Required: `company`, `title`, `description`, `job_url`

Optional: `location`, `work_mode`, `portal`, `salary`

## Data storage

Application records are stored locally in `data/applications.db` (SQLite). Export the tracker as CSV from the dashboard. Keep your resume private and do not commit it to a public Git repository.

## Troubleshooting

- If `streamlit` is not recognized, activate `.venv` and run `python -m streamlit run app.py`.
- If PDF text is blank, the PDF may be scanned/image-only. Use a text-based PDF or DOCX.
- If duplicate jobs are skipped, the same company/title/job URL combination is already stored.
