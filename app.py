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
from models import Game, db
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
    db.init_app(app)

    # ----- Routes -----

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
        for g in games:
            try:
                g._live_owner_leader = live_owner_leader_vs_spread(
                    g)  # type: ignore[attr-defined]
            except Exception:
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
        """
        def url_with_year(endpoint, **values):
            # Prefer explicitly provided year, else take it from the current query string
            year = values.pop("year", request.args.get("year"))
            if year:
                values["year"] = year
            return url_for(endpoint, **values)
        return dict(url_with_year=url_with_year)

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
