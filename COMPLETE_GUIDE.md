# 📖 Complete Usage Guide - fetch_opendota_matches.py

## Quick Start

```bash
python fetch_opendota_matches.py YOUR_API_KEY from=2023-01-01 to=2023-12-31 skip="DPC,Regional,Qualifier"
```

Replace `YOUR_API_KEY` with your actual OpenDota API key from https://www.opendota.com/api-keys

---

## What Data You Get

### Match-Level (8 fields):
- Match ID, Tournament, Teams (Radiant & Dire)
- Duration, Winner, Radiant Win

### Player-Level (17 fields per player):

**Economy (5):**
- GPM, XPM, Last Hits, Denies, Net Worth

**Combat (7):**
- Kills, Deaths, Assists
- Hero Damage, Tower Damage, Hero Healing
- Teamfight Participation

**Other (5):**
- Hero Name, Hero ID, Team
- Actions Per Min, Lane Efficiency %, Won

**Total: 17 meaningful fields per player!**

---

## Command Options

### Date Range (Recommended):
```bash
from=YYYY-MM-DD    # Start date (e.g., from=2023-01-01)
to=YYYY-MM-DD      # End date (e.g., to=2023-12-31)
```

### OR Use Months:
```bash
months=N           # Months back from now (e.g., months=6)
```

### Tournament Filtering:
```bash
skip="tournament,names"    # Skip tournaments (use quotes!)
```

**Rules:**
- ✅ Partial names work (e.g., "DPC" matches "DPC Western Europe 2023")
- ✅ Case-insensitive ("dpc" = "DPC")
- ✅ Comma-separated ("DPC,Regional,Qualifier")
- ✅ **USE QUOTES** if multiple words or commas

### Details:
```bash
details=yes/no     # Fetch detailed data (default: yes)
```

---

## Examples

### 1. All of 2023
```bash
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31
```

### 2. 2023, Skip DPC
```bash
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31 skip="DPC"
```

### 3. 2023, Skip Multiple Tournaments
```bash
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31 skip="DPC,Regional,Qualifier"
```

### 4. From 2023 to Now
```bash
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01
```

### 5. Last 6 Months (Old Format)
```bash
python fetch_opendota_matches.py YOUR_KEY 6
```

### 6. Q1 2023, Major Tournaments Only
```bash
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-03-31 skip="Regional,Qualifier,Open,Division"
```

---

## Important: Use Quotes!

### ❌ Wrong:
```bash
skip=DPC,Regional,Qualifier           # Shell splits this wrong
skip=Western Europe                    # Shell splits on space
```

### ✅ Correct:
```bash
skip="DPC,Regional,Qualifier"         # Quotes keep it together
skip="Western Europe"                  # Quotes handle spaces
```

**Rule: Always use quotes for `skip` value!**

---

## Features

### 1. Network Failure Protection 🛡️
- **Auto-checkpoint** every 10 matches
- **Auto-resume** if interrupted
- **Just run same command** to resume

### 2. Tournament Filtering 💰
- **Skip unwanted tournaments** to save API credits
- **Partial matching** (e.g., "DPC" matches all DPC tournaments)
- **Case-insensitive** ("dpc" = "DPC")

### 3. Date Range Control 📅
- **Exact dates** (from/to)
- **Or relative** (months back)
- **Flexible** for any time period

### 4. No Limits ∞
- **Removed 10k limit** 
- Fetch unlimited matches
- Only limited by date range

### 5. Clean Data 🎯
- **17 meaningful fields**
- **No role inference**
- **Factual stats only**

---

## Output Files

### Generated Files:
1. **JSON**: `opendota_pro_matches_20230101_to_20231231_detailed_TIMESTAMP.json`
2. **CSV**: `opendota_pro_matches_20230101_to_20231231_detailed_TIMESTAMP.csv`

### Checkpoint File (auto-created):
- **`.opendota_checkpoint_20230101_to_20231231_detailed.json`**
- Hidden file (starts with dot)
- Auto-deleted on successful completion
- Keep if you want to resume later

---

## If Interrupted

### Network fails or Ctrl+C?
**Just run the same command again:**

```bash
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31 skip="DPC"
```

**The script will:**
1. Find checkpoint file
2. Load already-fetched matches
3. Resume from where it stopped
4. No data loss!

---

## Performance Estimates

### Time & API Calls:

**Phase 1** (Match List):
- ~5-10 seconds
- ~20-50 API calls
- Gets all match IDs in date range

**Phase 2** (Details):
- Depends on match count
- 1 API call per match
- ~600 matches per 10 minutes (with rate limit)

**Example** - All of 2023:
- ~15,000 matches (estimate)
- ~25 minutes to fetch all details
- ~15,000 API calls
- But with checkpoint protection!

---

## Helper Scripts

### See Available Tournaments:
```bash
python list_tournaments.py your_existing_file.json
```

Shows all tournaments in your data with match counts.

---

## Troubleshooting

### "Only fetching 10k matches"
✅ Fixed! Limit removed.

### "Skip doesn't work for multi-word names"
✅ Use quotes: `skip="Western Europe"`

### "Script crashed, lost data"
✅ No! Checkpoint saved. Run same command to resume.

### "Want to start fresh (ignore checkpoint)"
```bash
rm .opendota_checkpoint_*.json
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01
```

---

## Optional: hero_id_map.json

**Question**: Should I have `hero_id_map.json` in my folder?

**Answer**: Optional but recommended!

**With file:**
- Loads hero names from file (fast)
- Saves 1 API call

**Without file:**
- Fetches hero names from API (auto-fallback)
- Uses 1 extra API call at startup
- Still works fine!

**Where to get it:** Already in your workspace at `/workspace/hero_id_map.json` - just copy it to your working directory if you want.

---

## Summary

### Your Complete Command:
```bash
python fetch_opendota_matches.py YOUR_API_KEY \
  from=2023-01-01 \
  to=2023-12-31 \
  skip="DPC,Regional,Qualifier"
```

### What It Does:
- ✅ Fetches all 2023 matches (no limits!)
- ✅ Skips DPC, Regional, and Qualifier tournaments
- ✅ Saves 17 fields per player
- ✅ Checkpoint protection (resume if interrupted)
- ✅ Generates JSON + CSV files

### What You Need:
1. OpenDota API key
2. This command
3. Patience (can take 20-30 minutes for a full year)

### What You Get:
- Clean, factual data
- All the stats you need
- No inference, no guessing
- Ready for analysis!

---

## Documentation Files

📄 **`COMPLETE_GUIDE.md`** - This file (everything in one place)  
📄 **`FINAL_FIELD_LIST.md`** - Complete field documentation  
📄 **`DATE_RANGE_GUIDE.md`** - Date range usage examples  
📄 **`NETWORK_FAILURE_PROTECTION.md`** - Checkpoint/resume guide  

---

**Everything is ready! Just run your command and start collecting data!** 🚀✨
