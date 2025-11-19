#!/usr/bin/env python3
"""
Remap hero roles in existing OpenDota match data files.
This fixes the Support (pos 4) and Hard Support (pos 5) detection issue
without re-fetching data from the API.
"""

import json
import sys
import csv
from typing import Optional


def get_role_name(lane_role: Optional[int], player_slot: int, is_roaming: bool = False) -> str:
    """
    Determine role name from available data.
    
    In OpenDota API:
    - lane_role: 1=Safe Lane, 2=Mid, 3=Off Lane, 4=Jungle
    - player_slot: 0-4 for Radiant, 128-132 for Dire (encoded)
    - Players within each team are typically ordered by farm priority (pos 1-5)
    """
    # Decode player_slot to get position within team (0-4)
    if player_slot < 128:
        team_position = player_slot  # Radiant: 0-4
    else:
        team_position = player_slot - 128  # Dire: 128-132 -> 0-4
    
    # Try to determine role from lane_role first
    if lane_role == 1:
        return "Carry (pos 1)"
    elif lane_role == 2:
        return "Mid (pos 2)"
    elif lane_role == 3:
        return "Offlane (pos 3)"
    elif lane_role == 4 or is_roaming:
        # Jungle or roaming - could be pos 4 or 5
        # Use team position to distinguish
        if team_position >= 4:
            return "Hard Support (pos 5)"
        else:
            return "Support (pos 4)"
    
    # Fallback: use team position (farm priority order)
    # Players are typically ordered by position within their team
    position_map = {
        0: "Carry (pos 1)",
        1: "Mid (pos 2)",
        2: "Offlane (pos 3)",
        3: "Support (pos 4)",
        4: "Hard Support (pos 5)"
    }
    
    return position_map.get(team_position, f"Unknown (slot {player_slot})")


def remap_roles_in_match(match_data: dict) -> dict:
    """
    Remap roles for all players in a match using improved detection.
    """
    # Check if this is a detailed match (has players array)
    if 'players' not in match_data or not match_data['players']:
        return match_data
    
    # Update each player's role
    for i, player in enumerate(match_data['players']):
        # Get player_slot (or infer from position)
        player_slot = player.get('player_slot', i)
        lane_role = player.get('lane_role')
        is_roaming = player.get('is_roaming', False)
        
        # Add player_slot if missing
        if 'player_slot' not in player:
            player['player_slot'] = player_slot
        
        # Update role
        old_role = player.get('role', 'Unknown')
        new_role = get_role_name(lane_role, player_slot, is_roaming)
        player['role'] = new_role
        
        # Print if role changed
        if old_role != new_role:
            hero_name = player.get('hero_name', player.get('hero_id', 'Unknown'))
            print(f"  Updated: {hero_name}: '{old_role}' → '{new_role}' (slot {player_slot})")
    
    return match_data


def remap_json_file(input_file: str, output_file: str = None):
    """
    Remap roles in a JSON file containing match data.
    """
    if output_file is None:
        # Create output filename
        if input_file.endswith('.json'):
            output_file = input_file.replace('.json', '_remapped.json')
        else:
            output_file = input_file + '_remapped.json'
    
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
        total_changes = 0
        for idx, match in enumerate(data):
            if (idx + 1) % 100 == 0:
                print(f"Progress: {idx + 1}/{len(data)} matches processed...")
            original = json.dumps(match)
            remapped = remap_roles_in_match(match)
            if json.dumps(remapped) != original:
                total_changes += 1
        print(f"\n✓ Remapped roles in {total_changes} matches")
    else:
        print("Processing single match...")
        data = remap_roles_in_match(data)
        print("✓ Remapped roles")
    
    # Save the updated data
    print(f"\nSaving to: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Done! Saved remapped data to: {output_file}")
    return True


def export_to_csv(json_file: str, csv_file: str = None):
    """
    Export JSON match data to CSV with remapped roles.
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
        print("Usage: python remap_roles.py <input_json_file> [output_json_file]")
        print()
        print("This script remaps hero roles in existing OpenDota match data.")
        print("It fixes Support (pos 4) and Hard Support (pos 5) detection")
        print("without needing to re-fetch data from the API.")
        print()
        print("Examples:")
        print("  python remap_roles.py matches.json")
        print("  python remap_roles.py matches.json matches_fixed.json")
        print()
        print("The script will also generate a CSV file automatically.")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("="*60)
    print("OpenDota Match Data - Role Remapper")
    print("="*60)
    print()
    
    # Remap the JSON file
    success = remap_json_file(input_file, output_file)
    
    if success:
        # Export to CSV
        output_json = output_file if output_file else input_file.replace('.json', '_remapped.json')
        export_to_csv(output_json)
        
        print()
        print("="*60)
        print("✓ All done!")
        print("="*60)
        print()
        print("Role distribution per match should now show:")
        print("  • 2x Carry (pos 1)")
        print("  • 2x Mid (pos 2)")
        print("  • 2x Offlane (pos 3)")
        print("  • 2x Support (pos 4)")
        print("  • 2x Hard Support (pos 5)")
        print()


if __name__ == "__main__":
    main()
