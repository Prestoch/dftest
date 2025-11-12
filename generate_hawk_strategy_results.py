#!/usr/bin/env python3
"""
Generate betting strategy results for the Hawk dataset using matchup deltas
derived from the freshly generated `cs.json`.

Outputs a CSV mirroring `strategy_results_20220101_20230101_cs_pro_cap.csv`.
"""

from __future__ import annotations

import csv
import json
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


CS_PATH = Path("cs.json")
MATCHES_PATH = Path("hawk_matches_merged.csv")
OUTPUT_PATH = Path("strategy_results_hawk_cs.csv")

START_BANKROLL = 1000.0
MAX_BET = 10_000.0
THRESHOLDS: Tuple[int, ...] = (
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
)


@dataclass(frozen=True)
class StrategyConfig:
    strategy_group: str
    hero_filter: str  # "none", "4+4-", "5+5-"
    odds_condition: str  # "any", "underdog", "favorite"
    stake_type: str  # "flat", "percent", "fibonacci"
    stake_value: float  # amount, percent, or base unit


@dataclass
class Match:
    abs_delta: float
    favored_team: str  # "team1" or "team2"
    hero_deltas: Dict[str, List[float]]
    favored_odds: float
    opponent_odds: float
    favored_is_underdog: bool
    favored_is_favorite: bool
    winner: str  # "team1" or "team2"


def parse_cs(path: Path) -> Dict[str, object]:
    text = path.read_text()
    parts: Dict[str, object] = {}

    def extract(key: str, token: str) -> None:
        idx = text.find(token)
        if idx == -1:
            raise ValueError(f"Unable to locate `{token}` in {path}")
        eq_idx = text.find("=", idx)
        if eq_idx == -1:
            raise ValueError(f"Malformed `{token}` assignment in {path}")
        start = eq_idx + 1
        if key == "win_rates":
            end = text.find(",\nupdate_time", start)
            if end == -1:
                end = text.find(";\nupdate_time", start)
        else:
            end = text.find(",\n", start)
        if end == -1:
            raise ValueError(f"Unable to terminate `{token}` value in {path}")
        parts[key] = json.loads(text[start:end].strip())

    extract("heroes", "var heroes")
    extract("heroes_bg", "heroes_bg")
    extract("heroes_wr", "heroes_wr")
    extract("win_rates", "win_rates")

    idx = text.find("update_time")
    if idx == -1:
        raise ValueError("`update_time` missing from cs.json")
    start = text.find("=", idx) + 1
    end = text.find(";", start)
    parts["update_time"] = json.loads(text[start:end].strip())
    return parts


def normalize_hero_name(name: str) -> str:
    cleaned = (
        name.lower()
        .replace("'", "")
        .replace("-", " ")
        .replace(".", "")
    )
    tokens = cleaned.split()
    return " ".join(tokens)


def build_delta_matrix(win_rates: Sequence[Sequence[Optional[Sequence[str]]]]) -> List[List[Optional[float]]]:
    matrix: List[List[Optional[float]]] = []
    for row in win_rates:
        matrix_row: List[Optional[float]] = []
        for entry in row:
            if entry is None:
                matrix_row.append(None)
            else:
                matrix_row.append(float(entry[0]))
        matrix.append(matrix_row)
    return matrix


def hero_delta(hero_idx: int, opponent_indices: Sequence[int], delta_matrix: Sequence[Sequence[Optional[float]]]) -> float:
    total = 0.0
    for opp_idx in opponent_indices:
        value = delta_matrix[hero_idx][opp_idx]
        if value is None:
            continue
        total += value
    return total


