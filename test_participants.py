#!/usr/bin/env python3
"""
Test the participant management system.
Adds sample participants for testing.
"""

from app import create_app
from models import db, Participant

def test_participant_management():
    """Add some test participants."""
    app = create_app()
    
    with app.app_context():
        # Clear existing test participants
        print("🗑️  Clearing existing participants...")
        db.session.query(Participant).filter(
            Participant.name.like("Test %")
        ).delete()
        db.session.commit()
        
        # Add some test participants
        test_names = [
            "Ryan", "Alice", "Bob", "Carol", "David", 
            "Emma", "Frank", "Grace", "Henry", "Ivy",
            "Jack", "Kate", "Liam", "Maya", "Nathan", "Olivia"
        ]
        
        print(f"➕ Adding {len(test_names)} test participants...")
        
        for name in test_names:
            # Check if already exists
            existing = Participant.query.filter_by(name=name).first()
            if not existing:
                participant = Participant(
                    name=name,
                    email=f"{name.lower()}@example.com"
                )
                db.session.add(participant)
        
        db.session.commit()
        
        # Show results
        all_participants = Participant.query.order_by(Participant.name).all()
        print(f"\n✅ Current participants ({len(all_participants)}):")
        for i, p in enumerate(all_participants, 1):
            print(f"   {i:2d}. {p.name} ({p.email or 'no email'})")
        
        if len(all_participants) == 16:
            print(f"\n🎉 Perfect! You have exactly 16 participants.")
        elif len(all_participants) < 16:
            print(f"\n⚠️  You have {len(all_participants)} participants. Need {16 - len(all_participants)} more.")
        else:
            print(f"\n❌ You have {len(all_participants)} participants. Need exactly 16.")
        
        print(f"\n🌐 Visit http://localhost:5000/admin/participants to manage them!")


if __name__ == "__main__":
    test_participant_management()
