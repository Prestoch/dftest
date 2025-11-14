#!/usr/bin/env python3
"""
Betting simulator for Dota 2 matches using hero matchup advantages.
Simulates various betting strategies on the Hawk dataset.
"""

import pandas as pd
import json
import re
import numpy as np
from datetime import datetime
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

print("Loading data files...")

# Load hero matchup matrix
with open('cs_stratz_matrix.json', 'r') as f:
    matrix_content = f.read()

# Parse the matrix
heroes = json.loads(re.search(r'var heroes = (\[[^\]]+\])', matrix_content, re.DOTALL).group(1))
win_rates_matrix = json.loads(re.search(r'win_rates = (\[.*\]), update_time', matrix_content, re.DOTALL).group(1))

# Create hero name to index mapping
hero_to_idx = {hero.lower(): idx for idx, hero in enumerate(heroes)}

# Handle special cases for hero name variations
name_variations = {
    "nature's prophet": "natures prophet",
    "keeper of the light": "keeper of the light",
    "queen of pain": "queen of pain",
}

print(f"Loaded {len(heroes)} heroes from matchup matrix")

# Load hawk dataset
df = pd.read_csv('hawk_matches_merged.csv')
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)

# Filter to date range
df = df[(df['date'] >= '2023-01-02') & (df['date'] <= '2025-11-06')]
print(f"Loaded {len(df)} matches from {df['date'].min()} to {df['date'].max()}")

def get_hero_idx(hero_name):
    """Get hero index from name, handling variations."""
    hero_name = hero_name.strip().lower()
    
    # Try direct lookup
    if hero_name in hero_to_idx:
        return hero_to_idx[hero_name]
    
    # Try variations
    for variation, canonical in name_variations.items():
        if hero_name == variation:
            if canonical in hero_to_idx:
                return hero_to_idx[canonical]
    
    return None

def calculate_matchup_advantage(team1_heroes, team2_heroes):
    """
    Calculate the aggregate matchup advantage for team1 vs team2.
    Returns the sum of all individual hero matchup advantages.
    """
    team1_list = [h.strip() for h in team1_heroes.split('|')]
    team2_list = [h.strip() for h in team2_heroes.split('|')]
    
    total_advantage = 0
    matchup_count = 0
    missing_heroes = set()
    
    for hero1 in team1_list:
        idx1 = get_hero_idx(hero1)
        if idx1 is None:
            missing_heroes.add(hero1)
            continue
            
        for hero2 in team2_list:
            idx2 = get_hero_idx(hero2)
            if idx2 is None:
                missing_heroes.add(hero2)
                continue
            
            # Get matchup data from matrix
            # Look up opponent's advantage against our hero (idx2 vs idx1)
            matchup = win_rates_matrix[idx2][idx1]
            if matchup is not None and isinstance(matchup, list):
                advantage = float(matchup[0])  # First element is the advantage
                total_advantage += advantage
                matchup_count += 1
            elif matchup is None:
                # If no data, try reverse direction
                reverse_matchup = win_rates_matrix[idx1][idx2]
                if reverse_matchup is not None and isinstance(reverse_matchup, list):
                    advantage = float(reverse_matchup[0])
                    total_advantage += advantage
                    matchup_count += 1
    
    if missing_heroes:
        pass  # Silently handle missing heroes
    
    return total_advantage if matchup_count > 0 else 0

# Calculate advantages for all matches
print("\nCalculating matchup advantages...")
advantages = []
for idx, row in df.iterrows():
    adv = calculate_matchup_advantage(row['team1_heroes'], row['team2_heroes'])
    advantages.append(adv)
    if (idx + 1) % 1000 == 0:
        print(f"  Processed {idx + 1}/{len(df)} matches...")

df['calculated_advantage'] = advantages
print(f"Calculated advantages for {len(df)} matches")

def get_top_n_heroes(team_heroes, n):
    """Get top n heroes from a team based on their total advantage vs opponent."""
    return team_heroes.split('|')[:n]

