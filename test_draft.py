#!/usr/bin/env python3
"""
Test the draft/team assignment system.
Shows current assignments and validates the draft.
"""

from app import create_app
from models import db, Participant, Team
from collections import defaultdict

def test_draft():
    """Display current draft status and validate."""
    app = create_app()
    
    with app.app_context():
        # Get participants
        participants = Participant.query.order_by(Participant.name.asc()).all()
        
        if len(participants) != 16:
            print(f"⚠️  Warning: Have {len(participants)} participants (need exactly 16)")
            print(f"   Run: python test_participants.py to add participants\n")
        
        # Get teams for most recent year
        years = [y for (y,) in db.session.query(Team.year).distinct().order_by(Team.year.desc()).all()]
        if not years:
            print("❌ No teams found in database!")
            print("   Run: python fetch_bracket.py --year 2024 --csv bracket_2024.csv\n")
            return
        
        year = years[0]
        teams = Team.query.filter_by(year=year).all()
        
        print(f"\n🏀 Draft Status for {year}")
        print("="*70)
        
        # Count assignments
        assigned_teams = [t for t in teams if t.initial_owner_id]
        unassigned_teams = [t for t in teams if not t.initial_owner_id]
        
        print(f"\n📊 Overall Status:")
        print(f"   Total teams: {len(teams)}")
        print(f"   Assigned: {len(assigned_teams)}")
        print(f"   Unassigned: {len(unassigned_teams)}")
        
        if len(assigned_teams) == 64:
            print(f"   ✅ All teams assigned!")
        elif len(assigned_teams) > 0:
            print(f"   ⚠️  Draft in progress ({len(assigned_teams)}/64)")
        else:
            print(f"   ⏳ Draft not started")
        
        # Show assignments by participant
        print(f"\n👥 Assignments by Participant:")
        print("-"*70)
        
        for participant in participants:
            owned_teams = Team.query.filter_by(
                year=year,
                initial_owner_id=participant.id
            ).order_by(Team.region.asc(), Team.seed.asc()).all()
            
            # Count by region
            regions = defaultdict(list)
            for team in owned_teams:
                regions[team.region].append(f"#{team.seed} {team.name}")
            
            # Status
            if len(owned_teams) == 4 and all(len(v) == 1 for v in regions.values()):
                status = "✅"
            elif len(owned_teams) > 0:
                status = "⚠️ "
            else:
                status = "⏳"
            
            print(f"\n{status} {participant.name} ({len(owned_teams)}/4 teams):")
            
            for region in ["East", "West", "South", "Midwest"]:
                team_list = regions.get(region, [])
                if team_list:
                    print(f"      {region:8s}: {team_list[0]}")
                else:
                    print(f"      {region:8s}: —")
        
        # Validation
        print(f"\n" + "="*70)
        print(f"🔍 Validation:")
        
        all_valid = True
        
        # Check each participant has exactly 4 teams (one per region)
        for participant in participants:
            owned_teams = Team.query.filter_by(
                year=year,
                initial_owner_id=participant.id
            ).all()
            
            regions = defaultdict(int)
            for team in owned_teams:
                regions[team.region] += 1
            
            if len(owned_teams) != 4:
                print(f"   ❌ {participant.name} has {len(owned_teams)} teams (need 4)")
                all_valid = False
            elif not all(regions.get(r, 0) == 1 for r in ["East", "West", "South", "Midwest"]):
                print(f"   ❌ {participant.name} doesn't have one team per region")
                all_valid = False
        
        # Check all teams are assigned
        if len(unassigned_teams) > 0:
            print(f"   ❌ {len(unassigned_teams)} teams unassigned")
            all_valid = False
        
        if all_valid and len(participants) == 16:
            print(f"   ✅ Draft is valid and complete!")
            print(f"\n🎉 Ready for tournament!")
        elif len(assigned_teams) == 0:
            print(f"   ⏳ Draft not started yet")
            print(f"\n💡 Visit: http://localhost:5000/admin/draft")
        else:
            print(f"   ⚠️  Draft incomplete or has issues")
        
        print("="*70 + "\n")


if __name__ == "__main__":
    test_draft()
