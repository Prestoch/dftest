#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const INITIAL_BANK = 1000;
const MAX_BET = 10000;
const DELTA_THRESHOLDS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 75];

function main() {
  const csPath = path.join(process.cwd(), 'cs.json');
  const hawkPath = path.join(process.cwd(), 'hawk_matches_merged.csv');
  const heroData = loadCsData(csPath);
  const matches = loadMatches(hawkPath, heroData);
  console.log(`Loaded ${matches.length} matches with matchup data`);

  const combos = buildCombos();
  const rows = [];
  rows.push('strategy_group,hero_filter,odds_condition,delta_threshold,bets,wins,win_pct,final_bank,max_drawdown,max_stake,max_step');

  for (const combo of combos) {
    for (const deltaThreshold of DELTA_THRESHOLDS) {
      const stats = simulateStrategy(matches, combo, deltaThreshold);
      rows.push(formatRow(stats));
    }
  }

  const outPath = path.join(process.cwd(), 'strategy_results_hawk.csv');
  fs.writeFileSync(outPath, rows.join('\n'));
  console.log(`Wrote ${rows.length - 1} strategy rows to ${outPath}`);
}

function loadCsData(csPath) {
  const script = fs.readFileSync(csPath, 'utf8');
  const context = {};
  vm.createContext(context);
  vm.runInContext(script, context);
  const { heroes, heroes_wr: heroesWr, win_rates: winRates } = context;
  if (!Array.isArray(heroes) || !Array.isArray(heroesWr) || !Array.isArray(winRates)) {
    throw new Error('Failed to load heroes data from cs.json');
  }
  const heroIndex = new Map();
  heroes.forEach((name, idx) => {
    heroIndex.set(normalizeHeroName(name), idx);
  });
  return {
    heroes,
    heroesWr,
    winRates,
    heroIndex,
    missingHeroes: new Map(),
  };
}

function loadMatches(csvPath, heroData) {
  const text = fs.readFileSync(csvPath, 'utf8');
  const lines = text.split(/\r?\n/);
  const header = lines.shift();
  if (!header) {
    throw new Error('CSV header missing');
  }
  const matches = [];
  const skipCounters = {
    blank: 0,
    malformed: 0,
    delta: 0,
    heroes: 0,
    heroLookup: 0,
    odds: 0,
    favored: 0,
  };

  lines.forEach((line, idx) => {
    if (!line || !line.trim()) {
      skipCounters.blank += 1;
      return;
    }
    const row = parseCsvLine(line);
    if (row.length < 14) {
      skipCounters.malformed += 1;
      return;
    }
    const deltaRaw = parseNumber(row[10]);
    if (!Number.isFinite(deltaRaw)) {
      skipCounters.delta += 1;
      return;
    }
    const deltaAbs = Math.abs(deltaRaw);
    const team1Heroes = splitHeroes(row[7]);
    const team2Heroes = splitHeroes(row[8]);
    if (team1Heroes.length !== 5 || team2Heroes.length !== 5) {
      skipCounters.heroes += 1;
      return;
    }
    const team1Ids = heroNamesToIds(team1Heroes, heroData);
    const team2Ids = heroNamesToIds(team2Heroes, heroData);
    if (!team1Ids || !team2Ids) {
      skipCounters.heroLookup += 1;
      return;
    }
    const team1Counts = computeTeamCounts(team1Ids, team2Ids, heroData);
    const team2Counts = computeTeamCounts(team2Ids, team1Ids, heroData);

    const deltaFavTeam = (row[11] || '').trim();
    const team1Name = (row[5] || '').trim();
    const team2Name = (row[6] || '').trim();
    if (!deltaFavTeam || !team1Name || !team2Name) {
      skipCounters.favored += 1;
      return;
    }
    let deltaFavIsTeam1 = null;
    if (team1Name === deltaFavTeam) {
      deltaFavIsTeam1 = true;
    } else if (team2Name === deltaFavTeam) {
      deltaFavIsTeam1 = false;
    } else {
      skipCounters.favored += 1;
      return;
    }

    const team1Odds = parseNumber(row[12]);
    const team2Odds = parseNumber(row[13]);
    if (!Number.isFinite(team1Odds) || !Number.isFinite(team2Odds) || team1Odds <= 1 || team2Odds <= 1) {
      skipCounters.odds += 1;
      return;
    }

    const favOdds = deltaFavIsTeam1 ? team1Odds : team2Odds;
    const dogOdds = deltaFavIsTeam1 ? team2Odds : team1Odds;
    const oddsRelation = classifyOddsRelation(favOdds, dogOdds);

    matches.push({
      deltaAbs,
      deltaFavTeam,
      deltaDogTeam: deltaFavIsTeam1 ? team2Name : team1Name,
      deltaFavIsTeam1,
      favOdds,
      dogOdds,
      oddsRelation,
      winner: (row[9] || '').trim(),
      team1Pos: team1Counts.pos,
      team1Neg: team1Counts.neg,
      team2Pos: team2Counts.pos,
      team2Neg: team2Counts.neg,
    });
  });

  if (heroData.missingHeroes.size > 0) {
    console.warn(`Missing hero mappings for ${heroData.missingHeroes.size} hero names`);
  }
  console.log('Skip counters:', skipCounters);
  return matches;
}

