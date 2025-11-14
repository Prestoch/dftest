# Dota 2 Betting Simulation Results

## Main Results File

**`betting_simulation_results_complete.csv`** - 27 KB, 576 rows

### Format
Matches exactly: `strategy_results_20220101_20230101_cs_pro_cap.csv`

### Columns (11)
1. **strategy_group** - Betting strategy type (Flat100, Pct5, Fib1, Fib5)
2. **hero_filter** - Hero analysis scope (none, 4heroes, 5heroes)
3. **odds_condition** - Market filter (any, underdog, favorite)
4. **delta_threshold** - Minimum |Δ| to place bet (5-400)
5. **bets** - Total number of bets placed
6. **wins** - Number of winning bets
7. **win_pct** - Win percentage (integer, 0-100)
8. **final_bank** - Final bankroll (integer, starting: 1000)
9. **max_drawdown** - Maximum drawdown from peak (integer)
10. **max_stake** - Largest single bet placed (integer)
11. **max_step** - Maximum Fibonacci step reached (integer)

### Data Period
- **Start Date:** 2023-01-02
- **End Date:** 2025-11-06
- **Total Matches:** 26,801 professional Dota 2 matches

### Strategy Types

#### Flat100
- Fixed $100 bet per match
- Simple, high-risk approach
- Best for aggressive bettors with discipline

#### Pct5
- 5% of current bankroll per bet
- Conservative, protects capital
- Lower variance, stable growth

#### Fib1
- Fibonacci sequence with $1 base unit
- Very conservative progression
- Best for learning/testing

#### Fib5
- Fibonacci sequence with $5 base unit
- Moderate risk progression
- Balances growth and safety

### Hero Filters

- **none** - Use all 5 heroes from each team (full analysis)
- **4heroes** - Use only first 4 heroes (excluding 5th support)
- **5heroes** - Same as 'none' (explicit full team)

### Odds Conditions

- **any** - Bet on any qualifying match
- **underdog** - Only bet on underdogs (higher odds)
- **favorite** - Only bet on favorites (lower odds)

## Top Performing Strategies

### 🥇 #1: Flat100, 4heroes, underdog, threshold 100
- **Final Bank:** $2,773
- **Profit:** $1,773
- **ROI:** 177.3%
- **Bets:** 151
- **Win Rate:** 46%
- **Max Drawdown:** $1,773

### 🥈 #2: Fib1, 4heroes, underdog, threshold 25
- **Final Bank:** $2,450
- **Profit:** $1,450
- **ROI:** 145.0%
- **Bets:** 6,133
- **Win Rate:** 39%
- **Max Drawdown:** $2,411
- **Max Step:** 14

### 🥉 #3: Flat100, 4heroes, any, threshold 100
- **Final Bank:** $2,118
- **Profit:** $1,118
- **ROI:** 111.8%
- **Bets:** 330
- **Win Rate:** 57%
- **Max Drawdown:** $1,438

## Key Findings

### Profitability
- **Profitable Configs:** 51 / 576 (8.9%)
- **Best Strategy Type:** Fibonacci strategies (11.1-11.8% success rate)
- **Surprising Winner:** Underdog betting with 4-hero analysis

### Critical Thresholds
- **|Δ| < 50:** Almost always bankrupt
- **|Δ| 50-75:** Transition zone
- **|Δ| 100-150:** Sweet spot for profitability
- **|Δ| > 200:** Too restrictive (very few bets)

### Hero Analysis
- **4heroes filter:** Most profitable configurations
- **Focusing on core heroes (excluding 5th support) provided cleaner signals**
- **Full team (5heroes) requires higher thresholds**

### Market Selection
- **Underdogs:** Surprisingly effective with proper thresholds
- **Favorites:** Consistent but lower returns
- **Any:** Good balance when selective

## Usage Examples

### Load in Python
```python
import pandas as pd

df = pd.read_csv('betting_simulation_results_complete.csv')

# Find all profitable strategies
profitable = df[df['final_bank'] > 1000]

# Filter by strategy type
flat100 = df[df['strategy_group'] == 'Flat100']

# Find best for specific threshold
best_at_100 = df[df['delta_threshold'] == 100].nlargest(5, 'final_bank')

# Group by strategy type
by_strategy = df.groupby('strategy_group')['final_bank'].describe()
```

### Load in Excel/Google Sheets
1. Open the CSV file
2. Use AutoFilter on headers
3. Sort by `final_bank` to see top performers
4. Filter by `strategy_group` to compare strategy types

## Column Meanings

### win_pct
- Integer percentage (0-100)
- Example: 57 means 57% win rate

### max_drawdown
- Maximum loss from peak bankroll
- Measured in dollars
- Higher = more volatile strategy

### max_stake
- Largest single bet placed
- For Flat100: Always 100
- For Pct5/Fib: Varies with bankroll/sequence

### max_step
- Only for Fibonacci strategies
- How many losses in a row before recovering
- Higher = more stressful drawdown periods

## Important Notes

### Simulation Constraints
- Starting bankroll: $1,000
- Maximum bet: $10,000
- Bankruptcy: Stops when bankroll reaches $0
- No borrowing: Stake limited to current bankroll

### Data Source
- Hero matchups: `cs_stratz_matrix.json` (31,956 professional matches)
- Match data: `hawk_matches_merged.csv` (26,801 matches)
- Professional/competitive matches only

### Limitations
⚠️ **Past performance does not guarantee future results**

- Markets may be more efficient than simulated
- Hero meta changes with patches
- Bookmaker margins not fully reflected
- Real-world discipline is harder than simulated
- Sample sizes vary by threshold

## Additional Files

- **EXECUTIVE_SUMMARY.txt** - Quick overview and recommendations
- **BETTING_SIMULATION_SUMMARY.md** - Detailed analysis
- **ANALYSIS_SUMMARY.md** - Hero matchup matrix documentation
- **betting_simulator.py** - Source code
- **cs_stratz_matrix.json** - Hero matchup advantage data

## Questions?

Review the source code in `betting_simulator.py` for simulation logic details.

---

**Generated:** November 14, 2025  
**Format Version:** Matches strategy_results_20220101_20230101_cs_pro_cap.csv  
**Total Configurations:** 576 (36 strategies × 16 thresholds)
