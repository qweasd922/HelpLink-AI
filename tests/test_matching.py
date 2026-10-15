from datetime import datetime, timedelta, timezone
from services.matching_service import rank_tasks, haversine_km

NOW = datetime(2026, 10, 15, tzinfo=timezone.utc)


def rep(i, cat="Cleaning", lat=None, lon=None, days=1, status="open"):
    return {"id": i, "status": status, "category": cat, "latitude": lat, "longitude": lon,
            "created_at": (NOW - timedelta(days=days)).isoformat()}


def test_only_open_tasks_ranked():
    assert [r["id"] for r in rank_tasks([rep("a", status="resolved"), rep("b")], ["Cleaning"], now=NOW)] == ["b"]


def test_skill_match_and_proximity_win():
    near, far = rep("near", lat=13.0, lon=100.0), rep("far", lat=14.0, lon=100.0)
    other = rep("other", cat="Other", lat=13.0, lon=100.0)
    ids = [r["id"] for r in rank_tasks([far, other, near], ["Cleaning"], 13.0, 100.0, now=NOW)]
    assert ids[0] == "near"


def test_missing_location_is_handled_and_explained():
    r = rank_tasks([rep("x")], ["Cleaning"], None, None, now=NOW)[0]
    assert any("proximity not used" in w for w in r["reasons"]) and 0 <= r["score"] <= 100


def test_no_skills_no_location_uses_age_only():
    old, new = rep("old", days=7), rep("new", days=0)
    assert [r["id"] for r in rank_tasks([new, old], [], now=NOW)] == ["old", "new"]


def test_haversine_zero():
    assert haversine_km(1, 1, 1, 1) == 0
