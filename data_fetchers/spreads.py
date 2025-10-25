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
from datetime import date, datetime, timezone
from flask import current_app
from models import db, Game, Team
from util.name_map import to_canonical, normalize_key
from providers.odds_api import fetch_spreads_for_date
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


def _normalize_spreads_payload(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Accepts either test-style payload:
      {"team1": "...", "team2": "...", "favorite": "...", "spread": 6.5, "tip_time": "..."}
    or provider-style payload:
      {"home": "...", "away": "...", "favorite": "...", "spread": 6.5, "tip_iso": "..."}
    Returns unified dicts with keys: home, away, favorite, spread, tip_iso
    """
    out: List[Dict[str, Any]] = []
    for it in items or []:
        if "home" in it or "away" in it:
            home = it.get("home")
            away = it.get("away")
            tip_iso = it.get("tip_iso")
        else:
            # test-style keys
            home = it.get("team1")
            away = it.get("team2")
            tip_iso = it.get("tip_time")
        fav = it.get("favorite")
        spr = it.get("spread")
        if home and away and fav is not None and spr is not None:
            out.append({
                "home": str(home),
                "away": str(away),
                "favorite": str(fav),
                "spread": float(spr),
                "tip_iso": tip_iso,
            })
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


def update_game_spreads(target_date: date, data: Optional[List[Dict[str, Any]]] = None) -> int:
    """
    Fetch spreads from live provider (if enabled) OR use injected `data` (for tests),
    then update matching games for the given date/year. Returns # updated.
    Safe-by-default: if disabled, no key, or empty data, returns 0.
    """
    cfg = current_app.config

    if data is not None:
        payload = _normalize_spreads_payload(data)
    else:
        if not cfg.get("ENABLE_LIVE_SPREADS", True):
            return 0
        api_key = cfg.get("ODDS_API_KEY", "")
        # tolerate provider signature variants robustly
        try:
            payload = fetch_spreads_for_date(target_date, api_key=api_key)
        except TypeError:
            # fallback if a local version lacks the named parameter
            payload = fetch_spreads_for_date(
                target_date)  # type: ignore[call-arg]

    if not payload:
        return 0

    year = target_date.year
    teams = db.session.query(Team).filter(Team.year == year).all()
    by_name = {normalize_key(t.name): t for t in teams}

    updated = 0
    for item in payload:
        home_name = to_canonical(item["home"])
        away_name = to_canonical(item["away"])
        fav_name = to_canonical(item["favorite"])
        spread = float(item["spread"])

        home = by_name.get(normalize_key(home_name))
        away = by_name.get(normalize_key(away_name))
        favorite = by_name.get(normalize_key(fav_name))
        if not home or not away or not favorite:
            continue

        game = (
            db.session.query(Game)
            .filter(
                Game.year == year,
                Game.team1_id.in_([home.id, away.id]),
                Game.team2_id.in_([home.id, away.id]),
            )
            .order_by(Game.id.asc())
            .first()
        )
        if not game:
            continue

        game.spread = spread
        game.spread_favorite_team_id = favorite.id

        tip_iso = item.get("tip_iso")
        if tip_iso:
            try:
                # Accept both "...Z" and "+00:00" forms
                iso = tip_iso.replace("Z", "+00:00")
                dt = datetime.fromisoformat(iso)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                game.game_time = dt
            except Exception:
                # Don't fail the whole update if time parsing hiccups
                pass

        updated += 1

    db.session.commit()
    return updated
