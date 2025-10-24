# models.py
# -------------------------------
# Database models for March Madness Madness.
# This version adds a Python-side default year for Team and Game to avoid
# NOT NULL errors when tests or scripts omit the 'year' field. It also
# allows the same team name to appear across different years by removing
# the unique constraint on Team.name and adding a composite index on
# (name, year) instead.
# -------------------------------

from datetime import datetime, timezone
from sqlalchemy import Index
from flask_sqlalchemy import SQLAlchemy

# Shared SQLAlchemy handle used by the Flask app
db = SQLAlchemy()


class Participant(db.Model):
    """Represents a bracket participant (owner), e.g., "Ryan", "Alice"."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=True)

    def __repr__(self):
        return f"<Participant {self.name}>"


# --- NEW: helper for Python-side default year ---
def current_year() -> int:
    """Return the current year in UTC. Used as a SQLAlchemy default callable."""
    return datetime.now(timezone.utc).year


class Team(db.Model):
    """Represents an NCAA tournament team (scoped by year)."""
    id = db.Column(db.Integer, primary_key=True)
    # NOTE: Not unique across all time; the same school can appear in multiple years.
    name = db.Column(db.String(100), nullable=False, unique=False)
    seed = db.Column(db.Integer, nullable=True)
    region = db.Column(db.String(50), nullable=True)

    # NOTE: Python-side default ensures inserts without 'year' won't fail.
    year = db.Column(db.Integer, nullable=False,
                     index=True, default=current_year)

    # Ownership — optional now, but very useful later
    initial_owner_id = db.Column(
        db.Integer, db.ForeignKey("participant.id"), nullable=True)
    current_owner_id = db.Column(
        db.Integer, db.ForeignKey("participant.id"), nullable=True)

    # Convenient relationships (don’t change schema; just give us Python accessors)
    initial_owner = db.relationship("Participant", foreign_keys=[
                                    initial_owner_id], lazy="joined")
    current_owner = db.relationship("Participant", foreign_keys=[
                                    current_owner_id], lazy="joined")

    def __repr__(self):
        return f"<Team {self.name} (Seed {self.seed}, {self.region}, {self.year})>"


# Composite index to make lookups by (name, year) efficient and non-unique
Index("ix_team_name_year", Team.name, Team.year, unique=False)


class Game(db.Model):
    """Represents a single game and its result/spread."""
    id = db.Column(db.Integer, primary_key=True)

    # Same Python-side default for Game
    year = db.Column(db.Integer, nullable=False,
                     index=True, default=current_year)

    # Rounds: "64","32","16","8","4","2","Championship"
    round = db.Column(db.String(20), nullable=False)
    region = db.Column(db.String(50), nullable=True)

    # Current participants
    team1_id = db.Column(db.Integer, db.ForeignKey("team.id"))
    team2_id = db.Column(db.Integer, db.ForeignKey("team.id"))

    team1_owner_id = db.Column(
        db.Integer, db.ForeignKey("participant.id"), nullable=True)
    team2_owner_id = db.Column(
        db.Integer, db.ForeignKey("participant.id"), nullable=True)

    # Pre-game spread info
    spread = db.Column(db.Float, nullable=True)
    spread_favorite_team_id = db.Column(
        db.Integer, db.ForeignKey("team.id"), nullable=True)

    # Live/final scoring
    team1_score = db.Column(db.Integer, nullable=True)
    team2_score = db.Column(db.Integer, nullable=True)

    # Finalization
    winner_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=True)
    status = db.Column(db.String(20), default="Scheduled", nullable=False)
    game_time = db.Column(db.DateTime, nullable=True)

    # 🔗 next-round linkage (this game feeds into next_game in slot 1 or 2)
    next_game_id = db.Column(
        db.Integer, db.ForeignKey("game.id"), nullable=True)
    next_game_slot = db.Column(db.Integer, nullable=True)  # 1 or 2

    # Relationships
    team1 = db.relationship("Team", foreign_keys=[team1_id], lazy="joined")
    team2 = db.relationship("Team", foreign_keys=[team2_id], lazy="joined")
    team1_owner = db.relationship("Participant", foreign_keys=[
                                  team1_owner_id], lazy="joined")
    team2_owner = db.relationship("Participant", foreign_keys=[
                                  team2_owner_id], lazy="joined")
    spread_favorite_team = db.relationship(
        "Team", foreign_keys=[spread_favorite_team_id], lazy="joined")
    winner = db.relationship("Team", foreign_keys=[winner_id], lazy="joined")

    # Self-referential next game relationship
    next_game = db.relationship("Game", remote_side=[id], lazy="joined")

    def spread_label(self):
        """Return a human-readable label for the spread, e.g., "Duke -4.5"."""
        if self.spread is None or not self.spread_favorite_team:
            return None
        return f"{self.spread_favorite_team.name} -{self.spread:g}"

    def score_label(self):
        """Return "X–Y" if scores exist, otherwise None."""
        if self.team1_score is None or self.team2_score is None:
            return None
        return f"{self.team1_score}–{self.team2_score}"

    def __repr__(self):
        return f"<Game {self.year} R{self.round}: {self.team1_id} vs {self.team2_id} ({self.status})>"
