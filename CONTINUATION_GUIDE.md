# Complete Continuation Guide - Save API Credits! 💰

## Your Situation

You've already fetched **21,370 matches** over **14 hours** before the crash. 

**Don't re-fetch them!** This guide shows how to **continue from where you stopped** and save thousands of API credits.

---

## 📥 Step 1: Download Updated Scripts

```bash
# Download the new streaming script (memory-safe)
curl -o fetch_opendota_matches.py https://raw.githubusercontent.com/Prestoch/dftest/refs/heads/cursor/fetch-specific-dota-2-match-data-caf8/fetch_opendota_matches.py

# Download the continuation setup script
curl -o setup_continuation.py https://raw.githubusercontent.com/Prestoch/dftest/refs/heads/cursor/fetch-specific-dota-2-match-data-caf8/setup_continuation.py

# Make them executable (optional)
chmod +x *.py
```

---

## 🔧 Step 2: Stop Your Old Script

If still running:
```bash
# Press Ctrl+C in the terminal where it's running
```

---

## ⚙️ Step 3: Setup Continuation

Run the setup script to convert your checkpoint:

```bash
python3 setup_continuation.py .opendota_checkpoint_20230401_to_20251119_detailed.json
```

### What This Does:

1. **Converts checkpoint** from old format (50MB) to new format (~1MB)
2. **Extracts your 21,370 matches** to starter files:
   - `opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.json`
   - `opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.csv`
3. **Creates metadata** file for the new script to find these files

### Expected Output:

```
====================================================================
Setup Continuation from Old Checkpoint
====================================================================

[1/4] Reading old checkpoint: .opendota_checkpoint_20230401_to_20251119_detailed.json
✓ Found 21370 matches

[2/4] Converting to new checkpoint format...
✓ Converted checkpoint (now 21370 match IDs only)
✓ Checkpoint size reduced: ~87MB → ~86KB

[3/4] Creating starter JSON file: opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.json
✓ Created JSON with 21370 matches (open array for appending)

[4/4] Creating starter CSV file: opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.csv
✓ Created CSV with 21370 matches (213700 player rows)

✓ Created metadata file: .continuation_metadata.json

====================================================================
✓ Setup Complete! Ready for Continuation
====================================================================

📊 Summary:
  Checkpoint: .opendota_checkpoint_20230401_to_20251119_detailed.json
  - Converted to new format (match IDs only)
  - Contains 21370 already-fetched matches

📁 Starter files created:
  - opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.json
  - opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.csv
  - These contain your existing 21370 matches

🚀 Next step - Run the new script WITH special flag:

  python fetch_opendota_matches.py YOUR_API_KEY \
    from=2023-04-01 to=2025-11-19 \
    skip="ultras,lunar,mad dogs,destiny,dota 2 space,impacto,ancients" \
    continue=yes

💡 What will happen:
  ✓ Script loads checkpoint (21370 match IDs)
  ✓ Skips these 21370 matches (saves API credits!)
  ✓ Fetches remaining ~59,012 matches
  ✓ Appends to opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.json
  ✓ Appends to opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.csv
  ✓ Final files will have ALL ~80,000 matches

⚡ Memory-safe streaming writes + No wasted API credits!
```

---

## 🚀 Step 4: Run New Script with `continue=yes`

```bash
python3 fetch_opendota_matches.py 26ce8060-bcc2-47c4-9a86-42b15af442f2 \
  from=2023-04-01 to=2025-11-19 \
  skip="ultras,lunar,mad dogs,destiny,dota 2 space,impacto,ancients" \
  continue=yes
```

### What You'll See:

```
✓ Continuation mode: Loading metadata from .continuation_metadata.json
  Will append to existing files:
    - opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.json
    - opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.csv
  Already have: 21370 matches

============================================================
💾 Checkpoint file found: will resume if interrupted
   (Checkpoint file: .opendota_checkpoint_20230401_to_20251119_detailed.json)
   ⚡ Streaming mode: data written incrementally (low memory)

Skipping tournaments containing: ultras, lunar, mad dogs, destiny, dota 2 space, impacto, ancients

Fetching pro matches from 2023-04-01 to 2025-11-19
Rate limit: 600 requests/minute
Include details: True

Phase 1: Fetching match list...
✓ Fetched 80382 pro matches in 451 seconds

Phase 2: Fetching detailed data for 80382 matches...
Data will be written incrementally to save memory
📁 Loaded checkpoint: 21370 matches already fetched
  Resuming from checkpoint (21370 already fetched)

Fetching details:  27%|██▋  | 21370/80382 [00:00<15:30:00, 21370 success, 0 failed]
                    ↑ Starts here! Skips first 21,370
```

---

## 💡 Key Benefits

### API Credits Saved:
```
Without continuation: 80,382 API calls
With continuation:    59,012 API calls (skips 21,370)
                      ↓
Saves: 21,370 API calls = ~$10-20 worth!
```

### Time Saved:
```
Without continuation: ~24 hours total
With continuation:    ~18 hours remaining (skips 6 hours)
```

