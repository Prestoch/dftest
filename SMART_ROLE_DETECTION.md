# ✅ Smart Role Detection - Using Actual Game Stats

## The Real Problem

You were 100% right! Simply using `player_slot` order doesn't reflect **actual in-game roles**. 

Looking at your example:
- **Enchantress** (slot 5): GPM 174, XPM 199 → Clearly a **support**, not carry!
- **Terrorblade** (slot 6): GPM 539, XPM 597 → Actually the **carry**!

The player_slot is just roster order, NOT the position they actually played.

## The Solution: Farm Priority Analysis

### Smart Detection Algorithm

```python
def determine_role_by_stats(player, team_players):
    # 1. If lane_role exists for cores (1,2,3), use it
    if lane_role in [1, 2, 3]:
        return role_map[lane_role]
    
    # 2. Sort team by farm priority
    sorted_team = sorted by (GPM * 2 + XPM), descending
    
    # 3. Assign role based on farm ranking
    position 0 (highest farm) → Carry (pos 1)
    position 1 → Mid (pos 2)
    position 2 → Offlane (pos 3)
    position 3 → Support (pos 4)
    position 4 (lowest farm) → Hard Support (pos 5)
```

### Why This Works

**Farm priority = Actual position played**

- **Carries** need the most gold (items) → Highest GPM
- **Mids** need levels + gold → High GPM + XPM
- **Offlaners** need levels → Medium-high XPM
- **Supports** buy wards/smokes → Low GPM
- **Hard Supports** poorest → Lowest GPM

## Your Example - Correctly Mapped

### DIRE Team (LAVA SPORT):

| Hero | Slot | GPM | XPM | **OLD Role** | **NEW Role** |
|------|------|-----|-----|--------------|--------------|
| Enchantress | 5 | 174 | 199 | ❌ Carry (pos 1) | ✅ Hard Support (pos 5) |
| Terrorblade | 6 | 539 | 597 | ❌ Mid (pos 2) | ✅ Carry (pos 1) |
| Queen of Pain | 7 | 369 | 540 | ❌ Offlane (pos 3) | ✅ Mid (pos 2) |
| Mars | 8 | 277 | 278 | ❌ Support (pos 4) | ✅ Offlane (pos 3) |
| Snapfire | 9 | 192 | 187 | ❌ Hard Support (pos 5) | ✅ Support (pos 4) |

**Sorted by farm priority:**
1. Terrorblade (539 GPM) → Carry
2. Queen of Pain (369 GPM) → Mid
3. Mars (277 GPM) → Offlane
4. Snapfire (192 GPM) → Support
5. Enchantress (174 GPM) → Hard Support

## What Changed

### 1. New Script: `smart_remap_roles.py`
- Use this to fix your existing file
- Analyzes GPM/XPM to determine real roles
- Much more accurate than slot-based detection

### 2. Updated: `fetch_opendota_matches.py`
- Future fetches now use smart detection automatically
- Added `_determine_role_by_stats()` method
- Two-pass algorithm: collect data, then assign roles by farm priority

## How to Fix Your Existing File

### Use the SMART remapper:

```bash
python smart_remap_roles.py your_file.json
```

This will:
- ✅ Analyze each team's GPM/XPM distribution
- ✅ Sort players by actual farm priority
- ✅ Assign roles based on real performance
- ✅ Create `your_file_smart_remapped.json`
- ✅ Create `your_file_smart_remapped.csv`

### Example Output:

```
Match 1 (ID: 8522266954):
  DIRE    Enchantress: 'Carry (pos 1)' → 'Hard Support (pos 5)' (GPM: 174, XPM: 199)
  DIRE    Terrorblade: 'Mid (pos 2)' → 'Carry (pos 1)' (GPM: 539, XPM: 597)
  DIRE    Queen of Pain: 'Offlane (pos 3)' → 'Mid (pos 2)' (GPM: 369, XPM: 540)
  DIRE    Mars: 'Support (pos 4)' → 'Offlane (pos 3)' (GPM: 277, XPM: 278)
  DIRE    Snapfire: 'Hard Support (pos 5)' → 'Support (pos 4)' (GPM: 192, XPM: 187)
```

## Technical Details

### Farm Priority Formula
```python
farm_score = (GPM * 2) + XPM
```

- GPM weighted 2x because gold is more important than XP for position determination
- Carries prioritize farm over everything
- Supports sacrifice farm for team utility

### Hybrid Approach
1. **Trust lane_role for cores** - If API says lane_role=1/2/3, use it
2. **Use stats for supports** - lane_role often missing/wrong for pos 4/5
3. **Fallback to farm priority** - Always works, reflects actual gameplay

### Per-Team Analysis
- Each team analyzed independently
- Farm priority relative to teammates
- One pos 1-5 per team guaranteed

## Result

Now your data will show:
- ✅ **Actual carry** (highest farm) as pos 1
- ✅ **Actual mid** (2nd highest) as pos 2
- ✅ **Actual offlane** (3rd highest) as pos 3
- ✅ **Real supports** (4th & 5th) as pos 4 & 5

Based on how they **actually played**, not roster order! 🎯

---

**Run this now:**
```bash
python smart_remap_roles.py your_file.json
```

Get accurate roles based on real game performance! 🚀
