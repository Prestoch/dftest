const fs = require('fs');
const data = JSON.parse(fs.readFileSync('stratz_with_tiers_filtered.json', 'utf8'));

let latestTs = -Infinity;
let latestId = null;

for (const [id, match] of Object.entries(data)) {
  let ts = null;
  if (typeof match.startTime === 'number') ts = match.startTime * 1000;
  else if (typeof match.matchTime === 'number') ts = match.matchTime * 1000;
  else if (match.date) ts = Date.parse(match.date);
  else if (match.matchDate) ts = Date.parse(match.matchDate);
  if (ts !== null && !Number.isNaN(ts) && ts > latestTs) {
    latestTs = ts;
    latestId = id;
  }
}

if (latestTs === -Infinity) {
  console.log('No valid dates found');
} else {
  console.log('Latest match ID:', latestId, 'Date:', new Date(latestTs).toISOString());
}
