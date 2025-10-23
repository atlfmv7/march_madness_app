# tests/test_seed_counts.py
# -------------------------------
# Verifies that the seed created at least some participants, teams, and games.
# -------------------------------
from app import create_app
from models import db, Participant, Team, Game

def test_seed_counts():
    app = create_app()
    with app.app_context():
        # Basic sanity checks
        assert db.session.query(Participant).count() >= 8
        assert db.session.query(Team).count() >= 8
        assert db.session.query(Game).count() >= 4
