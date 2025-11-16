#!/usr/bin/env node

/**
 * Build DotabuffCP-compatible matrices from STRATZ match exports.
 *
 * Usage:
 *   node build_cs_matrix.js --input stratz_clean_96507.json --output cs_pro_regen.json
 * Options:
 *   --meta <file>   Existing cs*.json to copy hero metadata from (default: cs.json if present, else cs_pro.json)
 *   --csmeta <file> alias for --meta
 *   --hero-map <file> Path to hero_id_map.json (default: hero_id_map.json)
 *   --update-time <YYYY-MM-DD> Override update_time stamp (default: today)
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

function parseArgs() {
  const args = process.argv.slice(2);
  const opts = {
    input: null,
    output: null,
    meta: null,
    heroMap: path.join(__dirname, 'hero_id_map.json'),
    updateTime: new Date().toISOString().slice(0, 10),
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    switch (arg) {
      case '--input':
      case '-i':
        opts.input = args[++i];
        break;
      case '--output':
      case '-o':
        opts.output = args[++i];
        break;
      case '--meta':
      case '--csmeta':
        opts.meta = args[++i];
        break;
      case '--hero-map':
        opts.heroMap = args[++i];
        break;
      case '--update-time':
        opts.updateTime = args[++i];
        break;
      default:
        console.warn(`Unknown argument: ${arg}`);
        break;
    }
  }

  if (!opts.input || !opts.output) {
    console.error('Usage: node build_cs_matrix.js --input <stratz.json> --output <cs_out.json> [--meta <cs.json>]');
    process.exit(1);
  }

  if (!opts.meta) {
    const csPath = path.join(__dirname, 'cs.json');
    const csProPath = path.join(__dirname, 'cs_pro.json');
    opts.meta = fs.existsSync(csPath) ? csPath : csProPath;
  }

  opts.input = path.resolve(opts.input);
  opts.output = path.resolve(opts.output);
  opts.meta = path.resolve(opts.meta);
  opts.heroMap = path.resolve(opts.heroMap);

  return opts;
}

function loadMeta(metaPath) {
  const sandbox = {};
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(metaPath, 'utf8'), sandbox);
  const { heroes, heroes_bg } = sandbox;
  if (!Array.isArray(heroes) || !Array.isArray(heroes_bg)) {
    throw new Error(`Meta file ${metaPath} missing heroes arrays`);
  }
  return { heroes, heroes_bg };
}

function loadHeroMap(mapPath) {
  const raw = JSON.parse(fs.readFileSync(mapPath, 'utf8'));
  const mapping = new Map();
  Object.entries(raw).forEach(([stratzId, heroIdx]) => {
    mapping.set(Number(stratzId), heroIdx);
  });
  return mapping;
}

function normalizeHeroIds(rawHeroes, heroMap) {
  const ids = [];
  for (const entry of rawHeroes || []) {
    const heroId = typeof entry === 'object' ? entry.heroId : entry;
    const mapped = heroMap.get(heroId);
    if (mapped === undefined) return null;
    ids.push(mapped);
  }
  return ids.length === 5 ? ids : null;
}

function buildMatrix(inputPath, heroes, heroMap, updateTime) {
  const raw = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  const heroCount = heroes.length;
  const heroStats = Array.from({ length: heroCount }, () => ({ games: 0, wins: 0 }));
  const pairStats = Array.from({ length: heroCount }, () => Array(heroCount).fill(null));

  let processed = 0;
  let skipped = 0;

  for (const match of Object.values(raw)) {
    const radiant = normalizeHeroIds(match.radiantRoles, heroMap);
    const dire = normalizeHeroIds(match.direRoles, heroMap);
    if (!radiant || !dire) {
      skipped++;
      continue;
    }

    const radiantWin = Boolean(match.radiantWin);

    const updateHero = (id, win) => {
      const hs = heroStats[id];
      hs.games += 1;
      if (win) hs.wins += 1;
    };

    radiant.forEach((id) => updateHero(id, radiantWin));
    dire.forEach((id) => updateHero(id, !radiantWin));

    for (const r of radiant) {
      for (const d of dire) {
        let cell = pairStats[r][d];
        if (!cell) cell = pairStats[r][d] = { games: 0, wins: 0 };
        cell.games += 1;
        if (radiantWin) cell.wins += 1;

        let cellRev = pairStats[d][r];
        if (!cellRev) cellRev = pairStats[d][r] = { games: 0, wins: 0 };
        cellRev.games += 1;
        if (!radiantWin) cellRev.wins += 1;
      }
    }

    processed++;
  }

  const heroesWr = heroStats.map(({ games, wins }) => {
    if (!games) return '50.00';
    return (wins / games * 100).toFixed(2);
  });

  const winRates = pairStats.map((row) =>
    row.map((cell) => {
      if (!cell || !cell.games) return null;
      const wr = cell.wins / cell.games * 100;
      const adv = wr - 50;
      return [adv.toFixed(4), wr.toFixed(4), cell.games];
    })
  );

  return {
    heroes,
    heroesWr,
    winRates,
    processed,
    skipped,
    update_time: updateTime,
  };
}

function writeOutput(outputPath, meta, matrix) {
  const { heroes, heroes_bg } = meta;
  const content =
    'var heroes = ' +
    JSON.stringify(heroes) +
    ', heroes_bg = ' +
    JSON.stringify(heroes_bg) +
    ', heroes_wr = ' +
    JSON.stringify(matrix.heroesWr) +
    ', win_rates = ' +
    JSON.stringify(matrix.winRates) +
    ', update_time = ' +
    JSON.stringify(matrix.update_time) +
    ';\n';
  fs.writeFileSync(outputPath, content);
}

function main() {
  const opts = parseArgs();
  const meta = loadMeta(opts.meta);
  const heroMap = loadHeroMap(opts.heroMap);
  const matrix = buildMatrix(opts.input, meta.heroes, heroMap, opts.updateTime);
  writeOutput(opts.output, meta, matrix);
  console.log(
    `Processed ${matrix.processed} matches (${matrix.skipped} skipped) from ${path.basename(
      opts.input
    )} -> ${opts.output}`
  );
}

main();

