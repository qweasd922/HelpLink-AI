"""Pure task-state rules. The demo backend uses these directly; schema.sql enforces the same rules in Postgres."""
from datetime import datetime, timezone

CATEGORIES = ["Cleaning", "Minor maintenance", "Animal welfare", "Public facilities", "Other"]
STATUS_LABEL = {
    "open": "Open", "claimed": "Claimed", "in_progress": "In Progress",
    "awaiting_confirmation": "Awaiting Confirmation", "resolved": "Resolved", "cancelled": "Cancelled",
}


class RuleError(Exception):
    """A user-facing rule violation."""


def _touch(r: dict, **changes) -> dict:
    return {**r, **changes, "updated_at": datetime.now(timezone.utc).isoformat()}


def _assigned(r: dict, uid: str, allowed: tuple) -> None:
    if r.get("claimed_by") != uid:
        raise RuleError("Only the assigned volunteer can do this.")
    if r["status"] not in allowed:
        raise RuleError(f"Not allowed while the task is '{STATUS_LABEL[r['status']]}'.")


def claim(r: dict, uid: str) -> dict:
    if r["status"] != "open":
        raise RuleError("This task is no longer available to claim.")
    if r["reporter_id"] == uid:
        raise RuleError("You cannot claim your own report.")
    return _touch(r, status="claimed", claimed_by=uid)


def start(r: dict, uid: str) -> dict:
    _assigned(r, uid, ("claimed",))
    return _touch(r, status="in_progress")


def release(r: dict, uid: str) -> dict:
    _assigned(r, uid, ("claimed", "in_progress"))
    return _touch(r, status="open", claimed_by=None)


def complete(r: dict, uid: str, after_photo_url) -> dict:
    _assigned(r, uid, ("claimed", "in_progress"))
    if not after_photo_url:
        raise RuleError("An after-photo is required.")
    return _touch(r, status="awaiting_confirmation", after_photo_url=after_photo_url)


def review(r: dict, uid: str, decision: str) -> dict:
    if r["reporter_id"] != uid:
        raise RuleError("Only the reporter can review completion.")
    if r["status"] != "awaiting_confirmation":
        raise RuleError("This task is not awaiting confirmation.")
    if decision == "confirmed":
        return _touch(r, status="resolved")
    if decision == "needs_more_work":
        return _touch(r, status="in_progress")
    raise RuleError("Invalid decision.")


def cancel(r: dict, uid: str) -> dict:
    if r["reporter_id"] != uid or r["status"] != "open":
        raise RuleError("Only the reporter can cancel an open report.")
    return _touch(r, status="cancelled")
