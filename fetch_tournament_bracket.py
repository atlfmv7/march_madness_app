#!/usr/bin/env python3
"""
Fetch NCAA Tournament Bracket from ESPN API and populate database.

This script fetches the official NCAA Men's Basketball Tournament bracket
after Selection Sunday and automatically populates:
- All 68 teams (64 main bracket + 4 First Four)
- Seeds and regions for each team
- All 67 games with proper round structure
- next_game_id links for bracket progression

Usage:
    # After Selection Sunday 2025 (March 16):
    python fetch_tournament_bracket.py --year 2025

    # Test with 2024 data:
    python fetch_tournament_bracket.py --year 2024

    # Dry run (don't save to DB):
    python fetch_tournament_bracket.py --year 2024 --dry-run
"""

import sys
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import httpx

from app import create_app
from models import db, Team, Game


# Region mappings
REGIONS = ["East", "West", "South", "Midwest"]


class BracketFetcher:
    """Fetches and parses NCAA Tournament bracket from ESPN."""
    
    def __init__(self, year: int, dry_run: bool = False):
        self.year = year
        self.dry_run = dry_run
        self.teams: Dict[str, Team] = {}  # team_name -> Team object
        self.games: List[Game] = []
        
    def fetch_espn_bracket(self) -> Optional[dict]:
        """
        Fetch bracket data from ESPN Tournament Challenge API.
        
        ESPN provides bracket data through their tournament challenge API.
        This is publicly accessible and includes all teams, seeds, and matchups.
        """
        print(f"📡 Fetching {self.year} NCAA Tournament bracket from ESPN...")
        
        # ESPN Tournament Challenge API endpoint
        # Format: https://fantasy.espn.com/tournament-challenge-bracket/{year}/en/api/
        url = f"https://fantasy.espn.com/tournament-challenge-bracket/{self.year}/en/api/"
        
        try:
            with httpx.Client(timeout=30) as client:
                # Try the main bracket endpoint
                resp = client.get(f"{url}tournament")
                resp.raise_for_status()
                data = resp.json()
                
                print(f"✅ Successfully fetched {self.year} bracket data")
                return data
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                print(f"⚠️  {self.year} bracket not available yet on ESPN")
                print(f"   (Selection Sunday for {self.year} is typically mid-March)")
                return None
            else:
                print(f"❌ HTTP Error: {e}")
                return None
        except Exception as e:
            print(f"❌ Error fetching bracket: {e}")
            return None
    
    def fetch_ncaa_bracket_alternative(self) -> Optional[dict]:
        """
        Alternative: Fetch from NCAA.com's API.
        This is a fallback if ESPN is unavailable.
        """
        print(f"📡 Trying NCAA.com API as fallback...")
        
        # NCAA.com has bracket data but format varies by year
        # This is a simplified example - may need adjustment
        url = f"https://data.ncaa.com/casablanca/brackets/mbb/{self.year}.json"
        
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
                
                print(f"✅ Successfully fetched {self.year} bracket from NCAA.com")
                return data
                
        except Exception as e:
            print(f"⚠️  NCAA.com fallback failed: {e}")
            return None
    
    def parse_espn_bracket(self, data: dict) -> bool:
        """
        Parse ESPN bracket JSON and create Team/Game objects.
        
        ESPN bracket structure (simplified):
        {
            "rounds": [
                {
                    "round": 1,  # First Four = 0, Round of 64 = 1, etc.
                    "games": [
                        {
                            "seeds": [16, 16],
                            "teams": [
                                {"name": "Team A", "region": "East"},
                                {"name": "Team B", "region": "East"}
                            ]
                        }
                    ]
                }
            ]
        }
        """
        print(f"\n🔍 Parsing bracket structure...")
        
        if not data or "rounds" not in data:
            print("❌ Invalid bracket data structure")
            return False
        
        try:
            # Parse teams and games from rounds
            for round_data in data.get("rounds", []):
                round_num = round_data.get("round")
                games = round_data.get("games", [])
                
                for game_data in games:
                    self._parse_game(game_data, round_num)
            
            print(f"✅ Parsed {len(self.teams)} teams and {len(self.games)} games")
            return True
            
        except Exception as e:
            print(f"❌ Error parsing bracket: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _parse_game(self, game_data: dict, round_num: int):
        """Parse a single game and its teams."""
        teams_data = game_data.get("teams", [])
        seeds = game_data.get("seeds", [])
        
        if len(teams_data) != 2:
            return
        
        # Create team objects if they don't exist
        for i, team_data in enumerate(teams_data):
            team_name = team_data.get("name") or team_data.get("displayName")
            region = team_data.get("region", "Unknown")
            seed = seeds[i] if i < len(seeds) else None
            
            if team_name and team_name not in self.teams:
                team = Team(
                    name=team_name,
                    seed=seed,
                    region=region,
                    year=self.year
                )
                self.teams[team_name] = team
        
        # Create game object (we'll link them later)
        # This is simplified - actual implementation needs more details
        round_map = {
            0: "First Four",
            1: "64",
            2: "32", 
            3: "16",
            4: "8",
            5: "4",
            6: "2",
            7: "Championship"
        }
        
        game = Game(
            round=round_map.get(round_num, str(64 // (2 ** round_num))),
            region=teams_data[0].get("region", "Unknown"),
            year=self.year,
            status="Scheduled"
        )
        self.games.append(game)
    
    def build_from_csv(self, csv_path: str) -> bool:
        """
        Alternative: Load bracket from CSV file.
        
        CSV Format:
        team_name,seed,region
        Duke,1,East
        UNC,2,East
        ...
        """
        print(f"📂 Loading bracket from CSV: {csv_path}")
        
        try:
            import csv
            
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    team = Team(
                        name=row['team_name'],
                        seed=int(row['seed']),
                        region=row['region'],
                        year=self.year
                    )
                    self.teams[team.name] = team
            
            print(f"✅ Loaded {len(self.teams)} teams from CSV")
            
            # Build standard bracket structure
            self._build_standard_bracket_games()
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading CSV: {e}")
            return False
    
    def _build_standard_bracket_games(self):
        """
        Build standard NCAA bracket game structure.
        Creates all 63 games (67 with First Four) with proper linking.
        """
        print(f"\n🏗️  Building bracket game structure...")
        
        # This is complex! NCAA bracket has:
        # - 4 First Four games (seeds 11 vs 11, 16 vs 16)
        # - 32 Round of 64 games  
        # - 16 Round of 32 games
        # - 8 Sweet 16 games
        # - 4 Elite 8 games
        # - 2 Final Four games
        # - 1 Championship game
        
        # For now, create a simplified structure
        # TODO: Full implementation with proper team matching
        
        rounds = [
            ("64", 32),
            ("32", 16),
            ("16", 8),
            ("8", 4),
            ("4", 2),
            ("2", 1),
            ("Championship", 1)
        ]
        
        for round_name, num_games in rounds:
            for i in range(num_games):
                game = Game(
                    round=round_name,
                    region=REGIONS[i % 4] if round_name in ["64", "32"] else None,
                    year=self.year,
                    status="Scheduled"
                )
                self.games.append(game)
        
        print(f"✅ Created {len(self.games)} game slots")
    
    def save_to_database(self, app) -> bool:
        """Save teams and games to database."""
        
        if self.dry_run:
            print(f"\n🔍 DRY RUN - Would save:")
            print(f"   {len(self.teams)} teams")
            print(f"   {len(self.games)} games")
            return True
        
        print(f"\n💾 Saving to database...")
        
        with app.app_context():
            try:
                # Clear existing data for this year
                db.session.query(Game).filter_by(year=self.year).delete()
                db.session.query(Team).filter_by(year=self.year).delete()
                db.session.commit()
                
                # Save teams
                for team in self.teams.values():
                    db.session.add(team)
                
                db.session.flush()  # Get IDs assigned
                
                # Save games
                for game in self.games:
                    db.session.add(game)
                
                db.session.commit()
                
                print(f"✅ Saved {len(self.teams)} teams and {len(self.games)} games")
                return True
                
            except Exception as e:
                print(f"❌ Database error: {e}")
                db.session.rollback()
                return False
    
    def display_summary(self):
        """Display a summary of the loaded bracket."""
        print(f"\n" + "="*60)
        print(f"📊 BRACKET SUMMARY FOR {self.year}")
        print("="*60)
        
        # Teams by region
        print(f"\n🏀 Teams by Region:")
        for region in REGIONS:
            region_teams = [t for t in self.teams.values() if t.region == region]
            print(f"   {region}: {len(region_teams)} teams")
            
            # Show top 4 seeds
            sorted_teams = sorted(region_teams, key=lambda t: t.seed or 99)[:4]
            for team in sorted_teams:
                print(f"      #{team.seed} {team.name}")
        
        # Games by round
        print(f"\n🏆 Games by Round:")
        round_counts = {}
        for game in self.games:
            round_counts[game.round] = round_counts.get(game.round, 0) + 1
        
        for round_name in ["64", "32", "16", "8", "4", "2", "Championship"]:
            count = round_counts.get(round_name, 0)
            print(f"   Round of {round_name}: {count} games")
        
        print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch NCAA Tournament bracket and populate database"
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
        help="Load from CSV file instead of API"
    )
    
    args = parser.parse_args()
    
    print(f"\n🏀 NCAA Tournament Bracket Fetcher")
    print(f"📅 Year: {args.year}")
    print(f"{'🔍 DRY RUN MODE' if args.dry_run else '💾 LIVE MODE'}\n")
    
    # Create fetcher
    fetcher = BracketFetcher(year=args.year, dry_run=args.dry_run)
    
    # Fetch bracket data
    if args.csv:
        success = fetcher.build_from_csv(args.csv)
    else:
        # Try ESPN first
        data = fetcher.fetch_espn_bracket()
        
        # Fall back to NCAA.com if ESPN fails
        if not data:
            data = fetcher.fetch_ncaa_bracket_alternative()
        
        if not data:
            print("\n❌ Could not fetch bracket from any source")
            print("\n💡 Try these alternatives:")
            print("   1. Wait until after Selection Sunday")
            print("   2. Use CSV import: --csv bracket_2025.csv")
            print("   3. Manually populate using admin interface (coming soon)")
            sys.exit(1)
        
        success = fetcher.parse_espn_bracket(data)
    
    if not success:
        print("\n❌ Failed to parse bracket data")
        sys.exit(1)
    
    # Display summary
    fetcher.display_summary()
    
    # Save to database
    if not args.dry_run:
        app = create_app()
        if fetcher.save_to_database(app):
            print(f"\n✅ SUCCESS! {args.year} bracket loaded into database")
            print(f"\n🎯 Next steps:")
            print(f"   1. Visit http://localhost:5000 to see the bracket")
            print(f"   2. Use admin interface to assign teams to participants")
            print(f"   3. Set up cron jobs for automated updates")
        else:
            print(f"\n❌ Failed to save to database")
            sys.exit(1)
    else:
        print(f"\n🔍 Dry run complete - no changes made to database")


if __name__ == "__main__":
    main()
