"""Two backends with the same interface: SupabaseBackend (real) and DemoBackend (in-memory, simulated)."""
import uuid
from datetime import datetime, timedelta, timezone
import streamlit as st
from . import rules
from .rules import RuleError
from .settings import DEMO, env

DEMO_USERS = [
    {"id": "u-ann", "display_name": "Ann (reporter)", "role": "reporter", "skills": [], "email": "ann@example.com"},
    {"id": "u-bee", "display_name": "Bee (fixer)", "role": "fixer", "skills": ["Cleaning", "Public facilities"], "email": "bee@example.com"},
    {"id": "u-chai", "display_name": "Chai (fixer)", "role": "fixer", "skills": ["Minor maintenance"], "email": "chai@example.com"},
]
BASE = (13.7563, 100.5018)


def compute_stats(reports: list) -> dict:
    n = lambda *s: sum(r["status"] in s for r in reports)
    return {"total": len(reports), "open": n("open"), "in_progress": n("claimed", "in_progress", "awaiting_confirmation"),
            "resolved": n("resolved")}


def _seed() -> list:
    now = datetime.now(timezone.utc)

    def mk(title, desc, cat, loc, dlat, dlon, status, days, claimed=None, flags=()):
        return {"id": str(uuid.uuid4()), "reporter_id": "u-ann", "title": title, "description": desc, "photo_url": None,
                "category": cat, "location_name": loc, "latitude": None if dlat is None else BASE[0] + dlat,
                "longitude": None if dlon is None else BASE[1] + dlon, "status": status, "claimed_by": claimed,
                "after_photo_url": None, "safety_flags": list(flags), "is_demo": True,
                "created_at": (now - timedelta(days=days)).isoformat(), "updated_at": now.isoformat()}
    return [
        mk("Litter near the engineering building", "Plastic bottles and food wrappers along the walkway.", "Cleaning", "Engineering Building, Gate 2", .001, .002, "open", 3),
        mk("Overflowing public waste bin", "Bin by the canteen is full and trash spills onto the ground.", "Cleaning", "Canteen A", .003, -.001, "open", 1),
        mk("Broken park bench", "Wooden slat missing on a bench; no sharp edges visible.", "Minor maintenance", "Central Park", -.002, .004, "claimed", 5, "u-chai"),
        mk("Community cleanup request", "Weekend cleanup of the pond area; volunteers welcome.", "Cleaning", "Pond area (no coordinates)", None, None, "open", 6),
        mk("Exposed wires near lamp post", "Cable cover missing. Needs a professional.", "Public facilities", "Library car park", .004, .003, "open", 2, flags=["Possible exposed electrical wiring"]),
    ]


class DemoBackend:
    is_demo = True

    def __init__(self):
        self.user, self.reports, self.confirmations = None, _seed(), []

    def demo_users(self): return DEMO_USERS
    def sign_in_demo(self, uid): self.user = dict(next(u for u in DEMO_USERS if u["id"] == uid))
    def sign_out(self): self.user = None
    def reset_demo(self): self.reports, self.confirmations = _seed(), []

    def list_reports(self):
        names = {u["id"]: u["display_name"] for u in DEMO_USERS}
        return [{**r, "reporter_name": names.get(r["reporter_id"]), "volunteer_name": names.get(r["claimed_by"])} for r in self.reports]

    def _apply(self, rid, fn, *args):
        i = next((i for i, r in enumerate(self.reports) if r["id"] == rid), None)
        if i is None:
            raise RuleError("Report not found.")
        self.reports[i] = fn(self.reports[i], self.user["id"], *args)

    def claim(self, rid): self._apply(rid, rules.claim)
    def start(self, rid): self._apply(rid, rules.start)
    def release(self, rid): self._apply(rid, rules.release)
    def cancel(self, rid): self._apply(rid, rules.cancel)
    def complete(self, rid, url): self._apply(rid, rules.complete, url)

    def review(self, rid, decision):
        self._apply(rid, rules.review, decision)
        self.confirmations.append({"report_id": rid, "confirmed_by": self.user["id"], "decision": decision})

    def store_photo(self, data: bytes, mime: str): return data  # kept in memory for the demo

    def create_report(self, d: dict):
        now = datetime.now(timezone.utc).isoformat()
        self.reports.insert(0, {**d, "id": str(uuid.uuid4()), "reporter_id": self.user["id"], "status": "open", "claimed_by": None,
                                "after_photo_url": None, "is_demo": True, "created_at": now, "updated_at": now})

    def save_skills(self, skills):
        self.user["skills"] = skills
        next(u for u in DEMO_USERS if u["id"] == self.user["id"])["skills"] = skills

    def fixer_emails(self, category):
        return [u["email"] for u in DEMO_USERS if u["role"] == "fixer" and category in u["skills"]]


