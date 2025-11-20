# Fetched Data Structure

## Overview
The script `fetch_opendota_matches.py` has been modified to fetch only specific fields from Dota 2 pro matches via the OpenDota API.

## Data Fields Extracted

### Match-Level Information
1. **Match ID** - Unique identifier for the match
2. **Tournament** - Tournament/league name
3. **Radiant Team** - Name of the Radiant team
4. **Dire Team** - Name of the Dire team
5. **Duration** - Game duration in seconds and minutes
6. **Winner** - Name of the winning team
7. **Radiant Win** - Boolean indicating if Radiant won

### Player/Hero-Level Information (per player)
1. **Hero Name** - Name of the hero played
2. **Hero ID** - Unique hero identifier
3. **Team** - Team the player is on
4. **Role** - Hero role/position:
   - Carry (pos 1)
   - Mid (pos 2)
   - Offlane (pos 3)
   - Support (pos 4)
   - Hard Support (pos 5)
5. **GPM** - Gold per minute
6. **XPM** - Experience per minute
7. **Tower Damage** - Total damage dealt to towers
8. **Hero Healing** - Total healing done
9. **Lane Efficiency %** - Lane phase efficiency percentage
10. **Kills** - Number of kills
11. **Deaths** - Number of deaths
12. **Assists** - Number of assists
13. **Won** - Boolean indicating if this player won

## Output Format

### JSON Structure
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
    },
    // ... 9 more players (5 per team)
  ]
}
```

### CSV Structure
The CSV export flattens the data with one row per player:

| match_id | tournament | radiant_team | dire_team | duration_minutes | winner | radiant_win | hero_name | hero_id | team | role | gpm | xpm | tower_damage | hero_healing | lane_efficiency_pct | kills | deaths | assists | won |
|----------|------------|--------------|-----------|------------------|--------|-------------|-----------|---------|------|------|-----|-----|--------------|--------------|---------------------|-------|--------|---------|-----|
| 7123456789 | The International 2023 | Team Secret | OG | 35.75 | Team Secret | true | Anti-Mage | 1 | Team Secret | Carry (pos 1) | 650 | 725 | 8500 | 0 | 0.82 | 12 | 2 | 8 | true |

## Usage

```bash
# Fetch detailed match data for last 3 months (default)
python fetch_opendota_matches.py YOUR_API_KEY

# Fetch detailed match data for last 6 months
python fetch_opendota_matches.py YOUR_API_KEY 6

# Fetch only match summaries (without detailed player data)
python fetch_opendota_matches.py YOUR_API_KEY 3 no
```

## Output Files

The script generates two files:
1. **JSON file**: `opendota_pro_matches_Xmonths_detailed_TIMESTAMP.json`
2. **CSV file**: `opendota_pro_matches_Xmonths_detailed_TIMESTAMP.csv`

Both files contain the same data, just in different formats for different use cases.

## Notes

- The script automatically loads hero names from `hero_id_map.json` if available
- If the hero map file is not found, it will fetch hero names from the OpenDota API
- Rate limiting is set to 600 requests/minute (50% of the API limit) to be safe
- Detailed fetching is now enabled by default since it's required for the specific fields
