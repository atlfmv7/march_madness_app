# seed_data.py
# -------------------------------
# Purpose:
#   Seed (or reset and seed) the database with a compact demo bracket so you can
#   verify the UI and bracket propagation logic end-to-end.
#
# What this script does:
#   - Clears existing Participants, Teams, and Games (idempotent while iterating).
#   - Creates 8 sample Participants (P1..P8).
#   - Creates 8 sample Teams split across two regions (East/West) and assigns
#     both initial and current owners round-robin so the UI has ownership data.
#   - Creates two Round of 32 (r32) *skeleton* Game records (one per region).
#     These have no teams yet; Round of 64 winners will auto-advance into these.
#   - Creates four Round of 64 (r64) Game records (two per region) with spreads
#     and favorites for simple rendering.
#   - Links the four r64 games to their corresponding r32 game targets via
#     next_game_id and next_game_slot so propagation is well-defined.
#
# NEW (Year tagging):
#   - Adds a single source of truth for the current year (CURRENT_YEAR).
#   - Sets `year=CURRENT_YEAR` on every Team and Game created here.
#
# Notes:
#   - We commit once after creating r32 games to ensure they have primary keys,
#     then create r64 games, set their next links, and commit again.
#   - Times are synthetic for demonstration; replace with real schedule data later.
# -------------------------------
#
# Why this file exists:
#   This file exists to provide a reproducible way to reset and seed your local
#   database with a minimal, but fully-linked tournament structure that exercises
#   ownership, spreads, and automatic advancement logic across rounds.
# -------------------------------

from app import create_app
from models import db, Team, Game, Participant
from datetime import datetime, timedelta, timezone


