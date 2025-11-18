#!/usr/bin/env node

/**
 * Build a cs-style hero matrix (win rates + extra per-hero stats) from the
 * OpenDota detailed pro matches dump.
 *
 * Usage:
 *   node build_opendota_matrix.js --input opendota_matches.json --output cs_opendota_matrix.json
 *
 * The input file is the raw JSON array exported from OpenDota (not NDJSON).
 */

const fs = require('fs');
const path = require('path');
const { chain } = require('stream-chain');
const { parser } = require('stream-json');
const { streamArray } = require('stream-json/streamers/StreamArray');

const heroStats = new Map(); // heroId -> { games, wins, gpmSum, xpmSum, heroDamageSum, towerDamageSum, durationSum }
const pairStats = new Map(); // heroA -> heroB -> { games, wins }

function ensureHeroStats(heroId) {
  if (!heroStats.has(heroId)) {
    heroStats.set(heroId, {
      games: 0,
      wins: 0,
      gpmSum: 0,
      xpmSum: 0,
      heroDamageSum: 0,
      towerDamageSum: 0,
      durationSum: 0,
    });
  }
  return heroStats.get(heroId);
}

function ensurePairStats(heroA, heroB) {
  if (!pairStats.has(heroA)) {
    pairStats.set(heroA, new Map());
  }
  const inner = pairStats.get(heroA);
  if (!inner.has(heroB)) {
    inner.set(heroB, { games: 0, wins: 0 });
  }
  return inner.get(heroB);
}

function processMatch(match) {
  if (!match || !Array.isArray(match.players) || match.players.length !== 10) return;
  const isRadiantWin = Boolean(match.radiant_win);
  const duration = Number(match.duration || 0);

  // Split players into radiant vs dire.
  const radiant = [];
  const dire = [];
  for (const player of match.players) {
    const heroId = player.hero_id;
    const gpm = player.gold_per_min;
    const xpm = player.xp_per_min;
    const heroDamage = player.hero_damage;
    const towerDamage = player.tower_damage;
    const isRadiant = Boolean(player.isRadiant);
    const won = (isRadiant && isRadiantWin) || (!isRadiant && !isRadiantWin);

    const stats = ensureHeroStats(heroId);
    stats.games += 1;
    if (won) stats.wins += 1;
    stats.gpmSum += Number(gpm || 0);
    stats.xpmSum += Number(xpm || 0);
    stats.heroDamageSum += Number(heroDamage || 0);
    stats.towerDamageSum += Number(towerDamage || 0);
    stats.durationSum += duration;

    const entry = { heroId, won };
    if (isRadiant) radiant.push(entry);
    else dire.push(entry);
  }

  // Update hero-vs-hero pair stats.
  for (const a of radiant) {
    for (const b of dire) {
      const ab = ensurePairStats(a.heroId, b.heroId);
      ab.games += 1;
      if (a.won) ab.wins += 1;

      const ba = ensurePairStats(b.heroId, a.heroId);
      ba.games += 1;
      if (!a.won) ba.wins += 1;
    }
  }
}

async function main() {
  const args = process.argv.slice(2);
  let inputPath = null;
  let outputPath = null;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--input' || arg === '-i') {
      inputPath = args[++i];
    } else if (arg === '--output' || arg === '-o') {
      outputPath = args[++i];
    } else {
      console.warn('Unknown option:', arg);
    }
  }

  if (!inputPath) {
    console.error('Usage: node build_opendota_matrix.js --input <file> [--output <file>]');
    process.exit(1);
  }

  inputPath = path.resolve(inputPath);
  const pipeline = chain([
    fs.createReadStream(inputPath),
    parser(),
    streamArray(),
  ]);

  await new Promise((resolve, reject) => {
    pipeline.on('data', ({ value }) => processMatch(value));
    pipeline.on('end', resolve);
    pipeline.on('error', reject);
  });

  // Build sorted hero list.
  const heroIds = Array.from(heroStats.keys()).sort((a, b) => a - b);

  const heroesWr = heroIds.map((heroId) => {
    const stats = heroStats.get(heroId);
    if (!stats || stats.games === 0) return '50.0';
    return ((stats.wins / stats.games) * 100).toFixed(2);
  });

  const heroesGpm = heroIds.map((heroId) => {
    const stats = heroStats.get(heroId);
    return stats && stats.games ? (stats.gpmSum / stats.games).toFixed(2) : '0';
  });

  const heroesXpm = heroIds.map((heroId) => {
    const stats = heroStats.get(heroId);
    return stats && stats.games ? (stats.xpmSum / stats.games).toFixed(2) : '0';
  });

  const heroesHeroDamage = heroIds.map((heroId) => {
    const stats = heroStats.get(heroId);
    return stats && stats.games ? (stats.heroDamageSum / stats.games).toFixed(2) : '0';
  });

  const heroesTowerDamage = heroIds.map((heroId) => {
    const stats = heroStats.get(heroId);
    return stats && stats.games ? (stats.towerDamageSum / stats.games).toFixed(2) : '0';
  });

  const heroesDuration = heroIds.map((heroId) => {
    const stats = heroStats.get(heroId);
    return stats && stats.games ? (stats.durationSum / stats.games).toFixed(2) : '0';
  });

  const heroIndexMap = new Map(heroIds.map((id, idx) => [id, idx]));

  const winRates = heroIds.map(() => Array(heroIds.length).fill(null));
  for (const [heroA, inner] of pairStats.entries()) {
    const idxA = heroIndexMap.get(heroA);
    if (idxA === undefined) continue;
    for (const [heroB, stats] of inner.entries()) {
      const idxB = heroIndexMap.get(heroB);
      if (idxB === undefined || stats.games === 0) continue;
      const wr = (stats.wins / stats.games) * 100;
      winRates[idxA][idxB] = [
        (wr - 50).toFixed(4), // advantage
        wr.toFixed(4),        // win rate
        stats.games,
      ];
    }
  }

  const output = {
    heroes: heroIds,
    heroes_wr: heroesWr,
    heroes_gpm: heroesGpm,
    heroes_xpm: heroesXpm,
    heroes_hero_damage: heroesHeroDamage,
    heroes_tower_damage: heroesTowerDamage,
    heroes_duration: heroesDuration,
    win_rates: winRates,
  };

  const serialized = 'var opendota_matrix = ' + JSON.stringify(output) + ';\n';
  if (outputPath) {
    fs.writeFileSync(path.resolve(outputPath), serialized);
  } else {
    process.stdout.write(serialized);
  }
}

main().catch((err) => {
  console.error('Failed to build matrix:', err);
  process.exit(1);
});
