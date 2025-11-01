# tests/test_propagation.py
# --------------------------------------------
# Ensures that when a Round of 64 game goes Final, the actual team winner
# is placed into the Round of 32 game's correct slot, and the advancing
# team's owner becomes the 'owner vs spread' for that game.
# --------------------------------------------

from app import create_app
from models import db, Team, Participant, Game
from bracket_logic import evaluate_and_finalize_game

def _mk_matchup(p1_name, p2_name, t1_name, t2_name, region, spread, fav_is_team1=True):
    p1 = Participant(name=p1_name)
    p2 = Participant(name=p2_name)
    db.session.add_all([p1, p2]); db.session.commit()

    t1 = Team(name=t1_name, seed=1, region=region, initial_owner_id=p1.id, current_owner_id=p1.id)
    t2 = Team(name=t2_name, seed=2, region=region, initial_owner_id=p2.id, current_owner_id=p2.id)
    db.session.add_all([t1, t2]); db.session.commit()

    g = Game(
        round="64", region=region,
        team1_id=t1.id, team2_id=t2.id,
        team1_owner_id=p1.id, team2_owner_id=p2.id,
        spread=spread,
        spread_favorite_team_id=t1.id if fav_is_team1 else t2.id,
        status="Scheduled"
    )
    db.session.add(g); db.session.commit()
    return p1, p2, t1, t2, g

def test_propagation_into_next_game_slot(tmp_path):
    app = create_app()
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path/'prop.db'}",
        TESTING=True,
    )
    with app.app_context():
        db.drop_all(); db.create_all()

        # Create the target R32 game (empty slots)
        r32 = Game(round="32", region="East", status="Scheduled")
        db.session.add(r32); db.session.commit()

        # Seed one R64 game that feeds slot 2 of r32
        p1, p2, t1, t2, r64 = _mk_matchup("Owner A", "Owner B", "FavU", "DogState", "East", spread=4.5, fav_is_team1=True)
        r64.next_game_id = r32.id
        r64.next_game_slot = 2
        db.session.commit()

        # Make the game Final:
        # - Team1 wins by 1 (actual winner: team1)
        # - Spread is 4.5, so favorite did NOT cover -> owner winner is underdog owner (Owner B)
        r64.team1_score = 71
        r64.team2_score = 70
        r64.status = "Final"
        db.session.commit()

        # Evaluate (should also propagate)
        team_winner, owner_winner = evaluate_and_finalize_game(r64.id)

        # Check team winner & owner winner identities
        assert team_winner.id == t1.id         # team1 actually won
        assert owner_winner.id == p2.id        # underdog owner wins against the spread

        # Propagation checks:
        r32_ref = db.session.get(Game, r32.id)
        assert r32_ref.team2_id == t1.id       # winner placed into slot 2 as configured
        assert r32_ref.team2_owner_id == p2.id # owner vs spread became advancing team's owner

        # Team’s current owner should update to the owner_winner
        t1_ref = db.session.get(Team, t1.id)
        assert t1_ref.current_owner_id == p2.id
