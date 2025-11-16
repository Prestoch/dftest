#!/usr/bin/env node

/**
 * Simulate betting strategies driven by cs_pro hero advantage deltas.
 * Output mirrors strategy_results_20220101_20230101_cs_pro_cap.csv column order.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const START_BANK = 1000;
const MAX_BET = 10000;
const DATA_FILE = path.join(__dirname, 'hawk_matches_merged.csv');
const CS_FILE = path.join(__dirname, 'cs_pro.json');
const DEFAULT_OUTPUT_FILE = path.join(__dirname, 'strategy_results_latest_cs_pro.csv');

const DELTA_THRESHOLDS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 75, 100, 125, 150, 200, 250, 300, 350, 400];

let CONFIG_ORDER = 0;
const STRATEGY_DEFS = (() => {
  const base = [];

  // Utility to add trio of odds conditions for a strategy definition
  const withOdds = (baseConfig) => {
    ['any', 'underdog', 'favorite'].forEach((odds_condition) => {
      base.push({ ...baseConfig, odds_condition, order: CONFIG_ORDER++ });
    });
  };

  // 1-3 Flat $100 (no hero filter)
  withOdds({ strategy_group: 'Flat100', hero_filter: 'none', stakeType: 'flat_amount', amount: 100 });

  // 4-6: 5% bankroll per bet (no hero filter)
  withOdds({ strategy_group: 'Bankroll5pct', hero_filter: 'none', stakeType: 'bankroll_percent', percent: 0.05 });

  // 7-9: Flat $100 with 4+4-
  withOdds({ strategy_group: 'Flat100', hero_filter: '4+4-', stakeType: 'flat_amount', amount: 100 });

  // 10-12: Flat 5% (constant) with 4+4-
  withOdds({ strategy_group: 'Flat5pct', hero_filter: '4+4-', stakeType: 'flat_percent', percent: 0.05 });

  // 13-15: Flat $100 with 5+5-
  withOdds({ strategy_group: 'Flat100', hero_filter: '5+5-', stakeType: 'flat_amount', amount: 100 });

  // 16-18: Flat 5% with 5+5-
  withOdds({ strategy_group: 'Flat5pct', hero_filter: '5+5-', stakeType: 'flat_percent', percent: 0.05 });

  // 19-27: Fibonacci 1$ unit (hero filters none, 4+4-, 5+5-)
  ['none', '4+4-', '5+5-'].forEach((hero_filter) => {
    withOdds({ strategy_group: 'Fib1', hero_filter, stakeType: 'fibonacci', unit: 1 });
  });

  // 28-36: Fibonacci $5 unit
  ['none', '4+4-', '5+5-'].forEach((hero_filter) => {
    withOdds({ strategy_group: 'Fib5', hero_filter, stakeType: 'fibonacci', unit: 5 });
  });

  return base;
})();

const fibCache = [1, 1];
function fibValue(index) {
  while (fibCache.length <= index) {
    const len = fibCache.length;
    fibCache.push(fibCache[len - 1] + fibCache[len - 2]);
  }
  return fibCache[index];
}

function parseCSVLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      result.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current);
  return result;
}

function normalize(text) {
  return (text || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function loadCSData() {
  const content = fs.readFileSync(CS_FILE, 'utf8');
  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(content, sandbox);
  const heroes = sandbox.heroes;
  const heroesWr = (sandbox.heroes_wr || []).map((v) => parseFloat(v));
  const winRates = sandbox.win_rates;
  if (!Array.isArray(heroes) || !Array.isArray(heroesWr) || !Array.isArray(winRates)) {
    throw new Error('cs_pro.json missing expected arrays');
  }
  const heroIndexMap = new Map();
  heroes.forEach((hero, idx) => {
    heroIndexMap.set(normalize(hero), idx);
  });
  return { heroes, heroesWr, winRates, heroIndexMap };
}

function heroIndexLookup(heroIndexMap, name) {
  const idx = heroIndexMap.get(normalize(name));
  if (idx === undefined) {
    throw new Error(`Hero not found: ${name}`);
  }
  return idx;
}

function calcTeamStats(heroIdxs, opponentIdxs, heroesWr, winRates) {
  const heroData = heroIdxs.map((heroIdx) => {
    const heroRow = winRates[heroIdx];
    let advantage = 0;
    if (Array.isArray(heroRow)) {
      opponentIdxs.forEach((oppIdx) => {
        const cell = heroRow[oppIdx];
        if (cell && cell[0] != null) {
          const val = parseFloat(cell[0]);
          if (!Number.isNaN(val)) {
            advantage += val;
          }
        }
      });
    }
    const winrate = heroesWr[heroIdx] || 50;
    return { winrate, advantage };
  });

  const score = heroData.reduce((sum, hero) => sum + hero.winrate + hero.advantage, 0);
  const pos = heroData.filter((hero) => hero.advantage > 0).length;
  const neg = heroData.filter((hero) => hero.advantage < 0).length;
  return { score, pos, neg };
}

function parseMatches(csData, options) {
  const champFilters = (options.championships || []).map((c) => c.trim()).filter(Boolean);
  const champFilterSet = new Set(champFilters.map((c) => c.toLowerCase()));
  const useChampFilter = champFilterSet.size > 0;
  const raw = fs.readFileSync(DATA_FILE, 'utf8').trim().split(/\r?\n/);
  const headers = parseCSVLine(raw[0]);
  const matches = [];
  let skippedMissingHero = 0;
  let skippedOdds = 0;
  let skippedChampionship = 0;

  for (let i = 1; i < raw.length; i++) {
    const line = raw[i];
    if (!line) continue;
    const values = parseCSVLine(line);
    const row = {};
    headers.forEach((header, idx) => {
      row[header] = values[idx] ?? '';
    });

    if (useChampFilter) {
      const champName = (row.championship || '').trim();
      if (!champFilterSet.has(champName.toLowerCase())) {
        skippedChampionship++;
        continue;
      }
    }

    const team1Heroes = (row.team1_heroes || '').split('|').map((h) => h.trim()).filter(Boolean);
    const team2Heroes = (row.team2_heroes || '').split('|').map((h) => h.trim()).filter(Boolean);
    if (team1Heroes.length !== 5 || team2Heroes.length !== 5) {
      skippedMissingHero++;
      continue;
    }

    let team1Idxs, team2Idxs;
    try {
      team1Idxs = team1Heroes.map((hero) => heroIndexLookup(csData.heroIndexMap, hero));
      team2Idxs = team2Heroes.map((hero) => heroIndexLookup(csData.heroIndexMap, hero));
    } catch (err) {
      skippedMissingHero++;
      continue;
    }

    const team1Stats = calcTeamStats(team1Idxs, team2Idxs, csData.heroesWr, csData.winRates);
    const team2Stats = calcTeamStats(team2Idxs, team1Idxs, csData.heroesWr, csData.winRates);

    const team1Odds = parseFloat(row.team1_odds);
    const team2Odds = parseFloat(row.team2_odds);
    if (!Number.isFinite(team1Odds) || !Number.isFinite(team2Odds) || team1Odds <= 1 || team2Odds <= 1) {
      skippedOdds++;
      continue;
    }

    const delta = team1Stats.score - team2Stats.score;
    const favoredFirst = delta >= 0;
    const favoredTeam = favoredFirst ? row.team1 : row.team2;
    const favoredScore = favoredFirst ? team1Stats : team2Stats;
    const opponentScore = favoredFirst ? team2Stats : team1Stats;
    const favoredOdds = favoredFirst ? team1Odds : team2Odds;
    const opponentOdds = favoredFirst ? team2Odds : team1Odds;

    const heroFilter4 = favoredScore.pos >= 4 && opponentScore.neg >= 4;
    const heroFilter5 = favoredScore.pos >= 5 && opponentScore.neg >= 5;

    const oddsDiff = favoredOdds - opponentOdds;
    const favoredIsFavorite = oddsDiff < -1e-9;
    const favoredIsUnderdog = oddsDiff > 1e-9;

    const winner = normalize(row.winner);
    const favoredNameNorm = normalize(favoredTeam);
    const betWin = winner && winner === favoredNameNorm;

    const date = new Date(row.date);
    const orderKey = date.getTime() || 0;
    const mapNumber = parseInt(row.map_number, 10) || 0;
    const seriesId = parseInt(row.series_id, 10) || 0;
    const hawkId = parseInt(row.hawk_match_id, 10) || 0;

    matches.push({
      absDelta: Math.abs(delta),
      favoredOdds,
      opponentOdds,
      betWin,
      heroFilter4,
      heroFilter5,
      favoredIsFavorite,
      favoredIsUnderdog,
      orderToken: {
        orderKey,
        seriesId,
        mapNumber,
        hawkId,
      },
    });
  }

  matches.sort((a, b) => {
    if (a.orderToken.orderKey !== b.orderToken.orderKey) {
      return a.orderToken.orderKey - b.orderToken.orderKey;
    }
    if (a.orderToken.seriesId !== b.orderToken.seriesId) {
      return a.orderToken.seriesId - b.orderToken.seriesId;
    }
    if (a.orderToken.mapNumber !== b.orderToken.mapNumber) {
      return a.orderToken.mapNumber - b.orderToken.mapNumber;
    }
    return a.orderToken.hawkId - b.orderToken.hawkId;
  });

  console.log(`Matches parsed: ${matches.length}`);
  console.log(`Skipped (heroes missing or unmatched): ${skippedMissingHero}`);
  console.log(`Skipped (invalid odds): ${skippedOdds}`);
  if (useChampFilter) {
    console.log(`Skipped (filtered championships): ${skippedChampionship}`);
  }

  return matches;
}

function shouldBet(match, config, threshold) {
  if (match.absDelta < threshold) return false;
  if (config.hero_filter === '4+4-' && !match.heroFilter4) return false;
  if (config.hero_filter === '5+5-' && !match.heroFilter5) return false;
  if (config.odds_condition === 'underdog' && !match.favoredIsUnderdog) return false;
  if (config.odds_condition === 'favorite' && !match.favoredIsFavorite) return false;
  return true;
}

function computeStake(config, state) {
  switch (config.stakeType) {
    case 'flat_amount':
      return config.amount;
    case 'flat_percent':
      return state.flatPercentAmount;
    case 'bankroll_percent':
      return state.bank * config.percent;
    case 'fibonacci': {
      const stepValue = fibValue(state.fibIndex);
      return stepValue * config.unit;
    }
    default:
      return 0;
  }
}

function clipMoney(value) {
  const rounded = Math.round(value);
  return rounded < 0 ? 0 : rounded;
}

function runStrategy(matches, config, threshold) {
  let bank = START_BANK;
  let peak = bank;
  let maxDrawdown = 0;
  let maxStake = 0;
  let bets = 0;
  let wins = 0;
  let fibIndex = 0;
  let maxStep = 0;
  const flatPercentAmount = Math.round(START_BANK * (config.percent || 0));

  for (const match of matches) {
    if (bank <= 0) break;
    if (!shouldBet(match, config, threshold)) continue;

    let stake = computeStake(config, {
      bank,
      fibIndex,
      flatPercentAmount,
    });
    if (!Number.isFinite(stake) || stake <= 0) continue;

    stake = Math.min(stake, bank, MAX_BET);
    stake = Math.round(stake);
    if (stake <= 0) continue;

    bets += 1;
    maxStake = Math.max(maxStake, stake);
    if (config.stakeType === 'fibonacci') {
      maxStep = Math.max(maxStep, fibIndex);
    }

    bank -= stake;
    let won = false;
    if (match.betWin) {
      won = true;
      wins += 1;
      const payout = Math.round(stake * match.favoredOdds);
      bank += payout;
      bank = clipMoney(bank);
      if (config.stakeType === 'fibonacci') {
        fibIndex = Math.max(0, fibIndex - 2);
      }
    } else {
      if (config.stakeType === 'fibonacci') {
        fibIndex += 1;
      }
    }

    if (bank > peak) {
      peak = bank;
    } else {
      const drawdown = peak - bank;
      if (drawdown > maxDrawdown) {
        maxDrawdown = drawdown;
      }
    }
  }

  return {
    strategy_group: config.strategy_group,
    hero_filter: config.hero_filter,
    odds_condition: config.odds_condition,
    delta_threshold: threshold,
    bets,
    wins,
    win_pct: bets ? Math.round((wins / bets) * 100) : 0,
    final_bank: clipMoney(bank),
    max_drawdown: clipMoney(maxDrawdown),
    max_stake: Math.round(maxStake),
    max_step: config.stakeType === 'fibonacci' ? maxStep : 0,
  };
}

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    output: DEFAULT_OUTPUT_FILE,
    championships: [],
  };
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if ((arg === '--output' || arg === '-o') && i + 1 < args.length) {
      options.output = path.resolve(args[++i]);
    } else if ((arg === '--championship' || arg === '--champ') && i + 1 < args.length) {
      options.championships.push(args[++i]);
    } else if (arg === '--championships' && i + 1 < args.length) {
      options.championships.push(...args[++i].split(','));
    }
  }
  return options;
}

function main() {
  const options = parseArgs();
  if (options.championships.length) {
    console.log(`Filtering championships: ${options.championships.join(', ')}`);
  } else {
    console.log('No championship filter; using entire dataset.');
  }

  const csData = loadCSData();
  const matches = parseMatches(csData, options);

  const results = [];
  for (const config of STRATEGY_DEFS) {
    for (const threshold of DELTA_THRESHOLDS) {
      const stats = runStrategy(matches, config, threshold);
      stats.order = config.order;
      results.push(stats);
    }
  }

  results.sort((a, b) => {
    if (a.order !== b.order) {
      return a.order - b.order;
    }
    return a.delta_threshold - b.delta_threshold;
  });

  const header = 'strategy_group,hero_filter,odds_condition,delta_threshold,bets,wins,win_pct,final_bank,max_drawdown,max_stake,max_step';
  const lines = results.map((row) =>
    [
      row.strategy_group,
      row.hero_filter,
      row.odds_condition,
      row.delta_threshold,
      row.bets,
      row.wins,
      row.win_pct,
      row.final_bank,
      row.max_drawdown,
      row.max_stake,
      row.max_step,
    ].join(',')
  );

  const csvContent = [header, ...lines].join('\n');
  fs.writeFileSync(options.output, csvContent);
  console.log(`Results written to ${options.output}`);
}

main();

