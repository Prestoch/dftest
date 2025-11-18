const https = require('https');
const fs = require('fs');

const url = 'https://github.com/Prestoch/dftest/releases/download/data-v1/opendota_pro_matches_3months_detailed_20251118_173427.json.gz';
const output = 'opendota_pro_matches_3months_detailed_20251118_173427.json.gz';

function download(targetUrl) {
  https.get(targetUrl, (res) => {
    if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
      download(res.headers.location);
      return;
    }
    if (res.statusCode !== 200) {
      console.error('Failed to download file. Status:', res.statusCode);
      res.resume();
      return;
    }
    const file = fs.createWriteStream(output);
    res.pipe(file);
    file.on('finish', () => {
      file.close(() => console.log('Download complete:', output));
    });
  }).on('error', (err) => {
    console.error('Download error:', err);
  });
}

download(url);
