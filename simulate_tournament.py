#!/usr/bin/env python3
"""
Game Simulator for March Madness Madness
Simulates games finishing with realistic scores to test bracket progression.

Usage:
    python simulate_tournament.py --game <game_id>     # Simulate one game
    python simulate_tournament.py --round 64           # Simulate Round of 64
    python simulate_tournament.py --round 32           # Simulate Round of 32
    python simulate_tournament.py --all                # Simulate entire tournament
    python simulate_tournament.py --interactive        # Interactive mode
"""

import random
import time
from app import create_app
from models import db, Game, Team
from bracket_logic import evaluate_and_finalize_game


def generate_realistic_score():
    """Generate a realistic college basketball score (50-95 range)."""
    # Most college games are in 60-85 range
    return random.randint(55, 90)


def simulate_game(game_id, verbose=True):
    """
    Simulate a single game with realistic scores.
    
    Args:
        game_id: ID of the game to simulate
        verbose: Whether to print details
    
    Returns:
        tuple: (team_winner, owner_winner) or None if game not found
    """
    game = db.session.get(Game, game_id)
    
    if not game:
        if verbose:
            print(f"❌ Game {game_id} not found")
        return None
    
    if game.status == "Final":
        if verbose:
            print(f"⚠️  Game {game_id} is already Final")
        return None
    
    if not game.team1 or not game.team2:
        if verbose:
            print(f"⚠️  Game {game_id} doesn't have both teams yet")
        return None
    
    # CRITICAL: Set game owner fields NOW (before playing the game)
    # This preserves who owns the teams at the TIME this game is played
    if game.team1_owner_id is None:
        game.team1_owner_id = game.team1.current_owner_id
    if game.team2_owner_id is None:
        game.team2_owner_id = game.team2.current_owner_id
    db.session.commit()
    
    # Set a realistic spread if not already set
    if not game.spread or not game.spread_favorite_team_id:
        # Favor lower seed
        if game.team1.seed < game.team2.seed:
            # Team 1 is favorite
            seed_diff = game.team2.seed - game.team1.seed
            game.spread = round(min(seed_diff * 1.5, 15.0), 1)  # Max 15 point spread
            game.spread_favorite_team_id = game.team1.id
        elif game.team2.seed < game.team1.seed:
            # Team 2 is favorite
            seed_diff = game.team1.seed - game.team2.seed
            game.spread = round(min(seed_diff * 1.5, 15.0), 1)
            game.spread_favorite_team_id = game.team2.id
        else:
            # Equal seeds (rare), make it a pick'em
            game.spread = 0.0
            game.spread_favorite_team_id = game.team1.id
        
        db.session.commit()
        
        if verbose:
            fav = game.team1 if game.spread_favorite_team_id == game.team1.id else game.team2
            print(f"🎯 Set spread: {fav.name} -{game.spread}")
    
    # Generate scores
    score1 = generate_realistic_score()
    score2 = generate_realistic_score()
    
    # Ensure scores aren't tied
    while score1 == score2:
        score2 = generate_realistic_score()
    
    # Slightly favor lower seeds (upsets happen but less frequently)
    if game.team1.seed < game.team2.seed:
        # Team 1 is favored, give them a 65% chance to win
        if random.random() > 0.35:
            if score2 > score1:
                score1, score2 = score2, score1
    elif game.team2.seed < game.team1.seed:
        # Team 2 is favored
        if random.random() > 0.35:
            if score1 > score2:
                score1, score2 = score2, score1
    
    # Set scores and mark final
    game.team1_score = score1
    game.team2_score = score2
    game.status = "Final"
    db.session.commit()
    
    # Evaluate spread and advance winner
    team_winner, owner_winner = evaluate_and_finalize_game(game.id)
    
    if verbose:
        winner_seed = team_winner.seed
        loser = game.team2 if team_winner.id == game.team1.id else game.team1
        loser_seed = loser.seed
        
        upset = ""
        if winner_seed > loser_seed:
            upset = " 🎉 UPSET!"
        
        print(f"✅ Game {game_id}: {game.team1.name} {score1} - {score2} {game.team2.name}{upset}")
        print(f"   Winner: {team_winner.name} (Seed {winner_seed})")
        print(f"   Owner Winner (vs spread): {owner_winner.name if owner_winner else 'Unknown'}")
    
    return team_winner, owner_winner


