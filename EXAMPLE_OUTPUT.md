# Example Output with Progress Bars

## Running the script with full details:
```bash
python3 fetch_opendota_matches.py YOUR_API_KEY 3 yes
```

## Expected Console Output:

```
============================================================
Fetching pro matches since 2025-08-18
Rate limit: 600 requests/minute
Include details: True

Phase 1: Fetching match list...
Fetching pages: 42 pages [00:25<00:00,  1.65 pages/s, Complete - 1247 total matches]
✓ Fetched 1247 pro matches in 25.4 seconds
  Made 42 API requests
  Average rate: 99.2 requests/minute

Phase 2: Fetching detailed data for 1247 matches...
This will take a while...

Fetching details: 100%|████████████████| 1247/1247 [02:04<00:00, 10.02 matches/s, 1245 success, 2 failed]

✓ Fetched details for 1245/1247 matches
  ⚠ Failed to fetch 2 matches: [7812345678, 7812345690]
============================================================
Saved 1245 matches to opendota_pro_matches_3months_detailed_20251118_143022.json

Match Statistics:
  Total matches: 1245
  Newest match: 2025-11-18 08:15:23
  Oldest match: 2025-08-18 12:34:56
  Match ID range: 7912345678 to 7812345679

Done!
```

## Progress Bar Features:

### Phase 1 - Fetching Match List
- **Real-time page counter**: Shows how many pages have been fetched
- **Match counter**: Updates as matches are discovered
- **Speed indicator**: Pages per second
- **Status**: Shows when complete or if cutoff date reached

### Phase 2 - Fetching Details (if enabled)
- **Full progress bar**: Visual bar showing percentage complete
- **Current/Total**: Shows exactly where you are (e.g., 450/1247)
- **ETA**: Estimated time remaining
- **Speed**: Matches processed per second
- **Success/Fail counters**: Shows how many succeeded vs failed
- **Percentage**: Shows exact progress percentage

## Benefits:
✅ **Know exactly how much is done** - No more guessing!
✅ **Time estimates** - See how long it will take
✅ **Real-time stats** - Success/failure counts as they happen
✅ **Speed monitoring** - Make sure rate limiting is working properly
