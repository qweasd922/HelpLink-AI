"""Email alerts to fixers who follow a report's category. Never raises: the report is already saved."""
import smtplib
from email.message import EmailMessage
from .settings import env


def smtp_ready() -> bool:
    return all(env(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def lookup_fixer_emails(category: str) -> list:
    """Server-side only. Uses the service key because fixer emails are private (no RLS policy exposes them)."""
    key = env("SUPABASE_SERVICE_KEY")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_KEY is not set")
    from supabase import create_client
    svc = create_client(env("SUPABASE_URL"), key)
    ids = [r["id"] for r in svc.table("profiles").select("id").eq("role", "fixer").contains("skills", [category]).execute().data]
    if not ids:
        return []
    return [r["email"] for r in svc.table("fixer_contacts").select("email").in_("id", ids).execute().data]


def send_email(report: dict, recipients: list) -> None:
    sender = env("SMTP_FROM") or env("SMTP_USER")
    msg = EmailMessage()
    msg["Subject"] = f"[HelpLink] New {report['category']} task: {report['title']}"
    msg["From"], msg["To"] = sender, sender  # real recipients are BCC so fixers don't see each other
    link = env("APP_URL")
    msg.set_content(
        f"A new problem was reported in a category you follow.\n\n"
        f"Title: {report['title']}\nCategory: {report['category']}\nLocation: {report['location_name']}\n\n"
        f"{report.get('description') or ''}\n\n" + (f"Open HelpLink to claim it: {link}\n" if link else "Open HelpLink to claim it.\n"))
    host, port = env("SMTP_HOST"), int(env("SMTP_PORT", "587"))
    with (smtplib.SMTP_SSL(host, port, timeout=20) if port == 465 else smtplib.SMTP(host, port, timeout=20)) as s:
        if port != 465:
            s.starttls()
        s.login(env("SMTP_USER"), env("SMTP_PASSWORD"))
        s.send_message(msg, to_addrs=recipients)


def notify_fixers(report: dict, db) -> str:
    """Returns a status message for the reporter."""
    cat = report["category"]
    try:
        emails = db.fixer_emails(cat)
    except Exception as e:
        return f"Report published, but fixers could not be looked up ({e}). No emails were sent."
    if not emails:
        return f"Report published. No fixers follow '{cat}' yet."
    if db.is_demo:
        return "Report published. 🧪 SIMULATED, no real email was sent. Would email: " + ", ".join(emails)
    if not smtp_ready():
        return f"Report published. {len(emails)} fixer(s) follow '{cat}', but email isn't configured (SMTP_* settings), so nothing was sent."
    try:
        send_email(report, emails)
    except Exception as e:
        return f"Report published, but sending email failed ({type(e).__name__})."
    return f"Report published and {len(emails)} fixer(s) notified by email."
