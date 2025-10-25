# providers/espn_scores.py
# Fetch NCAA game scores from ESPN's public scoreboard JSON.
# If ESPN structure changes, this returns [] rather than crashing.

from __future__ import annotations
from datetime import datetime, timezone
import httpx
from typing import List, Dict, Any

def fetch_scores_for_iso_date(date_iso: str) -> List[Dict[str, Any]]:
    """
    Returns a list of dicts like:
      {
        "home": "UConn", "away": "Kentucky",
        "home_score": 81, "away_score": 80,
        "status": "Final" | "In Progress" | "Scheduled"
      }
    """
    # ESPN scoreboard endpoint varies; one example (subject to change):
    # https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates=20250321
    ymd = date_iso.replace("-", "")
    url = (
        "https://site.api.espn.com/apis/site/v2/sports/"
        "basketball/mens-college-basketball/scoreboard"
    )
    params = {"dates": ymd}

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    for ev in data.get("events", []):
        try:
            comp = ev["competitions"][0]
            teams = comp["competitors"]
            home = next(t for t in teams if t["homeAway"] == "home")
            away = next(t for t in teams if t["homeAway"] == "away")
            status = comp["status"]["type"]["name"]  # e.g., "STATUS_FINAL", "STATUS_IN_PROGRESS"
            # Normalize status
            if "FINAL" in status.upper():
                st = "Final"
            elif "IN_PROGRESS" in status.upper():
                st = "In Progress"
            else:
                st = "Scheduled"

            out.append({
                "home": home["team"]["shortDisplayName"] or home["team"]["displayName"],
                "away": away["team"]["shortDisplayName"] or away["team"]["displayName"],
                "home_score": int(home.get("score") or 0),
                "away_score": int(away.get("score") or 0),
                "status": st,
            })
        except Exception:
            continue

    return out
