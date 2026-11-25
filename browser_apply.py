"""Conservative Playwright helper for supported employer/ATS application forms.

It does not bypass authentication, CAPTCHAs, queues, or access controls. Portal
sites (LinkedIn, Naukri, Indeed) are not auto-submitted by this generic helper.
Use only on sites whose terms permit browser automation.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from urllib.parse import urlparse

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
PROFILE_DIR = DATA_DIR / "browser_profile"
PROFILE_FILE = DATA_DIR / "candidate_profile.json"
PORTAL_HOSTS = {"linkedin.com", "www.linkedin.com", "naukri.com", "www.naukri.com", "indeed.com", "www.indeed.com", "in.indeed.com"}


def load_profile():
    if not PROFILE_FILE.exists():
        raise RuntimeError("Candidate profile is missing. Complete the Profile tab first.")
    data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    required = ["first_name", "last_name", "email", "phone"]
    missing = [x for x in required if not str(data.get(x, "")).strip()]
    if missing:
        raise RuntimeError("Complete these required profile fields first: " + ", ".join(missing))
    return data


def host_allowed(host: str, allowlist: list[str]) -> bool:
    host = (host or "").lower().split(":")[0]
    return any(host == d.lower().strip() or host.endswith("." + d.lower().strip()) for d in allowlist if d.strip())


def _fill_first(page, selectors, value):
    if not value:
        return False
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            if loc.count() and loc.is_visible() and loc.is_enabled():
                loc.fill(str(value), timeout=1200)
                return True
        except Exception:
            pass
    return False


def apply_to_job(job: dict, resume_path: str, auto_submit: bool = False, allowed_domains=None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed. Run: python -m pip install playwright && python -m playwright install chromium") from exc

    url = str(job.get("job_url", "")).strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError("Job URL must be a valid HTTPS URL.")
    host = parsed.hostname or ""
    if host.lower() in PORTAL_HOSTS or any(host.lower().endswith("." + d) for d in ("linkedin.com", "naukri.com", "indeed.com")):
        return {"status": "Manual action required", "detail": "This is a LinkedIn, Naukri or Indeed page. Open it and apply manually according to that portal's rules; generic form automation is intentionally disabled on portal domains."}

    profile = load_profile()
    resume = Path(resume_path) if resume_path else None
    if not resume or not resume.exists():
        raise RuntimeError("Upload and save your resume in the Resume tab before applying.")

    allowlist = allowed_domains or []
    submit_allowed = bool(auto_submit and host_allowed(host, allowlist))
    filled, skipped = [], []
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), headless=False,
            accept_downloads=False, viewport={"width": 1365, "height": 900}
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1800)
        body = (page.locator("body").inner_text(timeout=5000) or "").lower()
        if any(term in body for term in ["verify you are human", "captcha", "security challenge", "sign in to continue", "log in to continue"]):
            context.close()
            return {"status": "Manual action required", "detail": "The page requires sign-in or a human verification step. No attempt was made to bypass it. Use the saved browser session/login helper, then retry."}

        fields = [
            (["input[name*='first' i]", "input[id*='first' i]", "input[autocomplete='given-name']"], profile.get("first_name"), "first name"),
            (["input[name*='last' i]", "input[id*='last' i]", "input[autocomplete='family-name']"], profile.get("last_name"), "last name"),
            (["input[type='email']", "input[name*='email' i]", "input[id*='email' i]"], profile.get("email"), "email"),
            (["input[type='tel']", "input[name*='phone' i]", "input[id*='phone' i]"], profile.get("phone"), "phone"),
            (["input[name*='city' i]", "input[id*='city' i]"], profile.get("location"), "location"),
            (["input[name*='experience' i]", "input[id*='experience' i]"], profile.get("experience_years"), "experience"),
            (["textarea[name*='summary' i]", "textarea[name*='cover' i]", "textarea"], profile.get("cover_note", ""), "cover note"),
        ]
        for selectors, value, label in fields:
            if value and _fill_first(page, selectors, value):
                filled.append(label)
        try:
            uploads = page.locator("input[type='file']")
            if uploads.count():
                uploads.first.set_input_files(str(resume.resolve()), timeout=5000)
                filled.append("resume")
            else:
                skipped.append("resume upload field not detected")
        except Exception:
            skipped.append("resume upload could not be completed")

        # Conservative eligibility gate: only submit when user explicitly enabled it,
        # domain is allow-listed, and no required fields remain empty.
        required_missing = page.locator("input[required]:visible, textarea[required]:visible, select[required]:visible")
        missing_count = 0
        try:
            for i in range(required_missing.count()):
                el = required_missing.nth(i)
                typ = (el.get_attribute("type") or "").lower()
                if typ == "file":
                    continue
                val = el.input_value(timeout=700)
                if not val.strip():
                    missing_count += 1
        except Exception:
            missing_count += 1
        if submit_allowed and missing_count == 0:
            submit = page.get_by_role("button", name=re.compile(r"^(submit application|submit|apply now|send application)$", re.I))
            if submit.count() == 1 and submit.is_visible() and submit.is_enabled():
                submit.click(timeout=5000)
                page.wait_for_timeout(1800)
                result = {"status": "Submission attempted", "detail": "The allowed-domain submit control was clicked. Verify the confirmation on the opened browser page.", "filled": filled, "skipped": skipped}
            else:
                result = {"status": "Review required", "detail": "Could not identify one unambiguous submit button. Nothing was submitted.", "filled": filled, "skipped": skipped}
        else:
            why = "Auto-submit is off or this domain is not on your allowlist." if not submit_allowed else f"{missing_count} required field(s) remain empty."
            result = {"status": "Filled - not submitted", "detail": why + " Review the opened browser page and submit manually if everything is correct.", "filled": filled, "skipped": skipped}
        context.close()
        return result


def login_session(url):
    from playwright.sync_api import sync_playwright
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(user_data_dir=str(PROFILE_DIR), headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        input("Complete sign-in in the opened browser. Press Enter here when finished...")
        context.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", help="Open a site to sign in and save a local browser session")
    args = parser.parse_args()
    if args.login:
        login_session(args.login)
