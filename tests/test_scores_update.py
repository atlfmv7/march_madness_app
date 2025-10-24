# tests/test_scores_update.py
# --------------------------------------------
# Verifies that update_game_scores():
#  - writes scores/status
#  - evaluates Final games (sets winner_id)
# --------------------------------------------

from app import create_app
from models import db, Team, Participant, Game
from data_fetchers.scores import update_game_scores


def test_update_game_scores_and_finalize(tmp_path):
    app = create_app()
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path/'scores.db'}",
        TESTING=True,
    )
    with app.app_context():
        db.drop_all()
        db.create_all()

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
            spread=6.5, spread_favorite_team_id=t1.id,
            status="In Progress"
        )
        db.session.add(g)
        db.session.commit()

        # Mock a FINAL result where UConn wins by 1 (fails to cover)
        mock_scores = [{
            "team1": "UConn",
            "team2": "Kentucky",
            "score1": 81,
            "score2": 80,
            "status": "Final"
        }]

        count = update_game_scores(date_iso="2025-03-21", data=mock_scores)
        assert count == 1

        g_refreshed = db.session.get(Game, g.id)
        assert g_refreshed.status == "Final"
        assert g_refreshed.team1_score == 81
        assert g_refreshed.team2_score == 80
        # winner_id should be the actual game winner (UConn)
        assert g_refreshed.winner_id == t1.id
