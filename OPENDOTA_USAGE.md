# OpenDota Pro Matches Fetcher

## Overview
This script fetches all professional Dota 2 matches from the OpenDota API for the last 3 months (or custom timeframe) with proper rate limiting.

## Features
- ✅ Rate limited to 600 requests/minute (50% of OpenDota's 1200/min limit)
- ✅ Automatic pagination through all pro matches
- ✅ Date filtering for last N months
- ✅ **Visual progress bars** showing real-time progress and estimates
- ✅ Two-phase fetching with separate progress tracking
- ✅ Optional detailed match data fetching
- ✅ JSON output with timestamp

## Installation

First, install the required dependencies:
```bash
pip3 install -r requirements.txt
```

Or install manually:
```bash
pip3 install requests tqdm
```

## Usage

### Basic Usage (Summary Data Only)
```bash
python3 fetch_opendota_matches.py YOUR_API_KEY
```

This will fetch match summaries (basic info) for the last 3 months.

### Custom Timeframe
```bash
python3 fetch_opendota_matches.py YOUR_API_KEY 6
```

This fetches matches from the last 6 months.

### With Detailed Match Data
```bash
python3 fetch_opendota_matches.py YOUR_API_KEY 3 yes
```

This fetches full match details including player stats, items, etc. **Warning**: This is much slower as it requires 1 API call per match.

## Parameters
1. `API_KEY` (required): Your OpenDota API key
2. `months` (optional, default: 3): Number of months to look back
3. `include_details` (optional, default: no): Set to 'yes', 'true', or '1' to fetch full match details

## Output
The script generates a JSON file with the format:
```
opendota_pro_matches_{months}months_{summary|detailed}_{timestamp}.json
```

Example: `opendota_pro_matches_3months_summary_20251118_143022.json`

## Rate Limiting
- Target: 600 requests per minute (50% of limit)
- Minimum delay between requests: 0.1 seconds
- This ensures we stay well below OpenDota's 1200 req/min limit

## Expected Performance
- **Summary data**: ~100 requests for 3 months (depends on # of pro matches)
- **Detailed data**: 1 request per match + pagination (could be 1000+ requests for 3 months)
- **Time estimate**: 
  - Summary: 1-5 minutes for 3 months
  - Detailed: 10-30 minutes for 3 months (depending on match count)

## Progress Tracking
The script now includes visual progress bars that show:

**Phase 1 (Fetching match list):**
- Number of pages fetched
- Total matches found so far
- Dynamic status updates

**Phase 2 (Fetching details - if enabled):**
- Current match being fetched / Total matches
- Success count vs failed count
- Percentage complete with ETA
- Processing speed (matches/second)

## Data Structure

### Summary Data (from /proMatches endpoint)
Each match contains:
- `match_id`: Unique match identifier
- `start_time`: Unix timestamp
- `duration`: Match duration in seconds
- `radiant_team_id`, `dire_team_id`: Team IDs
- `radiant_name`, `dire_name`: Team names
- `leagueid`: Tournament/league ID
- `league_name`: Tournament/league name
- `radiant_score`, `dire_score`: Final scores
- `radiant_win`: Boolean indicating winner

### Detailed Data (from /matches/{match_id} endpoint)
Includes everything above plus:
- Player stats (kills, deaths, assists, GPM, XPM, etc.)
- Hero picks
- Items purchased
- Ability upgrades
- Detailed timeline data
- And much more...

## Example
```bash
# Fetch last 3 months of pro matches (summary only)
python3 fetch_opendota_matches.py sk-abc123xyz 3

# Output:
# opendota_pro_matches_3months_summary_20251118_143022.json
```

## Notes
- The script includes a safety limit of 10,000 matches per run
- Progress is printed every 100 requests
- Failed requests are logged but don't stop execution
- The script uses session pooling for better performance
