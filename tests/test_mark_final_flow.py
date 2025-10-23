# tests/test_mark_final_flow.py
# --------------------------------------------
# Simulates what the CLI command does without invoking Click:
# - Create a small matchup
# - Set scores and status to "Final"
# - Call evaluate_and_finalize_game()
# --------------------------------------------

from app import create_app
from models import db, Team, Participant, Game
from bracket_logic import evaluate_and_finalize_game


def test_mark_final_like_flow(tmp_path):
    app = create_app()
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path/'mark_final.db'}",
        TESTING=True,
    )

    with app.app_context():
        db.drop_all()
        db.create_all()

        # Seed minimal participants and teams
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

        # Favorite is t1 with spread 4.5 (t1 -4.5). We'll give a narrow 1-point win => doesn't cover.
        g = Game(
            round="64", region="East",
            team1_id=t1.id, team2_id=t2.id,
            team1_owner_id=p1.id, team2_owner_id=p2.id,
            spread=4.5, spread_favorite_team_id=t1.id,
            status="Scheduled",
        )
        db.session.add(g)
        db.session.commit()

        # Mimic the CLI: mark Final and write scores
        g.team1_score = 81
        g.team2_score = 80
        g.status = "Final"
        db.session.commit()

        # Evaluate (what CLI does after marking final)
        team_winner, owner_winner = evaluate_and_finalize_game(g.id)

        # Assert: team1 wins the game, but fails to cover => underdog owner wins
        assert team_winner.id == t1.id
        assert owner_winner.id == p2.id
