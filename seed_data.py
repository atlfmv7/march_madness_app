# seed_data.py
# -------------------------------
# One-time (or repeatable) script to populate the database with:
# - 8 sample teams across two regions (East/West)
# - 8 sample participants (P1..P8)
# - 4 Round-of-64 games with owners assigned and simple spreads
#
# You can safely run this multiple times; it clears existing data first.
# -------------------------------

from app import create_app
from models import db, Team, Game, Participant
from datetime import datetime, timedelta

def reset_and_seed():
    app = create_app()
    with app.app_context():
        # 1) Clear existing data to keep this script idempotent for now
        db.session.query(Game).delete()
        db.session.query(Team).delete()
        db.session.query(Participant).delete()
        db.session.commit()

        # 2) Create participants (P1..P8)
        participants = []
        for i in range(1, 9):
            p = Participant(name=f"Participant {i}", email=None)
            participants.append(p)
        db.session.add_all(participants)
        db.session.commit()

        # 3) Create teams (8 teams, 4 East and 4 West for a compact demo)
        # In the real tournament there are 64 teams, but this is perfect for verifying the UI.
        teams_data = [
            # East region (names are just examples)
            {"name": "Duke", "seed": 2, "region": "East"},
            {"name": "UConn", "seed": 1, "region": "East"},
            {"name": "UNC", "seed": 3, "region": "East"},
            {"name": "Kentucky", "seed": 4, "region": "East"},
            # West region
            {"name": "Gonzaga", "seed": 2, "region": "West"},
            {"name": "Arizona", "seed": 1, "region": "West"},
            {"name": "Kansas", "seed": 3, "region": "West"},
            {"name": "Baylor", "seed": 4, "region": "West"},
        ]
        teams = []
        for idx, td in enumerate(teams_data):
            # Assign initial/current owner in a round-robin fashion so the page can show owners
            owner = participants[idx % len(participants)]
            t = Team(
                name=td["name"],
                seed=td["seed"],
                region=td["region"],
                initial_owner_id=owner.id,
                current_owner_id=owner.id
            )
            teams.append(t)
        db.session.add_all(teams)
        db.session.commit()

        # Map names -> Team for convenience
        team_by_name = {t.name: t for t in teams}

        # 4) Create a few Round-of-64 games (2 per region)
        # NOTE: We’ll keep spreads small and attach a favorite so the template can render "X -N"
        #       Times are fake now; later we’ll wire these to real schedule data.
        now = datetime.utcnow()
        games_to_create = [
            # East region games
            {
                "round": "64",
                "region": "East",
                "team1": "UConn",    # favored
                "team2": "Kentucky",
                "team1_owner": team_by_name["UConn"].current_owner,
                "team2_owner": team_by_name["Kentucky"].current_owner,
                "spread": 6.5,
                "favorite": "UConn",
                "game_time": now + timedelta(days=1)
            },
            {
                "round": "64",
                "region": "East",
                "team1": "Duke",     # favored
                "team2": "UNC",
                "team1_owner": team_by_name["Duke"].current_owner,
                "team2_owner": team_by_name["UNC"].current_owner,
                "spread": 4.5,
                "favorite": "Duke",
                "game_time": now + timedelta(days=1, hours=2)
            },
            # West region games
            {
                "round": "64",
                "region": "West",
                "team1": "Arizona",  # favored
                "team2": "Baylor",
                "team1_owner": team_by_name["Arizona"].current_owner,
                "team2_owner": team_by_name["Baylor"].current_owner,
                "spread": 5.0,
                "favorite": "Arizona",
                "game_time": now + timedelta(days=1, hours=4)
            },
            {
                "round": "64",
                "region": "West",
                "team1": "Gonzaga",  # favored
                "team2": "Kansas",
                "team1_owner": team_by_name["Gonzaga"].current_owner,
                "team2_owner": team_by_name["Kansas"].current_owner,
                "spread": 2.5,
                "favorite": "Gonzaga",
                "game_time": now + timedelta(days=1, hours=6)
            },
        ]

        for g in games_to_create:
            t1 = team_by_name[g["team1"]]
            t2 = team_by_name[g["team2"]]
            fav = team_by_name[g["favorite"]]
            game = Game(
                round=g["round"],
                region=g["region"],
                team1_id=t1.id,
                team2_id=t2.id,
                team1_owner_id=g["team1_owner"].id if g["team1_owner"] else None,
                team2_owner_id=g["team2_owner"].id if g["team2_owner"] else None,
                spread=g["spread"],
                spread_favorite_team_id=fav.id,
                status="Scheduled",
                game_time=g["game_time"],
            )
            db.session.add(game)

        db.session.commit()
        print("✅ Seed complete: inserted Participants, Teams, and Games.")

if __name__ == "__main__":
    reset_and_seed()
