#!/usr/bin/env python3
"""
Robust NCAA Tournament Bracket Fetcher

Fetches bracket from multiple sources with intelligent fallback:
1. ESPN API (primary)
2. Sports Reference / College Basketball Reference (fallback)
3. Manual CSV import (ultimate fallback)

Usage:
    # Fetch 2024 bracket (test with known data):
    python fetch_bracket.py --year 2024
    
    # Fetch 2025 bracket (after Selection Sunday):
    python fetch_bracket.py --year 2025
    
    # Import from CSV:
    python fetch_bracket.py --year 2025 --csv bracket_2025.csv
    
    # Dry run (don't save):
    python fetch_bracket.py --year 2024 --dry-run
"""

import sys
import argparse
import csv
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import httpx
from bs4 import BeautifulSoup

from app import create_app
from models import db, Team, Game


REGIONS = ["East", "West", "South", "Midwest"]

# Standard bracket structure: (round_name, number_of_games)
BRACKET_STRUCTURE = [
    ("64", 32),   # Round of 64
    ("32", 16),   # Round of 32
    ("16", 8),    # Sweet 16
    ("8", 4),     # Elite 8
    ("4", 2),     # Final Four
    ("2", 1),     # Championship
]


class BracketData:
    """Container for bracket data."""
    def __init__(self, year: int):
        self.year = year
        self.teams: List[Dict] = []  # List of {name, seed, region}
        self.matchups: List[Tuple] = []  # List of (team1_name, team2_name, round, region)
    
    def add_team(self, name: str, seed: int, region: str):
        """Add a team to the bracket."""
        self.teams.append({
            "name": name,
            "seed": seed,
            "region": region
        })
    
    def add_matchup(self, team1: str, team2: str, round_name: str, region: str = None):
        """Add a matchup between two teams."""
        self.matchups.append((team1, team2, round_name, region))
    
    def validate(self) -> Tuple[bool, str]:
        """Validate bracket has correct structure."""
        if len(self.teams) < 64:
            return False, f"Only {len(self.teams)} teams (need at least 64)"
        
        # Check each region has 16 teams
        for region in REGIONS:
            region_teams = [t for t in self.teams if t["region"] == region]
            if len(region_teams) != 16:
                return False, f"Region {region} has {len(region_teams)} teams (need 16)"
        
        return True, "Valid bracket structure"


def fetch_from_csv(csv_path: str, year: int) -> Optional[BracketData]:
    """Load bracket from CSV file."""
    print(f"📂 Loading bracket from: {csv_path}")
    
    try:
        bracket = BracketData(year)
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                bracket.add_team(
                    name=row['team_name'].strip(),
                    seed=int(row['seed']),
                    region=row['region'].strip()
                )
        
        print(f"✅ Loaded {len(bracket.teams)} teams")
        return bracket
        
    except FileNotFoundError:
        print(f"❌ File not found: {csv_path}")
        return None
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return None


def fetch_from_sports_reference(year: int) -> Optional[BracketData]:
    """
    Fetch bracket from Sports Reference / College Basketball Reference.
    URL: https://www.sports-reference.com/cbb/postseason/{year}-ncaa.html
    """
    print(f"📡 Fetching {year} bracket from Sports Reference...")
    
    url = f"https://www.sports-reference.com/cbb/postseason/{year}-ncaa.html"
    
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        bracket = BracketData(year)
        
        # Find the bracket table
        # Sports Reference has a bracket visualization with team data
        # This is a simplified parser - may need adjustments
        
        # Look for team rows in bracket regions
        for region in REGIONS:
            region_section = soup.find('div', {'id': f'bracket-{region.lower()}'})
            if not region_section:
                continue
            
            # Find all team links in this region
            team_links = region_section.find_all('a', href=lambda h: h and '/cbb/schools/' in h)
            
            for i, link in enumerate(team_links[:16], 1):  # Top 16 teams per region
                team_name = link.get_text().strip()
                # Try to find seed number near the team name
                seed_elem = link.find_previous('span', class_='seed')
                seed = int(seed_elem.get_text()) if seed_elem else i
                
                bracket.add_team(team_name, seed, region)
        
        if len(bracket.teams) > 0:
            print(f"✅ Fetched {len(bracket.teams)} teams from Sports Reference")
            return bracket
        else:
            print(f"⚠️  No teams found in Sports Reference data")
            return None
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print(f"⚠️  {year} bracket not available on Sports Reference yet")
        else:
            print(f"❌ HTTP Error {e.response.status_code}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error fetching from Sports Reference: {e}")
        return None


