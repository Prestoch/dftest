const fs = require('fs');
const { chain } = require('stream-chain');
const { parser } = require('stream-json');
const { streamArray } = require('stream-json/streamers/StreamArray');

const file = 'opendota_pro_matches_3months_detailed_20251118_173427.json';
let count = 0;

const pipeline = chain([
  fs.createReadStream(file),
  parser(),
  streamArray()
]);

pipeline.on('data', ({ value }) => {
  console.log(JSON.stringify(value, null, 2));
  pipeline.destroy();
});

pipeline.on('end', () => console.log('done'));
pipeline.on('error', (err) => console.error(err));