def filter_matches_by_hero_count(df, min_heroes):
    """Filter matches where we use top N heroes from each team."""
    # For this simulation, we'll calculate advantage using only top N heroes
    filtered_df = df.copy()
    
    if min_heroes < 5:
        # Recalculate advantages with only top N heroes
        new_advantages = []
        for idx, row in filtered_df.iterrows():
            team1_heroes = '|'.join(row['team1_heroes'].split('|')[:min_heroes])
            team2_heroes = '|'.join(row['team2_heroes'].split('|')[:min_heroes])
            adv = calculate_matchup_advantage(team1_heroes, team2_heroes)
            new_advantages.append(adv)
        
        filtered_df['calculated_advantage'] = new_advantages
    
    return filtered_df

def simulate_betting_strategy(df, strategy_name, delta_thresholds, 
                              bet_type='flat', bet_amount=100, 
                              underdog_only=False, favorite_only=False,
                              min_heroes=5):
    """
    Simulate a betting strategy.
    
    Parameters:
    - df: DataFrame with match data
    - strategy_name: Name of the strategy
    - delta_thresholds: List of |Δ| thresholds to test
    - bet_type: 'flat', 'percentage', 'fibonacci_1', 'fibonacci_5'
    - bet_amount: Fixed bet amount (for flat) or percentage (for percentage)
    - underdog_only: Only bet on underdogs
    - favorite_only: Only bet on favorites
    - min_heroes: Minimum number of heroes to consider (4 or 5)
    """
    results = []
    
    # Filter by hero count if needed
    working_df = filter_matches_by_hero_count(df, min_heroes)
    
    for threshold in delta_thresholds:
        starting_bank = 1000
        max_bet = 10000
        bankroll = starting_bank
        
        bet_history = []
        fibonacci_position = 0  # For Fibonacci strategies
        fibonacci_sequence = [1, 1]  # Start of Fibonacci sequence
        
        for idx, row in working_df.iterrows():
            advantage = row['calculated_advantage']
            abs_advantage = abs(advantage)
            
            # Check if advantage meets threshold
            if abs_advantage < threshold:
                continue
            
            # Determine predicted winner based on advantage
            predicted_winner = row['team1'] if advantage > 0 else row['team2']
            actual_winner = row['winner']
            
            # Get odds for predicted winner
            if predicted_winner == row['team1']:
                odds = row['team1_odds']
                is_favorite = advantage > 0  # Positive advantage means team1 favored
            else:
                odds = row['team2_odds']
                is_favorite = advantage < 0  # Negative advantage means team2 favored
            
            # Apply underdog/favorite filters
            if underdog_only and is_favorite:
                continue
            if favorite_only and not is_favorite:
                continue
            
            # Calculate bet size
            if bet_type == 'flat':
                stake = bet_amount
            elif bet_type == 'percentage':
                stake = bankroll * (bet_amount / 100)
            elif bet_type in ['fibonacci_1', 'fibonacci_5']:
                unit = 1 if bet_type == 'fibonacci_1' else 5
                # Generate Fibonacci sequence up to current position
                while len(fibonacci_sequence) <= fibonacci_position:
                    fibonacci_sequence.append(
                        fibonacci_sequence[-1] + fibonacci_sequence[-2]
                    )
                stake = fibonacci_sequence[fibonacci_position] * unit
            else:
                stake = bet_amount
            
            # Apply constraints
            stake = min(stake, bankroll)  # Can't bet more than we have
            stake = min(stake, max_bet)   # Max bet limit
            
            if stake <= 0 or bankroll <= 0:
                break  # Out of money
            
            # Determine win/loss
            won = (predicted_winner == actual_winner)
            
            if won:
                profit = stake * (odds - 1)
                bankroll += profit
                if bet_type in ['fibonacci_1', 'fibonacci_5']:
                    fibonacci_position = 0  # Reset on win
            else:
                bankroll -= stake
                bankroll = max(0, bankroll)  # Clip at zero
                if bet_type in ['fibonacci_1', 'fibonacci_5']:
                    fibonacci_position += 1  # Move forward on loss
            
            bet_history.append({
                'date': row['date'],
                'match_id': row['hawk_match_id'],
                'advantage': advantage,
                'stake': stake,
                'odds': odds,
                'won': won,
                'bankroll': bankroll
            })
            
            if bankroll <= 0:
                break  # Bankrupt
        
        # Calculate statistics
        total_bets = len(bet_history)
        if total_bets > 0:
            wins = sum(1 for b in bet_history if b['won'])
            win_rate = wins / total_bets * 100
            final_bankroll = bankroll
            roi = (final_bankroll - starting_bank) / starting_bank * 100
        else:
            wins = 0
            win_rate = 0
            final_bankroll = starting_bank
            roi = 0
        
        results.append({
            'strategy': strategy_name,
            'delta_threshold': threshold,
            'total_bets': total_bets,
            'wins': wins,
            'losses': total_bets - wins,
            'win_rate': win_rate,
            'starting_bank': starting_bank,
            'final_bankroll': final_bankroll,
            'profit_loss': final_bankroll - starting_bank,
            'roi': roi
        })
    
    return pd.DataFrame(results)

