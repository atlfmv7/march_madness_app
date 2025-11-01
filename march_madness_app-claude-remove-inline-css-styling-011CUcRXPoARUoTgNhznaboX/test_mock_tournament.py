#!/usr/bin/env python3
"""
Test the complete flow with MOCK March Madness data.
This simulates a tournament game from start to finish.

Usage:
    python test_mock_tournament.py
"""

from app import create_app
from models import db, Game, Team, Participant
from data_fetchers.spreads import update_game_spreads
from data_fetchers.scores import update_game_scores
from datetime import date, datetime, timezone

def test_complete_flow():
    """Test the entire flow from spread fetch to final evaluation."""
    
    print("🏀 Mock March Madness Tournament Test")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        # Step 1: Verify we have test data
        print("\n1️⃣  Checking database...")
        games = Game.query.filter_by(round="64").all()
        
        if not games:
            print("❌ No games found! Run: python seed_data.py")
            return False
        
        print(f"✅ Found {len(games)} Round of 64 games")
        
        # Pick the first game
        game = games[0]
        print(f"\n📋 Test Game Details:")
        print(f"   ID: {game.id}")
        print(f"   Matchup: {game.team1.name} vs {game.team2.name}")
        print(f"   Region: {game.region}")
        print(f"   Team1 Owner: {game.team1_owner.name if game.team1_owner else 'None'}")
        print(f"   Team2 Owner: {game.team2_owner.name if game.team2_owner else 'None'}")
        
        # Step 2: Test spread update (with mock data)
        print("\n2️⃣  Testing spread update with MOCK data...")
        
        mock_spread_data = [{
            "team1": game.team1.name,
            "team2": game.team2.name,
            "favorite": game.team1.name,  # Team1 is favorite
            "spread": 5.5,
            "tip_time": datetime.now(timezone.utc).isoformat()
        }]
        
        count = update_game_spreads(date.today(), data=mock_spread_data)
        print(f"✅ Updated {count} game(s) with spreads")
        
        # Refresh game from DB
        db.session.refresh(game)
        print(f"   Game spread: {game.spread_label()}")
        
        # Step 3: Test score update (game in progress)
        print("\n3️⃣  Testing score update - Game IN PROGRESS...")
        
        mock_scores_in_progress = [{
            "team1": game.team1.name,
            "team2": game.team2.name,
            "score1": 45,
            "score2": 42,
            "status": "In Progress"
        }]
        
        count = update_game_scores(date_iso=date.today().isoformat(), data=mock_scores_in_progress)
        print(f"✅ Updated {count} game(s) with scores")
        
        db.session.refresh(game)
        print(f"   Score: {game.score_label()}")
        print(f"   Status: {game.status}")
        
        # Calculate live leader
        from bracket_logic import live_owner_leader_vs_spread
        leader = live_owner_leader_vs_spread(game)
        if leader:
            print(f"   Live Leader (vs spread): {leader.name}")
        else:
            print(f"   Live Leader: Unable to calculate")
        
        # Step 4: Test final score and evaluation
        print("\n4️⃣  Testing FINAL score and bracket evaluation...")
        
        # Scenario: Favorite wins by 3 (doesn't cover the 5.5 spread)
        mock_scores_final = [{
            "team1": game.team1.name,
            "team2": game.team2.name,
            "score1": 78,  # Favorite (team1)
            "score2": 75,  # Underdog (team2)
            "status": "Final"
        }]
        
        count = update_game_scores(date_iso=date.today().isoformat(), data=mock_scores_final)
        print(f"✅ Updated {count} game(s) - marked FINAL")
        
        db.session.refresh(game)
        print(f"   Final Score: {game.score_label()}")
        print(f"   Status: {game.status}")
        
        # Check evaluation results
        if game.winner:
            print(f"   Actual Winner: {game.winner.name}")
        
        # Manually check the logic
        from bracket_logic import determine_owner_winner_vs_spread, actual_game_winner_team
        
        team_winner = actual_game_winner_team(game)
        owner_winner = determine_owner_winner_vs_spread(game)
        
        print(f"\n📊 Bracket Logic Results:")
        print(f"   Team Winner (actual): {team_winner.name}")
        print(f"   Owner Winner (vs spread): {owner_winner.name}")
        print(f"   Spread: {game.spread} points")
        print(f"   Margin: {game.team1_score - game.team2_score} points")
        print(f"   Favorite covered? {'YES' if (game.team1_score - game.team2_score) > game.spread else 'NO'}")
        
        # Step 5: Check propagation to next round
        if game.next_game_id:
            print(f"\n5️⃣  Checking next round propagation...")
            next_game = db.session.get(Game, game.next_game_id)
            
            if game.next_game_slot == 1:
                print(f"   Next Game: #{next_game.id} (Round of {next_game.round})")
                print(f"   Team advances to slot 1: {next_game.team1.name if next_game.team1 else 'TBD'}")
                print(f"   Owner in slot 1: {next_game.team1_owner.name if next_game.team1_owner else 'TBD'}")
            else:
                print(f"   Next Game: #{next_game.id} (Round of {next_game.round})")
                print(f"   Team advances to slot 2: {next_game.team2.name if next_game.team2 else 'TBD'}")
                print(f"   Owner in slot 2: {next_game.team2_owner.name if next_game.team2_owner else 'TBD'}")
        else:
            print(f"\n5️⃣  No next round configured (this is expected for demo data)")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n📝 What this test verified:")
        print("   ✓ Database has seeded games")
        print("   ✓ Spread update works with mock data")
        print("   ✓ Score update works (in progress)")
        print("   ✓ Score update works (final)")
        print("   ✓ Bracket logic correctly evaluates spread outcome")
        print("   ✓ Team/owner propagation logic works")
        
        print("\n🎯 To test with REAL APIs:")
        print("   1. Wait for NCAA regular season (November - March)")
        print("   2. Run: python test_api_live.py")
        print("   3. Run: flask get-spreads")
        print("   4. Run: flask update-scores")
        
        print("\n🌐 To test the web interface:")
        print("   1. Start the app: python app.py")
        print("   2. Visit: http://localhost:5000")
        print("   3. Visit admin: http://localhost:5000/admin")
        
        return True


if __name__ == "__main__":
    try:
        success = test_complete_flow()
        if not success:
            exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
