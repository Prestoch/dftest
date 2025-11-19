# Updated fetch_opendota_matches.py

## Summary
The script has been successfully updated to fetch **only** the specific Dota 2 match data fields you requested.

## What Changed

### ✅ All Requested Fields Are Now Extracted:

1. **Match ID** - Unique match identifier
2. **Team/Tournament Names** - League name and team names (Radiant & Dire)
3. **Name of heroes** - Hero names automatically mapped from IDs
4. **Hero roles** - Position names (Carry pos 1, Mid pos 2, Offlane pos 3, Support pos 4, Hard Support pos 5)
5. **Hero's GPM** - Gold per minute
6. **Hero's XPM** - Experience per minute
7. **Hero's Tower Damage** - Total tower damage
8. **Hero's Healing** - Total hero healing
9. **Hero's Lane advantages** - Lane efficiency percentage
10. **Hero's Kills/Death/Assist** - Full K/D/A stats
11. **Hero's Game Duration** - Duration in both seconds and minutes
12. **Match Winner** - Winning team name and boolean flag

## New Features

### 1. Automatic Hero Name Mapping
- Loads hero names from `hero_id_map.json` (already in your workspace)
- Falls back to API if file not available
- Converts hero IDs (like `1`) to names (like `Anti-Mage`)

### 2. Role/Position Labels
- Converts numeric lane_role to readable format
- Examples: "Carry (pos 1)", "Mid (pos 2)", etc.

### 3. Dual Output Format
The script now generates **TWO** files per run:
- **JSON file**: Structured data with nested player arrays
- **CSV file**: Flattened data (one row per player) for easy analysis in Excel/pandas

### 4. Default Behavior Changed
- Now fetches detailed data **by default** (since that's needed for your fields)
- No need to specify `yes` for detailed data anymore

## Usage

```bash
# Basic usage - fetch last 3 months (detailed data by default)
python fetch_opendota_matches.py YOUR_API_KEY

# Fetch last 6 months
python fetch_opendota_matches.py YOUR_API_KEY 6

# Fetch last 1 month
python fetch_opendota_matches.py YOUR_API_KEY 1

# Get only match summaries without details (if needed)
python fetch_opendota_matches.py YOUR_API_KEY 3 no
```

## Output Files

Each run creates two files:

### 1. JSON File
```
opendota_pro_matches_3months_detailed_20231119_143022.json
```

Structure:
```json
{
  "match_id": 7123456789,
  "tournament": "The International 2023",
  "radiant_team": "Team Secret",
  "dire_team": "OG",
  "duration_seconds": 2145,
  "duration_minutes": 35.75,
  "radiant_win": true,
  "winner": "Team Secret",
  "players": [
    {
      "hero_name": "Anti-Mage",
      "hero_id": 1,
      "team": "Team Secret",
      "role": "Carry (pos 1)",
      "gpm": 650,
      "xpm": 725,
      "tower_damage": 8500,
      "hero_healing": 0,
      "lane_efficiency_pct": 0.82,
      "kills": 12,
      "deaths": 2,
      "assists": 8,
      "won": true
    }
    // ... 9 more players
  ]
}
```

### 2. CSV File
```
opendota_pro_matches_3months_detailed_20231119_143022.csv
```

One row per player with columns:
- match_id, tournament, radiant_team, dire_team, duration_minutes, winner, radiant_win
- hero_name, hero_id, team, role
- gpm, xpm, tower_damage, hero_healing, lane_efficiency_pct
- kills, deaths, assists, won

## Example Run

```bash
$ python fetch_opendota_matches.py YOUR_API_KEY 1

============================================================
Fetching pro matches since 2023-10-19
Rate limit: 600 requests/minute
Include details: True

Phase 1: Fetching match list...
Fetching pages: 100%|████████| 15/15 [00:02<00:00]
✓ Fetched 1,234 pro matches in 3.5 seconds
  Made 15 API requests
  Average rate: 257.1 requests/minute

Phase 2: Fetching detailed data for 1,234 matches...
This will take a while...

Fetching details: 100%|████████| 1234/1234 [04:15<00:00]
✓ Fetched details for 1234/1234 matches
============================================================

Saved 1234 matches to opendota_pro_matches_1months_detailed_20231119_143022.json
Saved 1234 matches to CSV: opendota_pro_matches_1months_detailed_20231119_143022.csv

Match Statistics:
  Total matches: 1234
  Total players/heroes: 12340
  Unique tournaments: 45

  Sample data from first match (ID: 7123456789):
    Tournament: The International 2023
    Teams: Team Secret vs OG
    Winner: Team Secret
    Duration: 35.75 minutes
    Players: 10 heroes

Done!
```

## Technical Details

- **Rate Limiting**: 600 requests/minute (50% of API limit for safety)
- **Progress Bars**: Uses `tqdm` for real-time progress tracking
- **Error Handling**: Gracefully handles missing data and API failures
- **Hero Names**: Automatically loaded from local file or API
- **Data Validation**: All fields have default values if missing

## Files in Workspace

- `fetch_opendota_matches.py` - **Updated main script** ✅
- `hero_id_map.json` - Hero ID to name mapping (used by script)
- `FETCHED_DATA_STRUCTURE.md` - Detailed data structure documentation
- `CHANGES_SUMMARY.md` - Summary of all changes made
- `README_UPDATED_SCRIPT.md` - This file

## Notes

- The script **automatically** extracts only the fields you specified
- **No manual filtering** needed - data is pre-filtered
- Both JSON and CSV formats available for different use cases
- CSV is ideal for Excel, pandas, or database import
- JSON preserves the hierarchical match → players structure

## Next Steps

1. Get your OpenDota API key from: https://www.opendota.com/api-keys
2. Run the script: `python fetch_opendota_matches.py YOUR_API_KEY`
3. Wait for it to complete (can take several minutes for many matches)
4. Find your data in the generated `.json` and `.csv` files

That's it! The script is ready to use. 🚀
