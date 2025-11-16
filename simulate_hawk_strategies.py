#!/usr/bin/env python3
import csv
import json
import math
import re
from pathlib import Path
from typing import List, Dict, Any

START_BANK = 1000.0
MAX_BET = 10000.0
THRESHOLDS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 75]


def read_cs_pro(path: Path) -> Dict[str, Any]:
    text = path.read_text()

    def extract(pattern: str):
        match = re.search(pattern, text, flags=re.S)
        if not match:
            raise RuntimeError(f"Pattern not found: {pattern[:30]}")
        return json.loads(match.group(1))

    heroes = extract(r"var\s+heroes\s*=\s*(\[[\s\S]*?\])\s*,\s*heroes_bg")
    heroes_wr = [float(x) if x not in (None, "null") else 50.0 for x in extract(r"heroes_wr\s*=\s*(\[[\s\S]*?\])\s*,\s*win_rates")]
    win_rates = extract(r"win_rates\s*=\s*(\[[\s\S]*?\])\s*;\s*update_time")
    return {
        "heroes": heroes,
        "heroes_wr": heroes_wr,
        "win_rates": win_rates,
    }


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def build_hero_index(heroes: List[str]) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for idx, name in enumerate(heroes):
        mapping.setdefault(normalize(name), idx)
    # Additional aliases for common variants
    alias_pairs = {
        "outworlddevourer": "outworlddestroyer",
        "keeperofthelight": "keeperofthelight",
        "naturesprophet": "naturesprophet",
        "lifestealer": "lifestealer",
        "queenofpain": "queenofpain",
        "spiritbreaker": "spiritbreaker",
        "ancientapparition": "ancientapparition",
        "wraithking": "wraithking",
        "shadowfiend": "shadowfiend",
        "timbersaw": "timbersaw",
        "phantomassassin": "phantomassassin",
    }
    for alias, target in alias_pairs.items():
        if alias not in mapping and target in mapping:
            mapping[alias] = mapping[target]
    return mapping


def safe_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def compute_adv_list(hero_ids: List[int], opponent_ids: List[int], win_rates: List[List[Any]]) -> List[float]:
    advs: List[float] = []
    for hero_id in hero_ids:
        total = 0.0
        for opp_id in opponent_ids:
            try:
                entry = win_rates[opp_id][hero_id]
            except (TypeError, IndexError):
                entry = None
            if not entry:
                continue
            val = entry[0]
            if val is None:
                continue
            total += float(val)
        advs.append(total)
    return advs


def load_matches(csv_path: Path, hero_index: Dict[str, int], heroes_wr: List[float], win_rates: List[List[Any]]):
    matches = []
    missing_heroes = set()
    skipped_rows = 0
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            delta = safe_float(row.get("delta", ""))
            if math.isnan(delta):
                skipped_rows += 1
                continue
            team1 = row["team1"].strip()
            team2 = row["team2"].strip()
            fav_team = row.get("delta_favored_team", "").strip()
            if fav_team not in (team1, team2):
                skipped_rows += 1
                continue
            t1_odds = safe_float(row.get("team1_odds", ""))
            t2_odds = safe_float(row.get("team2_odds", ""))
            if math.isnan(t1_odds) or math.isnan(t2_odds):
                skipped_rows += 1
                continue
            winner = row.get("winner", "").strip()
            heroes1 = [h.strip() for h in row.get("team1_heroes", "").split("|") if h.strip()]
            heroes2 = [h.strip() for h in row.get("team2_heroes", "").split("|") if h.strip()]
            if len(heroes1) != 5 or len(heroes2) != 5:
                skipped_rows += 1
                continue
            try:
                ids1 = [hero_index[normalize(name)] for name in heroes1]
                ids2 = [hero_index[normalize(name)] for name in heroes2]
            except KeyError as exc:
                missing_heroes.add(str(exc))
                skipped_rows += 1
                continue
            advs1 = compute_adv_list(ids1, ids2, win_rates)
            advs2 = compute_adv_list(ids2, ids1, win_rates)
            pos1 = sum(1 for adv in advs1 if adv > 0)
            pos2 = sum(1 for adv in advs2 if adv > 0)
            hero_flags = {
                "none": True,
                "4+4-": pos1 >= 4 and pos2 >= 4,
                "5+5-": pos1 >= 5 and pos2 >= 5,
            }
            fav_is_team1 = fav_team == team1
            fav_odds = t1_odds if fav_is_team1 else t2_odds
            other_odds = t2_odds if fav_is_team1 else t1_odds
            match = {
                "delta": delta,
                "abs_delta": abs(delta),
                "fav_team": fav_team,
                "winner": winner,
                "fav_odds": fav_odds,
                "other_odds": other_odds,
                "is_favorite": fav_odds < other_odds,
                "is_underdog": fav_odds > other_odds,
                "hero_flags": hero_flags,
            }
            matches.append(match)
    if missing_heroes:
        print(f"Warning: missing heroes for keys: {sorted(missing_heroes)[:5]} (total {len(missing_heroes)})")
    print(f"Loaded {len(matches)} matches, skipped {skipped_rows}")
    return matches


def desired_stake(strategy: Dict[str, Any], bank: float, fib_index: int, fib_sequence: List[int]) -> float:
    mode = strategy["mode"]
    if mode == "flat":
        return strategy["amount"]
    if mode == "percent":
        return bank * strategy["percent"]
    if mode == "fibonacci":
        units = fib_sequence[min(fib_index, len(fib_sequence) - 1)]
        return units * strategy["unit"]
    raise ValueError("Unknown mode")


