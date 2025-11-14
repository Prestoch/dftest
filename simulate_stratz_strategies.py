#!/usr/bin/env python3
"""
Apply the cs_stratz hero matchup matrix to the Hawk match dataset and
simulate a set of betting strategies under various delta thresholds.

The script produces one CSV per requested strategy combination, each
containing per-threshold performance metrics.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple


ROOT = Path(__file__).parent
MATRIX_PATH = ROOT / "cs_stratz.json"
HAWK_DATA_PATH = ROOT / "hawk_matches_merged.csv"
OUTPUT_DIR = ROOT / "stratz_results"

START_DATE = datetime.fromisoformat("2023-01-02")
END_DATE = datetime.fromisoformat("2025-11-06")
START_BANKROLL = 1000.0
MAX_BET = 10_000.0
THRESHOLDS: list[int] = [
    5,
    10,
    15,
    20,
    25,
    30,
    35,
    40,
    45,
    50,
    75,
    100,
    125,
    150,
    200,
    250,
    300,
    350,
    400,
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatchRecord:
    date: datetime
    championship: str
    series_id: str
    map_number: str
    match_id: str
    team1: str
    team2: str
    team1_heroes: list[str]
    team2_heroes: list[str]
    winner: str
    delta: float
    abs_delta: float
    favored_team: str
    favored_is_team1: bool
    favored_odds: float
    opponent_odds: float
    is_underdog_pick: bool
    is_favorite_pick: bool
    favored_advantage_count: int
    underdog_disadvantage_count: int


@dataclass(frozen=True)
class Strategy:
    key: str
    label: str
    stake_type: Literal["flat", "percent", "fibonacci"]
    stake_value: float
    hero_filter: Literal["none", "4+4-", "5+5-"]
    odds_condition: Literal["any", "underdog", "favorite"]


# ---------------------------------------------------------------------------
# Matrix loading utilities
# ---------------------------------------------------------------------------


def extract_js_array(content: str, current_var: str, next_var: str) -> Any:
    pattern = rf"{current_var}\s*=\s*(\[[\s\S]*?\]),\s*{next_var}"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        raise ValueError(f"Failed to locate array for {current_var!r}")
    return json.loads(match.group(1))


def load_matrix(path: Path) -> tuple[list[str], dict[str, float], list[list[float]]]:
    content = path.read_text()
    heroes = extract_js_array(content, r"var heroes", r"heroes_bg")
    heroes_wr_raw = extract_js_array(content, r"heroes_wr", r"win_rates")
    win_rates_raw = extract_js_array(content, r"win_rates", r"update_time")

    hero_wr = {name: float(wr) for name, wr in zip(heroes, heroes_wr_raw)}

    delta_matrix: list[list[float]] = []
    for row in win_rates_raw:
        delta_row: list[float] = []
        for cell in row:
            if cell is None:
                delta_row.append(0.0)
            else:
                delta_row.append(float(cell[0]))
        delta_matrix.append(delta_row)

    return heroes, hero_wr, delta_matrix


def build_hero_lookup(heroes: Iterable[str]) -> dict[str, str]:
    lookup: dict[str, str] = {}

    def normalize(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower())

    for hero in heroes:
        normalized = normalize(hero)
        if normalized in lookup:
            raise ValueError(f"Duplicate normalized hero name detected: {hero}")
        lookup[normalized] = hero

    return lookup


def normalize_hero(name: str, lookup: dict[str, str]) -> str:
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    if key not in lookup:
        raise KeyError(f"Unknown hero name: {name}")
    return lookup[key]


# ---------------------------------------------------------------------------
# Match delta computation
# ---------------------------------------------------------------------------


class MatrixEvaluator:
    def __init__(
        self, heroes: list[str], hero_wr: dict[str, float], delta_matrix: list[list[float]]
    ) -> None:
        self._heroes = heroes
        self._hero_wr = hero_wr
        self._delta_matrix = delta_matrix
        self._hero_index = {name: idx for idx, name in enumerate(heroes)}

    def delta(self, hero_a: str, hero_b: str) -> float:
        return self._delta_matrix[self._hero_index[hero_a]][self._hero_index[hero_b]]

    def hero_wr(self, hero: str) -> float:
        return self._hero_wr[hero]

    def matchup_score(self, hero: str, opponents: Iterable[str]) -> float:
        return sum(self.delta(hero, opp) for opp in opponents)

    def team_delta(self, team_a: Iterable[str], team_b: Iterable[str]) -> float:
        return sum(self.delta(a, b) for a in team_a for b in team_b)

    def hero_scores(self, heroes: Iterable[str], opponents: Iterable[str]) -> list[float]:
        opp_list = list(opponents)
        return [self.matchup_score(hero, opp_list) for hero in heroes]

    def match_delta(self, team1: list[str], team2: list[str]) -> float:
        sum1 = self.team_delta(team1, team2)
        sum2 = self.team_delta(team2, team1)
        wr_diff = sum(self.hero_wr(hero) for hero in team1) - sum(
            self.hero_wr(hero) for hero in team2
        )
        return sum2 - sum1 + wr_diff


def load_matches(evaluator: MatrixEvaluator, lookup: dict[str, str]) -> list[MatchRecord]:
    records: list[MatchRecord] = []

    with HAWK_DATA_PATH.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            date = datetime.fromisoformat(row["date"])
            if not (START_DATE <= date <= END_DATE):
                continue

            team1_heroes_raw = row["team1_heroes"].split("|")
            team2_heroes_raw = row["team2_heroes"].split("|")

            try:
                team1_heroes = [normalize_hero(hero.strip(), lookup) for hero in team1_heroes_raw]
                team2_heroes = [normalize_hero(hero.strip(), lookup) for hero in team2_heroes_raw]
            except KeyError as exc:
                # Skip matches containing heroes not found in the matrix.
                raise KeyError(f"Failed to map hero in match {row['hawk_match_id']}: {exc}") from exc

            delta = evaluator.match_delta(team1_heroes, team2_heroes)
            favored_is_team1 = delta >= 0
            favored_team = row["team1"] if favored_is_team1 else row["team2"]
            favored_odds_raw = float(row["team1_odds"]) if favored_is_team1 else float(row["team2_odds"])
            opponent_odds_raw = float(row["team2_odds"]) if favored_is_team1 else float(row["team1_odds"])

            favored_scores = (
                evaluator.hero_scores(team1_heroes, team2_heroes)
                if favored_is_team1
                else evaluator.hero_scores(team2_heroes, team1_heroes)
            )
            underdog_scores = (
                evaluator.hero_scores(team2_heroes, team1_heroes)
                if favored_is_team1
                else evaluator.hero_scores(team1_heroes, team2_heroes)
            )

            favored_advantage_count = sum(score <= 0 for score in favored_scores)
            underdog_disadvantage_count = sum(score >= 0 for score in underdog_scores)

            records.append(
                MatchRecord(
                    date=date,
                    championship=row["championship"],
                    series_id=row["series_id"],
                    map_number=row["map_number"],
                    match_id=row["hawk_match_id"],
                    team1=row["team1"],
                    team2=row["team2"],
                    team1_heroes=team1_heroes,
                    team2_heroes=team2_heroes,
                    winner=row["winner"],
                    delta=delta,
                    abs_delta=abs(delta),
                    favored_team=favored_team,
                    favored_is_team1=favored_is_team1,
                    favored_odds=favored_odds_raw,
                    opponent_odds=opponent_odds_raw,
                    is_underdog_pick=favored_odds_raw > opponent_odds_raw,
                    is_favorite_pick=favored_odds_raw < opponent_odds_raw,
                    favored_advantage_count=favored_advantage_count,
                    underdog_disadvantage_count=underdog_disadvantage_count,
                )
            )

    records.sort(key=lambda record: record.date)
    return records


# ---------------------------------------------------------------------------
# Strategy filters
# ---------------------------------------------------------------------------


def hero_filter_fn(name: str) -> Callable[[MatchRecord], bool]:
    if name == "none":
        return lambda record: True
    if name == "4+4-":
        return lambda record: record.favored_advantage_count >= 4 and record.underdog_disadvantage_count >= 4
    if name == "5+5-":
        return lambda record: record.favored_advantage_count >= 5 and record.underdog_disadvantage_count >= 5
    raise ValueError(f"Unknown hero filter: {name}")


def odds_filter_fn(condition: str) -> Callable[[MatchRecord], bool]:
    if condition == "any":
        return lambda record: True
    if condition == "underdog":
        return lambda record: record.is_underdog_pick
    if condition == "favorite":
        return lambda record: record.is_favorite_pick
    raise ValueError(f"Unknown odds condition: {condition}")


# ---------------------------------------------------------------------------
# Betting engine
# ---------------------------------------------------------------------------


def fibonacci_value(step: int, cache: list[int]) -> int:
    while len(cache) <= step:
        cache.append(cache[-1] + cache[-2])
    return cache[step]


def run_strategy(
    strategy: Strategy, matches: list[MatchRecord], thresholds: Iterable[int]
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    hero_filter = hero_filter_fn(strategy.hero_filter)
    odds_filter = odds_filter_fn(strategy.odds_condition)

    for threshold in thresholds:
        bank = START_BANKROLL
        peak_bank = bank
        max_drawdown = 0.0
        total_staked = 0.0
        wins = 0
        losses = 0
        max_stake = 0.0

        fib_cache = [1, 1]
        fib_step = 0
        max_fib_step = 0

        for match in matches:
            if match.abs_delta < threshold:
                continue
            if not hero_filter(match):
                continue
            if not odds_filter(match):
                continue
            if bank <= 0:
                break

            if strategy.stake_type == "flat":
                requested = strategy.stake_value
            elif strategy.stake_type == "percent":
                requested = bank * strategy.stake_value
            elif strategy.stake_type == "fibonacci":
                requested = strategy.stake_value * fibonacci_value(fib_step, fib_cache)
                max_fib_step = max(max_fib_step, fib_step)
            else:
                raise ValueError(f"Unsupported stake type: {strategy.stake_type}")

            stake = min(requested, bank, MAX_BET)
            if stake <= 0:
                continue

            bank -= stake
            max_stake = max(max_stake, stake)
            total_staked += stake

            if match.favored_team == match.winner:
                wins += 1
                bank += stake * match.favored_odds
                if strategy.stake_type == "fibonacci":
                    fib_step = max(fib_step - 2, 0)
            else:
                losses += 1
                if strategy.stake_type == "fibonacci":
                    fib_step += 1

            peak_bank = max(peak_bank, bank)
            drawdown = peak_bank - bank
            max_drawdown = max(max_drawdown, drawdown)

        bets = wins + losses
        profit = bank - START_BANKROLL
        roi = profit / total_staked if total_staked else 0.0
        win_pct = wins / bets * 100 if bets else 0.0

        results.append(
            {
                "strategy": strategy.label,
                "hero_filter": strategy.hero_filter,
                "odds_condition": strategy.odds_condition,
                "delta_threshold": threshold,
                "bets": bets,
                "wins": wins,
                "losses": losses,
                "win_pct": round(win_pct, 2),
                "final_bank": round(bank, 2),
                "profit": round(profit, 2),
                "total_staked": round(total_staked, 2),
                "roi": round(roi, 4),
                "max_drawdown": round(max_drawdown, 2),
                "max_stake": round(max_stake, 2),
                "max_fib_step": max_fib_step if strategy.stake_type == "fibonacci" else 0,
            }
        )

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_strategies() -> list[Strategy]:
    strategies: list[Strategy] = []

    def add(
        key: str,
        label: str,
        stake_type: Literal["flat", "percent", "fibonacci"],
        stake_value: float,
        hero_filter: Literal["none", "4+4-", "5+5-"],
        odds_condition: Literal["any", "underdog", "favorite"],
    ) -> None:
        strategies.append(
            Strategy(
                key=key,
                label=label,
                stake_type=stake_type,
                stake_value=stake_value,
                hero_filter=hero_filter,
                odds_condition=odds_condition,
            )
        )

    # Flat $100 combinations
    add("flat100_none_any", "Flat $100", "flat", 100.0, "none", "any")
    add("flat100_none_underdog", "Flat $100", "flat", 100.0, "none", "underdog")
    add("flat100_none_favorite", "Flat $100", "flat", 100.0, "none", "favorite")

    # 5% bankroll combinations
    add("pct5_none_any", "5% Bankroll", "percent", 0.05, "none", "any")
    add("pct5_none_underdog", "5% Bankroll", "percent", 0.05, "none", "underdog")
    add("pct5_none_favorite", "5% Bankroll", "percent", 0.05, "none", "favorite")

    # Flat $100 with hero filters
    add("flat100_4plus_any", "Flat $100 (4+4-)", "flat", 100.0, "4+4-", "any")
    add("flat100_4plus_underdog", "Flat $100 (4+4-)", "flat", 100.0, "4+4-", "underdog")
    add("flat100_4plus_favorite", "Flat $100 (4+4-)", "flat", 100.0, "4+4-", "favorite")

    # Flat 5% (constant $50) with 4+4-
    add("flat5pct_4plus_any", "Flat $50 (4+4-)", "flat", START_BANKROLL * 0.05, "4+4-", "any")
    add(
        "flat5pct_4plus_underdog",
        "Flat $50 (4+4-)",
        "flat",
        START_BANKROLL * 0.05,
        "4+4-",
        "underdog",
    )
    add(
        "flat5pct_4plus_favorite",
        "Flat $50 (4+4-)",
        "flat",
        START_BANKROLL * 0.05,
        "4+4-",
        "favorite",
    )

    # Flat $100 with 5+5-
    add("flat100_5plus_any", "Flat $100 (5+5-)", "flat", 100.0, "5+5-", "any")
    add("flat100_5plus_underdog", "Flat $100 (5+5-)", "flat", 100.0, "5+5-", "underdog")
    add("flat100_5plus_favorite", "Flat $100 (5+5-)", "flat", 100.0, "5+5-", "favorite")

    # Flat $50 with 5+5-
    add(
        "flat5pct_5plus_any",
        "Flat $50 (5+5-)",
        "flat",
        START_BANKROLL * 0.05,
        "5+5-",
        "any",
    )
    add(
        "flat5pct_5plus_underdog",
        "Flat $50 (5+5-)",
        "flat",
        START_BANKROLL * 0.05,
        "5+5-",
        "underdog",
    )
    add(
        "flat5pct_5plus_favorite",
        "Flat $50 (5+5-)",
        "flat",
        START_BANKROLL * 0.05,
        "5+5-",
        "favorite",
    )

    # Fibonacci $1 unit
    add("fib1_none_any", "Fibonacci $1", "fibonacci", 1.0, "none", "any")
    add("fib1_none_underdog", "Fibonacci $1", "fibonacci", 1.0, "none", "underdog")
    add("fib1_none_favorite", "Fibonacci $1", "fibonacci", 1.0, "none", "favorite")

    # Fibonacci $1 with 4+4-
    add("fib1_4plus_any", "Fibonacci $1 (4+4-)", "fibonacci", 1.0, "4+4-", "any")
    add("fib1_4plus_underdog", "Fibonacci $1 (4+4-)", "fibonacci", 1.0, "4+4-", "underdog")
    add("fib1_4plus_favorite", "Fibonacci $1 (4+4-)", "fibonacci", 1.0, "4+4-", "favorite")

    # Fibonacci $1 with 5+5-
    add("fib1_5plus_any", "Fibonacci $1 (5+5-)", "fibonacci", 1.0, "5+5-", "any")
    add("fib1_5plus_underdog", "Fibonacci $1 (5+5-)", "fibonacci", 1.0, "5+5-", "underdog")
    add("fib1_5plus_favorite", "Fibonacci $1 (5+5-)", "fibonacci", 1.0, "5+5-", "favorite")

    # Fibonacci $5 unit
    add("fib5_none_any", "Fibonacci $5", "fibonacci", 5.0, "none", "any")
    add("fib5_none_underdog", "Fibonacci $5", "fibonacci", 5.0, "none", "underdog")
    add("fib5_none_favorite", "Fibonacci $5", "fibonacci", 5.0, "none", "favorite")

    # Fibonacci $5 with 4+4-
    add("fib5_4plus_any", "Fibonacci $5 (4+4-)", "fibonacci", 5.0, "4+4-", "any")
    add("fib5_4plus_underdog", "Fibonacci $5 (4+4-)", "fibonacci", 5.0, "4+4-", "underdog")
    add("fib5_4plus_favorite", "Fibonacci $5 (4+4-)", "fibonacci", 5.0, "4+4-", "favorite")

    # Fibonacci $5 with 5+5-
    add("fib5_5plus_any", "Fibonacci $5 (5+5-)", "fibonacci", 5.0, "5+5-", "any")
    add("fib5_5plus_underdog", "Fibonacci $5 (5+5-)", "fibonacci", 5.0, "5+5-", "underdog")
    add("fib5_5plus_favorite", "Fibonacci $5 (5+5-)", "fibonacci", 5.0, "5+5-", "favorite")

    return strategies


def write_results(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    heroes, hero_wr, delta_matrix = load_matrix(MATRIX_PATH)
    lookup = build_hero_lookup(heroes)
    evaluator = MatrixEvaluator(heroes, hero_wr, delta_matrix)
    matches = load_matches(evaluator, lookup)
    strategies = build_strategies()

    for strategy in strategies:
        results = run_strategy(strategy, matches, THRESHOLDS)
        output_path = OUTPUT_DIR / f"{strategy.key}.csv"
        write_results(output_path, results)


if __name__ == "__main__":
    main()

