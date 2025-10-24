# tests/test_year_filtering.py
# --------------------------------------------
# Ensures the homepage filters games by the selected year.
# --------------------------------------------
from app import create_app
from models import db, Team, Participant, Game

def _mk(app, y, region="East"):
    p = Participant(name=f"Owner{y}")
    db.session.add(p); db.session.commit()
    t1 = Team(name=f"TeamA{y}", seed=1, region=region, year=y, initial_owner_id=p.id, current_owner_id=p.id)
    t2 = Team(name=f"TeamB{y}", seed=2, region=region, year=y, initial_owner_id=p.id, current_owner_id=p.id)
    db.session.add_all([t1, t2]); db.session.commit()
    g = Game(round="64", region=region, year=y, team1_id=t1.id, team2_id=t2.id,
             team1_owner_id=p.id, team2_owner_id=p.id, status="Scheduled")
    db.session.add(g); db.session.commit()

def test_home_filters_by_year(tmp_path):
    app = create_app()
    app.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path/'year.db'}", TESTING=True)
    with app.app_context():
        db.drop_all(); db.create_all()
        # Seed two different years
        _mk(app, 2024)
        _mk(app, 2025)

        with app.test_client() as c:
            # default should show latest year (2025)
            r = c.get("/")
            assert r.status_code == 200
            assert b"TeamA2025" in r.data
            assert b"TeamA2024" not in r.data

            # explicitly request 2024
            r = c.get("/?year=2024")
            assert b"TeamA2024" in r.data
            assert b"TeamA2025" not in r.data
