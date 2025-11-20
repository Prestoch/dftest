# ⚠️ Deprecated Files Note

## These Files Are No Longer Needed

The following files are kept for reference only but are **deprecated** and should NOT be used:

### Deprecated Scripts:
- ❌ `remap_roles.py` - Old role remapper (slot-based)
- ❌ `smart_remap_roles.py` - Smart role remapper (stats-based)

### Deprecated Documentation:
- ❌ `ROLE_DETECTION_FIX.md` - Role detection fix docs
- ❌ `SMART_ROLE_DETECTION.md` - Smart role detection docs
- ❌ `SUPPORT_ROLE_FIX_SUMMARY.md` - Support role fix docs
- ❌ `OPENDOTA_ROLE_REALITY.md` - Role detection reality check
- ❌ `PLAYER_SLOT_FIX.md` - Player slot fix docs
- ❌ `REMAP_SOLUTION.md` - Remapping solution docs
- ❌ Various other role-related docs

## Why Deprecated?

As discussed, role detection was **statistical inference**, not official OpenDota data. 

**Decision**: Better to provide only factual data, no guessing!

## What to Use Instead

### ✅ Current Active Files:

**Scripts**:
- ✅ `fetch_opendota_matches.py` - Main fetch script (no roles, has tournament filtering)
- ✅ `list_tournaments.py` - Helper to list tournaments

**Documentation**:
- ✅ `UPDATED_FEATURES.md` - Complete feature documentation
- ✅ `FINAL_UPDATE_SUMMARY.md` - Quick reference guide
- ✅ `README_UPDATED_SCRIPT.md` - Original update documentation

## What Data You Get Now

All the stats you need, **without** role inference:

### Match Data:
- Match ID
- Tournament name
- Team names
- Duration
- Winner

### Hero Data (per player):
- Hero name
- Team
- **GPM** (Gold per minute)
- **XPM** (Experience per minute)
- **Tower damage**
- **Hero healing**
- **Lane efficiency %**
- **K/D/A**
- **Won** (boolean)

### NOT Included:
- ❌ Role/position labels - removed as unreliable

## Migration Guide

If you have old data files with role fields:

1. **Option A**: Just ignore the `role` field in your analysis
2. **Option B**: Re-fetch using updated script (no role field)
3. **Option C**: Use `list_tournaments.py` to see what you can skip

New data files will not have the `role` field at all.

## Summary

- ❌ Old scripts: Don't use (role detection removed)
- ✅ New script: `fetch_opendota_matches.py` (clean, factual data)
- ✅ Helper: `list_tournaments.py` (to filter tournaments)
- ✅ Result: Honest data you can trust!

---

**Last Updated**: 2025-11-19  
**Reason**: Role detection removed per user request (not reliable enough)
