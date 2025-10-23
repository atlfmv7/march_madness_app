# config.py
# -------------------------------
# Centralized configuration.
# We’ll expand this as the project grows (e.g., DB URI, API keys via env vars).
# -------------------------------

import os

class Config:
    # Later we’ll set a proper SQLite path (e.g., instance folder).
    # For now we leave placeholders to keep things simple.
    SECRET_KEY = os.environ.get("MMM_SECRET_KEY", "dev-key-not-for-production")

    # Example placeholders for future steps:
    # DATABASE_URI = os.environ.get("MMM_DATABASE_URI", "sqlite:///mmm.db")
    # ODDS_API_KEY = os.environ.get("MMM_ODDS_API_KEY", "")
    # SCORE_API_SOURCE = os.environ.get("MMM_SCORE_API_SOURCE", "ncaa")
    pass
