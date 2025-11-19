# 💾 Checkpoint & Recovery Guide

## Network Failure Protection

The script now automatically saves progress as it fetches data, so **you won't lose data if your network fails!**

---

## How It Works

### Automatic Checkpointing

1. **Progress saved every 10 matches**
2. **Automatic resume** if interrupted
3. **No data loss** on network failure or crash
4. **Atomic writes** - checkpoint file is never corrupted

### Checkpoint File

The script creates a hidden checkpoint file:
```
.opendota_checkpoint_3months_detailed.json
```

This file contains:
- All matches fetched so far
- Timestamp of last save
- Match IDs already processed

---

## Usage

### Normal Operation (Nothing New!)

Just run the script normally:
```bash
python fetch_opendota_matches.py YOUR_API_KEY
```

**The checkpoint happens automatically** - you don't need to do anything!

### If Network Fails or Script Crashes

**Just run the same command again:**
```bash
python fetch_opendota_matches.py YOUR_API_KEY
```

The script will:
1. ✅ Detect the checkpoint file
2. ✅ Load already-fetched matches
3. ✅ Resume from where it left off
4. ✅ Continue fetching remaining matches

---

## Example Scenarios

### Scenario 1: Network Timeout

```bash
$ python fetch_opendota_matches.py YOUR_KEY 3

Phase 2: Fetching detailed data for 500 matches...
Fetching details: 47%|████████░░░| 235/500 [05:23<06:12]
Error: Network timeout
💾 Progress saved in checkpoint: .opendota_checkpoint_3months_detailed.json
```

**To resume:**
```bash
$ python fetch_opendota_matches.py YOUR_KEY 3

💾 Checkpoint file found: will resume if interrupted
📁 Loaded checkpoint: 235 matches already fetched

Phase 2: Fetching detailed data for 500 matches...
  Resuming from checkpoint (235 already fetched)

Fetching details: 47%|████████░░░| 235/500 [00:00<05:45]  ← Starts from 235!
```

### Scenario 2: Power Loss

```bash
$ python fetch_opendota_matches.py YOUR_KEY 6

Fetching details: 73%|████████████░| 365/500 [08:45<03:15]
[Power failure - computer shuts down]
```

**After restart:**
```bash
$ python fetch_opendota_matches.py YOUR_KEY 6

💾 Checkpoint file found: will resume if interrupted
📁 Loaded checkpoint: 365 matches already fetched

Fetching details: 73%|████████████░| 365/500 [00:00<02:45]  ← Continues!
```

### Scenario 3: Ctrl+C (Manual Stop)

```bash
$ python fetch_opendota_matches.py YOUR_KEY

Fetching details: 34%|██████░░░░░| 170/500 [04:12<08:15]
^C
⚠ Interrupted by user!
💾 Progress saved in checkpoint: .opendota_checkpoint_3months_detailed.json
   To resume, run the same command again:
   python fetch_opendota_matches.py YOUR_KEY
```

**To resume:**
```bash
$ python fetch_opendota_matches.py YOUR_KEY

📁 Loaded checkpoint: 170 matches already fetched
Fetching details: 34%|██████░░░░░| 170/500 [00:00<06:45]  ← Continues!
```

---

## How Often Is Data Saved?

### Checkpoint Interval: Every 10 Matches

- Match 10 fetched → Checkpoint saved ✓
- Match 20 fetched → Checkpoint saved ✓
- Match 30 fetched → Checkpoint saved ✓
- ... and so on

### Also Saved:
- **At the end** of fetching (final save)
- **On error** (before script exits)
- **On Ctrl+C** (before script exits)

---

## Technical Details

### Atomic Writes

The checkpoint uses atomic file operations:
```python
1. Write to temporary file: .opendota_checkpoint_3months_detailed.json.tmp
2. Atomic rename to: .opendota_checkpoint_3months_detailed.json
```

**Result**: The checkpoint file is never corrupted, even if power fails mid-write!

### Checkpoint File Content

```json
{
  "matches": [
    {
      "match_id": 8522266954,
      "tournament": "...",
      "players": [...]
    }
    // ... all fetched matches
  ],
  "timestamp": "2025-11-19T14:30:22.123456",
  "total_matches": 235
}
```

