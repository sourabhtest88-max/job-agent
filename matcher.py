import io
import re

SKILLS = [
    "manual testing", "functional testing", "regression testing", "smoke testing",
    "sanity testing", "integration testing", "system testing", "uat",
    "test case", "test scenario", "defect", "bug tracking", "jira",
    "sql", "api testing", "postman", "agile", "sdlc", "stlc",
    "database testing", "web testing", "exploratory testing"
]

def extract_text(filename, content):
    name = filename.lower()
    if name.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError("Unsupported file type")

def normalize(text):
    return re.sub(r"\s+", " ", (text or "").lower())

def score_job(description, resume_text):
    desc = normalize(description)
    resume = normalize(resume_text)
    matched = [skill for skill in SKILLS if skill in desc and (not resume or skill in resume)]
    # If resume has not been uploaded, provide a provisional description-based skill signal.
    if not resume:
        matched = [skill for skill in SKILLS if skill in desc]
        score = min(60, round(60 * len(matched) / 8))
    else:
        job_skills = [skill for skill in SKILLS if skill in desc]
        if not job_skills:
            return 0, []
        score = round(100 * len(matched) / len(job_skills))
    return min(100, score), matched

def make_hr_email(company, title, experience, matched_skills):
    skills = matched_skills or "Manual Testing, SQL and API Testing"
    return f"""Subject: Application for {title} opportunity

Dear Hiring Team,

I am interested in the {title} opportunity at {company}. I have {experience:.1f} years of experience in software testing, with skills in {skills}.

My experience includes manual testing, test case preparation and execution, defect tracking, SQL validation and API testing, along with working in Agile teams.

Please find my resume attached for your consideration. I would appreciate the opportunity to discuss how my experience aligns with your requirements.

Regards,
[Your Name]
[Phone Number]
[Email Address]"""