# Define delta thresholds
delta_thresholds = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 75, 100, 150, 200, 300, 400]

print("\n" + "="*70)
print("Starting betting simulations...")
print("="*70)

all_results = []
strategy_count = 0

# Strategy 1-3: Flat $100, various filters
print("\n[1-3] Flat $100 strategies...")
for name, underdog, favorite in [
    ('1_flat100_all', False, False),
    ('2_flat100_underdogs', True, False),
    ('3_flat100_favorites', False, True)
]:
    result = simulate_betting_strategy(
        df, name, delta_thresholds, 
        bet_type='flat', bet_amount=100,
        underdog_only=underdog, favorite_only=favorite
    )
    all_results.append(result)
    strategy_count += 1

# Strategy 4-6: 5% bankroll, various filters
print("[4-6] 5% bankroll strategies...")
for name, underdog, favorite in [
    ('4_pct5_all', False, False),
    ('5_pct5_underdogs', True, False),
    ('6_pct5_favorites', False, True)
]:
    result = simulate_betting_strategy(
        df, name, delta_thresholds,
        bet_type='percentage', bet_amount=5,
        underdog_only=underdog, favorite_only=favorite
    )
    all_results.append(result)
    strategy_count += 1

# Strategy 7-9: Flat $100, 4+4 heroes
print("[7-9] Flat $100, 4+4 heroes strategies...")
for name, underdog, favorite in [
    ('7_flat100_4heroes_all', False, False),
    ('8_flat100_4heroes_underdogs', True, False),
    ('9_flat100_4heroes_favorites', False, True)
]:
    result = simulate_betting_strategy(
        df, name, delta_thresholds,
        bet_type='flat', bet_amount=100,
        underdog_only=underdog, favorite_only=favorite,
        min_heroes=4
    )
    all_results.append(result)
    strategy_count += 1

# Strategy 10-12: 5% bankroll, 4+4 heroes
print("[10-12] 5% bankroll, 4+4 heroes strategies...")
for name, underdog, favorite in [
    ('10_pct5_4heroes_all', False, False),
    ('11_pct5_4heroes_underdogs', True, False),
    ('12_pct5_4heroes_favorites', False, True)
]:
    result = simulate_betting_strategy(
        df, name, delta_thresholds,
        bet_type='percentage', bet_amount=5,
        underdog_only=underdog, favorite_only=favorite,
        min_heroes=4
    )
    all_results.append(result)
    strategy_count += 1

# Strategy 13-18: Using all 5 heroes (same as 1-6 since default is 5)
print("[13-18] 5+5 heroes strategies (same as full team)...")
for name, bet_type, bet_amount, underdog, favorite in [
    ('13_flat100_5heroes_all', 'flat', 100, False, False),
    ('14_flat100_5heroes_underdogs', 'flat', 100, True, False),
    ('15_flat100_5heroes_favorites', 'flat', 100, False, True),
    ('16_pct5_5heroes_all', 'percentage', 5, False, False),
    ('17_pct5_5heroes_underdogs', 'percentage', 5, True, False),
    ('18_pct5_5heroes_favorites', 'percentage', 5, False, True)
]:
    result = simulate_betting_strategy(
        df, name, delta_thresholds,
        bet_type=bet_type, bet_amount=bet_amount,
        underdog_only=underdog, favorite_only=favorite,
        min_heroes=5
    )
    all_results.append(result)
    strategy_count += 1