### What Gets Tracked

- ✅ All successfully fetched matches
- ✅ All extracted match data
- ✅ Match IDs already processed (prevents duplicates)
- ✅ Timestamp of last save

---

## Multiple Fetch Sessions

### Different Parameters = Different Checkpoint Files

```bash
# These create DIFFERENT checkpoint files:
python fetch_opendota_matches.py YOUR_KEY 3  # → .opendota_checkpoint_3months_detailed.json
python fetch_opendota_matches.py YOUR_KEY 6  # → .opendota_checkpoint_6months_detailed.json
python fetch_opendota_matches.py YOUR_KEY 3 no  # → .opendota_checkpoint_3months_summary.json
```

**You can run multiple fetches** - they won't interfere with each other!

### Same Parameters = Resume Previous Fetch

```bash
# First run (interrupted at 50%)
python fetch_opendota_matches.py YOUR_KEY 3 yes "DPC"

# Second run (resumes from 50%)
python fetch_opendota_matches.py YOUR_KEY 3 yes "DPC"  # ← Same params = resumes!
```

---

## Cleanup

### Automatic Cleanup

When fetch completes successfully, checkpoint file is **automatically deleted**.

### Manual Cleanup

If you want to start fresh (not resume):
```bash
# Delete the checkpoint file
rm .opendota_checkpoint_3months_detailed.json

# Then run fetch
python fetch_opendota_matches.py YOUR_KEY
```

### List Checkpoint Files

```bash
ls -la .opendota_checkpoint_*
```

---

## Benefits

### 1. Network Failure Protection
✅ No data loss on network timeout  
✅ No data loss on connection drop  
✅ Safe to use on unstable connections  

### 2. Flexibility
✅ Pause anytime (Ctrl+C)  
✅ Resume anytime (same command)  
✅ Switch between computers (copy checkpoint file)  

### 3. Time Savings
✅ Don't re-fetch already fetched data  
✅ Don't waste API credits on duplicates  
✅ Resume exactly where you left off  

### 4. Safety
✅ Atomic file writes (no corruption)  
✅ Checkpoint saved every 10 matches  
✅ Progress never lost  

---

## Edge Cases

### Q: What if I change parameters during resume?

**A**: The checkpoint file is based on parameters. Changing them creates a NEW fetch session.

```bash
# First run
python fetch_opendota_matches.py YOUR_KEY 3  # Creates checkpoint for 3 months

# Different parameters = different checkpoint = NEW fetch
python fetch_opendota_matches.py YOUR_KEY 6  # Creates NEW checkpoint for 6 months
```

### Q: What if I fetch from a different time period?

**A**: The checkpoint includes match IDs. If there's overlap, duplicates are automatically skipped.

### Q: Can I manually edit the checkpoint file?

**A**: Not recommended! The file is validated on load. If corrupted, it will be ignored.

### Q: What if disk fills up during checkpoint save?

**A**: The atomic write will fail, but previous checkpoint remains intact. Script continues running.

### Q: Can I transfer checkpoint between computers?

**A**: Yes! Copy the `.opendota_checkpoint_*.json` file to the other computer, then run with same parameters.

---

## Troubleshooting

### Checkpoint Not Loading

**Symptoms**: Script starts from beginning even though checkpoint exists.

**Possible causes**:
1. Different parameters (check filename matches)
2. Corrupted checkpoint (will be ignored)
3. Wrong working directory

**Solution**:
```bash
# Check if checkpoint exists
ls -la .opendota_checkpoint_*

# If corrupted, delete and start fresh
rm .opendota_checkpoint_3months_detailed.json
```

### Want to Start Fresh

```bash
# Delete checkpoint
rm .opendota_checkpoint_*.json

# Run fetch
python fetch_opendota_matches.py YOUR_KEY
```

---

## Summary

✅ **Automatic** - No extra steps needed  
✅ **Safe** - Atomic writes, no corruption  
✅ **Resumable** - Just run the same command  
✅ **Efficient** - Saves every 10 matches  
✅ **Reliable** - Network failures won't lose data  

**Just run your fetch command, and rest assured your data is safe!** 💾🛡️