def load_matches(
    path: Path,
    hero_to_index: Dict[str, int],
    delta_matrix: Sequence[Sequence[Optional[float]]],
    championship_filter: Optional[Sequence[str]] = None,
) -> List[Match]:
    with path.open(newline="") as f:
        reader = list(csv.DictReader(f))

    filter_set = (
        {championship.strip() for championship in championship_filter}
        if championship_filter
        else None
    )

    def sort_key(row: Dict[str, str]) -> Tuple:
        return (
            row.get("date", ""),
            row.get("championship", ""),
            int(row.get("series_id", 0) or 0),
            int(row.get("map_number", 0) or 0),
            int(row.get("hawk_match_id", 0) or 0),
        )

    reader.sort(key=sort_key)

    matches: List[Match] = []
    for row in reader:
        championship_name = row["championship"].strip()
        if filter_set and championship_name not in filter_set:
            continue

        team1_name = row["team1"].strip()
        team2_name = row["team2"].strip()

        try:
            team1_heroes = [hero_to_index[normalize_hero_name(h.strip())] for h in row["team1_heroes"].split("|")]
            team2_heroes = [hero_to_index[normalize_hero_name(h.strip())] for h in row["team2_heroes"].split("|")]
        except KeyError as exc:
            # Missing hero mapping – skip this match
            continue

        try:
            team1_odds = float(row["team1_odds"])
            team2_odds = float(row["team2_odds"])
        except ValueError:
            continue

        winner_raw = row["winner"].strip()
        if winner_raw == team1_name:
            winner = "team1"
        elif winner_raw == team2_name:
            winner = "team2"
        else:
            continue

        team1_hero_deltas = [
            hero_delta(hero_idx, team2_heroes, delta_matrix) for hero_idx in team1_heroes
        ]
        team2_hero_deltas = [
            hero_delta(hero_idx, team1_heroes, delta_matrix) for hero_idx in team2_heroes
        ]

        team1_delta = sum(team1_hero_deltas)
        match_delta = -team1_delta

        if abs(match_delta) < 1e-9:
            continue

        favored_team = "team1" if match_delta > 0 else "team2"
        favored_odds = team1_odds if favored_team == "team1" else team2_odds
        opponent_odds = team2_odds if favored_team == "team1" else team1_odds

        favored_is_underdog = favored_odds > opponent_odds
        favored_is_favorite = favored_odds < opponent_odds

        matches.append(
            Match(
                abs_delta=abs(match_delta),
                favored_team=favored_team,
                hero_deltas={"team1": team1_hero_deltas, "team2": team2_hero_deltas},
                favored_odds=favored_odds,
                opponent_odds=opponent_odds,
                favored_is_underdog=favored_is_underdog,
                favored_is_favorite=favored_is_favorite,
                winner=winner,
            )
        )

    return matches


def should_bet_on_match(
    match: Match,
    config: StrategyConfig,
    threshold: int,
) -> bool:
    if match.abs_delta < threshold:
        return False
    if config.odds_condition == "underdog" and not match.favored_is_underdog:
        return False
    if config.odds_condition == "favorite" and not match.favored_is_favorite:
        return False
    if config.hero_filter == "none":
        return True

    required = 4 if config.hero_filter == "4+4-" else 5
    favored_hero_deltas = match.hero_deltas[match.favored_team]
    qualifying = sum(1 for value in favored_hero_deltas if value <= -threshold)
    return qualifying >= required


def fibonacci_next(sequence: List[int]) -> int:
    sequence.append(sequence[-1] + sequence[-2])
    return sequence[-1]


