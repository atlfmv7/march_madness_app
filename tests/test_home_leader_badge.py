# tests/test_home_leader_badge.py
# -------------------------------
# Ensures the homepage shows the "Leader vs Spread" badge for a live game.
# -------------------------------
import pytest
from app import create_app
from models import db, Participant, Team, Game


@pytest.fixture
def client_with_live_game(tmp_path):
    app = create_app()
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path/'ui.db'}",
        TESTING=True,
    )
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Seed a minimal in-progress game where favorite is covering
        p1 = Participant(name="Owner A")
        p2 = Participant(name="Owner B")
        db.session.add_all([p1, p2])
        db.session.commit()

        t1 = Team(name="Fav U", seed=1, region="East",
                  initial_owner_id=p1.id, current_owner_id=p1.id)
        t2 = Team(name="Dog State", seed=16, region="East",
                  initial_owner_id=p2.id, current_owner_id=p2.id)
        db.session.add_all([t1, t2])
        db.session.commit()

        g = Game(
            round="64", region="East",
            team1_id=t1.id, team2_id=t2.id,
            team1_owner_id=p1.id, team2_owner_id=p2.id,
            spread=5.0, spread_favorite_team_id=t1.id,
            team1_score=66, team2_score=60,  # margin 6 > spread 5 => favorite covering
            status="In Progress"
        )
        db.session.add(g)
        db.session.commit()

        with app.test_client() as c:
            yield c


def test_homepage_shows_live_leader_badge(client_with_live_game):
    resp = client_with_live_game.get("/")
    assert resp.status_code == 200
    # The favorite owner's name should appear in the response
    assert b"Owner A" in resp.data
    # And the "Leader vs Spread" column should exist
    assert b"Leader vs Spread" in resp.data
