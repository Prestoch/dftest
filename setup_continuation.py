#!/usr/bin/env python3
"""
Setup continuation from old checkpoint:
1. Converts old checkpoint to new format (just match IDs)
2. Extracts existing matches to properly formatted starter files
3. New script will resume from these files

This saves API credits by not re-fetching already fetched matches.
"""

import json
import csv
import sys
import os
from datetime import datetime

def setup_continuation(old_checkpoint_file):
    """
    Convert checkpoint and create starter files for continuation.
    """
    print("="*70)
    print("Setup Continuation from Old Checkpoint")
    print("="*70)
    
    # Read old checkpoint
    print(f"\n[1/4] Reading old checkpoint: {old_checkpoint_file}")
    
    try:
        with open(old_checkpoint_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"✗ Error: Checkpoint file not found!")
        return False
    except Exception as e:
        print(f"✗ Error reading checkpoint: {e}")
        return False
    
    matches = data.get('matches', [])
    if not matches:
        print(f"✗ Error: No matches found in checkpoint")
        return False
    
    print(f"✓ Found {len(matches)} matches")
    
    # Extract match IDs
    print(f"\n[2/4] Converting to new checkpoint format...")
    match_ids = [m['match_id'] for m in matches]
    
    # Create new checkpoint format
    new_checkpoint_data = {
        'fetched_match_ids': match_ids,
        'timestamp': datetime.now().isoformat(),
        'total_matches': len(match_ids)
    }
    
    # Save new checkpoint (overwrite old one)
    with open(old_checkpoint_file, 'w') as f:
        json.dump(new_checkpoint_data, f)
    
    print(f"✓ Converted checkpoint (now {len(match_ids)} match IDs only)")
    print(f"✓ Checkpoint size reduced: ~{len(json.dumps(data))//1024//1024}MB → ~{len(json.dumps(new_checkpoint_data))//1024}KB")
    
    # Determine output filenames based on checkpoint name
    # .opendota_checkpoint_20230401_to_20251119_detailed.json
    # → opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.json
    checkpoint_base = os.path.basename(old_checkpoint_file)
    parts = checkpoint_base.replace('.opendota_checkpoint_', '').replace('.json', '')
    
    json_filename = f"opendota_pro_matches_{parts}_CONTINUING.json"
    csv_filename = f"opendota_pro_matches_{parts}_CONTINUING.csv"
    
    # Create starter JSON file
    print(f"\n[3/4] Creating starter JSON file: {json_filename}")
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        f.write('[\n')
        for i, match in enumerate(matches):
            if i > 0:
                f.write(',\n')
            f.write('  ' + json.dumps(match))
        # Don't close array - new script will append more and close it
    
    print(f"✓ Created JSON with {len(matches)} matches (open array for appending)")
    
    # Create starter CSV file
    print(f"\n[4/4] Creating starter CSV file: {csv_filename}")
    
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
    
    print(f"✓ Created CSV with {len(matches)} matches ({rows_written} player rows)")
    
    # Create metadata file with filenames
    metadata = {
        'checkpoint_file': old_checkpoint_file,
        'json_output': json_filename,
        'csv_output': csv_filename,
        'matches_saved': len(matches),
        'setup_timestamp': datetime.now().isoformat()
    }
    
    metadata_file = '.continuation_metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n✓ Created metadata file: {metadata_file}")
    
    # Print summary
    print("\n" + "="*70)
    print("✓ Setup Complete! Ready for Continuation")
    print("="*70)
    
    print(f"\n📊 Summary:")
    print(f"  Checkpoint: {old_checkpoint_file}")
    print(f"  - Converted to new format (match IDs only)")
    print(f"  - Contains {len(match_ids)} already-fetched matches")
    
    print(f"\n📁 Starter files created:")
    print(f"  - {json_filename}")
    print(f"  - {csv_filename}")
    print(f"  - These contain your existing {len(matches)} matches")
    
    print(f"\n🚀 Next step - Run the new script WITH special flag:")
    print(f"\n  python fetch_opendota_matches.py YOUR_API_KEY \\")
    print(f"    from=2023-04-01 to=2025-11-19 \\")
    print(f"    skip=\"ultras,lunar,mad dogs,destiny,dota 2 space,impacto,ancients\" \\")
    print(f"    continue=yes")
    
    print(f"\n💡 What will happen:")
    print(f"  ✓ Script loads checkpoint ({len(match_ids)} match IDs)")
    print(f"  ✓ Skips these {len(match_ids)} matches (saves API credits!)")
    print(f"  ✓ Fetches remaining ~{80382 - len(match_ids):,} matches")
    print(f"  ✓ Appends to {json_filename}")
    print(f"  ✓ Appends to {csv_filename}")
    print(f"  ✓ Final files will have ALL ~80,000 matches")
    
    print(f"\n⚡ Memory-safe streaming writes + No wasted API credits!")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python setup_continuation.py <old_checkpoint_file>")
        print("\nExample:")
        print("  python setup_continuation.py .opendota_checkpoint_20230401_to_20251119_detailed.json")
        print("\nThis will:")
        print("  1. Convert checkpoint to new lightweight format")
        print("  2. Create starter JSON/CSV files with your existing matches")
        print("  3. Prepare for continuation without re-fetching")
        print("\nAfter running this, use the new script with continue=yes flag")
        sys.exit(1)
    
    old_checkpoint_file = sys.argv[1]
    
    if not os.path.exists(old_checkpoint_file):
        print(f"✗ Error: File not found: {old_checkpoint_file}")
        print(f"\nAvailable checkpoint files:")
        for f in os.listdir('.'):
            if f.startswith('.opendota_checkpoint_'):
                print(f"  {f}")
        sys.exit(1)
    
    success = setup_continuation(old_checkpoint_file)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