function simulateStrategy(matches, combo, deltaThreshold) {
  let bank = INITIAL_BANK;
  let bets = 0;
  let wins = 0;
  let peak = bank;
  let maxDrawdown = 0;
  let maxStake = 0;
  let fibStep = 0;
  let maxStepReached = 0;

  for (const match of matches) {
    if (bank <= 0) {
      bank = 0;
      break;
    }

    if (!Number.isFinite(match.deltaAbs) || match.deltaAbs < deltaThreshold) {
      continue;
    }

    if (combo.odds_condition === 'favorite' && match.oddsRelation !== 'favorite') {
      continue;
    }
    if (combo.odds_condition === 'underdog' && match.oddsRelation !== 'underdog') {
      continue;
    }

    if (!heroFilterSatisfied(match, combo.hero_filter)) {
      continue;
    }

    const odds = match.favOdds;
    if (!Number.isFinite(odds) || odds <= 1) {
      continue;
    }

    const desiredStake = computeStake(bank, combo, fibStep);
    const stake = Math.min(desiredStake, MAX_BET, bank);
    if (stake <= 0) {
      continue;
    }

    const stepBefore = fibStep;
    bank -= stake;
    bets += 1;
    if (stake > maxStake) {
      maxStake = stake;
    }

    const betWon = match.winner === match.deltaFavTeam;
    if (combo.stake_type === 'fibonacci' && stepBefore > maxStepReached) {
      maxStepReached = stepBefore;
    }

    if (betWon) {
      wins += 1;
      bank += stake * odds;
      if (combo.stake_type === 'fibonacci') {
        fibStep = stepBefore <= 1 ? 0 : stepBefore - 2;
      }
    } else {
      if (combo.stake_type === 'fibonacci') {
        fibStep = stepBefore + 1;
      }
    }

    if (bank > peak) {
      peak = bank;
    } else {
      const dd = peak - bank;
      if (dd > maxDrawdown) {
        maxDrawdown = dd;
      }
    }
  }

  const winPct = bets === 0 ? 0 : Math.round((wins / bets) * 100);

  return {
    strategy_group: combo.strategy_group,
    hero_filter: combo.hero_filter,
    odds_condition: combo.odds_condition,
    delta_threshold: deltaThreshold,
    bets,
    wins,
    win_pct: winPct,
    final_bank: Math.round(bank),
    max_drawdown: Math.round(maxDrawdown),
    max_stake: Math.round(maxStake),
    max_step: combo.stake_type === 'fibonacci' ? maxStepReached : 0,
  };
}

function heroFilterSatisfied(match, filter) {
  if (filter === 'none') {
    return true;
  }
  const favPos = match.deltaFavIsTeam1 ? match.team1Pos : match.team2Pos;
  const oppNeg = match.deltaFavIsTeam1 ? match.team2Neg : match.team1Neg;
  if (filter === '4+4-') {
    return favPos >= 4 && oppNeg >= 4;
  }
  if (filter === '5+5-') {
    return favPos >= 5 && oppNeg >= 5;
  }
  return true;
}

function computeStake(bank, combo, fibStep) {
  if (bank <= 0) {
    return 0;
  }
  if (combo.stake_type === 'flat') {
    return Math.min(combo.flat_amount, bank);
  }
  if (combo.stake_type === 'pct_bankroll') {
    const wager = bank * combo.percent;
    return Math.min(wager, bank);
  }
  if (combo.stake_type === 'fibonacci') {
    const fibValue = getFibNumber(fibStep);
    return fibValue * combo.unit;
  }
  throw new Error(`Unknown stake type: ${combo.stake_type}`);
}

const fibCache = [1, 1];
function getFibNumber(step) {
  if (step <= 0) {
    return 1;
  }
  while (fibCache.length <= step) {
    const last = fibCache[fibCache.length - 1];
    const prev = fibCache[fibCache.length - 2];
    fibCache.push(last + prev);
  }
  return fibCache[step];
}

function formatRow(stats) {
  return [
    stats.strategy_group,
    stats.hero_filter,
    stats.odds_condition,
    stats.delta_threshold,
    stats.bets,
    stats.wins,
    stats.win_pct,
    stats.final_bank,
    stats.max_drawdown,
    stats.max_stake,
    stats.max_step,
  ].join(',');
}

