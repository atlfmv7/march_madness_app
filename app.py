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
from models import db
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
        Root page:
        - For Step 2, just render a simple template
        - Later, this will show current year bracket, owners, and spreads
        """
        # Pass a tiny bit of sample data to prove templating works
        sample_message = "Database connection initialized successfully!"
        return render_template("index.html", message=sample_message)

    # Create tables if not existing
    with app.app_context():
        db.create_all()
        
    return app

# Only run the dev server if this file is executed directly (not when imported by tests/tools).
if __name__ == "__main__":
    # Create the app and run it.
    app = create_app()
    # host="0.0.0.0" -> accessible on LAN; port 5000 matches our prior step
    app.run(host="0.0.0.0", port=5000, debug=False)

