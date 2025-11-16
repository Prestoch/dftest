#!/usr/bin/env python3
"""
Simulate betting strategies using cs_pro_filtered.json matchup data and
hawk_matches_merged.csv odds/results.

Outputs a CSV matching the structure of strategy_results_*.csv with bankroll
clipping (no borrowing) and maximum stake of $10,000.
"""

from __future__ import annotations

import csv
import json
import re
import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

START_BANKROLL = 1000.0
MAX_BET = 10_000.0
THRESHOLDS = (
    list(range(5, 55, 5))  # 5,10,...,50
    + [75, 100, 125, 150]
    + list(range(200, 401, 25))  # 200..400 step 25
)

HERO_FILTERS = ["none", "4+4-", "5+5-"]
ODDS_CONDITIONS = ["any", "underdog", "favorite"]


@dataclass
class MatchRecord:
    abs_delta: float
    favored_odds: Optional[float]
    odds_category: Optional[str]  # 'favorite', 'underdog', or None
    is_win: bool
    hero_filter_pass: Dict[str, bool]


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def load_cs_data(path: Path):
    text = path.read_text().strip()
    if text.startswith("var "):
        text = text[4:]
    text = text.rstrip(" ;\n")
    for key in ["heroes", "heroes_bg", "heroes_wr", "win_rates", "update_time"]:
        text = re.sub(rf"\b{key}\s*=", f'"{key}":', text, count=1)
    data = json.loads("{" + text + "}")
    heroes = data["heroes"]
    hero_wr = [float(x) if x not in (None, "") else 0.0 for x in data["heroes_wr"]]
    win_rates = data["win_rates"]
    hero_index = {normalize(name): idx for idx, name in enumerate(heroes)}
    alias_overrides = {
        "outworlddevourer": "Outworld Destroyer",
        "wisp": "Io",
    }
    for alias, canonical in alias_overrides.items():
        hero_index[alias] = hero_index[normalize(canonical)]
    return heroes, hero_wr, win_rates, hero_index


def hero_id(name: str, hero_index: Dict[str, int]) -> int:
    key = normalize(name)
    if key not in hero_index:
        raise KeyError(f"Unknown hero name '{name}'")
    return hero_index[key]


def hero_advantage(hero_idx: int, enemy_indices: List[int], win_rates: List) -> float:
    total = 0.0
    for enemy_idx in enemy_indices:
        if enemy_idx is None:
            continue
        row = win_rates[enemy_idx]
        if row is None:
            continue
        cell = row[hero_idx] if hero_idx < len(row) else None
        if cell is None:
            continue
        val = cell[0]
        try:
            total += float(val)
        except (TypeError, ValueError):
            continue
    return total


def team_summary(hero_names: List[str], enemy_names: List[str], hero_index, hero_wr, win_rates):
    hero_ids = [hero_id(h, hero_index) for h in hero_names]
    enemy_ids = [hero_id(h, hero_index) for h in enemy_names]
    details = []
    total = 0.0
    for name, idx in zip(hero_names, hero_ids):
        wr = hero_wr[idx]
        adv = hero_advantage(idx, enemy_ids, win_rates)
        details.append({"name": name, "adv": adv, "wr": wr})
        total += wr + adv
    return total, details


def build_match_records(
    csv_path: Path,
    heroes_data,
    allowed_championships: Optional[set[str]] = None,
) -> List[MatchRecord]:
    _heroes, hero_wr, win_rates, hero_index = heroes_data
    records: List[MatchRecord] = []
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    def parse_float(value: str) -> Optional[float]:
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    sortable_rows = []
    for row in rows:
        date_str = row.get("date")
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except (TypeError, ValueError):
            continue
        series_id = int(row.get("series_id") or 0)
        map_number = int(row.get("map_number") or 0)
        match_id = int(row.get("hawk_match_id") or 0)
        sortable_rows.append(((date, series_id, map_number, match_id), row))

    sortable_rows.sort(key=lambda x: x[0])

    for _, row in sortable_rows:
        championship = row.get("championship")
        if allowed_championships and championship not in allowed_championships:
            continue
        team1_heroes = row.get("team1_heroes", "")
        team2_heroes = row.get("team2_heroes", "")
        if not team1_heroes or not team2_heroes:
            continue
        heroes1 = team1_heroes.split("|")
        heroes2 = team2_heroes.split("|")
        if len(heroes1) != 5 or len(heroes2) != 5:
            continue
        try:
            total1, details1 = team_summary(heroes1, heroes2, hero_index, hero_wr, win_rates)
            total2, details2 = team_summary(heroes2, heroes1, hero_index, hero_wr, win_rates)
        except KeyError:
            continue

        delta = total1 - total2
        favored_is_team1 = delta >= 0
        abs_delta = abs(delta)

        winner = row.get("winner")
        team1 = row.get("team1")
        team2 = row.get("team2")
        if winner not in (team1, team2):
            continue

        team1_odds = parse_float(row.get("team1_odds", ""))
        team2_odds = parse_float(row.get("team2_odds", ""))
        favored_odds = team1_odds if favored_is_team1 else team2_odds
        opponent_odds = team2_odds if favored_is_team1 else team1_odds
        odds_category = None
        if favored_odds is not None and opponent_odds is not None:
            if favored_odds < opponent_odds:
                odds_category = "favorite"
            elif favored_odds > opponent_odds:
                odds_category = "underdog"

        favored_details = details1 if favored_is_team1 else details2
        opponent_details = details2 if favored_is_team1 else details1
        pos_count = sum(1 for h in favored_details if h["adv"] >= 4.0)
        neg_count = sum(1 for h in opponent_details if h["adv"] <= -4.0)
        hero_filter_pass = {
            "4+4-": pos_count >= 4 and neg_count >= 4,
            "5+5-": pos_count >= 5 and neg_count >= 5,
        }

        is_win = winner == (team1 if favored_is_team1 else team2)

        records.append(
            MatchRecord(
                abs_delta=abs_delta,
                favored_odds=favored_odds,
                odds_category=odds_category,
                is_win=is_win,
                hero_filter_pass=hero_filter_pass,
            )
        )
    return records