def simulate_strategy(matches: Sequence[Match], config: StrategyConfig) -> List[List[object]]:
    rows: List[List[object]] = []

    for threshold in THRESHOLDS:
        bankroll = START_BANKROLL
        peak_bankroll = bankroll
        max_drawdown = 0.0
        max_stake = 0.0
        bets = 0
        wins = 0
        max_step = 0

        fib_sequence = [1, 1]
        fib_index = 0  # position in sequence (0-based)

        for match in matches:
            if bankroll <= 0:
                bankroll = 0.0
                break

            if not should_bet_on_match(match, config, threshold):
                continue

            if config.stake_type == "flat":
                desired_stake = config.stake_value
            elif config.stake_type == "percent":
                desired_stake = bankroll * config.stake_value
            elif config.stake_type == "fibonacci":
                desired_units = fib_sequence[fib_index]
                desired_stake = desired_units * config.stake_value
            else:
                raise ValueError(f"Unknown stake type: {config.stake_type}")

            stake = min(desired_stake, bankroll, MAX_BET)
            if stake <= 0:
                continue

            bets += 1
            max_stake = max(max_stake, stake)

            if config.stake_type == "fibonacci":
                max_step = max(max_step, fib_index + 1)

            bankroll -= stake

            bet_won = match.winner == match.favored_team

            if bet_won:
                bankroll += stake * match.favored_odds
                wins += 1
                if config.stake_type == "fibonacci":
                    fib_index = max(fib_index - 2, 0)
            else:
                if config.stake_type == "fibonacci":
                    fib_index += 1
                    if fib_index >= len(fib_sequence):
                        fibonacci_next(fib_sequence)

            peak_bankroll = max(peak_bankroll, bankroll)
            max_drawdown = max(max_drawdown, peak_bankroll - bankroll)

        win_pct = round((wins / bets) * 100) if bets else 0

        rows.append(
            [
                config.strategy_group,
                config.hero_filter,
                config.odds_condition,
                threshold,
                bets,
                wins,
                win_pct,
                int(round(bankroll)),
                int(round(max_drawdown)),
                int(round(max_stake)),
                max_step if config.stake_type == "fibonacci" else 0,
            ]
        )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate betting strategies on Hawk dataset.")
    parser.add_argument("--cs", type=Path, default=CS_PATH, help="Path to cs.json (default: cs.json)")
    parser.add_argument(
        "--matches",
        type=Path,
        default=MATCHES_PATH,
        help="Path to hawk match CSV (default: hawk_matches_merged.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Destination CSV path (default: strategy_results_hawk_cs.csv)",
    )
    parser.add_argument(
        "--championship",
        action="append",
        help="Filter to specific championship (can be provided multiple times).",
    )
    args = parser.parse_args()

    cs_data = parse_cs(args.cs)
    heroes: List[str] = cs_data["heroes"]  # type: ignore[assignment]
    win_rates = cs_data["win_rates"]  # type: ignore[assignment]

    hero_to_index = {normalize_hero_name(name): idx for idx, name in enumerate(heroes)}
    delta_matrix = build_delta_matrix(win_rates)  # type: ignore[arg-type]

    matches = load_matches(
        args.matches,
        hero_to_index,
        delta_matrix,
        championship_filter=args.championship,
    )

    strategy_configs: List[StrategyConfig] = [
        StrategyConfig("Flat100", "none", "any", "flat", 100.0),
        StrategyConfig("Flat100", "none", "underdog", "flat", 100.0),
        StrategyConfig("Flat100", "none", "favorite", "flat", 100.0),
        StrategyConfig("Pct5", "none", "any", "percent", 0.05),
        StrategyConfig("Pct5", "none", "underdog", "percent", 0.05),
        StrategyConfig("Pct5", "none", "favorite", "percent", 0.05),
        StrategyConfig("Flat100", "4+4-", "any", "flat", 100.0),
        StrategyConfig("Flat100", "4+4-", "underdog", "flat", 100.0),
        StrategyConfig("Flat100", "4+4-", "favorite", "flat", 100.0),
        StrategyConfig("Pct5", "4+4-", "any", "percent", 0.05),
        StrategyConfig("Pct5", "4+4-", "underdog", "percent", 0.05),
        StrategyConfig("Pct5", "4+4-", "favorite", "percent", 0.05),
        StrategyConfig("Flat100", "5+5-", "any", "flat", 100.0),
        StrategyConfig("Flat100", "5+5-", "underdog", "flat", 100.0),
        StrategyConfig("Flat100", "5+5-", "favorite", "flat", 100.0),
        StrategyConfig("Pct5", "5+5-", "any", "percent", 0.05),
        StrategyConfig("Pct5", "5+5-", "underdog", "percent", 0.05),
        StrategyConfig("Pct5", "5+5-", "favorite", "percent", 0.05),
        StrategyConfig("Fib1", "none", "any", "fibonacci", 1.0),
        StrategyConfig("Fib1", "none", "underdog", "fibonacci", 1.0),
        StrategyConfig("Fib1", "none", "favorite", "fibonacci", 1.0),
        StrategyConfig("Fib1", "4+4-", "any", "fibonacci", 1.0),
        StrategyConfig("Fib1", "4+4-", "underdog", "fibonacci", 1.0),
        StrategyConfig("Fib1", "4+4-", "favorite", "fibonacci", 1.0),
        StrategyConfig("Fib1", "5+5-", "any", "fibonacci", 1.0),
        StrategyConfig("Fib1", "5+5-", "underdog", "fibonacci", 1.0),
        StrategyConfig("Fib1", "5+5-", "favorite", "fibonacci", 1.0),
        StrategyConfig("Fib5", "none", "any", "fibonacci", 5.0),
        StrategyConfig("Fib5", "none", "underdog", "fibonacci", 5.0),
        StrategyConfig("Fib5", "none", "favorite", "fibonacci", 5.0),
        StrategyConfig("Fib5", "4+4-", "any", "fibonacci", 5.0),
        StrategyConfig("Fib5", "4+4-", "underdog", "fibonacci", 5.0),
        StrategyConfig("Fib5", "4+4-", "favorite", "fibonacci", 5.0),
        StrategyConfig("Fib5", "5+5-", "any", "fibonacci", 5.0),
        StrategyConfig("Fib5", "5+5-", "underdog", "fibonacci", 5.0),
        StrategyConfig("Fib5", "5+5-", "favorite", "fibonacci", 5.0),
    ]

    header = [
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

    with args.output.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for config in strategy_configs:
            rows = simulate_strategy(matches, config)
            writer.writerows(rows)

    print(f"Wrote strategy results to {args.output}")


if __name__ == "__main__":
    main()
