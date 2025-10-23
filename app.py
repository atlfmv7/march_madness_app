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

    @app.route("/")
    def home():
        """
        Homepage:
        - Loads games from the database.
        - Groups by region then by round for a tidy display.
        """
        # Fetch all games; later we’ll filter by year, status, etc.
        games = Game.query.order_by(
            Game.region.asc(), Game.round.asc(), Game.id.asc()).all()

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
