import pytest
from services import rules
from services.rules import RuleError

R = {"id": "1", "reporter_id": "ann", "status": "open", "claimed_by": None, "after_photo_url": None}


def test_claim_and_duplicate_claim_blocked():
    r = rules.claim(R, "bee")
    assert r["status"] == "claimed" and r["claimed_by"] == "bee"
    with pytest.raises(RuleError):
        rules.claim(r, "chai")  # already claimed


def test_cannot_claim_resolved_or_own():
    with pytest.raises(RuleError):
        rules.claim({**R, "status": "resolved"}, "bee")
    with pytest.raises(RuleError):
        rules.claim(R, "ann")


def test_unauthorized_updates_blocked():
    claimed = rules.claim(R, "bee")
    for fn, args in [(rules.start, ()), (rules.release, ()), (rules.complete, ("url",))]:
        with pytest.raises(RuleError):
            fn(claimed, "chai", *args)


def test_full_happy_path_and_release():
    r = rules.start(rules.claim(R, "bee"), "bee")
    assert rules.release(r, "bee")["claimed_by"] is None
    done = rules.complete(r, "bee", "after.jpg")
    assert done["status"] == "awaiting_confirmation"
    assert rules.review(done, "ann", "confirmed")["status"] == "resolved"


def test_rejection_returns_to_in_progress_and_needs_photo():
    r = rules.claim(R, "bee")
    with pytest.raises(RuleError):
        rules.complete(r, "bee", "")
    done = rules.complete(r, "bee", "after.jpg")
    assert rules.review(done, "ann", "needs_more_work")["status"] == "in_progress"


def test_only_reporter_reviews():
    done = rules.complete(rules.claim(R, "bee"), "bee", "a.jpg")
    with pytest.raises(RuleError):
        rules.review(done, "bee", "confirmed")
