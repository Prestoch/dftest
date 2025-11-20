# Changes Summary for fetch_opendota_matches.py

## Overview
Modified `fetch_opendota_matches.py` to extract only specific Dota 2 match data fields as requested.

## Key Changes

### 1. Added Hero Name Mapping
- Added `_load_hero_names()` method that loads hero ID to name mapping
- Loads from local `hero_id_map.json` file if available
- Falls back to fetching from OpenDota API if file not found
- Automatically converts hero IDs to readable hero names

### 2. Added Role/Position Mapping
- New `_get_role_name()` method converts lane_role numbers to descriptive names:
  - 1 → "Carry (pos 1)"
  - 2 → "Mid (pos 2)"
  - 3 → "Offlane (pos 3)"
  - 4 → "Support (pos 4)"
  - 5 → "Hard Support (pos 5)"

### 3. New Data Extraction Method
- Added `extract_match_data()` method that extracts only the required fields:
  - **Match Level**: match_id, tournament, team names, duration, winner
  - **Player Level**: hero name, role, GPM, XPM, tower damage, healing, lane advantages, K/D/A, won status

### 4. CSV Export Functionality
- New `save_matches_csv()` method exports data to CSV format
- Flattened structure: one row per player
- Includes both match-level and player-level data in each row
- Useful for data analysis in Excel, pandas, etc.

### 5. Updated Default Behavior
- Changed default to `include_details=True` (was False before)
- Now fetches detailed match data by default since that's needed for the requested fields
- Users can still disable with 'no' parameter

### 6. Improved Output
- Updated help text to show what data is fetched
- Better statistics output for detailed matches
- Shows sample data from first match
- Displays tournament count and player count

## Data Fields Extracted

### Required Fields (All Implemented)
✅ 1. Match ID  
✅ 2. Team/Tournament Names  
✅ 3. Name of heroes  
✅ 4. Hero roles (e.g. Carry (pos 1), Mid (pos 2)...)  
✅ 5. Hero's GPM  
✅ 6. Hero's XPM  
✅ 7. Hero's Tower Damage  
✅ 8. Hero's Healing  
✅ 9. Hero's Lane advantages  
✅ 10. Hero's Kills/Death/Assist  
✅ 11. Hero's Game Duration  
✅ 12. Match Winner  

## Usage Examples

```bash
# Fetch detailed data for last 3 months (default behavior)
python fetch_opendota_matches.py YOUR_API_KEY

# Fetch detailed data for last 6 months
python fetch_opendota_matches.py YOUR_API_KEY 6

# Fetch only summaries without details
python fetch_opendota_matches.py YOUR_API_KEY 3 no
```

## Output Files

Each run now produces TWO files:
1. **JSON**: Full nested structure with match info and player array
2. **CSV**: Flattened structure with one row per player

Files are named:
- `opendota_pro_matches_3months_detailed_20231119_143022.json`
- `opendota_pro_matches_3months_detailed_20231119_143022.csv`

## Technical Notes

- Maintains the same rate limiting (600 req/min)
- Handles missing data gracefully with default values
- Properly maps hero IDs to names using local or API data
- Determines player's team and win status correctly
- Extracts lane efficiency percentage for lane advantages
- Converts game duration to both seconds and minutes

## Backward Compatibility

- Script still works with the same command-line interface
- Can still fetch match summaries if needed (with 'no' parameter)
- All existing functionality preserved
- Only the data extraction and output format changed
