# data_fetchers/scores.py
# --------------------------------------------
# Fetches and normalizes live scores and statuses for NCAA games.
# Design goals:
#  - Provider-agnostic via config.
#  - Testable offline: update function accepts optional 'data'.
#  - When a game becomes Final, run spread evaluation and persist winner_id.
# --------------------------------------------

from typing import Dict, Any, List, Optional
import requests
from flask import current_app
from models import db, Game, Team
from bracket_logic import evaluate_and_finalize_game
from util.name_map import to_canonical, normalize_key
from providers.espn_scores import fetch_scores_for_iso_date
from datetime import date

# Normalized score entry:
# {
#   "team1": "UConn",
#   "team2": "Kentucky",
#   "score1": 81,
#   "score2": 80,
#   "status": "Final" | "In Progress" | "Scheduled"
# }
ScoreEntry = Dict[str, Any]


def _normalize_from_ncaa_like(raw: Dict[str, Any]) -> List[ScoreEntry]:
    """
    Convert an NCAA-like scoreboard payload into our normalized entries.
    This is a placeholder shape — adjust mapping once a real source is picked.
    """
    out: List[ScoreEntry] = []
    games = raw.get("games") or []
    for g in games:
        home = g.get("home", {})
        away = g.get("away", {})
        status = g.get("status", "Scheduled")
        entry: ScoreEntry = {
            "team1": home.get("name"),
            "team2": away.get("name"),
            "score1": int(home.get("score")) if home.get("score") is not None else None,
            "score2": int(away.get("score")) if away.get("score") is not None else None,
            "status": status,
        }
        if entry["team1"] and entry["team2"]:
            out.append(entry)
    return out


def fetch_scores_for_date_iso(date_iso: str) -> List[ScoreEntry]:
    """
    Fetch scores for a given date string (YYYY-MM-DD).
    Returns normalized ScoreEntry list.
    """
    cfg = current_app.config
    source = cfg.get("SCORES_SOURCE", "ncaa")

    if source == "ncaa":
        # Placeholder demo endpoint — you will replace with a real source later.
        # For dev, we return an empty set (no external call) to avoid failures.
        # To wire a real endpoint, fetch JSON here and pass to _normalize_from_ncaa_like().
        return []

    # Unknown source
    return []


def _match_game_for_pair(team1_name: str, team2_name: str) -> Optional[Game]:
    """Find a game with the given two team names (order-insensitive)."""
    t1 = db.session.query(Team).filter(Team.name == team1_name).first()
    t2 = db.session.query(Team).filter(Team.name == team2_name).first()
    if not t1 or not t2:
        return None
    game = (
        db.session.query(Game)
        .filter(
            ((Game.team1_id == t1.id) & (Game.team2_id == t2.id))
            | ((Game.team1_id == t2.id) & (Game.team2_id == t1.id))
        )
        .first()
    )
    return game


def update_game_scores(*, date_iso: str, data: Optional[List[Dict[str, Any]]] = None) -> int:
    """
    Fetch scores from live provider (if enabled) OR use injected `data` for tests,
    write them to DB, and evaluate Final games. Returns # updated.
    Safe-by-default: if disabled or provider fails, returns 0.
    """
    cfg = current_app.config

    if data is not None:
        payload = _normalize_scores_payload(data)
    else:
        if not cfg.get("ENABLE_LIVE_SCORES", True):
            return 0
        payload = fetch_scores_for_iso_date(date_iso)
        if not payload:
            return 0

    year = int(date_iso[:4])
    teams = db.session.query(Team).filter(Team.year == year).all()
    by_name = {normalize_key(t.name): t for t in teams}

    updated = 0
    for item in payload:
        home_name = to_canonical(item["home"])
        away_name = to_canonical(item["away"])
        home = by_name.get(normalize_key(home_name))
        away = by_name.get(normalize_key(away_name))
        if not home or not away:
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

        # Apply score + status in the correct slot orientation
        # If team1 is the home team, assign home_score to team1_score, otherwise away_score
        if game.team1_id == home.id:
            game.team1_score = item["home_score"]
            game.team2_score = item["away_score"]
        else:  # team1 is away, team2 is home
            game.team1_score = item["away_score"]
            game.team2_score = item["home_score"]
        game.status = item["status"] or game.status
        db.session.commit()

        if game.status == "Final":
            try:
                evaluate_and_finalize_game(game.id)
            except Exception:
                pass

        updated += 1

    return updated


def _normalize_scores_payload(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Accepts either test-style payload:
      {"team1": "...", "team2": "...", "score1": 81, "score2": 80, "status": "Final"}
    or provider-style payload:
      {"home": "...", "away": "...", "home_score": 81, "away_score": 80, "status": "..."}
    Returns unified dicts with keys: home, away, home_score, away_score, status
    """
    out: List[Dict[str, Any]] = []
    for it in items or []:
        if "home" in it or "away" in it:
            home = it.get("home")
            away = it.get("away")
            s_home = it.get("home_score", 0)
            s_away = it.get("away_score", 0)
            status = it.get("status") or "Scheduled"
        else:
            home = it.get("team1")
            away = it.get("team2")
            s_home = it.get("score1", 0)
            s_away = it.get("score2", 0)
            status = it.get("status") or "Scheduled"
        try:
            s_home = int(s_home)
            s_away = int(s_away)
        except Exception:
            continue
        if home and away:
            out.append({
                "home": str(home),
                "away": str(away),
                "home_score": s_home,
                "away_score": s_away,
                "status": str(status),
            })
    return out
