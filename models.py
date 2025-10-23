# models.py
# -------------------------------
# Defines three starter tables using SQLAlchemy ORM:
#   Team – basic info for each tournament team
#   Game – stores matchups, rounds, scores, and spread
#   Participant – tracks bracket owners
# -------------------------------

from flask_sqlalchemy import SQLAlchemy

# Create the shared database object
db = SQLAlchemy()

class Team(db.Model):
    """Represents a team in the tournament."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    seed = db.Column(db.Integer, nullable=True)
    region = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"<Team {self.name} (Seed {self.seed})>"

class Game(db.Model):
    """Represents a single game and its result/spread."""
    id = db.Column(db.Integer, primary_key=True)
    round = db.Column(db.String(20), nullable=False)
    team1_id = db.Column(db.Integer, db.ForeignKey("team.id"))
    team2_id = db.Column(db.Integer, db.ForeignKey("team.id"))
    spread = db.Column(db.Float, nullable=True)
    team1_score = db.Column(db.Integer, nullable=True)
    team2_score = db.Column(db.Integer, nullable=True)
    winner_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=True)

    def __repr__(self):
        return f"<Game Round {self.round}: {self.team1_id} vs {self.team2_id}>"

class Participant(db.Model):
    """Represents a bracket participant (owner)."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=True)

    def __repr__(self):
        return f"<Participant {self.name}>"

