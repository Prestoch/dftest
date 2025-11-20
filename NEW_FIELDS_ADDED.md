# ✅ New Fields Added!

## 8 Additional Fields Now Included

You asked for these fields, and they're now added to the data!

---

## Complete Field List (20 Total)

### Match-Level (7 fields):
1. ✅ Match ID
2. ✅ Tournament Name
3. ✅ Team Names (Radiant & Dire)
4. ✅ Duration (seconds & minutes)
5. ✅ Winner
6. ✅ Radiant Win (boolean)

### Hero-Level Per Player (20 fields):
1. ✅ Hero Name
2. ✅ Hero ID
3. ✅ Team
4. ✅ Player Slot
5. ✅ **GPM** (Gold per minute)
6. ✅ **XPM** (Experience per minute)
7. ✅ **Tower Damage**
8. ✅ **Hero Healing**
9. ✅ **Lane Efficiency %**
10. ✅ **Kills**
11. ✅ **Deaths**
12. ✅ **Assists**
13. ✅ **Last Hits** ⭐ NEW!
14. ✅ **Denies** ⭐ NEW!
15. ✅ **Net Worth** ⭐ NEW!
16. ✅ **Hero Damage** ⭐ NEW!
17. ✅ **Damage Taken** ⭐ NEW!
18. ✅ **Teamfight Participation** ⭐ NEW!
19. ✅ **Actions Per Min** ⭐ NEW!
20. ✅ **Clicks Per Min** ⭐ NEW!
21. ✅ **Won** (boolean)

---

## Field Explanations

### 1. Last Hits
- **Type**: Integer
- **Description**: Total creeps/neutrals last-hit (killed)
- **Typical Values**: 
  - Carry: 300-600
  - Support: 50-150
- **Use**: Farming efficiency indicator

### 2. Denies
- **Type**: Integer
- **Description**: Allied creeps denied (killed to prevent enemy gold/XP)
- **Typical Values**: 10-50
- **Use**: Laning phase skill indicator

### 3. Net Worth
- **Type**: Integer
- **Description**: Total gold value (current gold + item value)
- **Typical Values**: 10,000 - 40,000
- **Use**: Overall economic advantage indicator
- **Note**: End-of-game value

### 4. Hero Damage
- **Type**: Integer
- **Description**: Total damage dealt to enemy heroes
- **Typical Values**: 10,000 - 60,000
- **Use**: Combat effectiveness, carry performance
- **Note**: Different from tower damage!

### 5. Damage Taken
- **Type**: Integer
- **Description**: Total damage received from enemy heroes
- **Typical Values**: 10,000 - 50,000
- **Use**: Tank/frontline effectiveness, survivability

### 6. Teamfight Participation
- **Type**: Float (0-1) or Percentage
- **Description**: Percentage of teamfights participated in
- **Typical Values**: 0.5 - 1.0 (50% - 100%)
- **Use**: Teamplay indicator
- **Note**: Shows how often player was present in fights

### 7. Actions Per Min (APM)
- **Type**: Integer
- **Description**: Game actions per minute (clicks, keypresses, commands)
- **Typical Values**: 100 - 300
- **Use**: Mechanical skill, multitasking ability
- **Note**: Higher = more active gameplay

### 8. Clicks Per Min (CPM)
- **Type**: Integer
- **Description**: Mouse clicks per minute
- **Typical Values**: 50 - 200
- **Use**: Mechanical activity level
- **Note**: Subset of APM (only mouse clicks)

---

## Questions Answered

### Q: What's the difference between `lane_efficiency` and `lane_efficiency_pct`?
**A**: Same data, different format!
- `lane_efficiency`: Raw decimal (0.94)
- `lane_efficiency_pct`: Percentage (94)
- **We save**: `lane_efficiency_pct` (easier to read)

### Q: What does `player_slot` give me?
**A**: Player's position in team roster (0-9)
- **Radiant**: 0-4
- **Dire**: 5-9 (or 128-132 in some formats)
- **Use cases**: 
  - Identify player order
  - Team roster position
  - Not super critical for most analysis

