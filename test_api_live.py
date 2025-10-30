#!/usr/bin/env python3
"""
Test script to verify Odds API and ESPN API are working.
This tests with CURRENT NCAA basketball games (regular season).

Usage:
    python test_api_live.py
"""

import os
import sys
from datetime import date, datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_odds_api():
    """Test The Odds API for NCAA basketball spreads."""
    print("=" * 60)
    print("Testing The Odds API (Spreads)")
    print("=" * 60)
    
    api_key = os.environ.get("ODDS_API_KEY", "")
    if not api_key:
        print("❌ No ODDS_API_KEY found in .env file!")
        return False
    
    print(f"✓ API Key found: {api_key[:8]}...{api_key[-4:]}")
    print(f"✓ Testing with sport: basketball_ncaab (NCAA Men's Basketball)")
    
    try:
        import httpx
        url = "https://api.the-odds-api.com/v4/sports/basketball_ncaab/odds"
        params = {
            "regions": "us",
            "markets": "spreads",
            "dateFormat": "iso",
            "oddsFormat": "american",
            "apiKey": api_key,
        }
        
        print(f"\n📡 Making request to: {url}")
        print(f"   Parameters: {', '.join(f'{k}={v}' for k, v in params.items() if k != 'apiKey')}")
        
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        
        print(f"\n✅ SUCCESS! Received {len(data)} games from API")
        
        if not data:
            print("\n⚠️  No games returned. This is normal if:")
            print("   - It's off-season")
            print("   - No games scheduled today/soon")
            print("   - Try during regular season (Nov-Mar)")
            return True
        
        # Show sample games
        print(f"\n📊 Sample Games (showing first 3):")
        print("-" * 60)
        for i, game in enumerate(data[:3], 1):
            home = game.get("home_team", "Unknown")
            away = game.get("away_team", "Unknown")
            commence = game.get("commence_time", "N/A")
            
            print(f"\n{i}. {away} @ {home}")
            print(f"   Tip-off: {commence}")
            
            # Try to find spread
            spread_found = False
            for book in game.get("bookmakers", [])[:1]:  # Just first bookmaker
                for market in book.get("markets", []):
                    if market.get("key") == "spreads":
                        print(f"   Bookmaker: {book.get('title', 'N/A')}")
                        for outcome in market.get("outcomes", []):
                            team = outcome.get("name", "")
                            point = outcome.get("point", 0)
                            if point:
                                print(f"   Spread: {team} {point:+.1f}")
                                spread_found = True
                        break
            
            if not spread_found:
                print(f"   Spread: Not available")
        
        # Check API usage
        remaining = resp.headers.get("x-requests-remaining")
        used = resp.headers.get("x-requests-used")
        if remaining:
            print(f"\n📈 API Usage: {used or '?'} used, {remaining} remaining")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_espn_scores():
    """Test ESPN API for NCAA basketball scores."""
    print("\n" + "=" * 60)
    print("Testing ESPN Scoreboard API (Scores)")
    print("=" * 60)
    
    try:
        import httpx
        
        # Use today's date in YYYYMMDD format
        today = datetime.now(timezone.utc)
        date_str = today.strftime("%Y%m%d")
        
        url = (
            "https://site.api.espn.com/apis/site/v2/sports/"
            "basketball/mens-college-basketball/scoreboard"
        )
        params = {"dates": date_str}
        
        print(f"📡 Making request to ESPN")
        print(f"   Date: {date_str} (today in UTC)")
        
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        
        events = data.get("events", [])
        print(f"\n✅ SUCCESS! Received {len(events)} games from ESPN")
        
        if not events:
            print("\n⚠️  No games today. Try during:")
            print("   - Regular season (Nov-Mar)")
            print("   - Conference tournaments (early March)")
            print("   - NCAA Tournament (mid-March to early April)")
            return True
        
        # Show sample games
        print(f"\n📊 Sample Games (showing first 3):")
        print("-" * 60)
        for i, event in enumerate(events[:3], 1):
            try:
                comp = event["competitions"][0]
                teams = comp["competitors"]
                home = next(t for t in teams if t["homeAway"] == "home")
                away = next(t for t in teams if t["homeAway"] == "away")
                status = comp["status"]["type"]["name"]
                
                home_name = home["team"].get("shortDisplayName") or home["team"]["displayName"]
                away_name = away["team"].get("shortDisplayName") or away["team"]["displayName"]
                home_score = home.get("score", "0")
                away_score = away.get("score", "0")
                
                print(f"\n{i}. {away_name} @ {home_name}")
                print(f"   Score: {away_name} {away_score}, {home_name} {home_score}")
                print(f"   Status: {status}")
                
            except Exception as e:
                print(f"\n{i}. Error parsing game: {e}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_provider_integration():
    """Test the actual provider modules."""
    print("\n" + "=" * 60)
    print("Testing Provider Integration")
    print("=" * 60)
    
    try:
        # Test odds provider
        from providers.odds_api import fetch_spreads_for_date
        
        today = date.today()
        print(f"\n📡 Testing odds_api.fetch_spreads_for_date({today})")
        
        api_key = os.environ.get("ODDS_API_KEY", "")
        spreads = fetch_spreads_for_date(today, api_key=api_key)
        
        print(f"✅ Received {len(spreads)} spread entries")
        
        if spreads:
            print("\nSample spread entry:")
            sample = spreads[0]
            print(f"  Home: {sample.get('home')}")
            print(f"  Away: {sample.get('away')}")
            print(f"  Favorite: {sample.get('favorite')}")
            print(f"  Spread: {sample.get('spread')}")
            print(f"  Tip-off: {sample.get('tip_iso')}")
        
        # Test ESPN provider
        from providers.espn_scores import fetch_scores_for_iso_date
        
        today_iso = today.isoformat()
        print(f"\n📡 Testing espn_scores.fetch_scores_for_iso_date({today_iso})")
        
        scores = fetch_scores_for_iso_date(today_iso)
        
        print(f"✅ Received {len(scores)} score entries")
        
        if scores:
            print("\nSample score entry:")
            sample = scores[0]
            print(f"  Home: {sample.get('home')}")
            print(f"  Away: {sample.get('away')}")
            print(f"  Score: {sample.get('home_score')} - {sample.get('away_score')}")
            print(f"  Status: {sample.get('status')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🏀 NCAA Basketball API Test Suite")
    print("=" * 60)
    print(f"Current Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)
    
    results = []
    
    # Test 1: Odds API
    results.append(("Odds API (Direct)", test_odds_api()))
    
    # Test 2: ESPN Scores API
    results.append(("ESPN Scores API (Direct)", test_espn_scores()))
    
    # Test 3: Provider Integration
    results.append(("Provider Integration", test_provider_integration()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(r for _, r in results)
    
    if all_passed:
        print("\n🎉 All tests passed! APIs are working correctly.")
        print("\n📝 Next Steps:")
        print("   1. During NCAA season, you'll see actual games")
        print("   2. Test the Flask CLI commands:")
        print("      flask get-spreads")
        print("      flask update-scores")
        print("   3. Try the admin interface at http://localhost:5000/admin")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")
        sys.exit(1)
