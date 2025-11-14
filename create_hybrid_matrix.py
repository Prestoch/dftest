#!/usr/bin/env python3
"""
Create a hybrid matrix that combines:
- cs_stratz_matrix matchup data (professional matches)
- cs_original.json to fill in missing hero winrates and matchups
"""

import json
import re

print("Creating hybrid matrix...")

# Load cs_stratz_matrix
with open('cs_stratz_matrix.json', 'r') as f:
    stratz_content = f.read()

stratz_heroes = json.loads(re.search(r'var heroes = (\[[^\]]+\])', stratz_content, re.DOTALL).group(1))
stratz_heroes_bg = json.loads(re.search(r'heroes_bg = (\[[^\]]+\])', stratz_content, re.DOTALL).group(1))
stratz_heroes_wr = json.loads(re.search(r'heroes_wr = (\[[^\]]+\])', stratz_content, re.DOTALL).group(1))
stratz_win_rates = json.loads(re.search(r'win_rates = (\[.*\]), update_time', stratz_content, re.DOTALL).group(1))

# Load cs_original.json
with open('cs_original.json', 'r') as f:
    orig_content = f.read()

orig_heroes = json.loads(re.search(r'var heroes = (\[[^\]]+\])', orig_content, re.DOTALL).group(1))
orig_heroes_wr = json.loads(re.search(r'heroes_wr = (\[[^\]]+\])', orig_content, re.DOTALL).group(1))
orig_win_rates = json.loads(re.search(r'win_rates = (\[.*\]), update_time', orig_content, re.DOTALL).group(1))

print(f"Stratz heroes: {len(stratz_heroes)}")
print(f"Original heroes: {len(orig_heroes)}")

# Create hybrid
hybrid_heroes = stratz_heroes.copy()
hybrid_heroes_bg = stratz_heroes_bg.copy()
hybrid_heroes_wr = []
hybrid_win_rates = []

# Fix hero winrates
print("\nFixing hero winrates...")
fixed_count = 0
for i, hero in enumerate(hybrid_heroes):
    stratz_wr = float(stratz_heroes_wr[i])
    orig_wr = float(orig_heroes_wr[i])
    
    # If stratz has 0 or very low winrate, use original
    if stratz_wr < 1.0:
        hybrid_heroes_wr.append(orig_heroes_wr[i])
        print(f"  Fixed {hero}: {stratz_wr:.2f}% → {orig_wr:.2f}%")
        fixed_count += 1
    else:
        hybrid_heroes_wr.append(stratz_heroes_wr[i])

print(f"Fixed {fixed_count} hero winrates")

# Fix matchup matrix
print("\nFixing matchup data...")
matchup_fixes = 0
total_matchups = 0

for i in range(len(hybrid_heroes)):
    hero_matchups = [None]  # First element is null
    
    for j in range(len(hybrid_heroes)):
        if i == j:
            if i > 0:  # Skip first null we already added
                hero_matchups.append(None)
            total_matchups += 1
            continue
        
        # Try to use stratz data first
        stratz_matchup = stratz_win_rates[i][j]
        
        if stratz_matchup is not None and isinstance(stratz_matchup, list):
            # Check if it has reasonable data (games > 0)
            if stratz_matchup[2] > 0:
                hero_matchups.append(stratz_matchup)
            else:
                # No games, use original
                orig_matchup = orig_win_rates[i][j]
                hero_matchups.append(orig_matchup)
                matchup_fixes += 1
        elif stratz_matchup is None:
            # No data in stratz, use original
            orig_matchup = orig_win_rates[i][j]
            hero_matchups.append(orig_matchup)
            matchup_fixes += 1
        else:
            # Use as is
            hero_matchups.append(stratz_matchup)
        
        total_matchups += 1
    
    hybrid_win_rates.append(hero_matchups)

print(f"Fixed {matchup_fixes} / {total_matchups} matchups ({matchup_fixes/total_matchups*100:.1f}%)")

# Create output
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")

output_lines = []
output_lines.append(f'var heroes = {json.dumps(hybrid_heroes)}, ')
output_lines.append(f'heroes_bg = {json.dumps(hybrid_heroes_bg)}, ')
output_lines.append(f'heroes_wr = {json.dumps(hybrid_heroes_wr)}, ')
output_lines.append(f'win_rates = {json.dumps(hybrid_win_rates)}, ')
output_lines.append(f'update_time = "{today}";')

output_content = ''.join(output_lines)

# Save
with open('cs_hybrid_matrix.json', 'w') as f:
    f.write(output_content)

print(f"\n✓ Created cs_hybrid_matrix.json")

# Verify no zeros
print("\nVerifying hybrid matrix...")
zero_count = 0
for i, wr in enumerate(hybrid_heroes_wr):
    if float(wr) == 0:
        print(f"  WARNING: {hybrid_heroes[i]} still has 0% WR!")
        zero_count += 1

if zero_count == 0:
    print("✓ All heroes have non-zero winrates!")
else:
    print(f"✗ Still have {zero_count} heroes with 0% WR")

# Show stats
hybrid_wr_vals = [float(x) for x in hybrid_heroes_wr]
print(f"\nHybrid matrix stats:")
print(f"  Min WR: {min(hybrid_wr_vals):.2f}%")
print(f"  Max WR: {max(hybrid_wr_vals):.2f}%")
print(f"  Avg WR: {sum(hybrid_wr_vals)/len(hybrid_wr_vals):.2f}%")
print(f"  Heroes: {len(hybrid_heroes)}")

print("\n✅ Complete! Use cs_hybrid_matrix.json for betting simulations.")