function buildCombos() {
  const combos = [];
  const oddsConditions = ['any', 'underdog', 'favorite'];
  const flat100 = amount => ({
    strategy_group: 'Flat100',
    stake_type: 'flat',
    flat_amount: amount,
  });
  const flat5 = amount => ({
    strategy_group: 'Flat5pct',
    stake_type: 'flat',
    flat_amount: amount,
  });
  const pct5 = () => ({
    strategy_group: 'Pct5',
    stake_type: 'pct_bankroll',
    percent: 0.05,
  });
  const fib1 = unit => ({
    strategy_group: unit === 1 ? 'Fibo1' : 'Fibo5',
    stake_type: 'fibonacci',
    unit,
  });

  // Helper to push combos for a stake template and hero filter list
  const pushCombos = (templateFactory, heroFilter, oddsList) => {
    oddsList.forEach(odds_condition => {
      combos.push({
        ...templateFactory(),
        hero_filter: heroFilter,
        odds_condition,
      });
    });
  };

  const pushFlat = (amount, heroFilter) => {
    oddsConditions.forEach(odds_condition => {
      combos.push({
        ...flat100(amount),
        hero_filter: heroFilter,
        odds_condition,
      });
    });
  };

  // 1-3: Flat $100, hero filter none
  pushFlat(100, 'none');
  // 4-6: 5% bankroll per bet, hero filter none
  oddsConditions.forEach(odds_condition => {
    combos.push({
      ...pct5(),
      hero_filter: 'none',
      odds_condition,
    });
  });
  // 7-9: Flat $100, hero filter 4+4-
  pushFlat(100, '4+4-');
  // 10-12: Flat 5% (=$50), hero filter 4+4-
  const flatFiveAmount = INITIAL_BANK * 0.05;
  oddsConditions.forEach(odds_condition => {
    combos.push({
      ...flat5(flatFiveAmount),
      hero_filter: '4+4-',
      odds_condition,
    });
  });
  // 13-15: Flat $100, hero filter 5+5-
  pushFlat(100, '5+5-');
  // 16-18: Flat 5%, hero filter 5+5-
  oddsConditions.forEach(odds_condition => {
    combos.push({
      ...flat5(flatFiveAmount),
      hero_filter: '5+5-',
      odds_condition,
    });
  });
  // 19-21: Fibonacci $1 unit, hero filter none
  oddsConditions.forEach(odds_condition => {
    combos.push({
      ...fib1(1),
      hero_filter: 'none',
      odds_condition,
    });
  });
  // 22-24: Fibonacci $1 unit, hero filter 4+4-
  oddsConditions.forEach(odds_condition => {
    combos.push({
      ...fib1(1),
      hero_filter: '4+4-',
      odds_condition,
    });
  });
  // 25-27: Fibonacci $1 unit, hero filter 5+5-
  oddsConditions.forEach(odds_condition => {
    combos.push({
      ...fib1(1),
      hero_filter: '5+5-',
      odds_condition,
    });
  });
  // 28-30: Fibonacci $5 unit, hero filter none
  oddsConditions.forEach(odds_condition => {
    combos.push({
      ...fib1(5),
      hero_filter: 'none',
      odds_condition,
    });
  });
  // 31-33: Fibonacci $5 unit, hero filter 4+4-
  oddsConditions.forEach(odds_condition => {
    combos.push({
      ...fib1(5),
      hero_filter: '4+4-',
      odds_condition,
    });
  });
  // 34-36: Fibonacci $5 unit, hero filter 5+5-
  oddsConditions.forEach(odds_condition => {
    combos.push({
      ...fib1(5),
      hero_filter: '5+5-',
      odds_condition,
    });
  });

  return combos;
}

function parseCsvLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i += 1;
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

function splitHeroes(field) {
  if (!field) {
    return [];
  }
  return field.split('|').map(h => h.trim()).filter(Boolean);
}

function normalizeHeroName(name) {
  return name.toLowerCase().replace(/[^a-z0-9]/g, '');
}

function heroNamesToIds(heroNames, heroData) {
  const ids = [];
  for (const name of heroNames) {
    const normalized = normalizeHeroName(name);
    if (!heroData.heroIndex.has(normalized)) {
      heroData.missingHeroes.set(normalized, name);
      return null;
    }
    ids.push(heroData.heroIndex.get(normalized));
  }
  return ids;
}

function computeTeamCounts(heroIds, enemyIds, heroData) {
  let pos = 0;
  let neg = 0;
  for (const heroId of heroIds) {
    const adv = computeAdvantage(heroId, enemyIds, heroData.winRates);
    if (adv > 0) {
      pos += 1;
    } else if (adv < 0) {
      neg += 1;
    }
  }
  return { pos, neg };
}

function computeAdvantage(heroId, enemyIds, winRates) {
  let total = 0;
  for (const enemyId of enemyIds) {
    const row = winRates[enemyId];
    if (!row) {
      continue;
    }
    const cell = row[heroId];
    if (!cell || cell[0] == null) {
      continue;
    }
    const val = parseFloat(cell[0]);
    if (Number.isFinite(val)) {
      total += val;
    }
  }
  return total;
}

function parseNumber(value) {
  const num = parseFloat(value);
  return Number.isFinite(num) ? num : NaN;
}

function classifyOddsRelation(favOdds, dogOdds) {
  if (!Number.isFinite(favOdds) || !Number.isFinite(dogOdds)) {
    return 'any';
  }
  if (favOdds < dogOdds) {
    return 'favorite';
  }
  if (favOdds > dogOdds) {
    return 'underdog';
  }
  return 'any';
}

if (require.main === module) {
  main();
}