def fibonacci_value(step: int, fib_cache: List[int]) -> int:
    while step >= len(fib_cache):
        fib_cache.append(fib_cache[-1] + fib_cache[-2])
    return fib_cache[step]


def simulate_strategy(matches: List[MatchRecord], strategy_group: str, hero_filter: str, odds_condition: str, threshold: float):
    bank = START_BANKROLL
    peak = bank
    max_drawdown = 0.0
    max_stake = 0.0
    bets = 0
    wins = 0
    max_step = 0
    fib_cache = [1, 1]
    fib_step = 0

    def stake_amount(current_bank: float) -> float:
        if strategy_group == "Flat100":
            return 100.0
        if strategy_group == "Pct5":
            return current_bank * 0.05
        if strategy_group == "Fib1":
            units = fibonacci_value(fib_step, fib_cache)
            return float(units)
        if strategy_group == "Fib5":
            units = fibonacci_value(fib_step, fib_cache)
            return float(units * 5)
        raise ValueError(f"Unknown strategy group: {strategy_group}")

    for match in matches:
        if match.abs_delta < threshold:
            continue
        if hero_filter != "none" and not match.hero_filter_pass.get(hero_filter, False):
            continue
        if odds_condition == "favorite" and match.odds_category != "favorite":
            continue
        if odds_condition == "underdog" and match.odds_category != "underdog":
            continue
        if match.favored_odds is None:
            continue
        if bank <= 0:
            break

        desired_stake = stake_amount(bank)
        stake = min(desired_stake, bank, MAX_BET)
        if stake <= 0:
            continue

        bets += 1
        bank -= stake
        if match.is_win:
            wins += 1
            bank += stake * match.favored_odds
            if strategy_group.startswith("Fib"):
                fib_step = max(fib_step - 2, 0)
        else:
            if strategy_group.startswith("Fib"):
                fib_step += 1
        if strategy_group.startswith("Fib"):
            max_step = max(max_step, fib_step)

        max_stake = max(max_stake, stake)
        if bank > peak:
            peak = bank
        else:
            drawdown = peak - bank
            max_drawdown = max(max_drawdown, drawdown)

    win_pct = (wins / bets * 100.0) if bets else 0.0

    def round_metric(value: float) -> int:
        return int(round(value))
    return {
        "strategy_group": strategy_group,
        "hero_filter": hero_filter,
        "odds_condition": odds_condition,
        "delta_threshold": threshold,
        "bets": bets,
        "wins": wins,
        "win_pct": round_metric(win_pct),
        "final_bank": round_metric(bank),
        "max_drawdown": round_metric(max_drawdown),
        "max_stake": round_metric(max_stake),
        "max_step": max_step,
    }


def main():
    parser = argparse.ArgumentParser(description="Simulate bankroll strategies from hawk match data.")
    parser.add_argument(
        "--championship",
        action="append",
        dest="championships",
        help="Championship name to include (can be provided multiple times). Defaults to all.",
    )
    parser.add_argument(
        "--output",
        default="strategy_results_hawk_cs_bankroll.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--cs-file",
        default="cs_pro_filtered.json",
        help="Path to hero matchup dataset (e.g. cs_pro_filtered.json or cs.json).",
    )
    args = parser.parse_args()

    heroes_data = load_cs_data(Path(args.cs_file))
    allowed = set(args.championships) if args.championships else None
    matches = build_match_records(Path("hawk_matches_merged.csv"), heroes_data, allowed)
    if not matches:
        print("No matches matched the provided filters.", file=sys.stderr)
        # Still write the CSV (all zeros)

    strategy_specs = []
    for strategy_group in ("Flat100", "Pct5", "Fib1", "Fib5"):
        for hero_filter in HERO_FILTERS:
            for odds_condition in ODDS_CONDITIONS:
                strategy_specs.append((strategy_group, hero_filter, odds_condition))

    results = []
    for strategy_group, hero_filter, odds_condition in strategy_specs:
        for threshold in THRESHOLDS:
            summary = simulate_strategy(matches, strategy_group, hero_filter, odds_condition, threshold)
            results.append(summary)

    strategy_order = {"Flat100": 0, "Pct5": 1, "Fib1": 2, "Fib5": 3}
    hero_order = {"none": 0, "4+4-": 1, "5+5-": 2}
    odds_order = {"any": 0, "underdog": 1, "favorite": 2}
    results.sort(
        key=lambda r: (
            strategy_order[r["strategy_group"]],
            hero_order[r["hero_filter"]],
            odds_order[r["odds_condition"]],
            r["delta_threshold"],
        )
    )

    output_path = Path(args.output)
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"Wrote {len(results)} rows to {output_path}")


if __name__ == "__main__":
    main()
