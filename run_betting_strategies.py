import csv
import json
import math
import re
from pathlib import Path

START_BANK = 1000.0
MAX_BET = 10000.0
THRESHOLDS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 75]

CS_PATH = Path('cs.json')
MATCHES_PATH = Path('hawk_matches_merged.csv')
OUTPUT_PATH = Path('strategy_results_hawk_bankroll.csv')

RE_HEROES = re.compile(r'var heroes = (\[[\s\S]*?\])\s*,\s*heroes_bg')
RE_HEROES_WR = re.compile(r'heroes_wr = (\[[\s\S]*?\])\s*,\s*win_rates')
RE_WIN_RATES = re.compile(r'win_rates = (\[[\s\S]*?\])\s*,\s*update_time')


def normalize(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', name.lower())


def load_cs_data():
    text = CS_PATH.read_text()
    heroes = json.loads(RE_HEROES.search(text).group(1))
    heroes_wr_raw = json.loads(RE_HEROES_WR.search(text).group(1))
    win_rates_raw = json.loads(RE_WIN_RATES.search(text).group(1))

    hero_wr = [float(v) if v not in (None, '') else 0.0 for v in heroes_wr_raw]
    hero_map = {normalize(name): idx for idx, name in enumerate(heroes)}

    win_rates = []
    for row in win_rates_raw:
        if row is None:
            win_rates.append(None)
            continue
        converted_row = []
        for entry in row:
            if entry is None:
                converted_row.append(None)
            else:
                converted_row.append(float(entry[0]))
        win_rates.append(converted_row)

    return heroes, hero_wr, hero_map, win_rates


def hero_advantage(hero_id: int, opponent_ids, win_rates):
    total = 0.0
    for opp in opponent_ids:
        if opp < 0 or opp >= len(win_rates):
            continue
        opp_row = win_rates[opp]
        if not opp_row:
            continue
        if hero_id >= len(opp_row):
            continue
        val = opp_row[hero_id]
        if val is None:
            continue
        total += val
    return total


def compute_match_records(heroes, hero_wr, hero_map, win_rates):
    matches = []
    missing_heroes = set()
    with MATCHES_PATH.open() as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            try:
                delta = float(row['delta'])
            except (ValueError, KeyError):
                continue
            fav_team = (row.get('delta_favored_team') or '').strip()
            if not fav_team:
                continue
            team1 = (row.get('team1') or '').strip()
            team2 = (row.get('team2') or '').strip()
            winner = (row.get('winner') or '').strip()
            team1_odds = row.get('team1_odds')
            team2_odds = row.get('team2_odds')
            try:
                odds1 = float(team1_odds)
                odds2 = float(team2_odds)
            except (TypeError, ValueError):
                continue
            if odds1 <= 1.0 or odds2 <= 1.0:
                continue

            try:
                team1_ids = [hero_map[normalize(h.strip())] for h in row['team1_heroes'].split('|') if h.strip()]
                team2_ids = [hero_map[normalize(h.strip())] for h in row['team2_heroes'].split('|') if h.strip()]
            except KeyError as exc:
                missing_heroes.add(str(exc))
                continue

            if len(team1_ids) != 5 or len(team2_ids) != 5:
                continue

            team1_adv = [hero_advantage(hid, team2_ids, win_rates) for hid in team1_ids]
            team2_adv = [hero_advantage(hid, team1_ids, win_rates) for hid in team2_ids]

            t1_pos = sum(1 for v in team1_adv if v > 0)
            t1_neg = sum(1 for v in team1_adv if v < 0)
            t2_pos = sum(1 for v in team2_adv if v > 0)
            t2_neg = sum(1 for v in team2_adv if v < 0)

            combo_4 = (t1_pos >= 4 and t2_neg >= 4) or (t1_neg >= 4 and t2_pos >= 4)
            combo_5 = (t1_pos >= 5 and t2_neg >= 5) or (t1_neg >= 5 and t2_pos >= 5)

            fav_idx = None
            bet_odds = None
            opp_odds = None
            if fav_team.lower() == team1.lower():
                fav_idx = 1
                bet_odds = odds1
                opp_odds = odds2
            elif fav_team.lower() == team2.lower():
                fav_idx = 2
                bet_odds = odds2
                opp_odds = odds1
            else:
                continue

            if bet_odds is None or opp_odds is None:
                continue

            fav_is_underdog = bet_odds > opp_odds
            fav_is_favorite = bet_odds < opp_odds

            matches.append({
                'abs_delta': abs(delta),
                'fav_idx': fav_idx,
                'bet_odds': bet_odds,
                'opp_odds': opp_odds,
                'fav_won': fav_team.lower() == winner.lower(),
                'combo_4': combo_4,
                'combo_5': combo_5,
                'date': row.get('date'),
                'fav_is_underdog': fav_is_underdog,
                'fav_is_favorite': fav_is_favorite,
                'row_index': idx,
            })
    if missing_heroes:
        raise RuntimeError(f"Missing heroes encountered: {sorted(missing_heroes)}")
    return matches


def ensure_fib_length(seq, step):
    while len(seq) <= step:
        seq.append(seq[-1] + seq[-2])
    return seq


def run_strategy(matches, cfg, threshold):
    bank = START_BANK
    peak = bank
    max_drawdown = 0.0
    max_stake = 0.0
    bets = 0
    wins = 0
    fib_step = 0
    max_step_reached = 0
    fib_seq = [1, 1]

    for match in matches:
        if match['abs_delta'] < threshold:
            continue
        hero_filter = cfg['hero_filter']
        if hero_filter == '4+4-' and not match['combo_4']:
            continue
        if hero_filter == '5+5-' and not match['combo_5']:
            continue
        odds_condition = cfg['odds_condition']
        if odds_condition == 'underdog' and not match['fav_is_underdog']:
            continue
        if odds_condition == 'favorite' and not match['fav_is_favorite']:
            continue
        if bank <= 0:
            break

        stake = 0.0
        stake_type = cfg['stake_type']
        if stake_type == 'flat':
            target = cfg['amount']
            if bank < 1:
                break
            if bank < target:
                stake = bank
            else:
                stake = target
        elif stake_type == 'percent':
            percent = cfg['percent']
            stake = bank * percent
            if stake < 1:
                break
            stake = min(stake, bank)
        elif stake_type == 'fib':
            ensure_fib_length(fib_seq, fib_step)
            unit = cfg['unit']
            stake = fib_seq[fib_step] * unit
            stake = min(stake, bank)
            max_step_reached = max(max_step_reached, fib_step)
        else:
            raise ValueError('Unknown stake type')

        stake = min(stake, MAX_BET)
        if stake <= 0:
            break

        bank -= stake
        bets += 1

        if match['fav_won']:
            wins += 1
            bank += stake * match['bet_odds']
            if stake_type == 'fib':
                if fib_step >= 2:
                    fib_step -= 2
                else:
                    fib_step = 0
        else:
            if stake_type == 'fib':
                fib_step += 1

        if stake_type != 'fib':
            max_step = 0
        else:
            max_step = max_step_reached

        peak = max(peak, bank)
        drawdown = peak - bank
        if drawdown > max_drawdown:
            max_drawdown = drawdown
        if stake > max_stake:
            max_stake = stake

    win_pct = round((wins / bets) * 100) if bets else 0
    result = {
        'strategy_group': cfg['name'],
        'hero_filter': cfg['hero_filter'],
        'odds_condition': cfg['odds_condition'],
        'delta_threshold': threshold,
        'bets': bets,
        'wins': wins,
        'win_pct': win_pct,
        'final_bank': round(bank),
        'max_drawdown': round(max_drawdown),
        'max_stake': round(max_stake),
        'max_step': max_step_reached if cfg['stake_type'] == 'fib' else 0,
    }
    return result


def main():
    heroes, hero_wr, hero_map, win_rates = load_cs_data()
    matches = compute_match_records(heroes, hero_wr, hero_map, win_rates)

    strategy_configs = []

    # Flat $100 strategies (none, 4+4-, 5+5-)
    for hero_filter in ['none', '4+4-', '5+5-']:
        strategy_configs.extend([
            {'name': 'Flat100', 'hero_filter': hero_filter, 'odds_condition': 'any', 'stake_type': 'flat', 'amount': 100},
            {'name': 'Flat100', 'hero_filter': hero_filter, 'odds_condition': 'underdog', 'stake_type': 'flat', 'amount': 100},
            {'name': 'Flat100', 'hero_filter': hero_filter, 'odds_condition': 'favorite', 'stake_type': 'flat', 'amount': 100},
        ])

    # 5% bankroll per bet (Percent5) - hero filters none, 4+4-, 5+5-
    for hero_filter in ['none', '4+4-', '5+5-']:
        strategy_configs.extend([
            {'name': 'Percent5', 'hero_filter': hero_filter, 'odds_condition': 'any', 'stake_type': 'percent', 'percent': 0.05},
            {'name': 'Percent5', 'hero_filter': hero_filter, 'odds_condition': 'underdog', 'stake_type': 'percent', 'percent': 0.05},
            {'name': 'Percent5', 'hero_filter': hero_filter, 'odds_condition': 'favorite', 'stake_type': 'percent', 'percent': 0.05},
        ])

    # Fibonacci $1 unit strategies
    for hero_filter in ['none', '4+4-', '5+5-']:
        strategy_configs.extend([
            {'name': 'Fibonacci1', 'hero_filter': hero_filter, 'odds_condition': 'any', 'stake_type': 'fib', 'unit': 1},
            {'name': 'Fibonacci1', 'hero_filter': hero_filter, 'odds_condition': 'underdog', 'stake_type': 'fib', 'unit': 1},
            {'name': 'Fibonacci1', 'hero_filter': hero_filter, 'odds_condition': 'favorite', 'stake_type': 'fib', 'unit': 1},
        ])

    # Fibonacci $5 unit strategies
    for hero_filter in ['none', '4+4-', '5+5-']:
        strategy_configs.extend([
            {'name': 'Fibonacci5', 'hero_filter': hero_filter, 'odds_condition': 'any', 'stake_type': 'fib', 'unit': 5},
            {'name': 'Fibonacci5', 'hero_filter': hero_filter, 'odds_condition': 'underdog', 'stake_type': 'fib', 'unit': 5},
            {'name': 'Fibonacci5', 'hero_filter': hero_filter, 'odds_condition': 'favorite', 'stake_type': 'fib', 'unit': 5},
        ])

    results = []
    for cfg in strategy_configs:
        for threshold in THRESHOLDS:
            result = run_strategy(matches, cfg, threshold)
            results.append(result)

    with OUTPUT_PATH.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'strategy_group', 'hero_filter', 'odds_condition', 'delta_threshold',
            'bets', 'wins', 'win_pct', 'final_bank', 'max_drawdown', 'max_stake', 'max_step'
        ])
        writer.writeheader()
        for row in results:
            writer.writerow(row)


if __name__ == '__main__':
    main()
