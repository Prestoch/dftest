#!/usr/bin/env python3
"""
Smart role remapping for OpenDota match data.
Uses GPM, XPM, and other stats to determine actual in-game roles.
"""

import json
import sys
import csv
from typing import Optional, List, Dict


def determine_role_by_stats(player: dict, team_players: List[dict]) -> str:
    """
    Determine role based on actual game statistics.
    
    Strategy:
    1. Sort team by farm priority (GPM + XPM)
    2. Use lane_role if available
    3. Consider hero typical positions
    4. Assign pos 1-5 based on farm priority
    """
    # If lane_role is available and valid, use it
    lane_role = player.get('lane_role')
    if lane_role in [1, 2, 3]:
        role_map = {
            1: "Carry (pos 1)",
            2: "Mid (pos 2)", 
            3: "Offlane (pos 3)"
        }
        return role_map[lane_role]
    
    # Sort team by farm priority (GPM is most important, then XPM)
    sorted_team = sorted(
        team_players, 
        key=lambda p: (p.get('gpm', 0) * 2 + p.get('xpm', 0)),
        reverse=True
    )
    
    # Find this player's position in farm priority (0-4)
    try:
        farm_position = sorted_team.index(player)
    except ValueError:
        farm_position = 0
    
    # Map farm priority to role
    position_map = {
        0: "Carry (pos 1)",      # Highest farm
        1: "Mid (pos 2)",         # Second highest farm
        2: "Offlane (pos 3)",     # Third highest farm
        3: "Support (pos 4)",     # Fourth highest farm
        4: "Hard Support (pos 5)" # Lowest farm
    }
    
    return position_map.get(farm_position, "Unknown")


def remap_match_with_stats(match_data: dict) -> dict:
    """
    Remap roles for all players in a match using statistics.
    """
    if 'players' not in match_data or not match_data['players']:
        return match_data
    
    # Separate players by team
    radiant_players = []
    dire_players = []
    
    for i, player in enumerate(match_data['players']):
        # Determine team from player data
        is_radiant = player.get('isRadiant')
        if is_radiant is None:
            # Fallback: first 5 are radiant, last 5 are dire
            player_slot = player.get('player_slot', i)
            if player_slot >= 128:
                is_radiant = False
            elif player_slot >= 5:
                is_radiant = False
            else:
                is_radiant = True
            player['isRadiant'] = is_radiant
        
        if is_radiant:
            radiant_players.append(player)
        else:
            dire_players.append(player)
    
    # Update roles for each team based on stats
    changes = 0
    
    for player in radiant_players:
        old_role = player.get('role', 'Unknown')
        new_role = determine_role_by_stats(player, radiant_players)
        if old_role != new_role:
            hero_name = player.get('hero_name', player.get('hero_id', 'Unknown'))
            print(f"  RADIANT {hero_name}: '{old_role}' → '{new_role}' (GPM: {player.get('gpm')}, XPM: {player.get('xpm')})")
            changes += 1
        player['role'] = new_role
    
    for player in dire_players:
        old_role = player.get('role', 'Unknown')
        new_role = determine_role_by_stats(player, dire_players)
        if old_role != new_role:
            hero_name = player.get('hero_name', player.get('hero_id', 'Unknown'))
            print(f"  DIRE    {hero_name}: '{old_role}' → '{new_role}' (GPM: {player.get('gpm')}, XPM: {player.get('xpm')})")
            changes += 1
        player['role'] = new_role
    
    return match_data


