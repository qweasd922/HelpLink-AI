# HelpLink — report a problem, a fixer gets an email

Streamlit + Supabase (Postgres, Auth, Storage). No AI. Two roles:
- **Reporter** posts a problem in a category (title, description, location, optional photo).
- **Fixer** picks the categories they follow, gets an email when a matching problem is posted, then claims and fixes it. The reporter confirms completion.

## Demo mode (no accounts, no keys)
```
pip install -r requirements.txt
copy .env.example .env      # keep DEMO_MODE=true  (macOS/Linux: cp)
streamlit run app.py
```
Sign in as Ann (reporter), post a problem in "Cleaning": the app shows which fixers WOULD be emailed (Bee). Emails are simulated in demo mode and clearly labelled.

## Real mode
1. Supabase: run `schema.sql` in the SQL Editor (safe to re-run). In Auth, turn off "Confirm email" for easy testing.
2. `.env`: `DEMO_MODE=false`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` (Project Settings > API).
3. Email: set `SMTP_*` (Gmail: 2-step verification on, then an App Password). Without SMTP the app still works and tells the reporter that nothing was sent.
4. Sign up two accounts: one "Fix problems" (open Profile, choose categories, Save) and one "Report problems". Post a problem; the fixer receives an email.

## Security notes
- Fixer emails live in `fixer_contacts`, which no client can read. Only the server-side `SUPABASE_SERVICE_KEY` reads it, to send alerts. Keep it in `.env` / Streamlit Secrets only, never in Git.
- Fixer addresses are BCC'd so fixers never see each other.
- Task rules (only fixers claim, one claim wins, only the assigned fixer updates, only the reporter confirms) are enforced in SQL functions, not just the UI.

## Tests
`pytest` covers task rules, validation, matching and notification behaviour (no fixers, SMTP missing, send failure).
