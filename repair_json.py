#!/usr/bin/env python3
"""
Repair corrupted JSON file from interrupted fetch.
Extracts all complete match records and creates valid JSON.
"""

import json
import sys
import os
import re

def repair_json(corrupted_file, repaired_file):
    """
    Repair corrupted JSON by finding last complete match and closing array.
    """
    print("="*70)
    print("JSON Repair Tool - Recover Interrupted Fetch Data")
    print("="*70)
    
    # Read corrupted file as text
    print(f"\n[1/5] Reading corrupted file: {corrupted_file}")
    
    try:
        with open(corrupted_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return None
    
    file_size_mb = len(content) / 1024 / 1024
    print(f"✓ Read {file_size_mb:.1f} MB")
    
    # Find all complete match objects
    print(f"\n[2/5] Searching for complete match records...")
    
    # Strategy: Find all positions where we have complete match objects
    # Each match ends with }
    # We need to find the last valid position before corruption
    
    # Try to parse progressively to find where corruption starts
    matches_found = []
    
    # Remove opening bracket if exists
    if content.strip().startswith('['):
        content = content.strip()[1:]
    
    # Split by lines and try to find complete matches
    # Matches are separated by comma and newline
    print(f"  Attempting to parse matches...")
    
    # Try a different approach: split by },\n and try to parse each chunk
    chunks = re.split(r'\},\s*\n', content)
    
    for i, chunk in enumerate(chunks):
        # Add back the closing brace if not the last chunk
        if i < len(chunks) - 1 or chunk.strip().endswith('}'):
            if not chunk.strip().endswith('}'):
                chunk = chunk + '}'
        
        try:
            # Try to parse this as a match object
            match_obj = json.loads(chunk.strip())
            if 'match_id' in match_obj:
                matches_found.append(match_obj)
        except:
            # This chunk is incomplete or corrupted, skip it
            pass
        
        if (i + 1) % 500 == 0:
            print(f"  Progress: {i + 1} chunks processed, {len(matches_found)} valid matches found")
    
    print(f"✓ Found {len(matches_found)} complete, valid matches")
    
    if not matches_found:
        print(f"✗ Error: No valid matches could be recovered")
        return None
    
    # Validate matches
    print(f"\n[3/5] Validating recovered matches...")
    
    valid_matches = []
    for match in matches_found:
        try:
            # Check required fields
            if all(key in match for key in ['match_id', 'tournament', 'players']):
                valid_matches.append(match)
        except:
            pass
    
    print(f"✓ {len(valid_matches)} matches passed validation")
    
    if len(valid_matches) < len(matches_found):
        print(f"  ⚠ Discarded {len(matches_found) - len(valid_matches)} incomplete matches")
    
    # Write repaired JSON
    print(f"\n[4/5] Writing repaired JSON: {repaired_file}")
    
    try:
        with open(repaired_file, 'w', encoding='utf-8') as f:
            json.dump(valid_matches, f, indent=2)
        print(f"✓ Wrote {len(valid_matches)} matches to repaired file")
    except Exception as e:
        print(f"✗ Error writing file: {e}")
        return None
    
    # Verify repaired file
    print(f"\n[5/5] Verifying repaired file...")
    
    try:
        with open(repaired_file, 'r') as f:
            test_load = json.load(f)
        repaired_size_mb = os.path.getsize(repaired_file) / 1024 / 1024
        print(f"✓ Repaired file is valid JSON")
        print(f"✓ File size: {repaired_size_mb:.1f} MB")
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return None
    
    print("\n" + "="*70)
    print("✓ JSON Repair Complete!")
    print("="*70)
    
    print(f"\n📊 Recovery Summary:")
    print(f"  Original file size: {file_size_mb:.1f} MB")
    print(f"  Repaired file size: {repaired_size_mb:.1f} MB")
    print(f"  Matches recovered: {len(valid_matches)}")
    print(f"  First match ID: {valid_matches[0]['match_id']}")
    print(f"  Last match ID: {valid_matches[-1]['match_id']}")
    
    print(f"\n📁 Files:")
    print(f"  Original (corrupted): {corrupted_file}")
    print(f"  Repaired (valid): {repaired_file}")
    
    print(f"\n🚀 Next step:")
    print(f"  python3 recreate_checkpoint.py {repaired_file}")
    
    return valid_matches

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 repair_json.py <corrupted_json_file> [output_file]")
        print("\nExample:")
        print("  python3 repair_json.py opendota_pro_matches_20230401_to_20251119_detailed_20251120_220924.json")
        print("\nThis will:")
        print("  1. Extract all complete, valid matches from corrupted file")
        print("  2. Create repaired file: opendota_pro_matches_20230401_to_20251119_detailed_20251120_220924_REPAIRED.json")
        print("  3. Allow you to recreate checkpoint from repaired data")
        sys.exit(1)
    
    corrupted_file = sys.argv[1]
    
    # Determine output filename
    if len(sys.argv) > 2:
        repaired_file = sys.argv[2]
    else:
        # Auto-generate: add _REPAIRED before .json
        base = corrupted_file.replace('.json', '')
        repaired_file = f"{base}_REPAIRED.json"
    
    if not os.path.exists(corrupted_file):
        print(f"✗ Error: File not found: {corrupted_file}")
        sys.exit(1)
    
    matches = repair_json(corrupted_file, repaired_file)
    
    if not matches:
        print("\n❌ Repair failed. File may be too corrupted.")
        print("You may need to start fresh (re-fetch all matches).")
        sys.exit(1)

if __name__ == "__main__":
    main()
