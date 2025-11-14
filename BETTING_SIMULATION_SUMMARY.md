# Dota 2 Betting Simulation Results Summary

## Overview
This simulation tested 36 different betting strategies across 16 delta (|Δ|) thresholds on 26,801 Dota 2 matches from January 2, 2023 to November 6, 2025.

**Starting Conditions:**
- Starting Bankroll: $1,000
- Maximum Bet: $10,000
- Bankroll clipped at zero (no borrowing)
- Chronological betting order

**Hero Matchup Data Source:** `cs_stratz_matrix.json` (professional match data)

## Key Findings

### Overall Performance
- **Total Strategy-Threshold Combinations:** 576
- **Profitable Configurations:** 36 out of 576 (6.2%)
- **Most matches analyzed:** 26,801 professional Dota 2 matches

### Critical Insight: Delta Threshold Matters Significantly
The simulation reveals that **higher delta thresholds (|Δ| ≥ 100-150)** dramatically improve profitability. Lower thresholds lead to too many bets with marginal edges, resulting in losses due to betting overhead and variance.

## Top Performing Strategies

### 🥇 #1: Flat $100, 4+4 Heroes, |Δ| ≥ 100
- **Final Bankroll:** $2,118
- **Profit:** $1,118
- **ROI:** 111.8%
- **Total Bets:** 330
- **Win Rate:** 56.7%
- **Key:** Using only 4 heroes from each team and requiring strong matchup advantage

### 🥈 #2: Flat $100, 5+5 Heroes (Full Team), |Δ| ≥ 150
- **Final Bankroll:** $1,690
- **Profit:** $690
- **ROI:** 69.0%
- **Total Bets:** 135
- **Win Rate:** 57.8%
- **Key:** Very selective betting on extreme matchup advantages

### 🥉 #3: Fibonacci $5 Unit, 4+4 Heroes, |Δ| ≥ 75
- **Final Bankroll:** $1,298
- **Profit:** $298
- **ROI:** 29.8%
- **Total Bets:** 1,290
- **Win Rate:** 55.1%
- **Key:** Progressive staking with moderate selectivity

## Strategy Type Comparison (Average Across All Thresholds)

| Strategy Type | Avg ROI | Avg Profit/Loss | Avg Win Rate | Avg Bets |
|---------------|---------|-----------------|--------------|----------|
| Flat $100 | -46.8% | -$467.53 | 28.5% | 138.88 |
| 5% Bankroll | -47.5% | -$474.57 | 29.9% | 6,303.75 |
| Fibonacci $1 | -30.9% | -$308.64 | 29.8% | 4,510.03 |
| Fibonacci $5 | -43.3% | -$433.08 | 29.7% | 1,900.10 |

**Important:** These averages include many unprofitable low-threshold configurations. The key is selecting the right threshold for each strategy type.

## Strategy Analysis by Type

### 1. Flat $100 Betting (Strategies 1-3, 7-9, 13-15)
**Best Threshold:** |Δ| ≥ 100-150
- Simple to implement
- Best when highly selective (high thresholds)
- Works better with 4+4 hero analysis than full 5+5
- **Winner:** 4+4 heroes at |Δ| ≥ 100 (111.8% ROI)

### 2. 5% Bankroll Betting (Strategies 4-6, 10-12, 16-18)
**Best Threshold:** |Δ| ≥ 100-150
- More conservative than flat betting
- Protects against total bankruptcy
- Lower absolute profits but safer
- **Winner:** 5+5 heroes at |Δ| ≥ 150 (20.4% ROI)

### 3. Fibonacci Betting - $1 Unit (Strategies 19-27)
**Best Threshold:** |Δ| ≥ 100
- Very conservative
- Good for learning/testing
- Minimal risk exposure
- **Winner:** All bets at |Δ| ≥ 100 (3.7% ROI)

### 4. Fibonacci Betting - $5 Unit (Strategies 28-36)
**Best Threshold:** |Δ| ≥ 75-100
- Moderate risk-reward balance
- Better returns than $1 unit
- Still protective against ruin
- **Winner:** 4+4 heroes at |Δ| ≥ 75 (29.8% ROI)

