#!/usr/bin/env node

/**
 * Generic delta-percentage bankroll simulator.
 * Usage example:
 *   node run_delta_pct_custom.js --data hawk_matches_20220101_20230101.csv \
 *        --csfile cs_pro_from_filtered.json \
 *        --summary out_summary.csv --bets out_bets.csv \
 *        --from 2025-08 --to 2025-11 --max-bet 0
 *
 * Options:
 *   --data <path>       CSV with matches (default: hawk_matches_merged.csv)
 *   --csfile <path>     cs_pro-style matrix (default: cs_pro_from_filtered.json)
 *   --summary <path>    Summary CSV output (default: delta_pct_strategy_full.csv)
 *   --bets <path>       Per-bet CSV output (default: delta_pct_strategy_bets.csv)
   *   --from <YYYY-MM>    Lower bound month filter (inclusive)
   *   --to <YYYY-MM>      Upper bound month filter (inclusive)
   *   --max-bet <number>  Maximum stake per bet (0 or negative = no cap). Default 10000.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const START_BANK = 1000;

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    dataFile: path.join(__dirname, 'hawk_matches_merged.csv'),
    matrixFile: path.join(__dirname, 'cs_pro_from_filtered.json'),
    summaryFile: path.join(__dirname, 'delta_pct_strategy_full.csv'),
    betsFile: path.join(__dirname, 'delta_pct_strategy_bets.csv'),
    monthFrom: null,
    monthTo: null,
    maxBet: 10000,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    switch (arg) {
      case '--data':
        opts.dataFile = path.resolve(args[++i]);
        break;
      case '--csfile':
        opts.matrixFile = path.resolve(args[++i]);
        break;
      case '--summary':
        opts.summaryFile = path.resolve(args[++i]);
        break;
      case '--bets':
        opts.betsFile = path.resolve(args[++i]);
        break;
      case '--from':
        opts.monthFrom = args[++i];
        break;
      case '--to':
        opts.monthTo = args[++i];
        break;
      case '--max-bet':
        {
          const v = parseFloat(args[++i]);
          opts.maxBet = Number.isFinite(v) ? v : 0;
        }
        break;
      default:
        console.warn(`Unknown option: ${arg}`);
        break;
    }
  }

  if (!opts.dataFile || !opts.matrixFile) {
    throw new Error('Missing required --data or --csfile');
  }

  return opts;
}

function loadMatrix(file) {
  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(file, 'utf8'), sandbox);
  const { heroes, heroes_wr, win_rates } = sandbox;
  const normalize = (name) => name.toLowerCase().replace(/[^a-z0-9]/g, '');
  const idxMap = new Map();
  heroes.forEach((hero, idx) => idxMap.set(normalize(hero), idx));

  function heroScore(heroName, opponentHeroes) {
    const idx = idxMap.get(normalize(heroName));
    if (idx === undefined) throw new Error(`Hero not found: ${heroName}`);
    const wr = parseFloat(heroes_wr[idx] ?? 50);
    let adv = 0;
    const row = win_rates[idx];
    if (Array.isArray(row)) {
      for (const opp of opponentHeroes) {
        const oppIdx = idxMap.get(normalize(opp));
        if (oppIdx === undefined) throw new Error(`Hero not found: ${opp}`);
        const cell = row[oppIdx];
        if (cell && cell[0] != null) {
          adv += parseFloat(cell[0]);
        }
      }
    }
    return wr + adv;
  }

  function delta(match) {
    const t1 = match.team1_heroes.split('|').map((h) => h.trim());
    const t2 = match.team2_heroes.split('|').map((h) => h.trim());
    if (t1.length !== 5 || t2.length !== 5) return null;
    const s1 = t1.reduce((sum, hero) => sum + heroScore(hero, t2), 0);
    const s2 = t2.reduce((sum, hero) => sum + heroScore(hero, t1), 0);
    return parseFloat((s1 - s2).toFixed(4));
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
  return lines
    .slice(1)
    .map((line) => {
      const values = parseCSVLine(line);
      const obj = {};
      headers.forEach((h, idx) => (obj[h] = values[idx] ?? ''));
      obj.date_obj = new Date(obj.date);
      obj.month = obj.date ? obj.date.slice(0, 7) : '0000-00';
      obj.series_id_num = parseInt(obj.series_id, 10) || 0;
      obj.map_number_num = parseInt(obj.map_number, 10) || 0;
      obj.hawk_match_id_num = parseInt(obj.hawk_match_id, 10) || 0;
      return obj;
    })
    .filter((m) => !isNaN(m.date_obj));
}

function toCSV(records, columns) {
  const header = columns;
  const lines = [header.join(',')];
  for (const rec of records) {
    const row = header.map((key) => {
      const val = rec[key];
      if (val === undefined || val === null) return '';
      const str = String(val);
      if (str.includes(',') || str.includes('"')) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    });
    lines.push(row.join(','));
  }
  return lines.join('\n') + '\n';
}

function execute(opts) {
  const matches = loadMatches(opts.dataFile)
    .filter((m) => {
      if (opts.monthFrom && m.month < opts.monthFrom) return false;
      if (opts.monthTo && m.month > opts.monthTo) return false;
      return true;
    })
    .sort((a, b) => {
      const ad = a.date_obj - b.date_obj;
      if (ad !== 0) return ad;
      if (a.series_id_num !== b.series_id_num) return a.series_id_num - b.series_id_num;
      if (a.map_number_num !== b.map_number_num) return a.map_number_num - b.map_number_num;
      return a.hawk_match_id_num - b.hawk_match_id_num;
    });

  const matrix = loadMatrix(opts.matrixFile);
  let bank = START_BANK;
  let peak = bank;
  let maxDrawdown = 0;
  let bets = 0;
  let wins = 0;
  let losses = 0;
  let skipped = 0;
  const betRecords = [];
  const maxBetCap = opts.maxBet > 0 ? opts.maxBet : Infinity;

  for (const match of matches) {
    const delta = matrix.delta(match);
    if (delta === null || delta === 0) {
      skipped++;
      continue;
    }
    const favored = delta > 0 ? match.team1 : match.team2;
    const favoredOdds = parseFloat(delta > 0 ? match.team1_odds : match.team2_odds);
    if (!Number.isFinite(favoredOdds) || favoredOdds <= 1) {
      skipped++;
      continue;
    }

    const pct = Math.min(Math.abs(delta) / 1000, 1);
    let stake = bank * pct;
    if (stake > maxBetCap) stake = maxBetCap;
    if (stake > bank) stake = bank;
    stake = Math.floor(stake);
    if (stake <= 0) continue;

    const bankBefore = bank;
    bank -= stake;
    const won = match.winner === favored;
    let payout = 0;
    if (won) {
      payout = Math.floor(stake * favoredOdds);
      bank += payout;
      wins++;
    } else {
      losses++;
    }
    bets++;

    if (bank > peak) peak = bank;
    const drawdown = peak - bank;
    if (drawdown > maxDrawdown) maxDrawdown = drawdown;
    if (bank <= 0) {
      betRecords.push({
        month: match.month,
        date: match.date,
        match_id: match.hawk_match_id,
        championship: match.championship,
        team1: match.team1,
        team2: match.team2,
        delta: delta.toFixed(4),
        favored,
        odds: favoredOdds,
        stake,
        outcome: won ? 'win' : 'loss',
        payout,
        bank_before: bankBefore,
        bank_after: bank,
      });
      break;
    }

    betRecords.push({
      month: match.month,
      date: match.date,
      match_id: match.hawk_match_id,
      championship: match.championship,
      team1: match.team1,
      team2: match.team2,
      delta: delta.toFixed(4),
      favored,
      odds: favoredOdds,
      stake,
      outcome: won ? 'win' : 'loss',
      payout,
      bank_before: bankBefore,
      bank_after: bank,
    });
  }

  const summary = [
    {
      strategy_group: 'DeltaPctBankroll',
      hero_filter: 'none',
      odds_condition: 'any',
      delta_threshold: 0,
      bets,
      wins,
      win_pct: bets ? ((wins / bets) * 100).toFixed(2) : '0.00',
      final_bank: bank,
      max_drawdown: maxDrawdown,
      max_stake: betRecords.reduce((max, r) => Math.max(max, r.stake || 0), 0),
      max_step: 0,
    },
  ];

  fs.writeFileSync(
    opts.summaryFile,
    toCSV(summary, [
      'strategy_group',
      'hero_filter',
      'odds_condition',
      'delta_threshold',
      'bets',
      'wins',
      'win_pct',
      'final_bank',
      'max_drawdown',
      'max_stake',
      'max_step',
    ])
  );
  fs.writeFileSync(
    opts.betsFile,
    toCSV(betRecords, [
      'month',
      'date',
      'match_id',
      'championship',
      'team1',
      'team2',
      'delta',
      'favored',
      'odds',
      'stake',
      'outcome',
      'payout',
      'bank_before',
      'bank_after',
    ])
  );

  return {
    ...summary[0],
    summary_file: opts.summaryFile,
    bets_file: opts.betsFile,
    skipped,
  };
}

function run() {
  const opts = parseArgs();
  return execute(opts);
}

if (require.main === module) {
  console.log(run());
}

module.exports = { runWithOptions: execute };