class SupabaseBackend:
    is_demo = False

    def __init__(self):
        from supabase import create_client
        self.client = create_client(env("SUPABASE_URL"), env("SUPABASE_ANON_KEY"))  # anon key + user JWT => RLS applies
        self.bucket = env("SUPABASE_BUCKET", "report-photos")
        self.user = None

    def sign_in(self, email, password):
        res = self.client.auth.sign_in_with_password({"email": email, "password": password})
        self._load(res.user.id)

    def sign_up(self, email, password, name, role="reporter") -> bool:
        """Returns True if signed in immediately; False if email confirmation is required."""
        res = self.client.auth.sign_up({"email": email, "password": password, "options": {"data": {"display_name": name, "role": role}}})
        if res.session:
            self._load(res.user.id)
            return True
        return False

    def _load(self, uid):
        p = self.client.table("profiles").select("*").eq("id", uid).single().execute().data
        self.user = {"id": uid, "display_name": p["display_name"], "role": p.get("role", "reporter"), "skills": p.get("skills") or []}

    def sign_out(self):
        self.client.auth.sign_out()
        self.user = None

    def list_reports(self):
        rows = (self.client.table("reports")
                .select("*, reporter:profiles!reports_reporter_id_fkey(display_name), volunteer:profiles!reports_claimed_by_fkey(display_name)")
                .order("created_at", desc=True).limit(300).execute().data)
        return [{**r, "reporter_name": (r.pop("reporter") or {}).get("display_name"),
                 "volunteer_name": (r.pop("volunteer") or {}).get("display_name")} for r in rows]

    def _rpc(self, fn, **params):
        try:
            self.client.rpc(fn, params).execute()
        except Exception as e:  # postgres 'raise exception' messages are written for users
            raise RuleError(getattr(e, "message", None) or str(e))

    def claim(self, rid): self._rpc("claim_report", p_id=rid)
    def start(self, rid): self._rpc("start_report", p_id=rid)
    def release(self, rid): self._rpc("release_report", p_id=rid)
    def cancel(self, rid): self._rpc("cancel_report", p_id=rid)
    def complete(self, rid, url): self._rpc("submit_completion", p_id=rid, p_after_url=url)
    def review(self, rid, decision): self._rpc("review_completion", p_id=rid, p_decision=decision)

    def store_photo(self, data: bytes, mime: str) -> str:
        path = f"{self.user['id']}/{uuid.uuid4()}.{mime.split('/')[1].replace('jpeg', 'jpg')}"
        self.client.storage.from_(self.bucket).upload(path, data, {"content-type": mime})
        return self.client.storage.from_(self.bucket).get_public_url(path)

    def fixer_emails(self, category):
        from .notify_service import lookup_fixer_emails
        return lookup_fixer_emails(category)

    def create_report(self, d: dict):
        self.client.table("reports").insert({**d, "reporter_id": self.user["id"]}).execute()

    def save_skills(self, skills):
        self.client.table("profiles").update({"skills": skills}).eq("id", self.user["id"]).execute()
        self.user["skills"] = skills


def get_db():
    if "db" not in st.session_state:
        st.session_state["db"] = DemoBackend() if DEMO else SupabaseBackend()
    return st.session_state["db"]
