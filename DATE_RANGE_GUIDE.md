# 📅 Date Range Filtering Guide

## New Feature: Specify Exact Dates!

You can now specify **exact start and end dates** instead of just "months back from now"!

---

## Usage

### New Format (Recommended)

```bash
python fetch_opendota_matches.py YOUR_KEY from=YYYY-MM-DD to=YYYY-MM-DD
```

**Date format**: `YYYY-MM-DD` (e.g., `2023-01-01`)

---

## Examples

### 1. Specific Date Range
```bash
# Fetch matches from Jan 1, 2023 to Dec 31, 2023
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31
```

### 2. From Specific Date to Now
```bash
# Fetch matches from Jan 1, 2023 to today
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01
```

### 3. With Tournament Filtering
```bash
# Fetch 2023 matches, skip DPC tournaments
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31 skip=DPC
```

### 4. Multiple Options
```bash
# Fetch Q1 2023, skip regionals and qualifiers, no details
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-03-31 skip=Regional,Qualifier details=no
```

---

## Date Range vs Months

### Option A: Date Range (NEW)
```bash
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31
```
✅ Exact control  
✅ Specify any date range  
✅ Consistent results (same data every time)  

### Option B: Months Back
```bash
python fetch_opendota_matches.py YOUR_KEY months=6
```
✅ Simple  
✅ Always gets recent data  
✅ Relative to today  

**Choose based on your needs!**

---

## All Options

### Complete Syntax
```bash
python fetch_opendota_matches.py YOUR_KEY [options]
```

### Available Options:

| Option | Values | Example | Description |
|--------|--------|---------|-------------|
| `from` | YYYY-MM-DD | `from=2023-01-01` | Start date (inclusive) |
| `to` | YYYY-MM-DD | `to=2023-12-31` | End date (inclusive, defaults to now) |
| `months` | Number | `months=6` | Months back from now (if no `from`) |
| `details` | yes/no | `details=yes` | Fetch detailed data (default: yes) |
| `skip` | Text list | `skip=DPC,Regional` | Skip tournaments (comma-separated) |

---

## Date Format Rules

### ✅ Valid Dates
```bash
from=2023-01-01      # January 1, 2023
from=2023-12-31      # December 31, 2023
from=2022-06-15      # June 15, 2022
```

### ❌ Invalid Dates
```bash
from=2023/01/01      # Wrong separator (use -)
from=01-01-2023      # Wrong order (use YYYY-MM-DD)
from=2023-1-1        # Missing leading zeros
from=Jan 1, 2023     # Text format not supported
```

**Always use**: `YYYY-MM-DD` format

---

## Examples by Use Case

### Historical Data (Specific Year)
```bash
# All of 2023
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31

# All of 2022
python fetch_opendota_matches.py YOUR_KEY from=2022-01-01 to=2022-12-31
```

### Recent Data (From Date to Now)
```bash
# Everything since Jan 1, 2024
python fetch_opendota_matches.py YOUR_KEY from=2024-01-01

# Everything since 6 months ago (use months)
python fetch_opendota_matches.py YOUR_KEY months=6
```

### Specific Tournament Period
```bash
# The International 2023 period (example dates)
python fetch_opendota_matches.py YOUR_KEY from=2023-10-12 to=2023-10-29

# DPC Tour 1 2023 (example dates)
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-03-31
```

### Quarter/Month Ranges
```bash
# Q1 2023
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-03-31

# Q2 2023
python fetch_opendota_matches.py YOUR_KEY from=2023-04-01 to=2023-06-30

# January 2023 only
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-01-31
```

---

## Output Files

### Filenames Include Date Range

**With date range:**
```
opendota_pro_matches_20230101_to_20231231_detailed_20251119_143022.json
```

**With months:**
```
opendota_pro_matches_6months_detailed_20251119_143022.json
```

### Checkpoint Files

**With date range:**
```
.opendota_checkpoint_20230101_to_20231231_detailed.json
```

**With months:**
```
.opendota_checkpoint_6months_detailed.json
```

---

## Combining Options

### All Options Together
```bash
python fetch_opendota_matches.py YOUR_KEY \
  from=2023-01-01 \
  to=2023-12-31 \
  details=yes \
  skip=Regional,Qualifier,Open
```

### Order Doesn't Matter
```bash
# These are equivalent:
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 skip=DPC details=yes
python fetch_opendota_matches.py YOUR_KEY details=yes skip=DPC from=2023-01-01
```

---

## Old Format Still Works!

### Old Positional Format
```bash
python fetch_opendota_matches.py YOUR_KEY 6 yes "DPC,BTS"
#                                         ^  ^   ^
#                                         |  |   └─ skip tournaments
#                                         |  └───── details
#                                         └──────── months
```

### New Key=Value Format
```bash
python fetch_opendota_matches.py YOUR_KEY months=6 details=yes skip=DPC,BTS
```

**Both work!** Use whichever you prefer.

---

## Error Handling

### Invalid Date Format
```bash
$ python fetch_opendota_matches.py YOUR_KEY from=01-01-2023

Error: Invalid date format for 'from': 01-01-2023
Use YYYY-MM-DD format, e.g., from=2023-01-01
```

### End Before Start
```bash
$ python fetch_opendota_matches.py YOUR_KEY from=2023-12-31 to=2023-01-01

Error: 'from' date must be before 'to' date!
```

---

## Tips

### 1. Check OpenDota for Tournament Dates
Visit https://www.opendota.com/leagues to see when tournaments happened

### 2. Use Checkpoint for Large Ranges
Long date ranges = many matches. Checkpoint protects your progress!

### 3. Filter Tournaments to Save Time
```bash
# Year of data, skip minor tournaments
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31 skip=Regional,Qualifier
```

### 4. Test with Small Ranges First
```bash
# Test with one month
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-01-31

# If it works, expand to full range
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31
```

---

## Quick Reference

### Most Common Commands

```bash
# Last 3 months (default)
python fetch_opendota_matches.py YOUR_KEY

# Last 6 months
python fetch_opendota_matches.py YOUR_KEY months=6

# All of 2023
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31

# From Jan 2023 to now
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01

# Specific range, skip tournaments
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31 skip=DPC
```

---

## Summary

### What Changed:
- ✅ Added: `from=YYYY-MM-DD` option
- ✅ Added: `to=YYYY-MM-DD` option
- ✅ Added: New key=value format
- ✅ Kept: Old positional format still works

### Date Format:
- ✅ **YYYY-MM-DD** (e.g., 2023-01-01)
- ❌ Not DD-MM-YYYY or MM-DD-YYYY
- ❌ Not text dates or other formats

### Benefits:
- ✅ Exact date control
- ✅ Reproducible results
- ✅ Historical data analysis
- ✅ Specific tournament periods

**Now you can fetch exactly the data you need!** 📅✨
