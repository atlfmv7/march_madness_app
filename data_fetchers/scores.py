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


def update_game_scores(date_iso: Optional[str] = None, data: Optional[List[ScoreEntry]] = None) -> int:
    """
    Update Game rows with scores/status.
    - If 'data' provided, use it.
    - Else if date_iso provided, fetch for that date.
    When a game transitions to Final, evaluate spread logic and persist winner_id.
    Returns number of games that were updated.
    """
    updated = 0

    if data is None:
        if not date_iso:
            # Safe default: nothing to do
            return 0
        data = fetch_scores_for_date_iso(date_iso)

    with current_app.app_context():
        for entry in data:
            team1 = entry["team1"]
            team2 = entry["team2"]
            game = _match_game_for_pair(team1, team2)
            if not game:
                continue

            # Apply scores/status when provided
            if entry.get("score1") is not None:
                game.team1_score = int(entry["score1"])
            if entry.get("score2") is not None:
                game.team2_score = int(entry["score2"])
            if entry.get("status"):
                game.status = entry["status"]

            updated += 1

            # If Final, run evaluation (sets winner_id)
            if game.status == "Final":
                try:
                    evaluate_and_finalize_game(game.id)
                except Exception:
                    # Keep going; don't break bulk updates on one bad game
                    pass

        db.session.commit()

    return updated
