#!/usr/bin/env python3
"""
Extract data from old-format checkpoint file and save to final files.
This recovers data from a checkpoint created before the streaming update.
"""

import json
import csv
import sys
from datetime import datetime

def extract_checkpoint(checkpoint_file):
    """Extract match data from checkpoint file."""
    print(f"Reading checkpoint file: {checkpoint_file}")
    
    try:
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        matches = data.get('matches', [])
        print(f"✓ Found {len(matches)} matches in checkpoint")
        
        if not matches:
            print("⚠ No matches found in checkpoint file")
            return None
        
        return matches
        
    except FileNotFoundError:
        print(f"✗ Checkpoint file not found: {checkpoint_file}")
        return None
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in checkpoint file: {e}")
        return None
    except Exception as e:
        print(f"✗ Error reading checkpoint: {e}")
        return None

def save_to_json(matches, filename):
    """Save matches to JSON file."""
    print(f"\nSaving to JSON: {filename}")
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(matches, f, indent=2)
    
    print(f"✓ Saved {len(matches)} matches to {filename}")

def save_to_csv(matches, filename):
    """Save matches to CSV file."""
    print(f"\nSaving to CSV: {filename}")
    
    if not matches:
        print("⚠ No matches to save")
        return
    
    fieldnames = [
        'match_id', 'tournament', 'radiant_team', 'dire_team',
        'duration_minutes', 'winner', 'radiant_win',
        'hero_name', 'hero_id', 'team',
        'gpm', 'xpm', 'tower_damage', 'hero_healing',
        'lane_efficiency_pct', 'kills', 'deaths', 'assists',
        'last_hits', 'denies', 'net_worth', 'hero_damage', 
        'teamfight_participation', 'actions_per_min', 'won'
    ]
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        rows_written = 0
        for match in matches:
            match_info = {
                'match_id': match['match_id'],
                'tournament': match['tournament'],
                'radiant_team': match['radiant_team'],
                'dire_team': match['dire_team'],
                'duration_minutes': match['duration_minutes'],
                'winner': match['winner'],
                'radiant_win': match['radiant_win']
            }
            
            for player in match.get('players', []):
                row = {**match_info, **player}
                writer.writerow(row)
                rows_written += 1
        
        print(f"✓ Saved {len(matches)} matches ({rows_written} player rows) to {filename}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_checkpoint_data.py <checkpoint_file>")
        print("\nExample:")
        print("  python extract_checkpoint_data.py .opendota_checkpoint_20230401_to_20251119_detailed.json")
        print("\nThis will create:")
        print("  - recovered_matches_TIMESTAMP.json")
        print("  - recovered_matches_TIMESTAMP.csv")
        sys.exit(1)
    
    checkpoint_file = sys.argv[1]
    
    print("="*60)
    print("Checkpoint Data Recovery Tool")
    print("="*60)
    
    # Extract data
    matches = extract_checkpoint(checkpoint_file)
    
    if not matches:
        sys.exit(1)
    
    # Generate output filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"recovered_matches_{timestamp}.json"
    csv_filename = f"recovered_matches_{timestamp}.csv"
    
    # Save to files
    save_to_json(matches, json_filename)
    save_to_csv(matches, csv_filename)
    
    print("\n" + "="*60)
    print("✓ Recovery Complete!")
    print("="*60)
    print(f"\nYour 14 hours of work has been saved to:")
    print(f"  📄 {json_filename}")
    print(f"  📄 {csv_filename}")
    print(f"\n💡 You can now:")
    print(f"  1. Use these files for analysis")
    print(f"  2. Continue fetching remaining matches with the new script")
    print(f"  3. Merge files later if needed")

if __name__ == "__main__":
    main()
