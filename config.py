# config.py
# -------------------------------
# Centralized configuration.
# Adds database config pointing to instance/mmm.db
# We’ll expand this as the project grows (e.g., DB URI, API keys via env vars).
# -------------------------------

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

class Config:
    # Later we’ll set a proper SQLite path (e.g., instance folder).
    # For now we leave placeholders to keep things simple.
    SECRET_KEY = os.environ.get("MMM_SECRET_KEY", "dev-key-not-for-production")


    # Ensure instance directory exists
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    # SQLite database path (local only)
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(INSTANCE_DIR, 'mmm.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Example placeholders for future steps:
    # DATABASE_URI = os.environ.get("MMM_DATABASE_URI", "sqlite:///mmm.db")
    # ODDS_API_KEY = os.environ.get("MMM_ODDS_API_KEY", "")
    # SCORE_API_SOURCE = os.environ.get("MMM_SCORE_API_SOURCE", "ncaa")

