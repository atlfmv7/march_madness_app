# app.py
# -------------------------------
# Flask application entry point and CLI commands.
# This version consolidates imports, standardizes timezone-aware dates,
# and avoids redundant logic. It uses the app-factory pattern.
#
# Why this file exists and what it does:
#   - Creates and configures the Flask app (via create_app).
#   - Initializes the database and provides routes and CLI helpers.
#   - Renders the homepage, showing games grouped by region/round.
#   - NEW: Supports selecting a tournament 'year' (via querystring ?year=YYYY),
#           defaults to the most recent year in the DB (or current UTC year when none).
#           Filters displayed games to the selected year, and provides a list of
#           available years for a dropdown in the template.
# -------------------------------

from __future__ import annotations
import os

from datetime import datetime, date, timezone
from typing import Dict

import click
from flask import Flask, render_template, request, url_for

from bracket_logic import evaluate_and_finalize_game, live_owner_leader_vs_spread
from data_fetchers.scores import update_game_scores
from data_fetchers.spreads import update_game_spreads
from models import Game, Team, db
# config.py
# Load environment variables from .env if present
from dotenv import load_dotenv
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(basedir, 'instance', 'mmm.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Providers / toggles
    ODDS_API_KEY = os.environ.get("ODDS_API_KEY", "").strip()
    ENABLE_LIVE_SPREADS = os.environ.get(
        "ENABLE_LIVE_SPREADS", "true").lower() == "true"
    ENABLE_LIVE_SCORES = os.environ.get(
        "ENABLE_LIVE_SCORES", "true").lower() == "true"


# ---------- Utilities ----------

def today_utc() -> date:
    """Return today's date in UTC as a date object (timezone-aware)."""
    return datetime.now(timezone.utc).date()


# ---------- App Factory ----------

def create_app() -> Flask:
    """
    Create and configure the Flask app:
      - Loads configuration from config.Config
      - Initializes SQLAlchemy
      - Registers routes
      - Registers CLI commands
    """
    app = Flask(__name__)
    app.config.from_object("config.Config")
    # Enable flash messaging for admin interface
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    db.init_app(app)

    # ----- Routes -----

    @app.route("/admin")
    def admin():
        """Admin dashboard with links to all admin functions."""
        from flask import render_template
        # Get all scheduled or in-progress games for current year
        current_year = datetime.now(timezone.utc).year
        games = (
            Game.query
            .filter(Game.year == current_year)
            .filter(Game.status.in_(["Scheduled", "In Progress"]))
            .order_by(Game.region.asc(), Game.round.asc(), Game.id.asc())
            .all()
        )
        
        # Get participant count for dashboard
        from models import Participant
        participant_count = db.session.query(Participant).count()
        
        return render_template(
            "admin.html", 
            games=games, 
            year=current_year,
            participant_count=participant_count
        )

    @app.route("/admin/update_game", methods=["POST"])
    def admin_update_game():
        """Handle manual game updates from admin form."""
        from flask import request, redirect, url_for, flash
        
        game_id = request.form.get("game_id", type=int)
        action = request.form.get("action")
        
        if not game_id:
            if hasattr(app, 'flash'):
                flash("Invalid game ID", "error")
            return redirect(url_for("admin"))
        
        game = db.session.get(Game, game_id)
        if not game:
            if hasattr(app, 'flash'):
                flash(f"Game {game_id} not found", "error")
            return redirect(url_for("admin"))
        
        try:
            if action == "set_spread":
                spread = request.form.get("spread", type=float)
                favorite_id = request.form.get("favorite_id", type=int)
                if spread is not None and favorite_id:
                    game.spread = spread
                    game.spread_favorite_team_id = favorite_id
                    db.session.commit()
                    if hasattr(app, 'flash'):
                        flash(f"Spread updated for game {game_id}", "success")
            
            elif action == "set_scores":
                team1_score = request.form.get("team1_score", type=int)
                team2_score = request.form.get("team2_score", type=int)
                status = request.form.get("status")
                
                if team1_score is not None and team2_score is not None:
                    game.team1_score = team1_score
                    game.team2_score = team2_score
                    if status:
                        game.status = status
                    db.session.commit()
                    
                    # If marked final, evaluate
                    if status == "Final":
                        team_winner, owner_winner = evaluate_and_finalize_game(game.id)
                        if hasattr(app, 'flash'):
                            flash(f"Game {game_id} finalized. Winner: {team_winner.name} (Owner: {owner_winner.name})", "success")
                    else:
                        if hasattr(app, 'flash'):
                            flash(f"Scores updated for game {game_id}", "success")
        
        except Exception as e:
            if hasattr(app, 'flash'):
                flash(f"Error updating game: {str(e)}", "error")
            import logging
            logging.error(f"Admin update error: {e}")
        
        return redirect(url_for("admin"))

    @app.route("/admin/participants")
    def admin_participants():
        """Manage tournament participants."""
        from flask import render_template
        from models import Participant
        
        participants = Participant.query.order_by(Participant.name.asc()).all()
        
        return render_template(
            "admin_participants.html",
            participants=participants
        )
    
    @app.route("/admin/participants/add", methods=["POST"])
    def admin_participants_add():
        """Add a new participant."""
        from flask import request, redirect, url_for, flash
        from models import Participant
        
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        
        if not name:
            flash("Participant name is required", "error")
            return redirect(url_for("admin_participants"))
        
        # Check for duplicate
        existing = Participant.query.filter_by(name=name).first()
        if existing:
            flash(f"Participant '{name}' already exists", "error")
            return redirect(url_for("admin_participants"))
        
        # Create new participant
        participant = Participant(name=name, email=email or None)
        db.session.add(participant)
        db.session.commit()
        
        flash(f"Added participant: {name}", "success")
        return redirect(url_for("admin_participants"))
    
    @app.route("/admin/participants/edit/<int:participant_id>", methods=["POST"])
    def admin_participants_edit(participant_id):
        """Edit an existing participant."""
        from flask import request, redirect, url_for, flash
        from models import Participant
        
        participant = db.session.get(Participant, participant_id)
        if not participant:
            flash("Participant not found", "error")
            return redirect(url_for("admin_participants"))
        
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        
        if not name:
            flash("Participant name is required", "error")
            return redirect(url_for("admin_participants"))
        
        # Check for duplicate (excluding current participant)
        existing = Participant.query.filter(
            Participant.name == name,
            Participant.id != participant_id
        ).first()
        if existing:
            flash(f"Participant '{name}' already exists", "error")
            return redirect(url_for("admin_participants"))
        
        # Update participant
        participant.name = name
        participant.email = email or None
        db.session.commit()
        
        flash(f"Updated participant: {name}", "success")
        return redirect(url_for("admin_participants"))
    
    @app.route("/admin/participants/delete/<int:participant_id>", methods=["POST"])
    def admin_participants_delete(participant_id):
        """Delete a participant."""
        from flask import redirect, url_for, flash
        from models import Participant
        
        participant = db.session.get(Participant, participant_id)
        if not participant:
            flash("Participant not found", "error")
            return redirect(url_for("admin_participants"))
        
        # Check if participant owns any teams
        teams_owned = Team.query.filter(
            (Team.initial_owner_id == participant_id) |
            (Team.current_owner_id == participant_id)
        ).count()
        
        if teams_owned > 0:
            flash(f"Cannot delete {participant.name} - they own {teams_owned} team(s). Remove team assignments first.", "error")
            return redirect(url_for("admin_participants"))
        
        name = participant.name
        db.session.delete(participant)
        db.session.commit()
        
        flash(f"Deleted participant: {name}", "success")
        return redirect(url_for("admin_participants"))

    @app.route("/admin/draft")
    def admin_draft():
        """Team assignment (draft) interface."""
        from flask import render_template, flash, redirect, url_for
        from models import Participant, Team
        
        # Get all participants
        participants = Participant.query.order_by(Participant.name.asc()).all()
        
        # Check if we have exactly 16
        if len(participants) != 16:
            flash(f"Need exactly 16 participants for draft (currently have {len(participants)})", "error")
            return redirect(url_for("admin_participants"))
        
        # Get all teams for current year (or most recent)
        years = [y for (y,) in db.session.query(Team.year).distinct().order_by(Team.year.desc()).all()]
        current_year = years[0] if years else datetime.now(timezone.utc).year
        
        teams = Team.query.filter_by(year=current_year).order_by(
            Team.region.asc(),
            Team.seed.asc()
        ).all()
        
        if len(teams) < 64:
            flash(f"Need 64 teams for draft (currently have {len(teams)} for {current_year})", "error")
            return redirect(url_for("admin"))
        
        # Group teams by region
        from collections import defaultdict
        teams_by_region = defaultdict(list)
        for team in teams:
            teams_by_region[team.region].append(team)
        
        # Calculate assignment stats
        assignment_stats = {}
        for participant in participants:
            owned_teams = Team.query.filter_by(
                year=current_year,
                initial_owner_id=participant.id
            ).all()
            
            # Count by region
            regions = {"East": 0, "West": 0, "South": 0, "Midwest": 0}
            for team in owned_teams:
                if team.region in regions:
                    regions[team.region] += 1
            
            assignment_stats[participant.id] = {
                "total": len(owned_teams),
                "regions": regions,
                "complete": len(owned_teams) == 4 and all(c == 1 for c in regions.values())
            }
        
        return render_template(
            "admin_draft.html",
            participants=participants,
            teams_by_region=dict(teams_by_region),
            assignment_stats=assignment_stats,
            year=current_year
        )
    
    @app.route("/admin/draft/assign", methods=["POST"])
    def admin_draft_assign():
        """Save team assignments from draft."""
        from flask import request, redirect, url_for, flash
        from models import Participant, Team
        
        # Get year
        year = request.form.get("year", type=int)
        if not year:
            flash("Invalid year", "error")
            return redirect(url_for("admin_draft"))
        
        # Process all team assignments
        teams = Team.query.filter_by(year=year).all()
        updated_count = 0
        
        for team in teams:
            owner_id = request.form.get(f"team_{team.id}", type=int)
            if owner_id:
                team.initial_owner_id = owner_id
                team.current_owner_id = owner_id
                updated_count += 1
        
        db.session.commit()
        
        # IMPORTANT: Now set game owner fields for Round of 64
        # This preserves who owned each team at the START of the tournament
        r64_games = Game.query.filter_by(year=year, round="64").all()
        for game in r64_games:
            if game.team1_id and game.team1:
                game.team1_owner_id = game.team1.initial_owner_id
            if game.team2_id and game.team2:
                game.team2_owner_id = game.team2.initial_owner_id
        
        db.session.commit()
        
        flash(f"Updated {updated_count} team assignments", "success")
        return redirect(url_for("admin_draft"))
    
    @app.route("/admin/draft/random", methods=["POST"])
    def admin_draft_random():
        """Randomly assign teams to participants."""
        from flask import request, redirect, url_for, flash
        from models import Participant, Team
        import random
        
        # Get year
        year = request.form.get("year", type=int)
        if not year:
            flash("Invalid year", "error")
            return redirect(url_for("admin_draft"))
        
        # Get participants and teams
        participants = Participant.query.all()
        if len(participants) != 16:
            flash(f"Need exactly 16 participants (have {len(participants)})", "error")
            return redirect(url_for("admin_draft"))
        
        teams = Team.query.filter_by(year=year).all()
        if len(teams) != 64:
            flash(f"Need exactly 64 teams (have {len(teams)})", "error")
            return redirect(url_for("admin_draft"))
        
        # Group teams by region
        from collections import defaultdict
        teams_by_region = defaultdict(list)
        for team in teams:
            teams_by_region[team.region].append(team)
        
        # Verify each region has 16 teams
        for region, region_teams in teams_by_region.items():
            if len(region_teams) != 16:
                flash(f"Region {region} has {len(region_teams)} teams (need 16)", "error")
                return redirect(url_for("admin_draft"))
        
        # Shuffle participants
        shuffled_participants = list(participants)
        random.shuffle(shuffled_participants)
        
        # Assign teams: each participant gets one team from each region
        for region, region_teams in teams_by_region.items():
            # Shuffle teams in this region
            shuffled_teams = list(region_teams)
            random.shuffle(shuffled_teams)
            
            # Assign one to each participant
            for i, participant in enumerate(shuffled_participants):
                team = shuffled_teams[i]
                team.initial_owner_id = participant.id
                team.current_owner_id = participant.id
        
        db.session.commit()
        
        # IMPORTANT: Set game owner fields for Round of 64
        # This preserves who owned each team at the START of the tournament
        r64_games = Game.query.filter_by(year=year, round="64").all()
        for game in r64_games:
            if game.team1_id and game.team1:
                game.team1_owner_id = game.team1.initial_owner_id
            if game.team2_id and game.team2:
                game.team2_owner_id = game.team2.initial_owner_id
        
        db.session.commit()
        
        flash("✅ Teams randomly assigned! Each participant has 4 teams (one per region).", "success")
        return redirect(url_for("admin_draft"))
    
    @app.route("/admin/draft/reset", methods=["POST"])
    def admin_draft_reset():
        """Clear all team assignments."""
        from flask import request, redirect, url_for, flash
        from models import Team

        # Get year
        year = request.form.get("year", type=int)
        if not year:
            flash("Invalid year", "error")
            return redirect(url_for("admin_draft"))

        # Clear all assignments for this year
        teams = Team.query.filter_by(year=year).all()
        for team in teams:
            team.initial_owner_id = None
            team.current_owner_id = None

        db.session.commit()

        flash("All team assignments cleared", "success")
        return redirect(url_for("admin_draft"))

    @app.route("/admin/reset_test_data", methods=["POST"])
    def admin_reset_test_data():
        """Reset all data and load test participants and 2024 bracket."""
        from flask import redirect, url_for, flash
        from models import Participant
        import csv
        import random
        from collections import defaultdict

        try:
            # Step 1: Delete all existing data
            print("🗑️  Deleting all games, teams, and participants...")
            db.session.query(Game).delete()
            db.session.query(Team).delete()
            db.session.query(Participant).delete()
            db.session.commit()

            # Step 2: Add test participants
            print("➕ Adding 16 test participants...")
            test_names = [
                "Ryan", "Alice", "Bob", "Carol", "David",
                "Emma", "Frank", "Grace", "Henry", "Ivy",
                "Jack", "Kate", "Liam", "Maya", "Nathan", "Olivia"
            ]

            participants = []
            for name in test_names:
                participant = Participant(
                    name=name,
                    email=f"{name.lower()}@example.com"
                )
                db.session.add(participant)
                participants.append(participant)

            db.session.commit()
            print(f"✅ Added {len(participants)} participants")

            # Step 3: Load 2024 bracket from CSV
            print("📂 Loading 2024 bracket from CSV...")
            csv_path = "bracket_2024.csv"
            year = 2024

            team_objects = {}
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    team = Team(
                        name=row['team_name'].strip(),
                        seed=int(row['seed']),
                        region=row['region'].strip(),
                        year=year
                    )
                    db.session.add(team)
                    team_objects[row['team_name'].strip()] = team

            db.session.flush()  # Assign IDs
            print(f"✅ Created {len(team_objects)} teams")

            # Step 4: Create games structure
            print("🎮 Creating bracket games...")
            REGIONS = ["East", "West", "South", "Midwest"]
            BRACKET_STRUCTURE = [
                ("64", 32), ("32", 16), ("16", 8), ("8", 4), ("4", 2), ("2", 1)
            ]

            games_by_round = {}
            for round_name, count in BRACKET_STRUCTURE:
                games_by_round[round_name] = []
                for i in range(count):
                    region = None
                    if round_name in ["64", "32", "16", "8"]:
                        region = REGIONS[i % len(REGIONS)]

                    game = Game(
                        round=round_name,
                        region=region,
                        year=year,
                        status="Scheduled"
                    )
                    db.session.add(game)
                    games_by_round[round_name].append(game)

            db.session.flush()

            # Link games for bracket progression
            print("🔗 Linking bracket games...")
            _link_bracket_games_helper(games_by_round, REGIONS)

            # Assign teams to first round
            print("👥 Assigning teams to first round...")
            _assign_first_round_helper(games_by_round["64"], team_objects, REGIONS)

            db.session.commit()

            # Step 5: Random draft assignment
            print("🎲 Randomly assigning teams to participants...")
            teams = Team.query.filter_by(year=year).all()
            teams_by_region = defaultdict(list)
            for team in teams:
                teams_by_region[team.region].append(team)

            shuffled_participants = list(participants)
            random.shuffle(shuffled_participants)

            for region, region_teams in teams_by_region.items():
                shuffled_teams = list(region_teams)
                random.shuffle(shuffled_teams)

                for i, participant in enumerate(shuffled_participants):
                    team = shuffled_teams[i]
                    team.initial_owner_id = participant.id
                    team.current_owner_id = participant.id

            # Set game owner fields for Round of 64
            r64_games = Game.query.filter_by(year=year, round="64").all()
            for game in r64_games:
                if game.team1_id and game.team1:
                    game.team1_owner_id = game.team1.initial_owner_id
                if game.team2_id and game.team2:
                    game.team2_owner_id = game.team2.initial_owner_id

            db.session.commit()

            flash("✅ Test data reset complete! Added 16 participants, loaded 2024 bracket, and randomly assigned teams.", "success")
            print("✅ Test data reset successful!")

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error resetting test data: {str(e)}", "error")
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        return redirect(url_for("admin"))

    def _link_bracket_games_helper(games_by_round, REGIONS):
        """Helper to link bracket games for progression."""
        # Round of 64 → Round of 32
        r64_games = games_by_round["64"]
        r32_games = games_by_round["32"]

        for region in REGIONS:
            region_r64 = sorted([g for g in r64_games if g.region == region], key=lambda g: g.id)
            region_r32 = sorted([g for g in r32_games if g.region == region], key=lambda g: g.id)

            for i, game in enumerate(region_r64):
                next_game_index = i // 2
                if next_game_index < len(region_r32):
                    game.next_game_id = region_r32[next_game_index].id
                    game.next_game_slot = 1 if i % 2 == 0 else 2

        # Round of 32 → Round of 16
        r16_games = games_by_round["16"]
        for region in REGIONS:
            region_r32 = sorted([g for g in r32_games if g.region == region], key=lambda g: g.id)
            region_r16 = sorted([g for g in r16_games if g.region == region], key=lambda g: g.id)

            for i, game in enumerate(region_r32):
                next_game_index = i // 2
                if next_game_index < len(region_r16):
                    game.next_game_id = region_r16[next_game_index].id
                    game.next_game_slot = 1 if i % 2 == 0 else 2

        # Round of 16 → Elite 8
        r8_games = games_by_round["8"]
        for region in REGIONS:
            region_r16 = sorted([g for g in r16_games if g.region == region], key=lambda g: g.id)
            region_r8 = sorted([g for g in r8_games if g.region == region], key=lambda g: g.id)

            for i, game in enumerate(region_r16):
                next_game_index = i // 2
                if next_game_index < len(region_r8):
                    game.next_game_id = region_r8[next_game_index].id
                    game.next_game_slot = 1 if i % 2 == 0 else 2

        # Elite 8 → Final Four
        r4_games = games_by_round["4"]
        r8_games_sorted = sorted(r8_games, key=lambda g: g.id)

        for i, game in enumerate(r8_games_sorted):
            next_game_index = i // 2
            if next_game_index < len(r4_games):
                game.next_game_id = r4_games[next_game_index].id
                game.next_game_slot = 1 if i % 2 == 0 else 2

        # Final Four → Championship
        r2_games = games_by_round["2"]
        for i, game in enumerate(r4_games):
            if len(r2_games) > 0:
                game.next_game_id = r2_games[0].id
                game.next_game_slot = 1 if i == 0 else 2

    def _assign_first_round_helper(games, team_objects, REGIONS):
        """Helper to assign teams to first round based on standard seeding."""
        matchups = [
            (1, 16), (8, 9), (5, 12), (4, 13),
            (6, 11), (3, 14), (7, 10), (2, 15)
        ]

        for region in REGIONS:
            region_teams = {
                t.seed: t for t in team_objects.values()
                if t.region == region
            }

            region_games = sorted([g for g in games if g.region == region], key=lambda g: g.id)

            for game_idx, (seed1, seed2) in enumerate(matchups):
                if game_idx < len(region_games):
                    game = region_games[game_idx]
                    team1 = region_teams.get(seed1)
                    team2 = region_teams.get(seed2)

                    if team1 and team2:
                        game.team1_id = team1.id
                        game.team2_id = team2.id
                        game.team1_owner_id = team1.initial_owner_id
                        game.team2_owner_id = team2.initial_owner_id

    @app.route("/admin/simulate_tournament", methods=["POST"])
    def admin_simulate_tournament():
        """Simulate tournament games."""
        from flask import request, redirect, url_for, flash
        import random

        action = request.form.get("action")
        year = request.form.get("year", type=int) or datetime.now(timezone.utc).year

        try:
            if action == "simulate_all":
                # Simulate entire tournament
                print(f"\n🏆 Simulating entire {year} tournament...")

                rounds = [64, 32, 16, 8, 4, 2]
                total_games = 0

                for round_num in rounds:
                    games = (
                        Game.query
                        .filter_by(year=year, round=str(round_num), status="Scheduled")
                        .all()
                    )

                    if not games:
                        break

                    for game in games:
                        if game.team1 and game.team2:
                            _simulate_single_game(game)
                            total_games += 1

                # Check for champion
                championship_game = (
                    Game.query
                    .filter_by(year=year, round="2", status="Final")
                    .first()
                )

                if championship_game and championship_game.winner_id:
                    champion = db.session.get(Team, championship_game.winner_id)
                    flash(f"🏆 Tournament Complete! Champion: {champion.name} (Seed {champion.seed}) - Owner: {champion.current_owner.name if champion.current_owner else 'Unknown'}", "success")
                else:
                    flash(f"✅ Simulated {total_games} games successfully!", "success")

            elif action == "simulate_next":
                # Simulate next available round
                rounds = [64, 32, 16, 8, 4, 2]
                simulated = False

                for round_num in rounds:
                    games = (
                        Game.query
                        .filter_by(year=year, round=str(round_num), status="Scheduled")
                        .all()
                    )

                    if games:
                        count = 0
                        for game in games:
                            if game.team1 and game.team2:
                                _simulate_single_game(game)
                                count += 1

                        flash(f"✅ Simulated Round of {round_num} ({count} games)", "success")
                        simulated = True
                        break

                if not simulated:
                    flash("⚠️ No scheduled games to simulate", "warning")

            else:
                flash("Invalid action", "error")

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error simulating tournament: {str(e)}", "error")
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        return redirect(url_for("admin"))

    def _simulate_single_game(game):
        """Helper to simulate a single game."""
        import random
        from bracket_logic import evaluate_and_finalize_game

        # Set game owner fields if not set
        if game.team1_owner_id is None:
            game.team1_owner_id = game.team1.current_owner_id
        if game.team2_owner_id is None:
            game.team2_owner_id = game.team2.current_owner_id

        # Set spread if not already set
        if not game.spread or not game.spread_favorite_team_id:
            if game.team1.seed < game.team2.seed:
                seed_diff = game.team2.seed - game.team1.seed
                game.spread = round(min(seed_diff * 1.5, 15.0), 1)
                game.spread_favorite_team_id = game.team1.id
            elif game.team2.seed < game.team1.seed:
                seed_diff = game.team1.seed - game.team2.seed
                game.spread = round(min(seed_diff * 1.5, 15.0), 1)
                game.spread_favorite_team_id = game.team2.id
            else:
                game.spread = 0.0
                game.spread_favorite_team_id = game.team1.id

        # Generate realistic scores (50-95 range)
        score1 = random.randint(55, 90)
        score2 = random.randint(55, 90)

        # Ensure no tie
        while score1 == score2:
            score2 = random.randint(55, 90)

        # Favor lower seeds (65% chance to win)
        if game.team1.seed < game.team2.seed:
            if random.random() > 0.35:
                if score2 > score1:
                    score1, score2 = score2, score1
        elif game.team2.seed < game.team1.seed:
            if random.random() > 0.35:
                if score1 > score2:
                    score1, score2 = score2, score1

        # Set scores and finalize
        game.team1_score = score1
        game.team2_score = score2
        game.status = "Final"
        db.session.commit()

        # Evaluate and advance winner
        evaluate_and_finalize_game(game.id)

    @app.route("/bracket")
    def bracket():
        """Visual bracket tree display."""
        from flask import render_template
        from models import Team, Participant

        # Get year from query string or default to most recent
        years = [y for (y,) in db.session.query(Team.year).distinct().order_by(Team.year.desc()).all()]
        if not years:
            current_year = datetime.now(timezone.utc).year
        else:
            current_year = years[0]

        try:
            selected_year = int(request.args.get("year", current_year))
        except ValueError:
            selected_year = current_year

        # Get all games for this year, ordered by round and region
        games = (
            Game.query
            .filter_by(year=selected_year)
            .order_by(Game.region.asc(), Game.round.asc(), Game.id.asc())
            .all()
        )

        # Group by region
        from collections import defaultdict
        regions = defaultdict(lambda: defaultdict(list))
        for game in games:
            regions[game.region][game.round].append(game)

        # Get today's games for the score ticker
        today = datetime.now(timezone.utc).date()
        todays_games = [
            g for g in games
            if g.game_time and g.game_time.date() == today
        ]

        # Calculate high and low scores from completed games
        high_score_info = None
        low_score_info = None

        completed_games = [g for g in games if g.status == "Final"]

        if completed_games:
            # Find all individual scores with team and owner info
            all_scores = []
            for game in completed_games:
                if game.team1_score is not None:
                    all_scores.append({
                        'score': game.team1_score,
                        'team': game.team1,
                        'owner_id': game.team1_owner_id,
                        'game': game
                    })
                if game.team2_score is not None:
                    all_scores.append({
                        'score': game.team2_score,
                        'team': game.team2,
                        'owner_id': game.team2_owner_id,
                        'game': game
                    })

            if all_scores:
                # Find high score
                high_score_data = max(all_scores, key=lambda x: x['score'])
                high_score_owner = None
                if high_score_data['owner_id']:
                    high_score_owner = db.session.get(Participant, high_score_data['owner_id'])

                high_score_info = {
                    'score': high_score_data['score'],
                    'team': high_score_data['team'],
                    'owner': high_score_owner,
                    'round': high_score_data['game'].round
                }

                # Find low score
                low_score_data = min(all_scores, key=lambda x: x['score'])
                low_score_owner = None
                if low_score_data['owner_id']:
                    low_score_owner = db.session.get(Participant, low_score_data['owner_id'])

                low_score_info = {
                    'score': low_score_data['score'],
                    'team': low_score_data['team'],
                    'owner': low_score_owner,
                    'round': low_score_data['game'].round
                }

        return render_template(
            "bracket.html",
            regions=dict(regions),
            years=years,
            selected_year=selected_year,
            high_score=high_score_info,
            low_score=low_score_info,
            todays_games=todays_games
        )

    @app.route("/")
    def home():
        """
        Homepage:
        - Loads games for a selected year (default: latest available).
        - Computes the live 'leader vs spread' for in-progress games.
        - Groups the games by region and round for simple rendering.

        How 'year' works:
        - We look up all distinct Game.year values in ascending order to build a year list.
        - If no games exist yet, we fall back to the current UTC year.
        - If a 'year' query parameter is provided (e.g., /?year=2025), we attempt to use it;
          otherwise we default to the most recent year available in the DB.
        - We then filter the games query to only include the selected year.
        """
        # Build a sorted list of available years from the DB, e.g. [2024, 2025].
        years = [y for (y,) in db.session.query(
            Game.year).distinct().order_by(Game.year.asc()).all()]

        # Choose a default year: latest found in DB, or current UTC year if no data yet.
        if years:
            default_year = years[-1]  # latest
        else:
            default_year = datetime.now(timezone.utc).year

        # Parse the incoming ?year=YYYY, falling back to default_year on missing/invalid.
        try:
            selected_year = int(request.args.get("year", default_year))
        except ValueError:
            selected_year = default_year

        # ORDER: region asc, round asc (string), id asc for stability; filter by year.
        games = (
            Game.query
            .filter(Game.year == selected_year)
            .order_by(Game.region.asc(), Game.round.asc(), Game.id.asc())
            .all()
        )

        # Compute live leader safely; never let logic errors break the page.
        import logging
        logger = logging.getLogger(__name__)
        for g in games:
            try:
                g._live_owner_leader = live_owner_leader_vs_spread(
                    g)  # type: ignore[attr-defined]
            except Exception as e:
                logger.warning(f"Failed to compute live leader for game {g.id}: {e}")
                g._live_owner_leader = None  # type: ignore[attr-defined]

        # Group into nested dict: { region: { round: [games...] } }
        grouped: Dict[str, Dict[str, list[Game]]] = {}
        for g in games:
            region_key = g.region or "Unknown"
            round_key = g.round
            grouped.setdefault(region_key, {}).setdefault(
                round_key, []).append(g)

        return render_template(
            "index.html",
            message=f"Loaded games for {selected_year}.",
            grouped=grouped,
            years=years,
            selected_year=selected_year,
        )

    # Create tables once at startup (safe no-op if already exist)
    with app.app_context():
        db.create_all()

    # ----- CLI Commands -----
    @app.context_processor
    def inject_year_helpers():
        """
        Adds url_with_year() to Jinja:
        - Behaves like url_for(), but ensures the current ?year=... sticks
            unless you explicitly pass a different year.
        Also adds format_game_time() for displaying times in ET.
        """
        def url_with_year(endpoint, **values):
            # Prefer explicitly provided year, else take it from the current query string
            year = values.pop("year", request.args.get("year"))
            if year:
                values["year"] = year
            return url_for(endpoint, **values)
        
        def format_game_time(dt):
            """Format a datetime in Eastern Time for display."""
            if not dt:
                return None
            from datetime import timezone
            from zoneinfo import ZoneInfo
            # Ensure timezone aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # Convert to ET
            et_time = dt.astimezone(ZoneInfo("America/New_York"))
            return et_time.strftime("%a, %b %d at %I:%M %p ET")
        
        return dict(url_with_year=url_with_year, format_game_time=format_game_time)

    @app.cli.command("eval-game")
    def eval_game_cmd():
        """
        Evaluate a FINAL game by ID (interactive prompt if GAME_ID not set).
        Persists winner_id and prints both the team winner and owner winner.
        Usage:
            flask eval-game
            GAME_ID=12 flask eval-game
        """
        import os

        game_id = os.environ.get("GAME_ID")
        if not game_id:
            try:
                game_id = input("Enter the Game ID to evaluate: ").strip()
            except EOFError:
                click.echo("No GAME_ID provided. Aborting.")
                return
        if not game_id.isdigit():
            click.echo("GAME_ID must be an integer.")
            return

        with app.app_context():
            game = db.session.get(Game, int(game_id))
            if not game:
                click.echo(f"Game {game_id} not found.")
                return
            if game.status != "Final":
                click.echo(
                    f"Game {game.id} is not Final (status={game.status}).")
                return

            team_winner, owner_winner = evaluate_and_finalize_game(game.id)
            click.echo(f"✅ Evaluated game {game.id}")
            click.echo(f"   Actual team winner: {team_winner.name}")
            click.echo(
                f"   Owner winner (vs spread): {owner_winner.name if owner_winner else 'Unknown'}")

    @app.cli.command("mark-final")
    @click.option("--id", "game_id", required=True, type=int, help="Game ID to finalize")
    @click.option("--t1", "team1_score", required=True, type=int, help="Team 1 score")
    @click.option("--t2", "team2_score", required=True, type=int, help="Team 2 score")
    def mark_final_cmd(game_id: int, team1_score: int, team2_score: int):
        """
        Mark a game Final with the provided scores and evaluate spread outcome.
        Usage:
            flask mark-final --id 1 --t1 81 --t2 80
        """
        with app.app_context():
            game = db.session.get(Game, game_id)
            if not game:
                click.echo(f"❌ Game {game_id} not found.")
                return

            # Persist scores and status
            game.team1_score = team1_score
            game.team2_score = team2_score
            game.status = "Final"
            db.session.commit()

            # Evaluate spread result
            try:
                team_winner, owner_winner = evaluate_and_finalize_game(game.id)
            except Exception as ex:
                click.echo(f"❌ Error evaluating game {game_id}: {ex}")
                return

            click.echo(
                f"✅ Game {game.id} marked Final: {game.team1.name} {team1_score} – {team2_score} {game.team2.name}"
            )
            click.echo(f"   Actual team winner: {team_winner.name}")
            click.echo(
                f"   Owner winner (vs spread): {owner_winner.name if owner_winner else 'Unknown'}")

    @app.cli.command("get-spreads")
    @click.option("--date", "date_str", required=False, help="YYYY-MM-DD (defaults to today in UTC)")
    def get_spreads_cmd(date_str: str | None):
        """
        Fetch and write spreads for the given date (default: today UTC).
        Example:
            flask get-spreads --date 2025-03-21
        """
        target_date = today_utc() if not date_str else date.fromisoformat(date_str)
        count = update_game_spreads(target_date)
        click.echo(
            f"✅ Spreads updated for {target_date.isoformat()}: {count} game(s).")

    @app.cli.command("update-scores")
    @click.option("--date", "date_str", required=False, help="YYYY-MM-DD (defaults to today in UTC)")
    def update_scores_cmd(date_str: str | None):
        """
        Fetch and write scores (and finalize games when applicable) for the given date.
        Example:
            flask update-scores --date 2025-03-21
        """
        iso = (today_utc() if not date_str else date.fromisoformat(
            date_str)).isoformat()
        count = update_game_scores(date_iso=iso)
        click.echo(f"✅ Scores updated for {iso}: {count} game(s).")

    return app


# ---------- Dev Server ----------

if __name__ == "__main__":
    app = create_app()
    # Use debug=False because we don't want Flask reloader to double-run CLI, etc.
    app.run(host="0.0.0.0", port=5000, debug=False)
