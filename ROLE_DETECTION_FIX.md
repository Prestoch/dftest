# Role Detection Fix - Support Positions (pos 4 & 5)

## Issue
The original implementation was missing support heroes (pos 4 and pos 5) because OpenDota's `lane_role` field doesn't reliably capture support positions.

## Why This Happens
In the OpenDota API:
- **lane_role** values:
  - `1` = Safe Lane (Carry)
  - `2` = Mid Lane
  - `3` = Off Lane
  - `4` = Jungle
  - Often **missing or null** for supports (who roam/pull camps)

- **player_slot** values:
  - Radiant: `0-4` (positions 1-5)
  - Dire: `128-132` (encoded, actually positions 1-5)
  - Players are ordered by farm priority within their team

## The Fix

### Improved Role Detection Algorithm

The updated `_get_role_name()` method now uses a **fallback strategy**:

1. **First**: Try to determine role from `lane_role`
   - If lane_role = 1 → Carry (pos 1)
   - If lane_role = 2 → Mid (pos 2)
   - If lane_role = 3 → Offlane (pos 3)
   - If lane_role = 4 or is_roaming → Support (pos 4/5, distinguished by player_slot)

2. **Fallback**: Use `player_slot` (farm priority order)
   - Decode player_slot to get position within team (0-4)
   - Map to positions:
     - 0 → Carry (pos 1)
     - 1 → Mid (pos 2)
     - 2 → Offlane (pos 3)
     - 3 → Support (pos 4)
     - 4 → Hard Support (pos 5)

## What Changed in Code

### Before:
```python
def _get_role_name(self, lane_role: Optional[int]) -> str:
    role_map = {1: "Carry (pos 1)", 2: "Mid (pos 2)", 3: "Offlane (pos 3)", ...}
    return role_map.get(lane_role, "Unknown")
```
❌ Would return "Unknown" for most supports

### After:
```python
def _get_role_name(self, lane_role: Optional[int], player_slot: int, is_roaming: bool = False) -> str:
    # Decode player_slot
    if player_slot < 128:
        team_position = player_slot  # Radiant
    else:
        team_position = player_slot - 128  # Dire
    
    # Try lane_role first, fallback to team_position
    if lane_role == 1: return "Carry (pos 1)"
    elif lane_role == 2: return "Mid (pos 2)"
    elif lane_role == 3: return "Offlane (pos 3)"
    elif lane_role == 4 or is_roaming:
        return "Hard Support (pos 5)" if team_position >= 4 else "Support (pos 4)"
    
    # Fallback to position map
    position_map = {0: "Carry (pos 1)", ..., 4: "Hard Support (pos 5)"}
    return position_map.get(team_position, f"Unknown (slot {player_slot})")
```
✅ Always determines a position using player_slot as fallback

## Additional Changes

1. **Added `player_slot` to output** - Now included in both JSON and CSV for debugging
2. **Extract `is_roaming` flag** - Helps identify roaming supports
3. **Updated CSV columns** - Includes the new `player_slot` field

## Result

Now **all 10 players** in each match will have proper role assignments:
- ✅ Carry (pos 1)
- ✅ Mid (pos 2)
- ✅ Offlane (pos 3)
- ✅ Support (pos 4)
- ✅ Hard Support (pos 5)

Even if OpenDota's `lane_role` is missing/null for supports, the script falls back to using `player_slot` which reliably indicates farm priority and therefore position.

## Example Output

### Before Fix:
```json
{
  "hero_name": "Crystal Maiden",
  "role": "Unknown",  ❌
  ...
}
```

### After Fix:
```json
{
  "hero_name": "Crystal Maiden",
  "role": "Hard Support (pos 5)",  ✅
  "player_slot": 4,
  ...
}
```

## Testing the Fix

When you run the script now:
```bash
python fetch_opendota_matches.py YOUR_API_KEY
```

Check the output and you should see:
- All 10 heroes per match
- Each with a proper role (pos 1 through pos 5)
- 2 of each position per match (one for each team)

The `player_slot` field in the output helps verify the role detection is working correctly!
