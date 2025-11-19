# How to Remap Roles in Existing Files

## Why Use This?
If you already fetched match data with the old script and don't want to waste API credits re-fetching, use the **remap_roles.py** script to fix the role detection in your existing files.

## What It Does
- ✅ Reads your existing JSON file
- ✅ Applies the improved role detection algorithm
- ✅ Fixes Support (pos 4) and Hard Support (pos 5)
- ✅ Adds player_slot field if missing
- ✅ Saves remapped JSON file
- ✅ Generates updated CSV file
- ✅ **No API calls needed!**

## Usage

### Basic Usage (Creates new file)
```bash
python remap_roles.py your_file.json
```

This will create:
- `your_file_remapped.json` - Updated JSON with fixed roles
- `your_file_remapped.csv` - Updated CSV file

### Specify Output Filename
```bash
python remap_roles.py your_file.json fixed_file.json
```

This will create:
- `fixed_file.json` - Updated JSON
- `fixed_file.csv` - Updated CSV

## Example

If your existing file is named:
```
opendota_pro_matches_3months_detailed_20231119_143022.json
```

Run:
```bash
python remap_roles.py opendota_pro_matches_3months_detailed_20231119_143022.json
```

Output:
```
============================================================
OpenDota Match Data - Role Remapper
============================================================

Reading: opendota_pro_matches_3months_detailed_20231119_143022.json
Processing 1234 matches...
  Updated: Crystal Maiden: 'Unknown' → 'Hard Support (pos 5)' (slot 4)
  Updated: Lion: 'Unknown' → 'Support (pos 4)' (slot 3)
  Updated: Vengeful Spirit: 'Unknown' → 'Hard Support (pos 5)' (slot 132)
Progress: 100/1234 matches processed...
Progress: 200/1234 matches processed...
...
✓ Remapped roles in 1234 matches

Saving to: opendota_pro_matches_3months_detailed_20231119_143022_remapped.json
✓ Done! Saved remapped data to: opendota_pro_matches_3months_detailed_20231119_143022_remapped.json

Exporting to CSV: opendota_pro_matches_3months_detailed_20231119_143022_remapped.csv
✓ CSV export complete

============================================================
✓ All done!
============================================================

Role distribution per match should now show:
  • 2x Carry (pos 1)
  • 2x Mid (pos 2)
  • 2x Offlane (pos 3)
  • 2x Support (pos 4)
  • 2x Hard Support (pos 5)
```

## What Gets Fixed

### Before (Old File):
```json
{
  "hero_name": "Crystal Maiden",
  "role": "Unknown",
  "gpm": 250,
  ...
}
```

### After (Remapped):
```json
{
  "hero_name": "Crystal Maiden",
  "role": "Hard Support (pos 5)",
  "player_slot": 4,
  "gpm": 250,
  ...
}
```

## How It Works

The script uses the same improved role detection algorithm:

1. **Checks lane_role** - Works for cores
2. **Falls back to player_slot** - Works for supports
3. **Adds player_slot** - If missing from original data

The `player_slot` field indicates farm priority:
- Radiant: 0-4 (pos 1-5)
- Dire: 128-132 (pos 1-5)

## Features

✅ **No API calls** - Works entirely offline  
✅ **Fast** - Processes thousands of matches in seconds  
✅ **Safe** - Creates new files, doesn't modify originals  
✅ **Verbose** - Shows which heroes got their roles updated  
✅ **Complete** - Generates both JSON and CSV output  

## Notes

- Original file is never modified (unless you specify same filename)
- The script shows progress for large files
- It prints which heroes had their roles changed
- Both JSON and CSV outputs are created automatically
- Works with files containing any number of matches

## Quick Start

Just run this with your existing file:
```bash
python remap_roles.py YOUR_FILE.json
```

That's it! Your roles will be fixed without using any API credits. 🎉
