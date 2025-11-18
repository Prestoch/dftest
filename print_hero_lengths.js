const fs = require('fs');
const vm = require('vm');

const code = fs.readFileSync('cs.json', 'utf8');
const sandbox = {};
vm.runInNewContext(code, sandbox);

console.log('heroes length', sandbox.heroes.length);
console.log('heroes_bg length', sandbox.heroes_bg.length);
