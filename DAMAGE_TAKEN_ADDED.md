# Damage Taken Added Back ✅

## What Changed

**Added "damage_taken" field back to all data exports.**

---

## 📥 Download Updated Scripts

```bash
# Main script with damage_taken included
curl -o fetch_opendota_matches.py https://raw.githubusercontent.com/Prestoch/dftest/refs/heads/cursor/fetch-specific-dota-2-match-data-caf8/fetch_opendota_matches.py

# Setup continuation script (if you want to resume from old checkpoint)
curl -o setup_continuation.py https://raw.githubusercontent.com/Prestoch/dftest/refs/heads/cursor/fetch-specific-dota-2-match-data-caf8/setup_continuation.py
```

---

## 🚀 Starting Fresh

Since you want to start from scratch, follow these steps:

### 1. Clean Up Old Files (Optional)
```bash
# Delete old checkpoint and data files
rm .opendota_checkpoint_*.json
rm .continuation_metadata.json
rm opendota_pro_matches_*.json
rm opendota_pro_matches_*.csv
rm recovered_matches_*.json
rm recovered_matches_*.csv
```

### 2. Run the New Script
```bash
python3 fetch_opendota_matches.py 26ce8060-bcc2-47c4-9a86-42b15af442f2 \
  from=2023-04-01 to=2025-11-19 \
  skip="ultras,lunar,mad dogs,destiny,dota 2 space,impacto,ancients"
```

### What You'll Get:
```
============================================================
💾 Checkpoint enabled: progress saved every 100 matches
   (Checkpoint file: .opendota_checkpoint_20230401_to_20251119_detailed.json)
   ⚡ Streaming mode: data written incrementally (low memory)

Skipping tournaments containing: ultras, lunar, mad dogs, destiny, dota 2 space, impacto, ancients

Fetching pro matches from 2023-04-01 to 2025-11-19
Rate limit: 600 requests/minute
Include details: True

Phase 1: Fetching match list...
✓ Fetched 80382 pro matches...

Phase 2: Fetching detailed data for 80382 matches...
Data will be written incrementally to save memory

Fetching details: 100%|████████| 80382/80382 [18:30:15<00:00, 1.21 matches/s, 78234 success, 148 failed]
```

---

## 📊 Complete Field List

Your CSV/JSON will now include:

### Match Info:
- `match_id`
- `tournament`
- `radiant_team`
- `dire_team`
- `duration_minutes`
- `winner`
- `radiant_win`

### Player/Hero Stats:
- `hero_name`
- `hero_id`
- `team`
- `gpm` (Gold Per Minute)
- `xpm` (Experience Per Minute)
- `tower_damage`
- `hero_healing`
- `lane_efficiency_pct`
- `kills`
- `deaths`
- `assists`
- `last_hits`
- `denies`
- `net_worth`
- `hero_damage`
- **`damage_taken`** ← **ADDED BACK!**
- `teamfight_participation`
- `actions_per_min`
- `won` (true/false if this player won)

---

## 📈 Expected Results

### For 80,382 Matches (2023-04-01 to 2025-11-19):

| Metric | Value |
|--------|-------|
| **Total API calls** | ~80,000 |
| **Estimated time** | 16-24 hours |
| **Success rate** | 95-98% |
| **Memory usage** | ~50MB (constant) |
| **Final JSON size** | ~200MB |
| **Final CSV size** | ~320MB (slightly larger with damage_taken) |
| **Player rows** | ~800,000 (80k matches × 10 players) |

---

## 🛡️ Features

### ✅ Memory-Safe Streaming
- No more crashes after 14 hours
- Data written immediately to disk
- Constant 50MB RAM usage

### ✅ Checkpoint & Resume
- Saves progress every 100 matches
- If interrupted, just run same command again
- Zero data loss

### ✅ Automatic 500 Error Retry
- Retries failed requests 3 times
- Exponential backoff (1s, 2s, 4s)
- Handles OpenDota temporary glitches

### ✅ Tournament Filtering
- Skips unwanted tournaments
- Saves API credits
- Configured via `skip=` parameter

---

## 📝 Sample Output

### CSV Format:
```csv
match_id,tournament,radiant_team,dire_team,duration_minutes,winner,radiant_win,hero_name,hero_id,team,gpm,xpm,tower_damage,hero_healing,lane_efficiency_pct,kills,deaths,assists,last_hits,denies,net_worth,hero_damage,damage_taken,teamfight_participation,actions_per_min,won
8522266954,Americas Convergence Series 1,TeamCompromiso,LAVA SPORT,23.5,TeamCompromiso,true,Juggernaut,8,TeamCompromiso,763,745,9333,8069,94,5,0,7,345,12,28456,45678,12345,0.85,245,true
```

### JSON Format:
```json
{
  "match_id": 8522266954,
  "tournament": "Americas Convergence Series 1",
  "radiant_team": "TeamCompromiso",
  "dire_team": "LAVA SPORT",
  "duration_minutes": 23.5,
  "winner": "TeamCompromiso",
  "radiant_win": true,
  "players": [
    {
      "hero_name": "Juggernaut",
      "hero_id": 8,
      "team": "TeamCompromiso",
      "gpm": 763,
      "xpm": 745,
      "tower_damage": 9333,
      "hero_healing": 8069,
      "lane_efficiency_pct": 94,
      "kills": 5,
      "deaths": 0,
      "assists": 7,
      "last_hits": 345,
      "denies": 12,
      "net_worth": 28456,
      "hero_damage": 45678,
      "damage_taken": 12345,
      "teamfight_participation": 0.85,
      "actions_per_min": 245,
      "won": true
    }
  ]
}
```

---

## ⏱️ Timeline

### For Fresh Start (80,382 matches):

| Phase | Duration | Description |
|-------|----------|-------------|
| **Phase 1** | ~8 minutes | Fetch match list (fast) |
| **Phase 2** | ~16-24 hours | Fetch detailed data (slow) |
| **Total** | ~16-24 hours | Complete dataset |

### Checkpoint Progress:
- Saved every 100 matches
- Can resume anytime
- No data loss on crash/interrupt

---

## 🔍 Monitoring Progress

### Watch Files Grow:
```bash
# In another terminal
watch -n 10 'ls -lh opendota_pro_matches_*.{json,csv} 2>/dev/null'
```

### Check Progress:
```bash
# Count lines in CSV (header + player rows)
wc -l opendota_pro_matches_*.csv
```

### Estimated Completion:
```
Fetching details:  45%|████▌  | 36250/80382 [10:15:30<8:20:15]
                   ↑           ↑           ↑         ↑
                   %        Current     Elapsed   Remaining
```

---

## 🎯 Summary

| Feature | Status |
|---------|--------|
| ✅ **Damage Taken** | Added back |
| ✅ **Memory-safe streaming** | No crashes |
| ✅ **Automatic 500 retry** | Handles API glitches |
| ✅ **Checkpoint every 100** | Resume anytime |
| ✅ **Tournament filtering** | Saves API credits |
| ✅ **Date range support** | Precise time window |
| ✅ **Fresh start ready** | Clean slate |

---

## 📁 Output Files

After completion, you'll have:
```
opendota_pro_matches_20230401_to_20251119_detailed_20251119_XXXXXX.json  (~200MB)
opendota_pro_matches_20230401_to_20251119_detailed_20251119_XXXXXX.csv   (~320MB)
```

**Checkpoint file will be automatically deleted after successful completion.**

---

**Ready to start fresh with damage_taken included!** 🚀

Just download the script and run the command above!
