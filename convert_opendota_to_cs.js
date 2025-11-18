const fs = require('fs');
const vm = require('vm');
const path = require('path');

if (process.argv.length < 4) {
  console.error('Usage: node convert_opendota_to_cs.js <opendota_matrix.json> <output_cs.json>');
  process.exit(1);
}

const [,, opendotaPath, outputPath] = process.argv;
const opendotaCode = fs.readFileSync(opendotaPath, 'utf8');
const sandbox = {};
vm.runInNewContext(opendotaCode, sandbox);
const data = sandbox.opendota_matrix;
if (!data) {
  console.error('opendota_matrix not found in input');
  process.exit(1);
}

const heroMap = require('./hero_id_map.json');
const csCode = fs.readFileSync(path.resolve('cs_pro.json'), 'utf8');
const csSandbox = {};
vm.runInNewContext(csCode, csSandbox);
const baseHeroes = csSandbox.heroes;
const baseHeroesBg = csSandbox.heroes_bg;
const size = baseHeroes.length;

const heroIdToIndex = new Map();
for (const [heroIdStr, idx] of Object.entries(heroMap)) {
  heroIdToIndex.set(Number(heroIdStr), idx);
}

const fillArray = (val) => Array(size).fill(val);
const heroesWr = fillArray('50.00');
const heroesGpm = fillArray('0');
const heroesXpm = fillArray('0');
const heroesHeroDamage = fillArray('0');
const heroesTowerDamage = fillArray('0');
const heroesDuration = fillArray('0');
const winRates = Array.from({ length: size }, () => Array(size).fill(null));

const heroIds = data.heroes || [];
heroIds.forEach((heroId, i) => {
  const idx = heroIdToIndex.get(Number(heroId));
  if (idx === undefined) return;
  heroesWr[idx] = data.heroes_wr[i];
  heroesGpm[idx] = data.heroes_gpm[i];
  heroesXpm[idx] = data.heroes_xpm[i];
  heroesHeroDamage[idx] = data.heroes_hero_damage[i];
  heroesTowerDamage[idx] = data.heroes_tower_damage[i];
  heroesDuration[idx] = data.heroes_duration[i];
});

const srcWinRates = data.win_rates || [];
for (let i = 0; i < srcWinRates.length; i++) {
  const idxA = heroIdToIndex.get(Number(heroIds[i]));
  if (idxA === undefined) continue;
  const row = srcWinRates[i];
  if (!Array.isArray(row)) continue;
  for (let j = 0; j < row.length; j++) {
    const cell = row[j];
    if (!cell) continue;
    const idxB = heroIdToIndex.get(Number(heroIds[j]));
    if (idxB === undefined) continue;
    winRates[idxA][idxB] = cell;
  }
}

const content = `var heroes = ${JSON.stringify(baseHeroes)};
var heroes_wr = ${JSON.stringify(heroesWr)};
var heroes_bg = ${JSON.stringify(baseHeroesBg)};
var heroes_gpm = ${JSON.stringify(heroesGpm)};
var heroes_xpm = ${JSON.stringify(heroesXpm)};
var heroes_hero_damage = ${JSON.stringify(heroesHeroDamage)};
var heroes_tower_damage = ${JSON.stringify(heroesTowerDamage)};
var heroes_duration = ${JSON.stringify(heroesDuration)};
var win_rates = ${JSON.stringify(winRates)};
`;
fs.writeFileSync(outputPath, content);
console.log('Wrote', outputPath);
