# providers/odds_api.py
from __future__ import annotations
from datetime import date
import httpx
from typing import List, Dict, Any, Optional


def fetch_spreads_for_date(target_date: date, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns a list of dicts with at least:
      {
        "home": "UConn", "away": "Kentucky",
        "favorite": "UConn", "spread": 6.5, "tip_iso": "2025-03-21T17:10:00Z"
      }
    If api_key is empty/None, or any error occurs, returns [].
    """
    if not api_key:
        return []

    url = "https://api.the-odds-api.com/v4/sports/basketball_ncaab/odds"
    params = {
        "regions": "us",
        "markets": "spreads",
        "dateFormat": "iso",
        "oddsFormat": "american",
        "apiKey": api_key,
    }

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            raw = resp.json()
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    for game in raw if isinstance(raw, list) else []:
        home = game.get("home_team") or game.get("home") or ""
        away = game.get("away_team") or game.get("away") or ""
        tip_iso = game.get("commence_time") or game.get("tip_off") or None

        favorite = None
        spread = None
        for book in game.get("bookmakers", []):
            for market in book.get("markets", []):
                if market.get("key") == "spreads":
                    for outcome in market.get("outcomes", []):
                        if isinstance(outcome.get("point"), (int, float)):
                            pt = float(outcome["point"])
                            tm = outcome.get("name") or ""
                            if pt < 0:
                                favorite = tm
                                spread = abs(pt)
                                break
                    if favorite is not None:
                        break
            if favorite is not None:
                break

        if home and away and favorite is not None and spread is not None:
            out.append({
                "home": home,
                "away": away,
                "favorite": favorite,
                "spread": float(spread),
                "tip_iso": tip_iso,
            })

    return out