def simulate_round(round_number, year=2024, verbose=True):
    """
    Simulate all games in a specific round.
    
    Args:
        round_number: Round to simulate (64, 32, 16, 8, 4, 2)
        year: Tournament year
        verbose: Whether to print details
    
    Returns:
        int: Number of games simulated
    """
    games = (
        Game.query
        .filter_by(year=year, round=str(round_number), status="Scheduled")
        .all()
    )
    
    if not games:
        if verbose:
            print(f"\n⚠️  No scheduled games found in Round of {round_number}")
        return 0
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"🏀 SIMULATING ROUND OF {round_number} ({len(games)} games)")
        print(f"{'='*70}\n")
    
    count = 0
    upsets = 0
    
    for game in games:
        if game.team1 and game.team2:
            result = simulate_game(game.id, verbose=verbose)
            if result:
                count += 1
                team_winner, _ = result
                # Count upsets (higher seed wins)
                if game.team1.seed > game.team2.seed and team_winner.id == game.team1.id:
                    upsets += 1
                elif game.team2.seed > game.team1.seed and team_winner.id == game.team2.id:
                    upsets += 1
            
            if verbose:
                time.sleep(0.3)  # Slight delay for readability
        else:
            if verbose:
                print(f"⏭️  Skipping game {game.id} - teams not set yet")
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"📊 ROUND OF {round_number} COMPLETE")
        print(f"   Games Simulated: {count}")
        print(f"   Upsets: {upsets}")
        print(f"{'='*70}\n")
    
    return count


def simulate_tournament(year=2024, verbose=True):
    """
    Simulate the entire tournament from start to finish.
    
    Args:
        year: Tournament year
        verbose: Whether to print details
    
    Returns:
        dict: Tournament summary statistics
    """
    if verbose:
        print(f"\n🏆 SIMULATING ENTIRE {year} TOURNAMENT 🏆\n")
    
    rounds = [64, 32, 16, 8, 4, 2]
    stats = {
        'total_games': 0,
        'rounds_completed': [],
        'champion': None
    }
    
    for round_num in rounds:
        count = simulate_round(round_num, year=year, verbose=verbose)
        
        if count > 0:
            stats['total_games'] += count
            stats['rounds_completed'].append(round_num)
            
            if verbose and round_num < 2:
                input(f"\n⏸️  Press Enter to continue to Round of {rounds[rounds.index(round_num) + 1]}...")
        else:
            if verbose:
                print(f"⚠️  Stopped at Round of {round_num} (no games available)")
            break
    
    # Check for champion
    championship_game = (
        Game.query
        .filter_by(year=year, round="2", status="Final")
        .first()
    )
    
    if championship_game and championship_game.winner_id:
        champion = db.session.get(Team, championship_game.winner_id)
        stats['champion'] = champion
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"🏆 {year} CHAMPION: {champion.name} (Seed {champion.seed}) 🏆")
            print(f"   Owner: {champion.current_owner.name if champion.current_owner else 'Unknown'}")
            print(f"{'='*70}\n")
    
    return stats


