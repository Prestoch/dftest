#!/usr/bin/env python3
"""
Generate betting strategy backtest results for the Hawk match dataset.

This script mirrors the structure of `strategy_results_20220101_20230101_cs_pro_cap.csv`
by re-computing per-match deltas from `cs.json` and simulating a variety of staking
approaches across multiple delta thresholds, hero filters, and odds filters.
"""

from __future__ import annotations

import ast
import csv
import math
import re
from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

START_BANKROLL = 1000.0
MAX_BET = 10_000.0
THRESHOLDS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 75, 100, 125, 150, 200, 250, 300, 350, 400]


# -------------------------------------------------------------------------------------------------
# Utility helpers
# -------------------------------------------------------------------------------------------------


def normalize_name(raw: str) -> str:
    """Return a canonical lookup key for hero names."""
    return re.sub(r"[^a-z0-9]", "", raw.lower())


def load_cs_data(path: Path) -> tuple[list[str], list[float], list[list[object]]]:
    """Read cs.json and return heroes, hero win rates, and the matchup matrix."""
    text = path.read_text()

    def extract_array(name: str) -> list[object]:
        marker = f"{name} ="
        idx = text.index(marker)
        start = text.index("[", idx)
        depth = 0
        for pos in range(start, len(text)):
            ch = text[pos]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = pos
                    break
        else:
            raise RuntimeError(f"Missing closing bracket for {name}")

        payload = text[start : end + 1].replace("null", "None")
        return ast.literal_eval(payload)

    heroes = extract_array("heroes")
    heroes_wr = [float(value) for value in extract_array("heroes_wr")]
    win_rates = extract_array("win_rates")

    return heroes, heroes_wr, win_rates


# -------------------------------------------------------------------------------------------------
# Match modelling
# -------------------------------------------------------------------------------------------------


@dataclass
class MatchRecord:
    date: datetime
    hawk_match_id: str
    championship: str
    delta_value: float
    favored_team: str
    favored_odds: float
    opponent_team: str
    opponent_odds: float
    favored_is_underdog: bool
    favored_is_favorite: bool
    favored_won: bool
    abs_delta: float
    favored_advantages: list[float]
    opponent_advantages: list[float]
    has_4_plus_4_minus: bool
    has_5_plus_5_minus: bool


def compute_hero_advantage(
    hero_name: str,
    opponent_names: Iterable[str],
    hero_index_map: dict[str, int],
    win_rates: list[list[object]],
) -> float:
    hero_idx = hero_index_map[normalize_name(hero_name)]
    total = 0.0
    for opp in opponent_names:
        opp_idx = hero_index_map[normalize_name(opp)]
        row = win_rates[opp_idx]
        if row is None or hero_idx >= len(row):
            continue
        entry = row[hero_idx]
        if entry is None:
            continue
        try:
            total += float(entry[0])
        except (IndexError, TypeError, ValueError):
            continue
    return total


