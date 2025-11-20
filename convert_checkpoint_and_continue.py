#!/usr/bin/env python3
"""
Convert old checkpoint format to new format and prepare files for continuation.
This allows resuming with the new streaming script without re-fetching already fetched matches.
"""

import json
import csv
import sys
import os
from datetime import datetime

def convert_checkpoint(old_checkpoint_file, new_checkpoint_file):
    """
    Convert old checkpoint (full match data) to new checkpoint (just match IDs).
    
    Returns:
        tuple: (matches_data, match_ids_set)
    """
    print(f"Reading old checkpoint: {old_checkpoint_file}")
    
    try:
        with open(old_checkpoint_file, 'r') as f:
            data = json.load(f)
        
        matches = data.get('matches', [])
        match_ids = [m['match_id'] for m in matches]
        
        print(f"✓ Found {len(matches)} matches in old checkpoint")
        print(f"✓ Extracted {len(match_ids)} match IDs")
        
        # Create new checkpoint format (lightweight - just IDs)
        new_checkpoint_data = {
            'fetched_match_ids': match_ids,
            'timestamp': datetime.now().isoformat(),
            'total_matches': len(match_ids)
        }
        
        # Save new checkpoint
        with open(new_checkpoint_file, 'w') as f:
            json.dump(new_checkpoint_data, f)
        
        print(f"✓ Converted checkpoint saved to: {new_checkpoint_file}")
        
        return matches, set(match_ids)
        
    except FileNotFoundError:
        print(f"✗ Checkpoint file not found: {old_checkpoint_file}")
        return None, None
    except Exception as e:
        print(f"✗ Error reading checkpoint: {e}")
        return None, None

def create_initial_json(matches, json_filename):
    """
    Create initial JSON file properly formatted for appending.
    Format: [ match1, match2, match3  <-- no closing bracket yet
    """
    print(f"\nCreating initial JSON file: {json_filename}")
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        f.write('[\n')
        
        for i, match in enumerate(matches):
            if i > 0:
                f.write(',\n')
            f.write('  ' + json.dumps(match))
        
        # Don't write closing bracket - new script will add more matches then close it
    
    print(f"✓ Created {json_filename} with {len(matches)} matches (ready for appending)")

def create_initial_csv(matches, csv_filename):
    """
    Create initial CSV file with all existing matches.
    CSV can just be appended to normally.
    """
    print(f"\nCreating initial CSV file: {csv_filename}")
    
    fieldnames = [
        'match_id', 'tournament', 'radiant_team', 'dire_team',
        'duration_minutes', 'winner', 'radiant_win',
        'hero_name', 'hero_id', 'team',
        'gpm', 'xpm', 'tower_damage', 'hero_healing',
        'lane_efficiency_pct', 'kills', 'deaths', 'assists',
        'last_hits', 'denies', 'net_worth', 'hero_damage', 
        'teamfight_participation', 'actions_per_min', 'won'
    ]
    
    rows_written = 0
    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
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
    
    print(f"✓ Created {csv_filename} with {len(matches)} matches ({rows_written} player rows)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_checkpoint_and_continue.py <old_checkpoint_file> [output_base_name]")
        print("\nExample:")
        print("  python convert_checkpoint_and_continue.py .opendota_checkpoint_20230401_to_20251119_detailed.json")
        print("\nThis will:")
        print("  1. Convert checkpoint to new format (match IDs only)")
        print("  2. Create initial JSON/CSV files with your existing 21,370 matches")
        print("  3. Prepare for continuation with the new streaming script")
        print("\nThen run:")
        print("  python fetch_opendota_matches.py YOUR_KEY from=2023-04-01 to=2025-11-19 skip=\"...\"")
        sys.exit(1)
    
    old_checkpoint_file = sys.argv[1]
    
    # Determine output base name
    if len(sys.argv) > 2:
        base_name = sys.argv[2]
    else:
        # Extract date range from checkpoint filename
        # .opendota_checkpoint_20230401_to_20251119_detailed.json
        parts = os.path.basename(old_checkpoint_file).replace('.opendota_checkpoint_', '').replace('.json', '')
        base_name = f"opendota_pro_matches_{parts}"
    
    # Generate filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"{base_name}_{timestamp}.json"
    csv_filename = f"{base_name}_{timestamp}.csv"
    new_checkpoint_file = old_checkpoint_file  # Keep same name for new format
    
    print("="*60)
    print("Checkpoint Conversion & Continuation Setup")
    print("="*60)
    
    # Convert checkpoint
    matches, match_ids = convert_checkpoint(old_checkpoint_file, new_checkpoint_file + '.new')
    
    if not matches:
        sys.exit(1)
    
    # Create initial files
    create_initial_json(matches, json_filename)
    create_initial_csv(matches, csv_filename)
    
    # Replace old checkpoint with new format
    if os.path.exists(new_checkpoint_file + '.new'):
        os.replace(new_checkpoint_file + '.new', new_checkpoint_file)
        print(f"\n✓ Checkpoint converted to new format: {new_checkpoint_file}")
    
    print("\n" + "="*60)
    print("✓ Setup Complete!")
    print("="*60)
    
    print(f"\n📁 Files created:")
    print(f"  {json_filename}")
    print(f"  {csv_filename}")
    print(f"  {new_checkpoint_file} (converted)")
    
    print(f"\n💾 Your existing data:")
    print(f"  {len(matches)} matches successfully saved")
    print(f"  {len(matches) * 10} player records")
    
    print(f"\n🚀 Next steps:")
    print(f"  The new streaming script will:")
    print(f"  1. Load checkpoint ({len(matches)} match IDs)")
    print(f"  2. Skip these matches (saves API credits!)")
    print(f"  3. Fetch only NEW matches (remaining ~59,000)")
    print(f"  4. Append to your existing files")
    
    print(f"\n⚠️  IMPORTANT: Use these exact filenames when running new script:")
    print(f"  The script needs to know which files to append to.")
    print(f"\n  Run this command:")
    print(f"  python fetch_opendota_matches.py YOUR_KEY \\")
    print(f"    from=2023-04-01 to=2025-11-19 \\")
    print(f"    skip=\"ultras,lunar,mad dogs,destiny,dota 2 space,impacto,ancients\"")
    
    print(f"\n  The checkpoint file will tell it to skip your {len(matches)} matches!")
    print(f"  Files will be created with proper names automatically.")

if __name__ == "__main__":
    main()
