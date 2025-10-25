# tests/test_providers_fallback.py
from app import create_app
from models import db
from datetime import date

def test_fetchers_safe_without_keys(tmp_path, monkeypatch):
    app = create_app()
    app.config.update(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path/'fallback.db'}",
        TESTING=True,
        ENABLE_LIVE_SPREADS=True,
        ENABLE_LIVE_SCORES=True,
        ODDS_API_KEY="",  # no key on purpose
    )
    with app.app_context():
        db.drop_all(); db.create_all()

        # Import late to bind to app context
        from data_fetchers.spreads import update_game_spreads
        from data_fetchers.scores import update_game_scores

        # Should not raise, should return 0
        assert update_game_spreads(date.today()) == 0
        assert update_game_scores(date_iso=date.today().isoformat()) == 0