def build_bracket_from_data(bracket_data: BracketData, app, dry_run: bool = False) -> bool:
    """
    Build complete bracket structure in database from bracket data.
    Creates all teams and games with proper linking.
    """
    
    print(f"\n🏗️  Building bracket structure for {bracket_data.year}...")
    
    # Validate first
    valid, msg = bracket_data.validate()
    if not valid:
        print(f"❌ Invalid bracket: {msg}")
        return False
    
    print(f"✅ Bracket validation passed: {msg}")
    
    if dry_run:
        print(f"\n🔍 DRY RUN - Would create:")
        print(f"   {len(bracket_data.teams)} teams")
        print(f"   {sum(count for _, count in BRACKET_STRUCTURE)} games")
        _display_bracket_summary(bracket_data)
        return True
    
    with app.app_context():
        try:
            # Clear existing data for this year
            print(f"🗑️  Clearing existing {bracket_data.year} data...")
            db.session.query(Game).filter_by(year=bracket_data.year).delete()
            db.session.query(Team).filter_by(year=bracket_data.year).delete()
            db.session.commit()
            
            # Create teams
            print(f"📝 Creating {len(bracket_data.teams)} teams...")
            team_objects = {}
            
            for team_data in bracket_data.teams:
                team = Team(
                    name=team_data["name"],
                    seed=team_data["seed"],
                    region=team_data["region"],
                    year=bracket_data.year
                )
                db.session.add(team)
                team_objects[team_data["name"]] = team
            
            db.session.flush()  # Assign IDs
            
            # Create games with proper structure
            print(f"🎮 Creating games and linking bracket...")
            games_by_round = {}
            
            # Create all game shells first
            for round_name, count in BRACKET_STRUCTURE:
                games_by_round[round_name] = []
                
                for i in range(count):
                    # Determine region for regional rounds (64, 32, 16, 8)
                    # Each region has its own path until Final Four
                    region = None
                    if round_name in ["64", "32", "16", "8"]:
                        # Distribute games evenly across regions
                        region = REGIONS[i % len(REGIONS)]
                    
                    game = Game(
                        round=round_name,
                        region=region,
                        year=bracket_data.year,
                        status="Scheduled"
                    )
                    db.session.add(game)
                    games_by_round[round_name].append(game)
            
            db.session.flush()  # Assign game IDs
            
            # Link games: each game points to next round game
            print(f"🔗 Linking games for bracket progression...")
            _link_bracket_games(games_by_round)
            
            # Assign teams to Round of 64 based on standard seeding
            print(f"👥 Assigning teams to first round matchups...")
            _assign_teams_to_first_round(games_by_round["64"], team_objects, bracket_data.year)
            
            db.session.commit()
            
            print(f"✅ Successfully created bracket in database!")
            _display_bracket_summary(bracket_data)
            
            return True
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False


def _link_bracket_games(games_by_round: Dict[str, List[Game]]):
    """
    Link games so winners advance to next round.
    Standard NCAA bracket: 32→16→8→4→2→1
    
    For Round of 64 → 32: Games must be linked within regions
    For Round of 32 → 16: Games must be linked within regions
    For Round of 16 and beyond: Games link across regions
    """
    # Round of 64 → Round of 32 (within regions)
    r64_games = games_by_round["64"]
    r32_games = games_by_round["32"]
    
    # Group by region for proper linking
    for region in REGIONS:
        region_r64 = [g for g in r64_games if g.region == region]
        region_r32 = [g for g in r32_games if g.region == region]
        
        # Sort by ID for consistency
        region_r64.sort(key=lambda g: g.id)
        region_r32.sort(key=lambda g: g.id)
        
        # Link: 2 R64 games → 1 R32 game
        for i, game in enumerate(region_r64):
            next_game_index = i // 2
            if next_game_index < len(region_r32):
                game.next_game_id = region_r32[next_game_index].id
                game.next_game_slot = 1 if i % 2 == 0 else 2
    
    # Round of 32 → Round of 16 (within regions, advances to Sweet 16)
    r16_games = games_by_round["16"]
    
    for region in REGIONS:
        region_r32 = [g for g in r32_games if g.region == region]
        region_r16 = [g for g in r16_games if g.region == region]
        
        region_r32.sort(key=lambda g: g.id)
        region_r16.sort(key=lambda g: g.id)
        
        for i, game in enumerate(region_r32):
            next_game_index = i // 2
            if next_game_index < len(region_r16):
                game.next_game_id = region_r16[next_game_index].id
                game.next_game_slot = 1 if i % 2 == 0 else 2
    
    # Round of 16 → Elite 8 (within regions)
    r8_games = games_by_round["8"]
    
    for region in REGIONS:
        region_r16 = [g for g in r16_games if g.region == region]
        region_r8 = [g for g in r8_games if g.region == region]
        
        region_r16.sort(key=lambda g: g.id)
        region_r8.sort(key=lambda g: g.id)
        
        for i, game in enumerate(region_r16):
            next_game_index = i // 2
            if next_game_index < len(region_r8):
                game.next_game_id = region_r8[next_game_index].id
                game.next_game_slot = 1 if i % 2 == 0 else 2
    
    # Elite 8 → Final Four (cross-region)
    r4_games = games_by_round["4"]
    r8_games_sorted = sorted(r8_games, key=lambda g: g.id)
    
    for i, game in enumerate(r8_games_sorted):
        next_game_index = i // 2
        if next_game_index < len(r4_games):
            game.next_game_id = r4_games[next_game_index].id
            game.next_game_slot = 1 if i % 2 == 0 else 2
    
    # Final Four → Championship
    r2_games = games_by_round["2"]
    
    for i, game in enumerate(r4_games):
        if len(r2_games) > 0:
            game.next_game_id = r2_games[0].id
            game.next_game_slot = 1 if i == 0 else 2