### Memory Usage:
```
Old script: 2-4GB → CRASH 💥
New script: 50MB constant ✓
```

---

## 📊 What Gets Created

### During Execution:

| File | Purpose | Size |
|------|---------|------|
| `.opendota_checkpoint_*.json` | Lightweight checkpoint (match IDs) | ~86KB |
| `opendota_pro_matches_*_CONTINUING.json` | Growing JSON file | Starts 20MB, grows to ~200MB |
| `opendota_pro_matches_*_CONTINUING.csv` | Growing CSV file | Starts 30MB, grows to ~300MB |
| `.continuation_metadata.json` | Tells script which files to append to | 1KB |

### After Completion:

Checkpoint file is deleted, metadata file can be deleted. You're left with:
- `opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.json` (~200MB, ~80k matches)
- `opendota_pro_matches_20230401_to_20251119_detailed_CONTINUING.csv` (~300MB, ~800k player rows)

---

## 🛡️ Safety Features

### 1. Checkpoint Every 100 Matches
If script crashes or you stop it:
- Run same command again
- Resumes exactly where it stopped
- No data loss, no wasted API calls

### 2. Streaming Writes
- Data written immediately to disk
- Memory usage stays constant at ~50MB
- Can handle unlimited matches

### 3. Automatic Retry on 500 Errors
- OpenDota API sometimes returns 500 errors
- Script retries automatically (1s, 2s, 4s delays)
- Most 500 errors are temporary and succeed on retry

---

## 📈 Progress Tracking

### Watch Files Grow in Real-Time:
```bash
# In another terminal
watch -n 5 'wc -l opendota_pro_matches_*_CONTINUING.*'
```

### Monitor Progress:
```bash
# Progress bar shows:
Fetching details:  45%|████▌  | 36250/80382 [10:15:30<8:20:15, 36250 success, 23 failed]
                   ↑           ↑           ↑         ↑         ↑
                   %        Current     Elapsed   Remaining  Successful
```

---

## ⏱️ Expected Timeline

| Milestone | Matches | Time | Notes |
|-----------|---------|------|-------|
| **Already Done** | 21,370 | ~6 hours | Saved in checkpoint ✓ |
| **Phase 1** | 80,382 | ~8 minutes | Fetch match list (fast) |
| **Phase 2** | 59,012 | ~15-18 hours | Fetch details (slow) |
| **Total** | 80,382 | ~15-18 hours | vs 24 hours without continuation |

---

## 🔧 Troubleshooting

### If Setup Script Says "No Matches Found":
```bash
# Check if checkpoint file exists
ls -lh .opendota_checkpoint_*

# Check if it has the right format
python3 -c "import json; print(json.load(open('.opendota_checkpoint_20230401_to_20251119_detailed.json'))['matches'][:1])"
```

### If New Script Says "Metadata Not Found":
```bash
# Re-run setup script
python3 setup_continuation.py .opendota_checkpoint_20230401_to_20251119_detailed.json

# Check metadata was created
cat .continuation_metadata.json
```

### If Script Still Re-fetches Matches:
```bash
# Make sure you used continue=yes flag!
python3 fetch_opendota_matches.py YOUR_KEY \
  from=2023-04-01 to=2025-11-19 \
  skip="..." \
  continue=yes  # ← This is critical!
```

### If You Want to Start Fresh Instead:
```bash
# Delete all continuation files
rm .opendota_checkpoint_*.json
rm .continuation_metadata.json
rm opendota_pro_matches_*_CONTINUING.*

# Run without continue=yes flag
python3 fetch_opendota_matches.py YOUR_KEY from=2023-04-01 to=2025-11-19 skip="..."
```

---

## 🎯 Summary

| Action | Command |
|--------|---------|
| **1. Download scripts** | `curl -o fetch_opendota_matches.py https://raw...` |
| **2. Setup continuation** | `python3 setup_continuation.py .opendota_checkpoint_*.json` |
| **3. Continue fetching** | `python3 fetch_opendota_matches.py YOUR_KEY from=... continue=yes` |

**Result:**
- ✅ Saved 21,370 API calls (~$10-20 value)
- ✅ Saved 6 hours of runtime
- ✅ No more memory crashes
- ✅ Complete dataset with ~80,000 matches

---

## ❓ Questions?

**Q: Will this create duplicate matches?**  
A: No! The checkpoint contains the 21,370 match IDs. The new script checks each match ID and skips it if already fetched.

**Q: Can I stop and resume multiple times?**  
A: Yes! Just run the same command with `continue=yes`. The checkpoint updates every 100 matches.

**Q: What if I forgot to use continue=yes?**  
A: Stop the script (Ctrl+C) and re-run with `continue=yes`. It will skip already-fetched matches based on the checkpoint.

**Q: Do I need the old script anymore?**  
A: No! You can delete or rename `fetch_opendota_matches_OLD.py`. Only use the new one.

---

**Ready? Run the setup script and continue your fetch!** 🚀
