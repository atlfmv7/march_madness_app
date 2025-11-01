# tests/test_database.py
# -------------------------------
# Confirms that the database initializes and tables exist.
# -------------------------------
from app import create_app
from models import db, Team, Game, Participant


def test_database_tables_exist(tmp_path):
    app = create_app()
    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        assert "team" in tables
        assert "game" in tables
        assert "participant" in tables
