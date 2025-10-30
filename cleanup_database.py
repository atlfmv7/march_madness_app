#!/usr/bin/env python3
"""
Cleanup script to fix database issues.
Removes duplicate participants and old test data.
"""

from app import create_app
from models import db, Participant, Team, Game

def cleanup():
    """Clean up database."""
    app = create_app()
    
    with app.app_context():
        print("🧹 Cleaning up database...")
        
        # 1. Remove old test participants
        print("\n1️⃣ Removing old test participants...")
        old_participants = Participant.query.filter(
            Participant.name.in_(['Owner2024', 'Owner2025', 'Participant 1', 'Participant 2', 
                                   'Participant 3', 'Participant 4', 'Participant 5', 
                                   'Participant 6', 'Participant 7', 'Participant 8'])
        ).all()
        
        for p in old_participants:
            print(f"   Deleting: {p.name}")
            db.session.delete(p)
        
        db.session.commit()
        
        # 2. Remove 2025 test data (only 2 teams)
        print("\n2️⃣ Removing incomplete 2025 data...")
        teams_2025 = Team.query.filter_by(year=2025).all()
        games_2025 = Game.query.filter_by(year=2025).all()
        
        if len(teams_2025) < 64:
            print(f"   Deleting {len(games_2025)} games from 2025")
            print(f"   Deleting {len(teams_2025)} teams from 2025")
            
            Game.query.filter_by(year=2025).delete()
            Team.query.filter_by(year=2025).delete()
            db.session.commit()
        
        # 3. Show current status
        print("\n✅ Cleanup complete!")
        print("\n📊 Current Status:")
        
        participants = Participant.query.all()
        print(f"   Participants: {len(participants)}")
        for i, p in enumerate(participants, 1):
            print(f"      {i:2d}. {p.name}")
        
        years = db.session.query(Team.year).distinct().all()
        for (year,) in years:
            team_count = Team.query.filter_by(year=year).count()
            print(f"   Teams in {year}: {team_count}")
        
        if len(participants) == 16:
            print(f"\n🎉 Perfect! You have exactly 16 participants.")
        else:
            print(f"\n⚠️  You have {len(participants)} participants.")
            if len(participants) < 16:
                print(f"   Need {16 - len(participants)} more.")
            else:
                print(f"   Need to remove {len(participants) - 16}.")
                print(f"   Visit: http://localhost:5000/admin/participants")


if __name__ == "__main__":
    cleanup()
