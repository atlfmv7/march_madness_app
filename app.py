# app.py
# -------------------------------
# Entry point for the Flask app.
# For Step 2, we keep this VERY simple:
# - Creates a Flask app instance
# - Loads configuration from config.py (safe defaults for now)
# - Defines a single "/" route that renders templates/index.html
# - Runs on 0.0.0.0:5000 so other devices on the LAN can access it
# -------------------------------

from flask import Flask, render_template
from bracket_logic import evaluate_and_finalize_game, live_owner_leader_vs_spread
from models import db, Game
import os


def create_app():
    """
    Application factory pattern:
    - Keeps setup organized as the project grows
    - Lets tests create an isolated app instance easily
    """
    app = Flask(__name__)

    # Load configuration (safe defaults now; we’ll expand in later steps)
    app.config.from_object("config.Config")
    # Initialize SQLAlchemy with the app
    db.init_app(app)

    # --------------------------------------------
    # CLI: Evaluate a game (useful during dev/testing)
    # Usage:
    #   flask eval-game --id 12
    #   (Must be run from the project directory with the venv active)
    # --------------------------------------------
    @app.cli.command("eval-game")
    def eval_game_cmd():
        """
        Dev-only helper:
        - Looks for GAME_ID env var or prompts via input()
        - Marks game as evaluated: sets winner_id and prints both winners
        """
        import os
        from models import Game

        game_id = os.environ.get("GAME_ID")
        if not game_id:
            try:
                game_id = input("Enter the Game ID to evaluate: ").strip()
            except EOFError:
                print("No GAME_ID provided. Aborting.")
                return
        if not game_id.isdigit():
            print("GAME_ID must be an integer.")
            return

        with app.app_context():
            game = db.session.get(Game, int(game_id))
            if not game:
                print(f"Game {game_id} not found.")
                return
            if game.status != "Final":
                print(f"Game {game_id} is not Final (status={game.status}).")
                return

            team_winner, owner_winner = evaluate_and_finalize_game(game.id)
            print(f"✅ Evaluated game {game.id}")
            print(f"   Actual team winner: {team_winner.name}")
            print(
                f"   Owner winner (vs spread): {owner_winner.name if owner_winner else 'Unknown'}")

    @app.route("/")
    def home():
        """
        Homepage:
        - Loads games from the database.
        - Groups by region then by round for a tidy display.
        - Computes (dev-only hint) a live 'leader vs spread' for in-progress games.
        """
        from models import Game  # keep local to avoid circulars if you prefer

        # Fetch all games; later we’ll filter by year, status, etc.
        games = Game.query.order_by(
            Game.region.asc(), Game.round.asc(), Game.id.asc()).all()

        # NEW: compute current live leader (vs spread) for in-progress games
        for g in games:
            try:
                g._live_owner_leader = live_owner_leader_vs_spread(
                    g)  # may be None
            except Exception:
                # Be defensive: never let a logic error break the page
                g._live_owner_leader = None

        # Group into a nested dict: { region: { round: [games...] } }
        grouped = {}
        for g in games:
            region_key = g.region or "Unknown"
            round_key = g.round
            grouped.setdefault(region_key, {}).setdefault(
                round_key, []).append(g)

        return render_template("index.html", message="Loaded games from database.", grouped=grouped)

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)
