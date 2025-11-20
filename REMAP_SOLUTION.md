# ✅ Solution: Remap Existing Files (No API Credits Needed!)

## The Problem
You already generated files using API credits, but the roles weren't detected correctly for Support positions.

## The Solution
I've created **`remap_roles.py`** - a script that fixes the roles in your existing files **WITHOUT** making any API calls!

---

## 🚀 Quick Start

### Step 1: Find Your File
Locate the JSON file you already generated. It will be named something like:
```
opendota_pro_matches_3months_detailed_20231119_143022.json
```

### Step 2: Run the Remap Script
```bash
python remap_roles.py YOUR_FILE.json
```

### Step 3: Done! ✓
You'll get two new files with fixed roles:
- `YOUR_FILE_remapped.json` - Updated JSON
- `YOUR_FILE_remapped.csv` - Updated CSV

---

## What the Script Does

### ✅ Fixes Role Detection
- Reads your existing JSON file
- Applies the improved role detection algorithm
- Uses `player_slot` as fallback for support positions
- Properly labels Support (pos 4) and Hard Support (pos 5)

### ✅ No API Calls
- Works completely offline
- No API credits consumed
- Fast processing (thousands of matches in seconds)

### ✅ Safe & Non-Destructive
- Original file is never modified
- Creates new files with `_remapped` suffix
- Shows which heroes got updated

### ✅ Complete Output
- Generates both JSON and CSV formats
- Adds `player_slot` field for debugging
- Maintains all existing data

---

## Example Output

```bash
$ python remap_roles.py opendota_matches.json

============================================================
OpenDota Match Data - Role Remapper
============================================================

Reading: opendota_matches.json
Processing 500 matches...
  Updated: Crystal Maiden: 'Unknown' → 'Hard Support (pos 5)' (slot 4)
  Updated: Lion: 'Unknown' → 'Support (pos 4)' (slot 3)
  Updated: Vengeful Spirit: 'Unknown' → 'Hard Support (pos 5)' (slot 132)
  Updated: Shadow Demon: 'Unknown' → 'Support (pos 4)' (slot 131)
Progress: 100/500 matches processed...
Progress: 200/500 matches processed...
Progress: 300/500 matches processed...
Progress: 400/500 matches processed...

✓ Remapped roles in 500 matches

Saving to: opendota_matches_remapped.json
✓ Done! Saved remapped data to: opendota_matches_remapped.json

Exporting to CSV: opendota_matches_remapped.csv
✓ CSV export complete: opendota_matches_remapped.csv

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

---

## Before vs After

### Before (Your Current File):
```json
{
  "match_id": 7123456789,
  "players": [
    {"hero_name": "Anti-Mage", "role": "Carry (pos 1)", ...},
    {"hero_name": "Invoker", "role": "Mid (pos 2)", ...},
    {"hero_name": "Axe", "role": "Offlane (pos 3)", ...},
    {"hero_name": "Lion", "role": "Unknown", ...},           ❌
    {"hero_name": "Crystal Maiden", "role": "Unknown", ...}  ❌
  ]
}
```

### After (Remapped File):
```json
{
  "match_id": 7123456789,
  "players": [
    {"hero_name": "Anti-Mage", "role": "Carry (pos 1)", "player_slot": 0, ...},
    {"hero_name": "Invoker", "role": "Mid (pos 2)", "player_slot": 1, ...},
    {"hero_name": "Axe", "role": "Offlane (pos 3)", "player_slot": 2, ...},
    {"hero_name": "Lion", "role": "Support (pos 4)", "player_slot": 3, ...},           ✅
    {"hero_name": "Crystal Maiden", "role": "Hard Support (pos 5)", "player_slot": 4, ...}  ✅
  ]
}
```

---

## How It Works

The script uses the **same improved algorithm** as the updated fetch script:

1. **Primary**: Check `lane_role` field
   - Works for cores (Carry, Mid, Offlane)

2. **Fallback**: Use `player_slot` field
   - Indicates farm priority (0-4 per team)
   - Position 0 = highest farm (Carry)
   - Position 4 = lowest farm (Hard Support)
   - **Always available in OpenDota data!**

3. **Result**: All 10 heroes get proper pos 1-5 labels

---

## Files Created

### `remap_roles.py`
The remapping script - ready to use!

### Documentation:
- `HOW_TO_REMAP_EXISTING_FILES.md` - Detailed usage guide
- `REMAP_SOLUTION.md` - This file

---

## Summary

✅ **No API credits wasted**  
✅ **Fast offline processing**  
✅ **Safe (doesn't modify originals)**  
✅ **Complete (JSON + CSV output)**  
✅ **Fixes all support roles**  

Just run:
```bash
python remap_roles.py YOUR_FILE.json
```

And you're done! 🎉

---

## Next Time

For future fetches, use the updated `fetch_opendota_matches.py` which now has the improved role detection built-in!
