#!/usr/bin/env node

/**
 * Simulate: stake = |Δ|/10 percent of bankroll (i.e. |Δ| / 1000 as a fraction),
 * clipped to bankroll and $10k max bet, using cs_pro_from_filtered.json.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const START_BANK = 1000;
const MAX_BET = 10000;
const DATA_FILE = path.join(__dirname, 'hawk_matches_merged.csv');
const MATRIX_FILE = path.join(__dirname, 'cs_pro_from_filtered.json');

function loadMatrix(file) {
  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(file, 'utf8'), sandbox);
  const { heroes, heroes_wr, win_rates } = sandbox;
  const heroIndex = new Map();
  const normalize = (name) => name.toLowerCase().replace(/[^a-z0-9]/g, '');
  heroes.forEach((hero, idx) => heroIndex.set(normalize(hero), idx));

  function heroScore(heroName, opponentHeroes) {
    const idx = heroIndex.get(normalize(heroName));
    if (idx === undefined) throw new Error(`Hero not found: ${heroName}`);
    const wr = parseFloat(heroes_wr[idx] ?? 50);
    let adv = 0;
    const row = win_rates[idx];
    if (Array.isArray(row)) {
      for (const opp of opponentHeroes) {
        const oppIdx = heroIndex.get(normalize(opp));
        if (oppIdx === undefined) throw new Error(`Hero not found: ${opp}`);
        const cell = row[oppIdx];
        if (cell && cell[0] != null) adv += parseFloat(cell[0]);
      }
    }
    return wr + adv;
  }

  function delta(match) {
    const t1 = match.team1_heroes.split('|').map((h) => h.trim());
    const t2 = match.team2_heroes.split('|').map((h) => h.trim());
    if (t1.length !== 5 || t2.length !== 5) return null;
    const score1 = t1.reduce((sum, hero) => sum + heroScore(hero, t2), 0);
    const score2 = t2.reduce((sum, hero) => sum + heroScore(hero, t1), 0);
    return parseFloat((score1 - score2).toFixed(4));
  }

  return { delta };
}

function parseCSVLine(line) {
  const result = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === ',' && !inQuotes) {
      result.push(current);
      current = '';
    } else {
      current += ch;
    }
  }
  result.push(current);
  return result;
}

function loadMatches(file) {
  const lines = fs.readFileSync(file, 'utf8').trim().split(/\r?\n/);
  const headers = parseCSVLine(lines[0]);
  const matches = lines.slice(1).map((line) => {
    const values = parseCSVLine(line);
    const obj = {};
    headers.forEach((h, idx) => (obj[h] = values[idx] ?? ''));
    obj.date_obj = new Date(obj.date);
    obj.map_number_num = parseInt(obj.map_number, 10) || 0;
    obj.series_id_num = parseInt(obj.series_id, 10) || 0;
    obj.hawk_match_id_num = parseInt(obj.hawk_match_id, 10) || 0;
    return obj;
  });
  matches.sort((a, b) => {
    const ad = a.date_obj - b.date_obj;
    if (ad !== 0) return ad;
    if (a.series_id_num !== b.series_id_num) return a.series_id_num - b.series_id_num;
    if (a.map_number_num !== b.map_number_num) return a.map_number_num - b.map_number_num;
    return a.hawk_match_id_num - b.hawk_match_id_num;
  });
  return matches;
}

function simulate() {
  const matrix = loadMatrix(MATRIX_FILE);
  const matches = loadMatches(DATA_FILE);

  let bank = START_BANK;
  let peak = bank;
  let trough = bank;
  let maxDrawdown = 0;
  let bets = 0;
  let wins = 0;
  let losses = 0;
  let skipped = 0;
  let maxStake = 0;

  for (const match of matches) {
    const delta = matrix.delta(match);
    if (delta === null || delta === 0) {
      skipped++;
      continue;
    }
    const favoredTeam = delta > 0 ? match.team1 : match.team2;
    const oddsStr = delta > 0 ? match.team1_odds : match.team2_odds;
    const favoredOdds = parseFloat(oddsStr);
    if (!Number.isFinite(favoredOdds) || favoredOdds <= 1) {
      skipped++;
      continue;
    }

    const pct = Math.min(Math.abs(delta) / 1000, 1); // absolute delta / 10 percent
    let stake = bank * pct;
    if (stake > MAX_BET) stake = MAX_BET;
    if (stake > bank) stake = bank;
    stake = Math.floor(stake);
    if (stake <= 0) continue;

    bets++;
    bank -= stake;
    const won = match.winner === favoredTeam;
    if (won) {
      const payout = Math.floor(stake * favoredOdds);
      bank += payout;
      wins++;
    } else {
      losses++;
    }

    if (bank > peak) peak = bank;
    if (bank < trough) trough = bank;
    const drawdown = peak - bank;
    if (drawdown > maxDrawdown) maxDrawdown = drawdown;
    if (stake > maxStake) maxStake = stake;

    if (bank <= 0) break;
  }

  return {
    starting_bank: START_BANK,
    ending_bank: bank,
    max_bank: peak,
    min_bank: trough,
    max_drawdown: maxDrawdown,
    bets,
    wins,
    losses,
    skipped,
    max_stake: maxStake,
  };
}

if (require.main === module) {
  console.log(simulate());
}