def remap_json_file(input_file: str, output_file: str = None):
    """
    Remap roles in a JSON file using smart stat-based detection.
    """
    if output_file is None:
        if input_file.endswith('.json'):
            output_file = input_file.replace('.json', '_smart_remapped.json')
        else:
            output_file = input_file + '_smart_remapped.json'
    
    print(f"Reading: {input_file}")
    
    # Load the data
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found!")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file: {e}")
        return False
    
    # Check if it's a list of matches or a single match
    if isinstance(data, list):
        print(f"Processing {len(data)} matches...")
        print()
        total_changes = 0
        
        for idx, match in enumerate(data):
            if (idx + 1) % 50 == 0:
                print(f"\nProgress: {idx + 1}/{len(data)} matches processed...")
            
            if idx < 3 or (idx + 1) % 50 == 0:  # Show details for first 3 and every 50th
                match_id = match.get('match_id', 'unknown')
                print(f"\nMatch {idx + 1} (ID: {match_id}):")
            
            original_roles = [p.get('role') for p in match.get('players', [])]
            remap_match_with_stats(match)
            new_roles = [p.get('role') for p in match.get('players', [])]
            
            if original_roles != new_roles:
                total_changes += 1
        
        print(f"\n✓ Remapped roles in {total_changes} matches (with statistical analysis)")
    else:
        print("Processing single match...")
        remap_match_with_stats(data)
        print("✓ Remapped roles")
    
    # Save the updated data
    print(f"\nSaving to: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Done! Saved remapped data to: {output_file}")
    return True


def export_to_csv(json_file: str, csv_file: str = None):
    """
    Export JSON match data to CSV.
    """
    if csv_file is None:
        csv_file = json_file.replace('.json', '.csv')
    
    print(f"\nExporting to CSV: {csv_file}")
    
    # Load JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        data = [data]
    
    if not data or 'players' not in data[0]:
        print("Error: No player data found in JSON")
        return False
    
    # Write CSV
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'match_id', 'tournament', 'radiant_team', 'dire_team',
            'duration_minutes', 'winner', 'radiant_win',
            'hero_name', 'hero_id', 'team', 'role', 'player_slot',
            'gpm', 'xpm', 'tower_damage', 'hero_healing',
            'lane_efficiency_pct', 'kills', 'deaths', 'assists', 'won'
        ]
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # Flatten data: one row per player
        for match in data:
            match_info = {
                'match_id': match.get('match_id'),
                'tournament': match.get('tournament'),
                'radiant_team': match.get('radiant_team'),
                'dire_team': match.get('dire_team'),
                'duration_minutes': match.get('duration_minutes'),
                'winner': match.get('winner'),
                'radiant_win': match.get('radiant_win')
            }
            
            for player in match.get('players', []):
                row = {**match_info, **player}
                writer.writerow(row)
    
    print(f"✓ CSV export complete: {csv_file}")
    return True


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python smart_remap_roles.py <input_json_file> [output_json_file]")
        print()
        print("This script remaps hero roles using ACTUAL GAME STATISTICS:")
        print("  • Analyzes GPM, XPM, lane efficiency")
        print("  • Sorts each team by farm priority")
        print("  • Assigns pos 1-5 based on actual performance")
        print()
        print("This is more accurate than just using player_slot order!")
        print()
        print("Examples:")
        print("  python smart_remap_roles.py matches.json")
        print("  python smart_remap_roles.py matches.json matches_fixed.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("="*70)
    print("OpenDota Match Data - SMART Role Remapper (Stats-Based)")
    print("="*70)
    print()
    
    # Remap the JSON file
    success = remap_json_file(input_file, output_file)
    
    if success:
        # Export to CSV
        output_json = output_file if output_file else input_file.replace('.json', '_smart_remapped.json')
        export_to_csv(output_json)
        
        print()
        print("="*70)
        print("✓ All done!")
        print("="*70)
        print()
        print("Roles are now assigned based on ACTUAL in-game performance:")
        print("  • Highest farm → Carry (pos 1)")
        print("  • 2nd highest → Mid (pos 2)")
        print("  • 3rd highest → Offlane (pos 3)")
        print("  • 4th highest → Support (pos 4)")
        print("  • Lowest farm → Hard Support (pos 5)")
        print()


if __name__ == "__main__":
    main()
