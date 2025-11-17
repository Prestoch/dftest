const path = require('path');
const { runWithOptions } = require('./run_delta_pct_custom');

const result = runWithOptions({
  dataFile: path.resolve('hawk_matches_merged.csv'),
  matrixFile: path.resolve('cs_pro_from_filtered.json'),
  summaryFile: path.resolve('delta_pct_strategy_2025AugNov_cap500k_delta20_summary.csv'),
  betsFile: path.resolve('delta_pct_strategy_2025AugNov_cap500k_delta20_bets.csv'),
  monthFrom: '2025-08',
  monthTo: '2025-11',
  maxBet: 500000,
  minDelta: 20,
});

console.log(JSON.stringify(result, null, 2));
