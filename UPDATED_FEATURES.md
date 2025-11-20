# ✅ Updated Script Features

## Changes Made

### 1. ❌ Removed Role Detection
**Why**: Role detection was statistical inference, not official OpenDota data. Better to provide raw stats only.

**Removed**:
- All role/position fields (pos 1-5)
- `_get_role_name()` method
- `_determine_role_by_stats()` method

**Result**: Cleaner, more honest data - just the facts!

### 2. ✅ Added Tournament Filtering
**Why**: Save API credits by skipping tournaments you don't need.

**How it works**:
```bash
# Skip all DPC tournaments
python fetch_opendota_matches.py YOUR_KEY 3 yes "DPC"

# Skip multiple tournament types
python fetch_opendota_matches.py YOUR_KEY 3 yes "DPC,Regional,Qualifier"
```

**Features**:
- Case-insensitive matching
- Partial name matching (e.g., "dpc" matches "DPC WEU 2023")
- Comma-separated list
- Skips before fetching detailed data (saves API credits!)

---

## What Data You Get Now

### Match-Level Data:
1. ✅ Match ID
2. ✅ Tournament name
3. ✅ Team names (Radiant & Dire)
4. ✅ Duration (seconds & minutes)
5. ✅ Winner
6. ✅ Radiant win boolean

### Hero-Level Data (per player):
1. ✅ Hero name
2. ✅ Hero ID
3. ✅ Team
4. ✅ Player slot
5. ✅ **GPM** (Gold per minute)
6. ✅ **XPM** (Experience per minute)
7. ✅ **Tower damage**
8. ✅ **Hero healing**
9. ✅ **Lane efficiency %** (lane advantages)
10. ✅ **Kills/Deaths/Assists**
11. ✅ **Won** (did this player win?)

### NOT Included:
- ❌ Role/position labels (pos 1-5) - not reliable
- ❌ Statistical inference
- ❌ Guessed data

---

## Usage Examples

### Basic Usage
```bash
# Fetch last 3 months
python fetch_opendota_matches.py YOUR_API_KEY
```

### Fetch Specific Time Range
```bash
# Fetch last 6 months
python fetch_opendota_matches.py YOUR_API_KEY 6

# Fetch last 1 month
python fetch_opendota_matches.py YOUR_API_KEY 1
```

### Skip Tournaments (Save API Credits)
```bash
# Skip DPC tournaments
python fetch_opendota_matches.py YOUR_API_KEY 3 yes "DPC"

# Skip multiple types
python fetch_opendota_matches.py YOUR_API_KEY 3 yes "Regional,Qualifier,Open"

# Skip specific organizers
python fetch_opendota_matches.py YOUR_API_KEY 3 yes "BTS,ESL,DreamLeague"
```

---

## How Tournament Filtering Works

### Step 1: See Available Tournaments
```bash
# First, fetch a summary to see what tournaments exist
python fetch_opendota_matches.py YOUR_KEY 3 no

# Or use the list_tournaments.py helper on existing data
python list_tournaments.py your_existing_file.json
```

### Step 2: Choose What to Skip
Look at the tournament names and decide which to skip.

### Step 3: Fetch with Filters
```bash
python fetch_opendota_matches.py YOUR_KEY 3 yes "unwanted,terms"
```

### What Gets Skipped
- Match list is still fetched (minimal API cost)
- But detailed data is NOT fetched for filtered tournaments
- Saves the expensive `/matches/{match_id}` API calls
- Shows you how many matches were skipped

---

## Helper Script: list_tournaments.py

Use this to see what tournaments are in your data:

```bash
python list_tournaments.py your_file.json
```

**Output**:
```
TOURNAMENTS IN FILE
======================================================================
Matches    Tournament Name
----------------------------------------------------------------------
150        The International 2023
87         DPC WEU Tour 3
65         ESL One Berlin
42         BTS Pro Series
...
----------------------------------------------------------------------
Total: 45 unique tournaments, 1234 matches
```

This helps you decide what to skip next time!

---

## Output Files

### JSON Format
```json
{
  "match_id": 8522266954,
  "tournament": "Americas Convergence Series 1",
  "radiant_team": "TeamCompromiso",
  "dire_team": "LAVA SPORT",
  "duration_seconds": 1410,
  "duration_minutes": 23.5,
  "radiant_win": true,
  "winner": "TeamCompromiso",
  "players": [
    {
      "hero_name": "Juggernaut",
      "hero_id": 8,
      "team": "TeamCompromiso",
      "player_slot": 0,
      "gpm": 763,
      "xpm": 745,
      "tower_damage": 9333,
      "hero_healing": 8069,
      "lane_efficiency_pct": 94,
      "kills": 5,
      "deaths": 0,
      "assists": 7,
      "won": true
    }
    // ... 9 more players
  ]
}
```

### CSV Format
One row per player:

| match_id | tournament | radiant_team | dire_team | duration_minutes | winner | radiant_win | hero_name | hero_id | team | player_slot | gpm | xpm | tower_damage | hero_healing | lane_efficiency_pct | kills | deaths | assists | won |
|----------|------------|--------------|-----------|------------------|--------|-------------|-----------|---------|------|-------------|-----|-----|--------------|--------------|---------------------|-------|--------|---------|-----|
| 8522266954 | Americas... | TeamCompromiso | LAVA SPORT | 23.5 | TeamCompromiso | true | Juggernaut | 8 | TeamCompromiso | 0 | 763 | 745 | 9333 | 8069 | 94 | 5 | 0 | 7 | true |

---

## Benefits of Changes

### 1. More Honest Data
✅ No inference, no guessing  
✅ Only factual OpenDota data  
✅ Raw stats you can analyze yourself  

### 2. Cost Savings
✅ Skip unwanted tournaments  
✅ Save API credits  
✅ Faster fetching (fewer API calls)  

### 3. Flexibility
✅ Filter by tournament type  
✅ Filter by organizer  
✅ Filter by region  
✅ Any partial name match works  

### 4. Transparency
✅ Shows how many matches skipped  
✅ Clear what data you're getting  
✅ No hidden inferences  

---

## Example Workflow

### 1. Explore Available Data
```bash
# Fetch summary (fast, cheap)
python fetch_opendota_matches.py YOUR_KEY 3 no
```

### 2. Identify Tournaments
Look at the output or use `list_tournaments.py`

### 3. Fetch with Filters
```bash
# Fetch details, skip unwanted
python fetch_opendota_matches.py YOUR_KEY 3 yes "Regional,Qualifier"
```

### 4. Analyze
Use the JSON or CSV files for your analysis!

---

## Migration from Old Files

If you have old files with role data, you can:

**Option 1**: Just ignore the `role` field  
**Option 2**: Re-fetch with the new script  
**Option 3**: Use `list_tournaments.py` to identify what to skip  

The new files won't have the `role` field at all.

---

## Summary

### What Changed:
- ❌ Removed: Role/position detection
- ✅ Added: Tournament filtering
- ✅ Kept: All stat fields (GPM, XPM, K/D/A, etc.)

### Why:
- More honest (no inference)
- Cost savings (skip tournaments)
- Flexibility (filter what you need)

### Result:
Clean, factual data you can trust! 🎯