def run_strategy(strategy: Dict[str, Any], matches: List[Dict[str, Any]], threshold: int, fib_sequence: List[int]):
    bank = START_BANK
    peak_bank = bank
    bets = 0
    wins = 0
    max_drawdown = 0.0
    max_stake = 0.0
    fib_index = 0
    max_step = 0

    for match in matches:
        if bank <= 0:
            break
        if match["abs_delta"] < threshold:
            continue
        if not match["hero_flags"].get(strategy["hero_filter"], False):
            continue
        if strategy["odds_condition"] == "favorite" and not match["is_favorite"]:
            continue
        if strategy["odds_condition"] == "underdog" and not match["is_underdog"]:
            continue
        pre_bank = bank
        stake = desired_stake(strategy, pre_bank, fib_index, fib_sequence)
        if stake <= 0:
            break
        stake = min(stake, pre_bank, MAX_BET)
        if stake < 1e-6:
            break
        bank -= stake
        won = match["winner"] == match["fav_team"]
        if won:
            payout = stake * match["fav_odds"]
            bank += payout
            wins += 1
            if strategy["mode"] == "fibonacci":
                fib_index = max(fib_index - 2, 0)
        else:
            if strategy["mode"] == "fibonacci":
                fib_index += 1
        bets += 1
        max_stake = max(max_stake, stake)
        peak_bank = max(peak_bank, bank)
        max_drawdown = max(max_drawdown, peak_bank - bank)
        if strategy["mode"] == "fibonacci":
            max_step = max(max_step, fib_index + 1)
        if bank <= 0:
            bank = 0
            break
    final_bank = round(bank)
    max_drawdown = round(max_drawdown)
    max_stake = round(max_stake)
    win_pct = round((wins / bets) * 100) if bets else 0
    return {
        "strategy_group": strategy["name"],
        "hero_filter": strategy["hero_filter"],
        "odds_condition": strategy["odds_condition"],
        "delta_threshold": threshold,
        "bets": bets,
        "wins": wins,
        "win_pct": win_pct,
        "final_bank": final_bank,
        "max_drawdown": max_drawdown,
        "max_stake": max_stake,
        "max_step": max_step if strategy["mode"] == "fibonacci" else 0,
    }


def build_strategy_defs():
    strategies = []
    odds_conditions = ["any", "underdog", "favorite"]

    # Flat $100, hero_filter none, odds any/underdog/favorite (strategies 1-3)
    for odds_cond in odds_conditions:
        strategies.append({
            "name": "Flat100",
            "hero_filter": "none",
            "odds_condition": odds_cond,
            "mode": "flat",
            "amount": 100.0,
        })

    # 5% bankroll per bet (dynamic), hero_filter none (strategies 4-6)
    for odds_cond in odds_conditions:
        strategies.append({
            "name": "Pct5",
            "hero_filter": "none",
            "odds_condition": odds_cond,
            "mode": "percent",
            "percent": 0.05,
        })

    # Flat $100 with 4+4- hero filter (strategies 7-9)
    for odds_cond in odds_conditions:
        strategies.append({
            "name": "Flat100",
            "hero_filter": "4+4-",
            "odds_condition": odds_cond,
            "mode": "flat",
            "amount": 100.0,
        })

    # Flat 5% (i.e., $50) with 4+4- (strategies 10-12)
    for odds_cond in odds_conditions:
        strategies.append({
            "name": "Flat50",
            "hero_filter": "4+4-",
            "odds_condition": odds_cond,
            "mode": "flat",
            "amount": 50.0,
        })

    # Flat $100 with 5+5- (strategies 13-15)
    for odds_cond in odds_conditions:
        strategies.append({
            "name": "Flat100",
            "hero_filter": "5+5-",
            "odds_condition": odds_cond,
            "mode": "flat",
            "amount": 100.0,
        })

    # Flat 5% ($50) with 5+5- (strategies 16-18)
    for odds_cond in odds_conditions:
        strategies.append({
            "name": "Flat50",
            "hero_filter": "5+5-",
            "odds_condition": odds_cond,
            "mode": "flat",
            "amount": 50.0,
        })

    # Fibonacci $1 unit (strategies 19-27)
    for hero_filter in ["none", "4+4-", "5+5-"]:
        for odds_cond in odds_conditions:
            strategies.append({
                "name": "Fibo1",
                "hero_filter": hero_filter,
                "odds_condition": odds_cond,
                "mode": "fibonacci",
                "unit": 1.0,
            })

    # Fibonacci $5 unit (strategies 28-36)
    for hero_filter in ["none", "4+4-", "5+5-"]:
        for odds_cond in odds_conditions:
            strategies.append({
                "name": "Fibo5",
                "hero_filter": hero_filter,
                "odds_condition": odds_cond,
                "mode": "fibonacci",
                "unit": 5.0,
            })

    return strategies


def make_fibonacci_sequence(limit: int = 60) -> List[int]:
    seq = [1, 1]
    while len(seq) < limit:
        seq.append(seq[-1] + seq[-2])
        if seq[-1] > MAX_BET * 2:
            break
    return seq


def main():
    cs_data = read_cs_pro(Path("cs_pro.json"))
    hero_index = build_hero_index(cs_data["heroes"])
    matches = load_matches(Path("hawk_matches_merged.csv"), hero_index, cs_data["heroes_wr"], cs_data["win_rates"])
    fib_sequence = make_fibonacci_sequence()
    strategies = build_strategy_defs()

    rows = []
    for strategy in strategies:
        for threshold in THRESHOLDS:
            stats = run_strategy(strategy, matches, threshold, fib_sequence)
            rows.append(stats)

    output_path = Path("strategy_results_hawk_cs_pro_cap.csv")
    fieldnames = [
        "strategy_group",
        "hero_filter",
        "odds_condition",
        "delta_threshold",
        "bets",
        "wins",
        "win_pct",
        "final_bank",
        "max_drawdown",
        "max_stake",
        "max_step",
    ]
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
