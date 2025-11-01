# tests/test_seed_counts.py
# -------------------------------
# This test seeds the default (instance/mmm.db) database before asserting
# record counts. It does NOT rely on out-of-band manual runs.
# NOTE: Running this test will clear and reseed the default DB via reset_and_seed().
# -------------------------------

from app import create_app
from models import db, Participant, Team, Game

# Import the one-time seeding routine
from seed_data import reset_and_seed


def test_seed_counts():
    """
    Ensures that after seeding:
      - there are at least 8 participants,
      - at least 8 teams,
      - at least 4 games.
    This keeps the test aligned with the Step 4 seed data.
    """
    app = create_app()
    with app.app_context():
        # Seed (idempotent for this test; it clears then inserts known rows)
        reset_and_seed()

        # Basic sanity checks against the seeded data
        assert db.session.query(Participant).count() >= 8
        assert db.session.query(Team).count() >= 8
        assert db.session.query(Game).count() >= 4