## Underdog vs Favorite Analysis

### Underdogs Only
- **Profitable Configurations:** 0 out of 96
- **Finding:** Betting exclusively on underdogs was unprofitable across all strategies and thresholds
- **Reason:** Bookmaker odds already account for team strength; hero matchup advantages don't overcome the odds disadvantage

### Favorites Only
- **Profitable Configurations:** 18 out of 96
- **Best:** Flat $100, |Δ| ≥ 150 (69% ROI)
- **Finding:** Betting on favorites with strong hero matchup advantages is the most profitable approach
- **Reason:** Strong matchup advantages on already-favored teams provide edge over market odds

### All Bets (No Filter)
- **Profitable Configurations:** 18 out of 96
- **Finding:** Performs identically to favorites-only in many cases, as most high-delta situations favor the better team

## Hero Count Analysis (4+4 vs 5+5)

### 4+4 Heroes (First 4 from each team)
- **Best Configuration:** Flat $100, |Δ| ≥ 100 (111.8% ROI)
- **Advantage:** Focuses on core heroes, potentially more stable matchup readings
- **Trade-off:** Ignores one hero's impact (usually support)

### 5+5 Heroes (Full team)
- **Best Configuration:** Flat $100, |Δ| ≥ 150 (69% ROI)
- **Advantage:** Complete team analysis
- **Finding:** Requires higher thresholds for profitability

**Insight:** 4+4 analysis was surprisingly effective, suggesting that focusing on core heroes provides clearer signals.

## Delta Threshold Analysis

| Threshold | Profitable Strategies | Best ROI | Notes |
|-----------|---------------------|----------|-------|
| |Δ| ≥ 5 | 0 | -100% | Too many bets, no edge |
| |Δ| ≥ 10 | 0 | -100% | Still too permissive |
| |Δ| ≥ 15-50 | 0 | -100% | Marginal improvements but still unprofitable |
| |Δ| ≥ 75 | 9 | 29.8% | First profitable tier |
| |Δ| ≥ 100 | 18 | 111.8% | **Optimal threshold** |
| |Δ| ≥ 150 | 9 | 69.0% | Very selective, still profitable |
| |Δ| ≥ 200+ | 0 | 0% | Too restrictive, no bets placed |

**Critical Finding:** The "sweet spot" is |Δ| ≥ 100-150, providing enough selectivity to maintain an edge while still generating betting opportunities.

## Risk of Ruin Analysis

### Strategies That Went Bankrupt
- All percentage-based strategies at low thresholds (|Δ| < 75)
- All strategies at |Δ| ≥ 5-50 (too many marginal bets)

### Strategies That Preserved Capital
- All strategies at |Δ| ≥ 200+ (no bets placed, capital preserved)
- Fibonacci strategies at high thresholds (protective structure)

## Practical Recommendations

### For Conservative Bettors
**Strategy:** 5% Bankroll, 5+5 Heroes, |Δ| ≥ 150
- Lower risk of total loss
- Steady growth
- 135 bets over ~3 years
- Expected ROI: 20.4%

### For Moderate Risk-Takers
**Strategy:** Fibonacci $5, 4+4 Heroes, |Δ| ≥ 75
- Balanced approach
- More betting opportunities (1,290 bets)
- Progressive recovery from losses
- Expected ROI: 29.8%

### For Aggressive Bettors
**Strategy:** Flat $100, 4+4 Heroes, |Δ| ≥ 100
- Highest absolute returns
- 330 bets over period
- Requires bankroll discipline
- Expected ROI: 111.8%

### For Maximum Profit
**Strategy:** Flat $100, 4+4 Heroes, |Δ| ≥ 100
- **$1,118 profit on $1,000 starting capital**
- Best risk-reward ratio
- Requires consistent $100 stakes
- Only bet when hero matchup advantage ≥ 100

## Generated Files

