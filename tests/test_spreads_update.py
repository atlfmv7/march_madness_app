# tests/test_spreads_update.py
# --------------------------------------------
# Verifies that update_game_spreads() writes spreads and favorites
# when given normalized data (no internet required).
# --------------------------------------------

import datetime as dt
from app import create_app
from models import db, Team, Participant, Game
from data_fetchers.spreads import update_game_spreads


def test_update_game_spreads_with_mock_data(tmp_path):
    app = create_app()
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path/'spreads.db'}",
        TESTING=True,
    )
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Seed minimal matchup
        p1 = Participant(name="Owner A")
        p2 = Participant(name="Owner B")
        db.session.add_all([p1, p2])
        db.session.commit()

        t1 = Team(name="UConn", seed=1, region="East",
                  initial_owner_id=p1.id, current_owner_id=p1.id)
        t2 = Team(name="Kentucky", seed=4, region="East",
                  initial_owner_id=p2.id, current_owner_id=p2.id)
        db.session.add_all([t1, t2])
        db.session.commit()

        g = Game(
            round="64", region="East",
            team1_id=t1.id, team2_id=t2.id,
            team1_owner_id=p1.id, team2_owner_id=p2.id,
            status="Scheduled"
        )
        db.session.add(g)
        db.session.commit()

        # Mock normalized spread data as if fetched from provider
        mock_data = [{
            "team1": "UConn",
            "team2": "Kentucky",
            "favorite": "UConn",
            "spread": 6.5,
            "tip_time": "2025-03-21T16:00:00Z"
        }]

        count = update_game_spreads(dt.date(2025, 3, 21), data=mock_data)
        assert count == 1

        # Verify that the Game row was updated
        g_refreshed = db.session.get(Game, g.id)
        assert g_refreshed.spread == 6.5
        assert g_refreshed.spread_favorite_team_id == t1.id
        assert g_refreshed.game_time is not None  # parsed from ISO string
