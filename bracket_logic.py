# bracket_logic.py
# -------------------------------
# Core "against the spread" logic for March Madness Madness.
# This module deliberately contains NO Flask routes. It focuses purely on
# deterministic functions that are easy to unit test.
# -------------------------------

from typing import Optional, Tuple
from models import db, Game, Team, Participant


class SpreadEvaluationError(Exception):
    """Raised when a Game lacks the data needed to evaluate a spread result."""


def _validate_game_has_scores(game: Game) -> None:
    """Ensure the game has integer scores for both teams."""
    if game.team1_score is None or game.team2_score is None:
        raise SpreadEvaluationError(
            "Game scores are missing; cannot evaluate spread.")


def _favorite_and_underdog(game: Game) -> Tuple[Team, Team]:
    """
    Return (favorite_team, underdog_team) based on the stored favorite id.
    Requires: game.spread (float) and game.spread_favorite_team set.
    """
    if not game.spread or not game.spread_favorite_team:
        raise SpreadEvaluationError("Spread or favorite team missing on Game.")
    fav = game.spread_favorite_team

    if game.team1_id == fav.id:
        underdog = game.team2
    elif game.team2_id == fav.id:
        underdog = game.team1
    else:
        # Safety check in case of data inconsistency
        raise SpreadEvaluationError(
            "Favorite team is not one of the game's teams.")
    return fav, underdog


def determine_owner_winner_vs_spread(game: Game) -> Participant:
    """
    Determine which *participant/owner* wins this matchup *against the spread*
    for a FINAL game.

    Rules (from the project plan):
      - If the favorite covers (margin > spread), the favorite's owner wins.
      - If the favorite does NOT cover (margin <= spread), the underdog's owner wins.
        (This includes a 'push' where margin == spread — we treat that as the favorite
         not covering for our purposes.)
      - If the underdog wins the game outright, that's naturally 'not covering' for the
        favorite, so the underdog's owner wins.

    Returns:
      The Participant (owner) who wins the *matchup* (i.e., who advances ownership),
      which may differ from the actual game winner team.
    """
    if game.status != "Final":
        raise SpreadEvaluationError(
            "Game must be Final to determine the owner winner.")

    _validate_game_has_scores(game)
    fav_team, dog_team = _favorite_and_underdog(game)

    # Compute the favorite's margin of victory (positive means favorite is ahead)
    if fav_team.id == game.team1_id:
        margin = (game.team1_score or 0) - (game.team2_score or 0)
        fav_owner = game.team1_owner
        dog_owner = game.team2_owner
    else:
        margin = (game.team2_score or 0) - (game.team1_score or 0)
        fav_owner = game.team2_owner
        dog_owner = game.team1_owner

    # If margin > spread -> favorite covered -> favorite OWNER wins.
    # Else (margin <= spread) -> underdog OWNER wins (push counts here).
    if margin > (game.spread or 0):
        return fav_owner
    else:
        return dog_owner


def actual_game_winner_team(game: Game) -> Team:
    """Return the actual *team* that won the game by points (ties not expected)."""
    _validate_game_has_scores(game)
    if game.team1_score > game.team2_score:
        return game.team1
    elif game.team2_score > game.team1_score:
        return game.team2
    else:
        # NCAA games end with a winner; this protects against bad data.
        raise SpreadEvaluationError(
            "A tie score was encountered, which is unexpected for NCAA games.")


def evaluate_and_finalize_game(game_id: int) -> Tuple[Team, Participant]:
    """
    Evaluate a FINAL game's result and update its 'winner_id' field.
    Returns:
      (actual_winner_team, owner_winner_participant)

    NOTE:
      This function persists the updated 'winner_id' to the DB but does NOT
      propagate to any 'next round' game (that linkage will be added later).
    """
    game: Game = db.session.get(Game, game_id)
    if not game:
        raise SpreadEvaluationError(f"Game id {game_id} not found.")
    if game.status != "Final":
        raise SpreadEvaluationError(
            "Game must be marked Final before evaluation.")

    # Compute actual team winner & owner winner
    team_winner = actual_game_winner_team(game)
    owner_winner = determine_owner_winner_vs_spread(game)

    # Persist the actual *team* winner on the Game row
    game.winner_id = team_winner.id
    db.session.commit()

    return team_winner, owner_winner


def live_owner_leader_vs_spread(game: Game) -> Optional[Participant]:
    """
    For an IN-PROGRESS game, indicate which owner is currently 'winning vs the spread'
    based on the live score and the pre-game line.
      - If scores aren't available yet, return None.
      - If status isn't 'In Progress', return None.
    """
    if game.status != "In Progress":
        return None
    if game.team1_score is None or game.team2_score is None:
        return None
    if not game.spread or not game.spread_favorite_team:
        return None

    fav_team, _ = _favorite_and_underdog(game)

    if fav_team.id == game.team1_id:
        margin = (game.team1_score or 0) - (game.team2_score or 0)
        fav_owner = game.team1_owner
        dog_owner = game.team2_owner
    else:
        margin = (game.team2_score or 0) - (game.team1_score or 0)
        fav_owner = game.team2_owner
        dog_owner = game.team1_owner

    # If favorite is covering right now (margin > spread) -> favorite owner is leading,
    # else -> underdog owner is leading (push counts as underdog leading).
    if margin > (game.spread or 0):
        return fav_owner
    else:
        return dog_owner
