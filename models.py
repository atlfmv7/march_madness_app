# models.py
# -------------------------------
# Database models for March Madness Madness.
# This version introduces ownership fields and relationships so we can
# display owners next to teams in each game. We keep it minimal now,
# adding more fields later when we implement full bracket logic.
# -------------------------------

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Shared SQLAlchemy handle used by the Flask app
db = SQLAlchemy()


class Participant(db.Model):
    """
    Represents a bracket participant (owner).
    Ex: "Ryan", "Alice", etc.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=True)

    def __repr__(self):
        return f"<Participant {self.name}>"


class Team(db.Model):
    """
    Represents an NCAA tournament team.
    We include optional initial/current ownership to support 'spread-winner
    takes/keeps team' logic in later steps.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    seed = db.Column(db.Integer, nullable=True)
    region = db.Column(db.String(50), nullable=True)

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
        return f"<Team {self.name} (Seed {self.seed}, Region {self.region})>"


class Game(db.Model):
    """Represents a single game and its result/spread."""
    id = db.Column(db.Integer, primary_key=True)

    # "64","32","16","8","4","2","Championship"
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

    # 🔗 NEW: next-round linkage (this game feeds into next_game in slot 1 or 2)
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

    # 🔗 NEW: next game relationship (self-referential)
    next_game = db.relationship("Game", remote_side=[id], lazy="joined")

    def spread_label(self):
        if self.spread is None or not self.spread_favorite_team:
            return None
        return f"{self.spread_favorite_team.name} -{self.spread:g}"

    def score_label(self):
        if self.team1_score is None or self.team2_score is None:
            return None
        return f"{self.team1_score}–{self.team2_score}"

    def __repr__(self):
        return f"<Game R{self.round}: {self.team1_id} vs {self.team2_id} ({self.status})>"

    def spread_label(self):
        """
        Returns a human-readable label for the spread, e.g.:
          "Duke -4.5" or "UNC -2"
        If spread data is missing, returns None.
        """
        if self.spread is None or not self.spread_favorite_team:
            return None
        return f"{self.spread_favorite_team.name} -{self.spread:g}"

    def score_label(self):
        """
        Returns "X–Y" if scores exist, otherwise None.
        """
        if self.team1_score is None or self.team2_score is None:
            return None
        return f"{self.team1_score}–{self.team2_score}"

    def __repr__(self):
        return f"<Game R{self.round}: {self.team1_id} vs {self.team2_id} ({self.status})>"