def load_matches(
    csv_path: Path,
    heroes: list[str],
    heroes_wr: list[float],
    win_rates: list[list[object]],
    championship_exact: set[str],
    championship_contains: list[str],
) -> list[MatchRecord]:
    index_map = {normalize_name(name): idx for idx, name in enumerate(heroes)}
    matches: list[MatchRecord] = []

    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            championship_name = row["championship"]
            if championship_exact and championship_name not in championship_exact:
                continue
            if championship_contains and not any(
                needle in championship_name for needle in championship_contains
            ):
                continue

            team1 = row["team1"]
            team2 = row["team2"]

            try:
                odds1 = float(row["team1_odds"])
                odds2 = float(row["team2_odds"])
            except (TypeError, ValueError):
                # Skip matches without valid odds
                continue

            team1_heroes = row["team1_heroes"].split("|")
            team2_heroes = row["team2_heroes"].split("|")

            try:
                team1_advantages = [
                    compute_hero_advantage(hero, team2_heroes, index_map, win_rates)
                    for hero in team1_heroes
                ]
                team2_advantages = [
                    compute_hero_advantage(hero, team1_heroes, index_map, win_rates)
                    for hero in team2_heroes
                ]
            except KeyError:
                # Hero not found in lookup; skip match
                continue

            team1_total = sum(
                heroes_wr[index_map[normalize_name(hero)]] + adv
                for hero, adv in zip(team1_heroes, team1_advantages)
            )
            team2_total = sum(
                heroes_wr[index_map[normalize_name(hero)]] + adv
                for hero, adv in zip(team2_heroes, team2_advantages)
            )

            delta_raw = team1_total - team2_total
            if math.isclose(delta_raw, 0.0, abs_tol=1e-9):
                # Ignore perfectly neutral matches
                continue

            if delta_raw > 0:
                favored_team = team1
                favored_odds = odds1
                opponent_team = team2
                opponent_odds = odds2
                favored_advantages = team1_advantages
                opponent_advantages = team2_advantages
            else:
                favored_team = team2
                favored_odds = odds2
                opponent_team = team1
                opponent_odds = odds1
                favored_advantages = team2_advantages
                opponent_advantages = team1_advantages

            favored_good = sum(1 for value in favored_advantages if value < 0)
            opponent_bad = sum(1 for value in opponent_advantages if value > 0)

            match = MatchRecord(
                date=datetime.strptime(row["date"], "%Y-%m-%d"),
                hawk_match_id=row["hawk_match_id"],
                championship=row["championship"],
                delta_value=abs(delta_raw),
                favored_team=favored_team,
                favored_odds=favored_odds,
                opponent_team=opponent_team,
                opponent_odds=opponent_odds,
                favored_is_underdog=favored_odds > opponent_odds,
                favored_is_favorite=favored_odds < opponent_odds,
                favored_won=row["winner"] == favored_team,
                abs_delta=abs(delta_raw),
                favored_advantages=favored_advantages,
                opponent_advantages=opponent_advantages,
                has_4_plus_4_minus=favored_good >= 4 and opponent_bad >= 4,
                has_5_plus_5_minus=favored_good >= 5 and opponent_bad >= 5,
            )
            matches.append(match)

    matches.sort(key=lambda item: (item.date, item.hawk_match_id))
    return matches


# -------------------------------------------------------------------------------------------------
# Strategy simulation
# -------------------------------------------------------------------------------------------------


def fibonacci_number(step: int, cache: List[int]) -> int:
    while step >= len(cache):
        cache.append(cache[-1] + cache[-2])
    return cache[step]


