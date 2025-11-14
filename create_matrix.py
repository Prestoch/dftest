#!/usr/bin/env python3
"""
Script to create a hero matchup matrix from stratz_with_tiers_filtered.json
similar to cs_original.json format.
"""

import json
import re
from collections import defaultdict
from datetime import datetime

# Load the data files
print("Loading data files...")
with open('stratz_with_tiers_filtered.json', 'r') as f:
    matches = json.load(f)

with open('hero_id_map.json', 'r') as f:
    hero_id_map = json.load(f)

# Parse cs_original.json to understand structure
print("Parsing cs_original.json structure...")
with open('cs_original.json', 'r') as f:
    cs_content = f.read()

# Extract heroes array using regex
heroes_match = re.search(r'var heroes = (\[.*?\])', cs_content)
heroes_array = json.loads(heroes_match.group(1))

print(f"\nTotal heroes in cs_original: {len(heroes_array)}")
print(f"Total matches in stratz data: {len(matches)}")

# Create reverse mapping from hero_id_map to get hero index
# hero_id_map maps: "stratz_hero_id" -> "cs_original_index"
hero_stratz_to_cs_index = {int(k): int(v) for k, v in hero_id_map.items()}

print(f"Hero ID mappings: {len(hero_stratz_to_cs_index)}")

# Initialize matchup matrix
# matrix[hero1_index][hero2_index] = {"wins": count, "total": count}
matrix = defaultdict(lambda: defaultdict(lambda: {"wins": 0, "total": 0}))

# Process matches to build hero vs hero matchup data
print("\nProcessing matches...")
processed = 0
skipped = 0

for match_id, match_data in matches.items():
    radiant_win = match_data['radiantWin']
    
    # Get hero IDs from both teams
    radiant_heroes = [hero['heroId'] for hero in match_data['radiantRoles']]
    dire_heroes = [hero['heroId'] for hero in match_data['direRoles']]
    
    # Convert to cs_original indices
    try:
        radiant_indices = [hero_stratz_to_cs_index[h] for h in radiant_heroes]
        dire_indices = [hero_stratz_to_cs_index[h] for h in dire_heroes]
    except KeyError as e:
        skipped += 1
        continue
    
    # For each radiant hero vs each dire hero matchup
    for rad_idx in radiant_indices:
        for dire_idx in dire_indices:
            # Radiant hero vs Dire hero
            matrix[rad_idx][dire_idx]["total"] += 1
            if radiant_win:
                matrix[rad_idx][dire_idx]["wins"] += 1
            
            # Dire hero vs Radiant hero (inverse matchup)
            matrix[dire_idx][rad_idx]["total"] += 1
            if not radiant_win:
                matrix[dire_idx][rad_idx]["wins"] += 1
    
    processed += 1
    if processed % 1000 == 0:
        print(f"Processed {processed}/{len(matches)} matches...")

print(f"\nProcessed: {processed} matches")
print(f"Skipped: {skipped} matches (missing hero mappings)")

# Build the win_rates array structure similar to cs_original.json
print("\nBuilding win_rates matrix...")
num_heroes = len(heroes_array)
win_rates = []

# Calculate overall hero win rates first
hero_stats = defaultdict(lambda: {"wins": 0, "total": 0})
for match_id, match_data in matches.items():
    radiant_win = match_data['radiantWin']
    
    try:
        radiant_indices = [hero_stratz_to_cs_index[hero['heroId']] for hero in match_data['radiantRoles']]
        dire_indices = [hero_stratz_to_cs_index[hero['heroId']] for hero in match_data['direRoles']]
    except KeyError:
        continue
    
    for idx in radiant_indices:
        hero_stats[idx]["total"] += 1
        if radiant_win:
            hero_stats[idx]["wins"] += 1
    
    for idx in dire_indices:
        hero_stats[idx]["total"] += 1
        if not radiant_win:
            hero_stats[idx]["wins"] += 1

# Calculate hero win rates
heroes_wr = []
for i in range(num_heroes):
    if hero_stats[i]["total"] > 0:
        wr = (hero_stats[i]["wins"] / hero_stats[i]["total"]) * 100
        heroes_wr.append(f"{wr:.2f}")
    else:
        heroes_wr.append("0.00")

print(f"Calculated win rates for {len([h for h in heroes_wr if h != '0.00'])} heroes")

# Build win_rates matrix
for hero_idx in range(num_heroes):
    hero_matchups = [None]  # First element is null for the hero itself
    
    for opponent_idx in range(num_heroes):
        if hero_idx == opponent_idx:
            # Same hero - add None as placeholder
            if hero_idx == 0:
                continue  # Already added None
            else:
                hero_matchups.append(None)
        else:
            matchup_data = matrix[hero_idx][opponent_idx]
            total = matchup_data["total"]
            
            if total > 0:
                wins = matchup_data["wins"]
                win_rate = (wins / total) * 100
                
                # Calculate advantage (difference from expected 50%)
                advantage = win_rate - 50.0
                
                # Format: [advantage, win_rate, total_games]
                hero_matchups.append([
                    f"{advantage:.4f}",
                    f"{win_rate:.4f}",
                    total
                ])
            else:
                # No data for this matchup
                hero_matchups.append(None)
    
    win_rates.append(hero_matchups)

# Get heroes_bg from cs_original
heroes_bg_match = re.search(r'heroes_bg = (\[.*?\])', cs_content)
heroes_bg = json.loads(heroes_bg_match.group(1))

# Create output in same format as cs_original.json
print("\nGenerating output file...")
today = datetime.now().strftime("%Y-%m-%d")

output_lines = []
output_lines.append(f'var heroes = {json.dumps(heroes_array)}, ')
output_lines.append(f'heroes_bg = {json.dumps(heroes_bg)}, ')
output_lines.append(f'heroes_wr = {json.dumps(heroes_wr)}, ')
output_lines.append(f'win_rates = {json.dumps(win_rates)}, ')
output_lines.append(f'update_time = "{today}";')

output_content = ''.join(output_lines)

# Write to output file
output_file = 'cs_stratz_matrix.json'
with open(output_file, 'w') as f:
    f.write(output_content)

print(f"\n✓ Created {output_file}")
print(f"  - {len(heroes_array)} heroes")
print(f"  - {processed} matches analyzed")
print(f"  - Matrix dimensions: {num_heroes}x{num_heroes}")

# Print some statistics
total_matchups = sum(1 for i in range(num_heroes) for j in range(num_heroes) 
                     if i != j and matrix[i][j]["total"] > 0)
print(f"  - {total_matchups} unique hero matchups with data")

# Find hero with most games
max_games_idx = max(range(num_heroes), key=lambda i: hero_stats[i]["total"])
max_games = hero_stats[max_games_idx]["total"]
print(f"  - Most played hero: {heroes_array[max_games_idx]} ({max_games} games)")

print("\nDone!")