### Q: What are `scaled_hero_damage`, `scaled_tower_damage`, `scaled_hero_healing`?
**A**: Duration-normalized stats!

**Why?** Compare short vs long games fairly:
- 30-min game: 10,000 damage
- 60-min game: 20,000 damage
- Both have same DPS, but raw totals differ

**How?** Normalized to standard game length:
```
scaled_damage = (actual_damage / game_duration) * standard_duration
```

**Use case**: 
- Compare player performance across different game lengths
- Identify consistent performers
- Rate DPS independent of game time

**We DON'T save these** (we save raw values instead), but you can calculate them:
```
scaled_hero_damage = (hero_damage / duration_minutes) * 40
```
(40 minutes = typical pro game)

---

## Output Example

### JSON Format:
```json
{
  "hero_name": "Juggernaut",
  "team": "Team Secret",
  "player_slot": 0,
  "gpm": 763,
  "xpm": 745,
  "tower_damage": 9333,
  "hero_healing": 8069,
  "lane_efficiency_pct": 94,
  "kills": 5,
  "deaths": 0,
  "assists": 7,
  "last_hits": 412,
  "denies": 18,
  "net_worth": 28450,
  "hero_damage": 31250,
  "damage_taken": 12800,
  "teamfight_participation": 0.85,
  "actions_per_min": 245,
  "clicks_per_min": 180,
  "won": true
}
```

### CSV Format:
One row per player with all 20+ fields!

---

## Field Relationships

### Farming Stats:
- `gpm` + `last_hits` + `denies` = Farming efficiency
- `net_worth` = End result of farming

### Combat Stats:
- `hero_damage` + `damage_taken` = Combat engagement
- `kills` + `deaths` + `assists` = Combat effectiveness
- `teamfight_participation` = Combat involvement

### Mechanical Stats:
- `actions_per_min` + `clicks_per_min` = Player speed/skill
- Higher values = more active, faster gameplay

### Economy Stats:
- `gpm` = Gold income rate
- `net_worth` = Total wealth
- `last_hits` = Main gold source

---

## Analysis Ideas

### Farm Priority:
Sort by `net_worth` or `last_hits` → Identify carry players

### Combat Effectiveness:
Sort by `hero_damage` / `deaths` → Identify efficient damage dealers

### Teamfight Players:
Sort by `teamfight_participation` → Identify playmakers

### Mechanical Skill:
Sort by `actions_per_min` → Identify mechanically skilled players

### Farming Efficiency:
Compare `last_hits` vs `denies` → Identify good laners

### Tank/Frontline:
Sort by `damage_taken` → Identify space creators

---

## Comparison to Previous Version

### Before (12 fields per player):
- Basic stats only
- GPM, XPM, K/D/A
- Tower damage, healing
- Lane efficiency

### Now (20 fields per player):
- **All previous fields** ✓
- **+ Farming stats** (last hits, denies)
- **+ Economy** (net worth)
- **+ Combat stats** (hero damage, damage taken)
- **+ Teamplay** (teamfight participation)
- **+ Mechanics** (APM, CPM)

---

## File Size Impact

### Approximate Size Increase:
- **Before**: ~100 KB per 100 matches
- **Now**: ~120 KB per 100 matches
- **Increase**: ~20% larger files

Still much smaller than full OpenDota data (95%+ reduction)!

---

## Command Still The Same

```bash
python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31 skip=DPC
```

**No changes needed!** The new fields are automatically included.

---

## Summary

### What Changed:
- ✅ Added 8 new fields
- ✅ Total: 20+ fields per player now
- ✅ More comprehensive stats
- ✅ Better analysis potential

### What Stayed the Same:
- ✅ Same command format
- ✅ Same checkpoint protection
- ✅ Same tournament filtering
- ✅ Same date range options

### File Sizes:
- ✅ Still compact (~20% larger than before)
- ✅ Still 95%+ smaller than full OpenDota data

**Now you have comprehensive player stats for detailed analysis!** 📊✨