def interactive_mode(year=2024):
    """Interactive mode for simulating games."""
    print(f"\n🎮 INTERACTIVE GAME SIMULATOR")
    print(f"{'='*70}\n")
    
    while True:
        print("\nWhat would you like to do?")
        print("  1. Simulate one game")
        print("  2. Simulate Round of 64")
        print("  3. Simulate Round of 32")
        print("  4. Simulate Round of 16")
        print("  5. Simulate Elite 8")
        print("  6. Simulate Final Four")
        print("  7. Simulate Championship")
        print("  8. Simulate entire tournament")
        print("  9. Show tournament status")
        print("  0. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == "0":
            print("👋 Goodbye!")
            break
        elif choice == "1":
            # Show available games
            games = (
                Game.query
                .filter_by(year=year, status="Scheduled")
                .order_by(Game.round.asc(), Game.id.asc())
                .limit(10)
                .all()
            )
            
            if not games:
                print("\n❌ No scheduled games available!")
                continue
            
            print("\nAvailable games:")
            for i, game in enumerate(games, 1):
                if game.team1 and game.team2:
                    print(f"  {i}. Game {game.id}: {game.team1.name} vs {game.team2.name} (Round of {game.round})")
            
            try:
                game_choice = int(input("\nSelect game number: "))
                if 1 <= game_choice <= len(games):
                    simulate_game(games[game_choice - 1].id, verbose=True)
                else:
                    print("Invalid choice!")
            except ValueError:
                print("Invalid input!")
        
        elif choice in ["2", "3", "4", "5", "6", "7"]:
            round_map = {"2": 64, "3": 32, "4": 16, "5": 8, "6": 4, "7": 2}
            simulate_round(round_map[choice], year=year, verbose=True)
        
        elif choice == "8":
            confirm = input("\n⚠️  This will simulate the entire tournament. Continue? (y/n): ")
            if confirm.lower() == 'y':
                simulate_tournament(year=year, verbose=True)
        
        elif choice == "9":
            show_tournament_status(year)
        
        else:
            print("Invalid choice!")


def show_tournament_status(year=2024):
    """Display current tournament status."""
    print(f"\n{'='*70}")
    print(f"📊 TOURNAMENT STATUS - {year}")
    print(f"{'='*70}\n")
    
    for round_num in [64, 32, 16, 8, 4, 2]:
        total = Game.query.filter_by(year=year, round=str(round_num)).count()
        completed = Game.query.filter_by(year=year, round=str(round_num), status="Final").count()
        scheduled = Game.query.filter_by(year=year, round=str(round_num), status="Scheduled").count()
        
        status = "✅" if completed == total and total > 0 else "⏳" if scheduled > 0 else "⏸️ "
        print(f"{status} Round of {round_num:2d}: {completed:2d}/{total:2d} complete ({scheduled:2d} scheduled)")
    
    # Check for champion
    championship = Game.query.filter_by(year=year, round="2", status="Final").first()
    if championship and championship.winner_id:
        champion = db.session.get(Team, championship.winner_id)
        print(f"\n🏆 Champion: {champion.name} (Seed {champion.seed})")
        print(f"   Owner: {champion.current_owner.name if champion.current_owner else 'Unknown'}")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Simulate March Madness games")
    parser.add_argument("--game", type=int, help="Simulate specific game by ID")
    parser.add_argument("--round", type=int, choices=[64, 32, 16, 8, 4, 2], help="Simulate entire round")
    parser.add_argument("--all", action="store_true", help="Simulate entire tournament")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--year", type=int, default=2024, help="Tournament year (default: 2024)")
    parser.add_argument("--status", action="store_true", help="Show tournament status")
    
    args = parser.parse_args()
    
    app = create_app()
    
    with app.app_context():
        if args.status:
            show_tournament_status(args.year)
        elif args.game:
            simulate_game(args.game, verbose=True)
        elif args.round:
            simulate_round(args.round, year=args.year, verbose=True)
        elif args.all:
            confirm = input(f"⚠️  Simulate entire {args.year} tournament? (y/n): ")
            if confirm.lower() == 'y':
                simulate_tournament(year=args.year, verbose=True)
        elif args.interactive:
            interactive_mode(year=args.year)
        else:
            # Default to interactive mode
            interactive_mode(year=args.year)
