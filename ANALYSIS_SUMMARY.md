# Dota 2 Hero Matchup Matrix Analysis

## Overview
This document summarizes the analysis of `cs_original.json` and `stratz_with_tiers_filtered.json`, and the creation of a new hero matchup matrix.

## Data Source Analysis

### cs_original.json
- **Format**: JavaScript variable declarations (single line)
- **Size**: 433 KB
- **Update Date**: 2025-11-05
- **Structure**:
  - `heroes`: Array of 126 hero names
  - `heroes_bg`: Array of 126 hero background image URLs (Dotabuff assets)
  - `heroes_wr`: Array of 126 hero win rates (as percentage strings)
  - `win_rates`: 126x126 matrix of hero vs hero matchup data
    - Each matchup: `[advantage, win_rate, total_games]`
    - `advantage`: Difference from 50% (positive = favored)
    - `win_rate`: Win percentage in that matchup
    - `total_games`: Number of games in that matchup
- **Data Source**: Appears to be from Dotabuff (based on image URLs)

### stratz_with_tiers_filtered.json
- **Format**: JSON object with match IDs as keys
- **Size**: 16 MB
- **Total Matches**: 31,956
- **Structure**: Each match contains:
  - `radiantWin`: Boolean indicating which team won
  - `radiantRoles`: Array of 5 heroes with `heroId` and `role`
  - `direRoles`: Array of 5 heroes with `heroId` and `role`
  - `leagueId`: Tournament ID
  - `leagueName`: Tournament name
  - `leagueTier`: Tournament tier (INTERNATIONAL, PROFESSIONAL, etc.)
- **Data Source**: Stratz API (professional/competitive matches)

### hero_id_map.json
- **Purpose**: Maps Stratz hero IDs to cs_original.json array indices
- **Mappings**: 126 hero mappings
- **Format**: `{"stratz_id": "cs_index", ...}`

## Generated Output: cs_stratz_matrix.json

### Statistics
- **File Size**: 432 KB (similar to original)
- **Total Heroes**: 126
- **Matches Analyzed**: 31,956
- **Matrix Dimensions**: 126x126
- **Unique Matchups with Data**: 15,244 (out of 15,750 possible)
- **Most Played Hero**: Tiny (8,655 games)
- **Heroes with Game Data**: 124 out of 126

### Generation Process
1. **Load Data**: Parse all three input files
2. **Process Matches**: For each of 31,956 matches:
   - Extract 5 Radiant heroes vs 5 Dire heroes
   - Record all 25 individual hero matchups (5x5)
   - Track wins/losses for each matchup
3. **Calculate Statistics**:
   - Overall hero win rates across all matches
   - Head-to-head win rates for each hero pair
   - Advantage metrics (deviation from 50%)
4. **Format Output**: Generate JavaScript format matching cs_original.json

### Key Differences from Original
| Aspect | cs_original.json | cs_stratz_matrix.json |
|--------|------------------|----------------------|
| Data Source | Dotabuff (public matches) | Stratz (pro matches) |
| Sample Size | Unknown | 31,956 matches |
| Win Rates | Public match data | Professional match data |
| Update Date | 2025-11-05 | 2025-11-14 |

### Example Win Rate Comparison
| Hero | Original WR | Stratz WR | Difference |
|------|------------|-----------|------------|
| Abaddon | 52.98% | 47.42% | -5.56% |
| Bounty Hunter | 49.11% | 51.49% | +2.38% |
| Dark Seer | 48.93% | 52.90% | +3.97% |
| Earthshaker | 49.59% | 51.51% | +1.92% |
| Invoker | 48.92% | 49.55% | +0.63% |
| Lifestealer | 51.71% | 49.91% | -1.80% |

**Note**: Differences are expected because:
- Original data likely includes all skill levels (public matches)
- Stratz data is from professional/competitive matches only
- Professional meta differs significantly from public games

## Matrix Structure Details

### Format
```javascript
var heroes = ["Abaddon", "Alchemist", ...], 
heroes_bg = ["https://...", ...], 
heroes_wr = ["47.42", "49.96", ...], 
win_rates = [
  [null, ["0.8323", "51.4546", 33410], ...],  // Abaddon's matchups
  [...],                                        // Alchemist's matchups
  ...
], 
update_time = "2025-11-14";
```

### Matchup Data Format
Each non-null entry in `win_rates[hero_a][hero_b]` represents:
- `[0]`: Advantage score (win_rate - 50.0)
- `[1]`: Win rate percentage
- `[2]`: Total games played in this matchup

Example: `["0.8323", "51.4546", 33410]` means:
- 0.8323% advantage (slightly favored)
- 51.45% win rate
- 33,410 total games

## Usage

The generated `cs_stratz_matrix.json` can be used as a drop-in replacement for `cs_original.json` in any application that visualizes or analyzes Dota 2 hero matchup data, with the understanding that it represents professional-level gameplay rather than public matches.

## Files Generated
- **cs_stratz_matrix.json**: Main output file with hero matchup matrix
- **create_matrix.py**: Python script used to generate the matrix
- **ANALYSIS_SUMMARY.md**: This documentation file