def simulate_strategy(
    matches: list[MatchRecord],
    threshold: float,
    strategy_group: str,
    hero_filter: str,
    odds_condition: str,
) -> dict[str, object]:
    bank = START_BANKROLL
    peak = bank
    max_drawdown = 0.0
    max_stake = 0.0
    max_step = 0
    bets = 0
    wins = 0

    is_flat = strategy_group.startswith("Flat100")
    is_percentage = strategy_group.startswith("Pct5")
    is_fib = strategy_group.startswith("Fib")

    fib_unit = 0.0
    fib_cache = [1, 1]
    fib_step = 0

    if strategy_group == "Flat100":
        flat_amount = 100.0
    elif strategy_group == "Pct5":
        percentage = 0.05
    elif strategy_group == "Fib1":
        fib_unit = 1.0
    elif strategy_group == "Fib5":
        fib_unit = 5.0
    else:
        raise ValueError(f"Unsupported strategy group: {strategy_group}")

    for match in matches:
        if match.abs_delta < threshold:
            continue

        if hero_filter == "4+4-" and not match.has_4_plus_4_minus:
            continue
        if hero_filter == "5+5-" and not match.has_5_plus_5_minus:
            continue

        if odds_condition == "underdog" and not match.favored_is_underdog:
            continue
        if odds_condition == "favorite" and not match.favored_is_favorite:
            continue
        if odds_condition not in {"any", "underdog", "favorite"}:
            raise ValueError(f"Unknown odds condition: {odds_condition}")

        if bank <= 0:
            break

        if is_flat:
            desired = flat_amount
        elif is_percentage:
            desired = max(0.0, percentage * bank)
        else:
            step_used = fib_step
            fib_value = fibonacci_number(step_used, fib_cache)
            desired = fib_unit * fib_value

        stake = min(desired, bank, MAX_BET)
        if stake <= 0:
            break

        if is_fib:
            step_used = fib_step
            max_step = max(max_step, step_used)

        bank -= stake
        bets += 1
        won = match.favored_won
        if won:
            bank += stake * match.favored_odds
            wins += 1
            if is_fib:
                fib_step = max(fib_step - 2, 0)
        else:
            if is_fib:
                fib_step += 1

        if is_fib and fib_step >= len(fib_cache):
            fibonacci_number(fib_step, fib_cache)

        if stake > max_stake:
            max_stake = stake

        if bank > peak:
            peak = bank
        else:
            drawdown = peak - bank
            if drawdown > max_drawdown:
                max_drawdown = drawdown

    win_pct = round((wins / bets) * 100) if bets else 0

    return {
        "strategy_group": strategy_group,
        "hero_filter": hero_filter,
        "odds_condition": odds_condition,
        "delta_threshold": threshold,
        "bets": bets,
        "wins": wins,
        "win_pct": win_pct,
        "final_bank": int(round(bank)),
        "max_drawdown": int(round(max_drawdown)),
        "max_stake": int(round(max_stake)),
        "max_step": max_step if is_fib else 0,
    }


def run_all_strategies(matches: list[MatchRecord]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []

    hero_filters = ["none", "4+4-", "5+5-"]
    odds_conditions = ["any", "underdog", "favorite"]
    strategy_groups = ["Flat100", "Pct5", "Fib1", "Fib5"]

    for strategy_group in strategy_groups:
        for hero_filter in hero_filters:
            for odds_condition in odds_conditions:
                # Only include combinations mentioned in the requirements.
                if hero_filter == "none":
                    include = True
                else:
                    include = strategy_group in {"Flat100", "Pct5", "Fib1", "Fib5"}

                if not include:
                    continue

                for threshold in THRESHOLDS:
                    result = simulate_strategy(
                        matches,
                        threshold,
                        strategy_group,
                        hero_filter,
                        odds_condition,
                    )
                    results.append(result)

    return results


# -------------------------------------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------------------------------------


def main() -> None:
    parser = ArgumentParser(description="Simulate betting strategies on Hawk match data.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("strategy_results_hawk.csv"),
        help="Path to the output CSV file.",
    )
    parser.add_argument(
        "--championship",
        action="append",
        default=[],
        help="Restrict to matches whose championship exactly matches this string. "
        "May be provided multiple times.",
    )
    parser.add_argument(
        "--championship-contains",
        dest="championship_contains",
        action="append",
        default=[],
        help="Restrict to matches whose championship contains this substring. "
        "May be provided multiple times.",
    )
    args = parser.parse_args()

    championship_exact = {entry.strip() for entry in args.championship if entry.strip()}
    championship_contains = [
        entry.strip() for entry in args.championship_contains if entry.strip()
    ]

    heroes, heroes_wr, win_rates = load_cs_data(Path("cs.json"))
    matches = load_matches(
        Path("hawk_matches_merged.csv"),
        heroes,
        heroes_wr,
        win_rates,
        championship_exact=championship_exact,
        championship_contains=championship_contains,
    )

    if not matches:
        print("No matches found with the specified filters.")
        return

    results = run_all_strategies(matches)

    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
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

    print(
        f"Wrote {len(results)} rows to {args.output} "
        f"from {len(matches)} filtered matches."
    )


if __name__ == "__main__":
    main()

