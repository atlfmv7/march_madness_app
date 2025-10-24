# data_fetchers/spreads.py
# --------------------------------------------
# Fetches and normalizes point spreads for NCAA games.
# Design goals:
#  - Provider-agnostic: use config to pick an implementation.
#  - Testable offline: update function accepts an optional 'data' override.
#  - Minimal fields: favorite team and numeric spread (favorite minus points).
# --------------------------------------------

from typing import Dict, Any, List, Optional, Tuple
import datetime as dt
import requests

from flask import current_app
from models import db, Game, Team

# ---------- Types ----------
# Normalized spread entry structure returned by fetch_spreads_for_date():
# {
#   "team1": "UConn",
#   "team2": "Kentucky",
#   "favorite": "UConn",
#   "spread": 6.5,
#   "region": "East",       # optional/if available
#   "tip_time": "2025-03-21T16:00:00Z"  # ISO8601 string (optional)
# }
SpreadEntry = Dict[str, Any]


def _normalize_from_the_odds_api(raw: List[Dict[str, Any]]) -> List[SpreadEntry]:
    """
    Convert The Odds API-like payload into our normalized structure.
    NOTE: This function is based on typical shapes; adjust when wiring a real key.
    """
    out: List[SpreadEntry] = []
    for game in raw:
        teams = game.get("teams") or []            # e.g., ["UConn","Kentucky"]
        if len(teams) != 2:
            continue
        home = game.get("home_team")               # may be one of teams[]
        # Markets might contain spreads; pick the first available book for simplicity
        bookmakers = game.get("bookmakers") or []
        spread_points: Optional[float] = None
        favorite: Optional[str] = None

        for book in bookmakers:
            markets = book.get("markets") or []
            for m in markets:
                if m.get("key") == "spreads":
                    outcomes = m.get("outcomes") or []
                    # Outcomes often look like [{"name":"UConn","point":-6.5}, {"name":"Kentucky","point":+6.5}]
                    # We want favorite (negative) and absolute spread value as positive float
                    fav_cand = None
                    fav_pts = None
                    for o in outcomes:
                        name = o.get("name")
                        point = o.get("point")
                        if name is None or point is None:
                            continue
                        # negative point implies favorite at that book
                        if isinstance(point, (int, float)) and point < 0:
                            fav_cand = name
                            fav_pts = abs(float(point))
                    if fav_cand is not None and fav_pts is not None:
                        favorite = fav_cand
                        spread_points = fav_pts
                        break
            if spread_points is not None:
                break

        if spread_points is None or favorite is None:
            # No usable spread; skip this game
            continue

        entry: SpreadEntry = {
            "team1": teams[0],
            "team2": teams[1],
            "favorite": favorite,
            "spread": float(spread_points),
            # Optional fields if present:
            "region": game.get("region"),  # many APIs won’t have this
            "tip_time": game.get("commence_time"),  # often ISO8601
        }
        out.append(entry)
    return out


def fetch_spreads_for_date(date: dt.date) -> List[SpreadEntry]:
    """
    Provider-agnostic fetcher for spreads for a given date.
    Returns normalized SpreadEntry list.

    For testability and simplicity, this makes one HTTP call if a known provider
    is configured; otherwise returns an empty list.
    """
    cfg = current_app.config
    provider = cfg.get("ODDS_API_PROVIDER", "the_odds_api")
    api_key = cfg.get("ODDS_API_KEY", "")

    if provider == "the_odds_api" and api_key:
        # Example The Odds API endpoint shape (subject to change):
        # https://api.the-odds-api.com/v4/sports/basketball_ncaab/odds?regions=us&markets=spreads&dateFormat=iso&apiKey=KEY
        url = "https://api.the-odds-api.com/v4/sports/basketball_ncaab/odds"
        params = {
            "regions": "us",
            "markets": "spreads",
            "dateFormat": "iso",
            "apiKey": api_key,
            # Many providers return upcoming odds; if a 'date' param exists, include it:
            # "date": date.isoformat(),   # Uncomment if supported by provider
        }
        resp = requests.get(url, params=params, timeout=12)
        resp.raise_for_status()
        raw = resp.json()
        return _normalize_from_the_odds_api(raw)

    # Unknown provider or no API key: return empty list (safe default).
    return []


def _match_team_by_name(session, name: str) -> Optional[Team]:
    """
    Naive name match. In real life we may need a mapping (e.g., "UConn" vs "Connecticut").
    For MVP we assume names align with fetched data or adjust manually in seed.
    """
    return session.query(Team).filter(Team.name == name).first()


def update_game_spreads(date: dt.date, data: Optional[List[SpreadEntry]] = None) -> int:
    """
    Update Game rows with spread and favorite team based on the given date.
    - If 'data' is provided, uses it instead of fetching (great for tests).
    - Returns the number of games updated.
    Matching approach:
      - Find the Game whose two team names match the entry’s teams (order-insensitive).
      - Set Game.spread and Game.spread_favorite_team_id accordingly.
      - Optionally set Game.game_time if tip_time is given.
    """
    updated = 0
    if data is None:
        data = fetch_spreads_for_date(date)

    with current_app.app_context():
        for entry in data:
            t1 = _match_team_by_name(db.session, entry["team1"])
            t2 = _match_team_by_name(db.session, entry["team2"])
            if not t1 or not t2:
                continue

            # Find a game for these two teams (order-insensitive)
            game = (
                db.session.query(Game)
                .filter(
                    ((Game.team1_id == t1.id) & (Game.team2_id == t2.id))
                    | ((Game.team1_id == t2.id) & (Game.team2_id == t1.id))
                )
                .first()
            )
            if not game:
                continue

            # Set spread and favorite
            game.spread = float(entry["spread"])
            favorite_name = entry["favorite"]
            fav_team = t1 if t1.name == favorite_name else (t2 if t2.name == favorite_name else None)
            if fav_team:
                game.spread_favorite_team_id = fav_team.id

            # Optional: set tip time if provided in ISO8601
            tip = entry.get("tip_time")
            if tip:
                try:
                    # Basic parse; we don’t hard-require tz-awareness at this stage
                    from datetime import datetime
                    game.game_time = datetime.fromisoformat(tip.replace("Z", "+00:00"))
                except Exception:
                    pass

            updated += 1

        db.session.commit()

    return updated
