#!/usr/bin/env python3
"""
Recreate checkpoint file from existing JSON data file.
This allows resuming without re-fetching already downloaded matches.
"""

import json
import sys
import os

def recreate_checkpoint(json_file, checkpoint_file):
    """
    Extract match IDs from JSON file and create checkpoint.
    """
    print("="*70)
    print("Recreate Checkpoint from Existing Data")
    print("="*70)
    
    # Read JSON file
    print(f"\n[1/3] Reading JSON file: {json_file}")
    
    try:
        with open(json_file, 'r') as f:
            matches = json.load(f)
    except FileNotFoundError:
        print(f"✗ Error: File not found: {json_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return False
    
    if not matches:
        print(f"✗ Error: No matches found in file")
        return False
    
    print(f"✓ Found {len(matches)} matches in file")
    
    # Extract match IDs
    print(f"\n[2/3] Extracting match IDs...")
    
    try:
        match_ids = [m['match_id'] for m in matches]
        print(f"✓ Extracted {len(match_ids)} match IDs")
    except KeyError:
        print(f"✗ Error: Invalid match format (missing match_id)")
        return False
    
    # Create checkpoint
    print(f"\n[3/3] Creating checkpoint: {checkpoint_file}")
    
    checkpoint_data = {
        'fetched_match_ids': match_ids,
        'timestamp': 'Recreated from existing data',
        'total_matches': len(match_ids)
    }
    
    try:
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f)
        print(f"✓ Checkpoint created successfully")
    except Exception as e:
        print(f"✗ Error creating checkpoint: {e}")
        return False
    
    # Verify checkpoint
    checkpoint_size = os.path.getsize(checkpoint_file)
    print(f"✓ Checkpoint file size: {checkpoint_size / 1024:.1f} KB")
    
    print("\n" + "="*70)
    print("✓ Checkpoint Recreation Complete!")
    print("="*70)
    
    print(f"\n📊 Summary:")
    print(f"  Matches in checkpoint: {len(match_ids)}")
    print(f"  First match ID: {match_ids[0]}")
    print(f"  Last match ID: {match_ids[-1]}")
    
    print(f"\n📁 Files:")
    print(f"  Data: {json_file}")
    print(f"  Checkpoint: {checkpoint_file}")
    
    print(f"\n🚀 Next step - Resume fetching:")
    print(f"\n  python3 fetch_opendota_matches.py YOUR_API_KEY \\")
    print(f"    from=2023-04-01 to=2025-11-19 \\")
    print(f"    skip=\"ultras,lunar,mad dogs,destiny,dota 2 space,impacto,ancients\"")
    
    print(f"\n💡 What will happen:")
    print(f"  ✓ Script loads checkpoint ({len(match_ids)} match IDs)")
    print(f"  ✓ Skips these {len(match_ids)} matches (saves API credits!)")
    print(f"  ✓ Fetches remaining ~{80382 - len(match_ids):,} matches")
    print(f"  ✓ Creates NEW output files (your existing files remain safe)")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 recreate_checkpoint.py <json_file> [checkpoint_file]")
        print("\nExample:")
        print("  python3 recreate_checkpoint.py opendota_pro_matches_20230401_to_20251119_detailed_20251120_220924.json")
        print("\nThis will:")
        print("  1. Read match IDs from your existing JSON file")
        print("  2. Create checkpoint file: .opendota_checkpoint_20230401_to_20251119_detailed.json")
        print("  3. Allow resuming without re-fetching already downloaded matches")
        sys.exit(1)
    
    json_file = sys.argv[1]
    
    # Determine checkpoint filename
    if len(sys.argv) > 2:
        checkpoint_file = sys.argv[2]
    else:
        # Auto-generate checkpoint filename based on JSON filename
        # opendota_pro_matches_20230401_to_20251119_detailed_20251120_220924.json
        # → .opendota_checkpoint_20230401_to_20251119_detailed.json
        import re
        match = re.search(r'(\d{8})_to_(\d{8})_detailed', json_file)
        if match:
            checkpoint_file = f".opendota_checkpoint_{match.group(1)}_to_{match.group(2)}_detailed.json"
        else:
            checkpoint_file = ".opendota_checkpoint_restored.json"
    
    if not os.path.exists(json_file):
        print(f"✗ Error: File not found: {json_file}")
        print(f"\nAvailable JSON files:")
        for f in os.listdir('.'):
            if f.startswith('opendota_pro_matches_') and f.endswith('.json'):
                size = os.path.getsize(f)
                print(f"  {f} ({size / 1024 / 1024:.1f} MB)")
        sys.exit(1)
    
    success = recreate_checkpoint(json_file, checkpoint_file)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
