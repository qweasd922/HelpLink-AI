import math
from datetime import datetime, timezone

DEFAULT_WEIGHTS = {"relevance": 0.40, "proximity": 0.35, "age": 0.25}
NEAR_KM = 5.0      # distance at which proximity score reaches 0
AGE_CAP_DAYS = 7   # age score maxes out after this many days


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def _parse(ts) -> datetime:
    return ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def rank_tasks(reports: list, skills: list, lat=None, lon=None, weights=None, now=None) -> list:
    """Ranks OPEN tasks. Components without data are skipped and the remaining weights renormalised."""
    w = weights or DEFAULT_WEIGHTS
    now = now or datetime.now(timezone.utc)
    ranked = []
    for r in reports:
        if r["status"] != "open":
            continue
        parts, why = {}, []
        if skills:
            hit = r["category"] in skills
            parts["relevance"] = 1.0 if hit else 0.0
            why.append("Matches your skills" if hit else "Outside your listed skills")
        else:
            why.append("No skills set: relevance not used")
        if None not in (lat, lon, r.get("latitude"), r.get("longitude")):
            d = haversine_km(lat, lon, r["latitude"], r["longitude"])
            parts["proximity"] = max(0.0, 1 - d / NEAR_KM)
            why.append(f"About {d:.1f} km from you")
        else:
            why.append("Distance unknown: proximity not used")
        days = max(0.0, (now - _parse(r["created_at"])).total_seconds() / 86400)
        parts["age"] = min(days / AGE_CAP_DAYS, 1.0)
        why.append(f"Waiting {days:.0f} day(s)")
        total_w = sum(w[k] for k in parts)
        score = sum(w[k] * v for k, v in parts.items()) / total_w
        ranked.append({**r, "score": round(score * 100), "reasons": why})
    return sorted(ranked, key=lambda x: x["score"], reverse=True)