def _assign_teams_to_first_round(games: List[Game], team_objects: Dict[str, Team], year: int):
    """
    Assign teams to Round of 64 based on standard NCAA seeding.
    Standard matchups: 1v16, 8v9, 5v12, 4v13, 6v11, 3v14, 7v10, 2v15
    """
    # Standard NCAA bracket matchups by seed
    matchups = [
        (1, 16), (8, 9), (5, 12), (4, 13),
        (6, 11), (3, 14), (7, 10), (2, 15)
    ]
    
    # Assign for each region
    for region_idx, region in enumerate(REGIONS):
        region_teams = {
            t.seed: t for t in team_objects.values()
            if t.region == region
        }
        
        # Get the 8 games for this region (each region has 8 first-round games)
        region_games = [g for g in games if g.region == region]
        region_games.sort(key=lambda g: g.id)  # Consistent ordering
        
        for game_idx, (seed1, seed2) in enumerate(matchups):
            if game_idx < len(region_games):
                game = region_games[game_idx]
                
                team1 = region_teams.get(seed1)
                team2 = region_teams.get(seed2)
                
                if team1 and team2:
                    game.team1_id = team1.id
                    game.team2_id = team2.id
                    game.team1_owner_id = team1.initial_owner_id
                    game.team2_owner_id = team2.initial_owner_id


def _display_bracket_summary(bracket_data: BracketData):
    """Display a summary of the loaded bracket."""
    print(f"\n" + "="*70)
    print(f"📊 BRACKET SUMMARY FOR {bracket_data.year}")
    print("="*70)
    
    # Teams by region
    print(f"\n🏀 Teams by Region:")
    for region in REGIONS:
        region_teams = [t for t in bracket_data.teams if t["region"] == region]
        print(f"\n   {region} Region ({len(region_teams)} teams):")
        
        # Show all 16 seeds
        sorted_teams = sorted(region_teams, key=lambda t: t["seed"])
        for team in sorted_teams:
            print(f"      #{team['seed']:2d} {team['name']}")
    
    print("\n" + "="*70)
    print(f"✅ Total: {len(bracket_data.teams)} teams across 4 regions")
    print("="*70)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch NCAA Tournament bracket and populate database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with 2024 bracket from Sports Reference:
  python fetch_bracket.py --year 2024
  
  # Fetch 2025 bracket after Selection Sunday:
  python fetch_bracket.py --year 2025
  
  # Import from CSV file:
  python fetch_bracket.py --year 2025 --csv bracket_2025.csv
  
  # Dry run (preview without saving):
  python fetch_bracket.py --year 2024 --dry-run

CSV Format:
  team_name,seed,region
  Duke,1,East
  Vermont,16,East
  ...
        """
    )
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now(timezone.utc).year,
        help="Tournament year (default: current year)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't save to database, just show what would be done"
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Load from CSV file instead of API (see bracket_template_2024.csv for format)"
    )
    
    args = parser.parse_args()
    
    print(f"\n🏀 NCAA Tournament Bracket Fetcher")
    print(f"📅 Year: {args.year}")
    print(f"{'🔍 DRY RUN MODE' if args.dry_run else '💾 LIVE MODE'}\n")
    
    # Fetch bracket data
    bracket_data = None
    
    if args.csv:
        # Option 1: Load from CSV
        bracket_data = fetch_from_csv(args.csv, args.year)
    else:
        # Option 2: Fetch from Sports Reference
        bracket_data = fetch_from_sports_reference(args.year)
        
        if not bracket_data:
            print("\n" + "="*70)
            print("❌ Could not fetch bracket from any source")
            print("="*70)
            print("\n💡 What to do:")
            print(f"   1. Wait until after Selection Sunday ({args.year})")
            print(f"   2. Use CSV import:")
            print(f"      python fetch_bracket.py --year {args.year} --csv bracket_{args.year}.csv")
            print(f"   3. Use the template: bracket_template_2024.csv")
            print(f"   4. Or use the upcoming admin interface to manually enter teams")
            sys.exit(1)
    
    if not bracket_data:
        print(f"\n❌ No bracket data available")
        sys.exit(1)
    
    # Build bracket in database
    app = create_app()
    success = build_bracket_from_data(bracket_data, app, dry_run=args.dry_run)
    
    if success and not args.dry_run:
        print(f"\n" + "="*70)
        print(f"✅ SUCCESS! {args.year} bracket is ready")
        print("="*70)
        print(f"\n🎯 Next steps:")
        print(f"   1. Start the app: python app.py")
        print(f"   2. Visit: http://localhost:5000")
        print(f"   3. Use admin to assign teams to your 16 participants")
        print(f"   4. Set up cron jobs before first game")
        print()
    elif success and args.dry_run:
        print(f"\n🔍 Dry run complete - no changes made to database")
    else:
        print(f"\n❌ Failed to build bracket")
        sys.exit(1)


if __name__ == "__main__":
    main()