# Strategy 19-21: Fibonacci $1 unit
print("[19-21] Fibonacci $1 unit strategies...")
for name, underdog, favorite in [
    ('19_fib1_all', False, False),
    ('20_fib1_underdogs', True, False),
    ('21_fib1_favorites', False, True)
]:
    result = simulate_betting_strategy(
        df, name, delta_thresholds,
        bet_type='fibonacci_1', bet_amount=1,
        underdog_only=underdog, favorite_only=favorite
    )
    all_results.append(result)
    strategy_count += 1

# Strategy 22-27: Fibonacci $1 unit with hero filters
print("[22-27] Fibonacci $1 unit with hero filters...")
for name, underdog, favorite, min_heroes in [
    ('22_fib1_4heroes_all', False, False, 4),
    ('23_fib1_4heroes_underdogs', True, False, 4),
    ('24_fib1_4heroes_favorites', False, True, 4),
    ('25_fib1_5heroes_all', False, False, 5),
    ('26_fib1_5heroes_underdogs', True, False, 5),
    ('27_fib1_5heroes_favorites', False, True, 5)
]:
    result = simulate_betting_strategy(
        df, name, delta_thresholds,
        bet_type='fibonacci_1', bet_amount=1,
        underdog_only=underdog, favorite_only=favorite,
        min_heroes=min_heroes
    )
    all_results.append(result)
    strategy_count += 1

# Strategy 28-36: Fibonacci $5 unit
print("[28-36] Fibonacci $5 unit strategies...")
for name, underdog, favorite, min_heroes in [
    ('28_fib5_all', False, False, 5),
    ('29_fib5_underdogs', True, False, 5),
    ('30_fib5_favorites', False, True, 5),
    ('31_fib5_4heroes_all', False, False, 4),
    ('32_fib5_4heroes_underdogs', True, False, 4),
    ('33_fib5_4heroes_favorites', False, True, 4),
    ('34_fib5_5heroes_all', False, False, 5),
    ('35_fib5_5heroes_underdogs', True, False, 5),
    ('36_fib5_5heroes_favorites', False, True, 5)
]:
    result = simulate_betting_strategy(
        df, name, delta_thresholds,
        bet_type='fibonacci_5', bet_amount=5,
        underdog_only=underdog, favorite_only=favorite,
        min_heroes=min_heroes
    )
    all_results.append(result)
    strategy_count += 1

print(f"\nCompleted {strategy_count} strategies!")

# Save all results to separate CSV files
print("\n" + "="*70)
print("Saving results to CSV files...")
print("="*70)

for idx, result_df in enumerate(all_results, 1):
    if len(result_df) > 0:
        strategy_name = result_df['strategy'].iloc[0]
        filename = f'betting_results_{strategy_name}.csv'
        result_df.to_csv(filename, index=False)
        print(f"  ✓ Saved {filename}")

# Create a summary file
print("\nCreating summary file...")
summary_data = []
for result_df in all_results:
    for _, row in result_df.iterrows():
        summary_data.append(row.to_dict())

summary_df = pd.DataFrame(summary_data)
summary_df = summary_df.sort_values(['strategy', 'delta_threshold'])
summary_df.to_csv('betting_results_SUMMARY.csv', index=False)
print("  ✓ Saved betting_results_SUMMARY.csv")

# Find best strategies
print("\n" + "="*70)
print("TOP PERFORMING STRATEGIES")
print("="*70)

best_roi = summary_df.nlargest(10, 'roi')[['strategy', 'delta_threshold', 'total_bets', 'win_rate', 'final_bankroll', 'roi']]
print("\nTop 10 by ROI:")
print(best_roi.to_string(index=False))

best_profit = summary_df.nlargest(10, 'profit_loss')[['strategy', 'delta_threshold', 'total_bets', 'win_rate', 'final_bankroll', 'profit_loss']]
print("\nTop 10 by Absolute Profit:")
print(best_profit.to_string(index=False))

print("\n" + "="*70)
print("SIMULATION COMPLETE!")
print("="*70)
print(f"Total strategies tested: {len(all_results)}")
print(f"Total CSV files generated: {len(all_results) + 1}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print(f"Total matches in dataset: {len(df)}")