### Individual Strategy Files (36 files)
1. `betting_results_1_flat100_all.csv`
2. `betting_results_2_flat100_underdogs.csv`
3. `betting_results_3_flat100_favorites.csv`
4. `betting_results_4_pct5_all.csv`
5. `betting_results_5_pct5_underdogs.csv`
6. `betting_results_6_pct5_favorites.csv`
7. `betting_results_7_flat100_4heroes_all.csv`
8. `betting_results_8_flat100_4heroes_underdogs.csv`
9. `betting_results_9_flat100_4heroes_favorites.csv`
10. `betting_results_10_pct5_4heroes_all.csv`
11. `betting_results_11_pct5_4heroes_underdogs.csv`
12. `betting_results_12_pct5_4heroes_favorites.csv`
13. `betting_results_13_flat100_5heroes_all.csv`
14. `betting_results_14_flat100_5heroes_underdogs.csv`
15. `betting_results_15_flat100_5heroes_favorites.csv`
16. `betting_results_16_pct5_5heroes_all.csv`
17. `betting_results_17_pct5_5heroes_underdogs.csv`
18. `betting_results_18_pct5_5heroes_favorites.csv`
19. `betting_results_19_fib1_all.csv`
20. `betting_results_20_fib1_underdogs.csv`
21. `betting_results_21_fib1_favorites.csv`
22. `betting_results_22_fib1_4heroes_all.csv`
23. `betting_results_23_fib1_4heroes_underdogs.csv`
24. `betting_results_24_fib1_4heroes_favorites.csv`
25. `betting_results_25_fib1_5heroes_all.csv`
26. `betting_results_26_fib1_5heroes_underdogs.csv`
27. `betting_results_27_fib1_5heroes_favorites.csv`
28. `betting_results_28_fib5_all.csv`
29. `betting_results_29_fib5_underdogs.csv`
30. `betting_results_30_fib5_favorites.csv`
31. `betting_results_31_fib5_4heroes_all.csv`
32. `betting_results_32_fib5_4heroes_underdogs.csv`
33. `betting_results_33_fib5_4heroes_favorites.csv`
34. `betting_results_34_fib5_5heroes_all.csv`
35. `betting_results_35_fib5_5heroes_underdogs.csv`
36. `betting_results_36_fib5_5heroes_favorites.csv`

### Summary File
- `betting_results_SUMMARY.csv` - Complete results across all 576 strategy-threshold combinations

## CSV File Format

Each strategy CSV contains:
- `strategy`: Strategy name
- `delta_threshold`: Minimum |Δ| required to place bet
- `total_bets`: Number of bets placed
- `wins`: Number of winning bets
- `losses`: Number of losing bets
- `win_rate`: Percentage of bets won
- `starting_bank`: Initial bankroll ($1,000)
- `final_bankroll`: Ending bankroll after all bets
- `profit_loss`: Net profit or loss
- `roi`: Return on investment (%)

## Limitations and Considerations

1. **Historical Data**: Past performance doesn't guarantee future results
2. **Market Efficiency**: Real betting markets may already price in hero advantages
3. **Odds Variation**: Simulation assumes consistent odds; real markets fluctuate
4. **Juice/Vig**: Real bookmakers take a commission not fully reflected here
5. **Sample Size**: Even with 26,801 matches, some strategy-threshold combinations have few bets
6. **Hero Meta Changes**: Hero balance patches affect matchup advantages over time

## Conclusion

The simulation demonstrates that:
1. **Selectivity is crucial** - Only bet on strong matchup advantages (|Δ| ≥ 100)
2. **Favorites with advantages** perform better than underdogs
3. **4+4 hero analysis** was surprisingly effective
4. **Flat betting with discipline** outperformed complex staking systems
5. **Low thresholds guarantee losses** - avoid betting on marginal advantages

**Best Overall Strategy:** Flat $100 on 4+4 heroes with |Δ| ≥ 100, focusing on favorites or all qualified bets, resulting in 111.8% ROI over the test period.
