import csv, json, re
from pathlib import Path

MATRIX_PATH = Path('cs_stratz.json')
HAWK_PATH = Path('hawk_matches_merged.csv')
content = MATRIX_PATH.read_text()
heroes = json.loads(re.search(r"var heroes = (\[.*?\]),\s*heroes_bg", content, re.S).group(1))
win_rates_raw = json.loads(re.search(r"win_rates = (\[.*?\]),\s*update_time", content, re.S).group(1))
hero_index = {name: idx for idx, name in enumerate(heroes)}
lookup = {re.sub(r"[^a-z0-9]", "", name.lower()): name for name in heroes}
match_id = '142712'
with HAWK_PATH.open(newline='', encoding='utf-8') as fh:
    match = next(row for row in csv.DictReader(fh) if row['hawk_match_id'] == match_id)

def norm(name):
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    return lookup.get(key, name)
team1 = [norm(h.strip()) for h in match['team1_heroes'].split('|')]
team2 = [norm(h.strip()) for h in match['team2_heroes'].split('|')]

def score(hero, opponents):
    total = 0.0
    for opp in opponents:
        entry = win_rates_raw[hero_index[hero]][hero_index[opp]]
        if entry is None:
            continue
        total += float(entry[0])
    return total

print('team1', team1)
print('scores', [score(h, team2) for h in team1])
print('team2', team2)
print('scores', [score(h, team1) for h in team2])