def reset_and_seed():
    """
    Reset and seed the database with demo data for the bracket app.

    Steps:
      1) Wipe existing Participants, Teams, Games.
      2) Create Participants (P1..P8).
      3) Create Teams (8 total, 4 per region) and set `year`.
      4) Create Round of 32 skeleton Games (one per region) and set `year`.
      5) Create Round of 64 Games (two per region) and set `year`.
      6) Link Round of 64 winners to their Round of 32 targets.
      7) Commit.
    """
    app = create_app()
    with app.app_context():
        # ------------------------------------------------------------
        # Single source of truth for the current tournament year
        # ------------------------------------------------------------
        CURRENT_YEAR = datetime.now(timezone.utc).year  # NEW

        # ------------------------------------------------------------
        # 1) Clear existing data to keep this script idempotent for now
        # ------------------------------------------------------------
        db.session.query(Game).delete()
        db.session.query(Team).delete()
        db.session.query(Participant).delete()
        db.session.commit()

        # ------------------------------------------------------------
        # 2) Create participants (P1..P8)
        # ------------------------------------------------------------
        participants = []
        for i in range(1, 9):
            p = Participant(name=f"Participant {i}", email=None)
            participants.append(p)
        db.session.add_all(participants)
        db.session.commit()

        # ------------------------------------------------------------
        # 3) Create teams (8 teams, 4 East and 4 West for a compact demo)
        #    In the real tournament there are 64 teams, but this is perfect
        #    for verifying the UI and propagation logic.
        #    NEW: year=CURRENT_YEAR
        # ------------------------------------------------------------
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
                year=CURRENT_YEAR,                 # NEW
                initial_owner_id=owner.id,
                current_owner_id=owner.id,
            )
            teams.append(t)
        db.session.add_all(teams)
        db.session.commit()

        # Convenience map for later lookups
        team_by_name = {t.name: t for t in teams}

        # ------------------------------------------------------------
        # 4) Create Round of 32 skeleton games (one per region)
        #    NEW: year=CURRENT_YEAR
        #    We commit here to ensure these games have IDs so r64 games
        #    can point their next_game_id to these records.
        # ------------------------------------------------------------
        r32_east = Game(
            round="32",
            region="East",
            status="Scheduled",
            year=CURRENT_YEAR,  # NEW
            # team1_id/team2_id will be filled by r64 winners via propagation
        )
        r32_west = Game(
            round="32",
            region="West",
            status="Scheduled",
            year=CURRENT_YEAR,  # NEW
        )
        db.session.add_all([r32_east, r32_west])
        db.session.commit()  # ensure r32_east.id / r32_west.id exist

        # ------------------------------------------------------------
        # 5) Create Round of 64 games (2 per region) with simple spreads
        #    NEW: include "year": CURRENT_YEAR in each dict; pass to Game(...)
        # ------------------------------------------------------------
        now = datetime.now(timezone.utc)
        games_to_create = [
            # East region games
            {
                "round": "64",
                "region": "East",
                "year": CURRENT_YEAR,  # NEW
                "team1": "UConn",    # favored
                "team2": "Kentucky",
                "team1_owner": team_by_name["UConn"].current_owner,
                "team2_owner": team_by_name["Kentucky"].current_owner,
                "spread": 6.5,
                "favorite": "UConn",
                "game_time": now + timedelta(days=1),
            },
            {
                "round": "64",
                "region": "East",
                "year": CURRENT_YEAR,  # NEW
                "team1": "Duke",     # favored
                "team2": "UNC",
                "team1_owner": team_by_name["Duke"].current_owner,
                "team2_owner": team_by_name["UNC"].current_owner,
                "spread": 4.5,
                "favorite": "Duke",
                "game_time": now + timedelta(days=1, hours=2),
            },
            # West region games
            {
                "round": "64",
                "region": "West",
                "year": CURRENT_YEAR,  # NEW
                "team1": "Arizona",  # favored
                "team2": "Baylor",
                "team1_owner": team_by_name["Arizona"].current_owner,
                "team2_owner": team_by_name["Baylor"].current_owner,
                "spread": 5.0,
                "favorite": "Arizona",
                "game_time": now + timedelta(days=1, hours=4),
            },
            {
                "round": "64",
                "region": "West",
                "year": CURRENT_YEAR,  # NEW
                "team1": "Gonzaga",  # favored
                "team2": "Kansas",
                "team1_owner": team_by_name["Gonzaga"].current_owner,
                "team2_owner": team_by_name["Kansas"].current_owner,
                "spread": 2.5,
                "favorite": "Gonzaga",
                "game_time": now + timedelta(days=1, hours=6),
            },
        ]

        # Add (but don't commit yet) so we can set next_game links first
        for g in games_to_create:
            t1 = team_by_name[g["team1"]]
            t2 = team_by_name[g["team2"]]
            fav = team_by_name[g["favorite"]]
            game = Game(
                round=g["round"],
                region=g["region"],
                year=g["year"],  # NEW ensure each has year set
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

        # ------------------------------------------------------------
        # 6) Link Round of 64 games to their Round of 32 targets
        #    Assumption for compact demo:
        #      - The two East r64 games feed into r32_east (slots 1 and 2)
        #      - The two West r64 games feed into r32_west (slots 1 and 2)
        #    We order by region then id; since we added East first, we expect
        #    [East A, East B, West A, West B].
        # ------------------------------------------------------------
        db.session.flush()  # ensure pending r64 games get IDs for ordering
        r64_games = (
            db.session.query(Game)
            .filter_by(round="64")
            .order_by(Game.region.asc(), Game.id.asc())
            .all()
        )

        if len(r64_games) == 4:
            # East
            r64_games[0].next_game_id = r32_east.id
            r64_games[0].next_game_slot = 1
            r64_games[1].next_game_id = r32_east.id
            r64_games[1].next_game_slot = 2

            # West
            r64_games[2].next_game_id = r32_west.id
            r64_games[2].next_game_slot = 1
            r64_games[3].next_game_id = r32_west.id
            r64_games[3].next_game_slot = 2

        # Finalize all inserts/updates
        db.session.commit()
        print(
            f"✅ Seed complete for {CURRENT_YEAR}: inserted Participants, Teams, r32 skeleton Games, r64 Games, and set next links.")


if __name__ == "__main__":
    reset_and_seed()
