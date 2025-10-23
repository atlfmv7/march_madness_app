# tests/test_bracket_logic.py
# -------------------------------
# Unit tests for the 'against the spread' logic.
# These tests use a temporary SQLite database and create small fixtures.
# -------------------------------

import pytest
from app import create_app
from models import db, Team, Participant, Game
from bracket_logic import (
    determine_owner_winner_vs_spread,
    actual_game_winner_team,
    evaluate_and_finalize_game,
    live_owner_leader_vs_spread,
    SpreadEvaluationError,
)


@pytest.fixture
def app_ctx(tmp_path):
    """Create an app with an isolated SQLite DB for each test run."""
    app = create_app()
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path/'test.db'}",
        TESTING=True,
    )
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app


def _seed_basic_matchup():
    # Participants
    p1 = Participant(name="Owner 1")
    p2 = Participant(name="Owner 2")
    db.session.add_all([p1, p2])
    db.session.commit()
    # Teams
    t1 = Team(name="FavoriteU", seed=1, region="East")
    t2 = Team(name="Dog State", seed=16, region="East")
    db.session.add_all([t1, t2])
    db.session.commit()
    return p1, p2, t1, t2


def test_favorite_covers_owner_wins(app_ctx):
    p1, p2, t1, t2 = _seed_basic_matchup()
    # FavoriteU is -4.5 and actually wins by 6 (covers) -> favorite owner wins
    g = Game(
        round="64",
        region="East",
        team1_id=t1.id, team2_id=t2.id,
        team1_owner_id=p1.id, team2_owner_id=p2.id,
        spread=4.5, spread_favorite_team_id=t1.id,
        team1_score=80, team2_score=74, status="Final"
    )
    db.session.add(g)
    db.session.commit()

    owner_winner = determine_owner_winner_vs_spread(g)
    assert owner_winner.id == p1.id

    team_winner = actual_game_winner_team(g)
    assert team_winner.id == t1.id


def test_favorite_wins_but_fails_to_cover_dog_owner_wins(app_ctx):
    p1, p2, t1, t2 = _seed_basic_matchup()
    # Favorite -4.5 wins by 2 (doesn't cover) -> underdog owner wins ownership
    g = Game(
        round="64",
        region="East",
        team1_id=t1.id, team2_id=t2.id,
        team1_owner_id=p1.id, team2_owner_id=p2.id,
        spread=4.5, spread_favorite_team_id=t1.id,
        team1_score=78, team2_score=76, status="Final"
    )
    db.session.add(g)
    db.session.commit()

    owner_winner = determine_owner_winner_vs_spread(g)
    assert owner_winner.id == p2.id

    team_winner = actual_game_winner_team(g)
    assert team_winner.id == t1.id


def test_underdog_wins_outright_dog_owner_wins(app_ctx):
    p1, p2, t1, t2 = _seed_basic_matchup()
    # Favorite -4.5 loses outright -> underdog owner wins
    g = Game(
        round="64",
        region="East",
        team1_id=t1.id, team2_id=t2.id,
        team1_owner_id=p1.id, team2_owner_id=p2.id,
        spread=4.5, spread_favorite_team_id=t1.id,
        team1_score=70, team2_score=75, status="Final"
    )
    db.session.add(g)
    db.session.commit()

    owner_winner = determine_owner_winner_vs_spread(g)
    assert owner_winner.id == p2.id

    team_winner = actual_game_winner_team(g)
    assert team_winner.id == t2.id


def test_push_treated_as_dog_owner_wins(app_ctx):
    p1, p2, t1, t2 = _seed_basic_matchup()
    # Favorite -4 exactly wins by 4 => push => treat as 'not covering' => underdog owner wins
    g = Game(
        round="64",
        region="East",
        team1_id=t1.id, team2_id=t2.id,
        team1_owner_id=p1.id, team2_owner_id=p2.id,
        spread=4.0, spread_favorite_team_id=t1.id,
        team1_score=84, team2_score=80, status="Final"
    )
    db.session.add(g)
    db.session.commit()

    owner_winner = determine_owner_winner_vs_spread(g)
    assert owner_winner.id == p2.id


def test_live_owner_leader_vs_spread(app_ctx):
    p1, p2, t1, t2 = _seed_basic_matchup()
    # In-progress game, favorite -5 up by 6 => favorite currently covering => favorite owner leads
    g = Game(
        round="64",
        region="East",
        team1_id=t1.id, team2_id=t2.id,
        team1_owner_id=p1.id, team2_owner_id=p2.id,
        spread=5.0, spread_favorite_team_id=t1.id,
        team1_score=66, team2_score=60, status="In Progress"
    )
    db.session.add(g)
    db.session.commit()

    leader = live_owner_leader_vs_spread(g)
    assert leader.id == p1.id


def test_evaluate_and_finalize_updates_winner_id(app_ctx):
    p1, p2, t1, t2 = _seed_basic_matchup()
    g = Game(
        round="64",
        region="East",
        team1_id=t1.id, team2_id=t2.id,
        team1_owner_id=p1.id, team2_owner_id=p2.id,
        spread=2.5, spread_favorite_team_id=t1.id,
        team1_score=81, team2_score=80, status="Final"
    )
    db.session.add(g)
    db.session.commit()

    team_winner, owner_winner = evaluate_and_finalize_game(g.id)
    # Actual winner by score is team1 (FavoriteU)
    assert team_winner.id == t1.id
    # Margin 1 vs spread 2.5 -> favorite didn't cover -> dog owner wins
    assert owner_winner.id == p2.id


def test_errors_for_missing_data(app_ctx):
    p1, p2, t1, t2 = _seed_basic_matchup()
    # Missing scores
    g = Game(
        round="64",
        region="East",
        team1_id=t1.id, team2_id=t2.id,
        team1_owner_id=p1.id, team2_owner_id=p2.id,
        spread=3.5, spread_favorite_team_id=t1.id,
        status="Final"
    )
    db.session.add(g)
    db.session.commit()

    with pytest.raises(SpreadEvaluationError):
        determine_owner_winner_vs_spread(g)
