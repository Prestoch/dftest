#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

START_BANK = 1000.0
MAX_BET = 10000.0

THRESHOLDS: Sequence[int] = (
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

STRATEGY_GROUPS = ("Flat100", "Pct5", "Fib1", "Fib5")
HERO_FILTERS = ("none", "4+4-", "5+5-")
ODDS_CONDITIONS = ("any", "underdog", "favorite")

OUTPUT_PATH = Path("strategy_results_latest.csv")
CS_PATH = Path("cs.json")
MATCHES_PATH = Path("hawk_matches_merged.csv")


def normalize_name(raw: str) -> str:
    lowered = raw.lower().replace("'", "")
    return re.sub(r"[\s\-]+", " ", lowered).strip()


def extract_array(text: str, label: str):
    marker = f"{label} ="
    try:
        idx = text.index(marker) + len(marker)
    except ValueError as exc:
        raise ValueError(f"Could not find marker for {label}") from exc

    while idx < len(text) and text[idx] != "[":
        idx += 1
    start = idx

    depth = 0
    for pos in range(start, len(text)):
        char = text[pos]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                end = pos + 1
                break
    else:
        raise ValueError(f"Unbalanced brackets while parsing {label}")

    return json.loads(text[start:end])


def load_cs(path: Path):
    text = path.read_text(encoding="utf-8")
    heroes = extract_array(text, "var heroes")
    heroes_wr_raw = extract_array(text, "heroes_wr")
    win_rates_raw = extract_array(text, "win_rates")

    heroes_wr = [
        float(value) if value is not None else 50.0 for value in heroes_wr_raw
    ]
    win_delta: List[List[Optional[float]]] = []
    for row in win_rates_raw:
        win_delta.append(
            [None if cell is None else float(cell[0]) for cell in row]
        )

    hero_index = {normalize_name(hero): idx for idx, hero in enumerate(heroes)}
    return heroes_wr, win_delta, hero_index


def parse_odds(raw: str) -> Optional[float]:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def hero_advantage(
    hero_idx: int, opponent_indices: Sequence[int], win_delta: Sequence[Sequence[Optional[float]]]
) -> float:
    total = 0.0
    for opp_idx in opponent_indices:
        cell = win_delta[opp_idx][hero_idx]
        if cell is not None:
            total += cell
    return total


def compute_matches(
    path: Path,
    heroes_wr: Sequence[float],
    win_delta: Sequence[Sequence[Optional[float]]],
    hero_index: dict[str, int],
    championship_filter: Optional[set[str]] = None,
):
    matches = []
    missing_heroes: set[str] = set()

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if championship_filter and row["championship"] not in championship_filter:
                continue

            team1_heroes = [name.strip() for name in row["team1_heroes"].split("|")]
            team2_heroes = [name.strip() for name in row["team2_heroes"].split("|")]

            try:
                team1_indices = [hero_index[normalize_name(name)] for name in team1_heroes]
                team2_indices = [hero_index[normalize_name(name)] for name in team2_heroes]
            except KeyError as exc:
                missing_heroes.add(str(exc))
                continue

            team1_adv = [
                hero_advantage(idx, team2_indices, win_delta) for idx in team1_indices
            ]
            team2_adv = [
                hero_advantage(idx, team1_indices, win_delta) for idx in team2_indices
            ]

            team1_total = sum(
                heroes_wr[idx] + adv for idx, adv in zip(team1_indices, team1_adv)
            )
            team2_total = sum(
                heroes_wr[idx] + adv for idx, adv in zip(team2_indices, team2_adv)
            )
            delta = team1_total - team2_total

            if delta > 0:
                favored_team = row["team1"]
                favored_is_team1 = True
                fav_adv = team1_adv
                opp_adv = team2_adv
            elif delta < 0:
                favored_team = row["team2"]
                favored_is_team1 = False
                fav_adv = team2_adv
                opp_adv = team1_adv
            else:
                favored_team = None
                favored_is_team1 = None
                fav_adv = None
                opp_adv = None

            team1_odds = parse_odds(row["team1_odds"])
            team2_odds = parse_odds(row["team2_odds"])

            if favored_is_team1 is True:
                favored_odds = team1_odds
                opponent_odds = team2_odds
            elif favored_is_team1 is False:
                favored_odds = team2_odds
                opponent_odds = team1_odds
            else:
                favored_odds = None
                opponent_odds = None

            if favored_team is None or favored_odds is None or opponent_odds is None:
                fav_is_favorite = None
                fav_is_underdog = None
                bettable = False
            else:
                fav_is_favorite = favored_odds < opponent_odds
                fav_is_underdog = favored_odds > opponent_odds
                bettable = True

            bet_win = row["winner"] == favored_team if favored_team else False

            fav_pos_count = (
                sum(1 for adv in fav_adv if adv >= 0) if fav_adv is not None else 0
            )
            opp_neg_count = (
                sum(1 for adv in opp_adv if adv <= 0) if opp_adv is not None else 0
            )

            match = {
                "date": datetime.strptime(row["date"], "%Y-%m-%d"),
                "series_id": int(row["series_id"]) if row["series_id"] else 0,
                "map_number": int(row["map_number"]) if row["map_number"] else 0,
                "hawk_match_id": int(row["hawk_match_id"]) if row["hawk_match_id"] else 0,
                "abs_delta": abs(delta),
                "delta": delta,
                "favored_team": favored_team,
                "favored_is_team1": favored_is_team1,
                "favored_odds": favored_odds,
                "opponent_odds": opponent_odds,
                "bet_win": bet_win,
                "fav_pos_count": fav_pos_count,
                "opp_neg_count": opp_neg_count,
                "fav_is_favorite": fav_is_favorite,
                "fav_is_underdog": fav_is_underdog,
                "bettable": bettable,
            }
            matches.append(match)

    if missing_heroes:
        raise ValueError(f"Missing hero mappings for: {sorted(missing_heroes)}")

    matches.sort(
        key=lambda m: (m["date"], m["series_id"], m["map_number"], m["hawk_match_id"])
    )
    return matches


@dataclass(frozen=True)
class StrategyConfig:
    strategy_group: str
    hero_filter: str
    odds_condition: str
    delta_threshold: int


def evaluate_strategy(matches: Sequence[dict], config: StrategyConfig):
    bank = START_BANK
    peak = bank
    max_drawdown = 0.0
    max_stake = 0.0
    bets = 0
    wins = 0
    max_step_reached = 0

    fib_index = 0
    fib_sequence = [1.0, 1.0]

    for match in matches:
        if bank <= 0:
            break

        if not match["bettable"]:
            continue
        if match["abs_delta"] < config.delta_threshold:
            continue

        if config.hero_filter == "4+4-":
            if match["fav_pos_count"] < 4 or match["opp_neg_count"] < 4:
                continue
        elif config.hero_filter == "5+5-":
            if match["fav_pos_count"] < 5 or match["opp_neg_count"] < 5:
                continue

        if config.odds_condition == "favorite":
            if match["fav_is_favorite"] is not True:
                continue
        elif config.odds_condition == "underdog":
            if match["fav_is_underdog"] is not True:
                continue

        if config.strategy_group == "Flat100":
            base_stake = 100.0
        elif config.strategy_group == "Pct5":
            base_stake = bank * 0.05
        elif config.strategy_group in ("Fib1", "Fib5"):
            unit = 1.0 if config.strategy_group == "Fib1" else 5.0
            while len(fib_sequence) <= fib_index:
                fib_sequence.append(fib_sequence[-1] + fib_sequence[-2])
            base_stake = fib_sequence[fib_index] * unit
        else:
            raise ValueError(f"Unknown strategy group {config.strategy_group}")

        stake = min(base_stake, bank, MAX_BET)
        if stake <= 0:
            continue

        bets += 1
        bank -= stake

        if config.strategy_group in ("Fib1", "Fib5"):
            max_step_reached = max(max_step_reached, fib_index)

        if match["bet_win"]:
            wins += 1
            payout = stake * match["favored_odds"]
            bank += payout
            if config.strategy_group in ("Fib1", "Fib5"):
                fib_index = max(fib_index - 2, 0)
        else:
            if config.strategy_group in ("Fib1", "Fib5"):
                fib_index += 1
                max_step_reached = max(max_step_reached, fib_index)

        max_stake = max(max_stake, stake)

        if bank > peak:
            peak = bank
        drawdown = peak - bank
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    final_bank = bank if bank > 0 else 0.0
    win_pct = int(round((wins / bets) * 100)) if bets else 0

    return {
        "strategy_group": config.strategy_group,
        "hero_filter": config.hero_filter,
        "odds_condition": config.odds_condition,
        "delta_threshold": config.delta_threshold,
        "bets": int(bets),
        "wins": int(wins),
        "win_pct": win_pct,
        "final_bank": int(round(final_bank)),
        "max_drawdown": int(round(max_drawdown)),
        "max_stake": int(round(max_stake)),
        "max_step": int(max_step_reached if config.strategy_group in ("Fib1", "Fib5") else 0),
    }


def main():
    parser = argparse.ArgumentParser(description="Compute betting strategy results.")
    parser.add_argument(
        "--championship",
        action="append",
        dest="championships",
        help="Restrict to specific championship (repeatable).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help=f"Output CSV path (default: {OUTPUT_PATH})",
    )
    args = parser.parse_args()

    championship_filter = (
        set(args.championships) if args.championships else None
    )

    heroes_wr, win_delta, hero_index = load_cs(CS_PATH)
    matches = compute_matches(
        MATCHES_PATH, heroes_wr, win_delta, hero_index, championship_filter
    )

    configs = [
        StrategyConfig(group, hero_filter, odds_condition, threshold)
        for group in STRATEGY_GROUPS
        for hero_filter in HERO_FILTERS
        for odds_condition in ODDS_CONDITIONS
        for threshold in THRESHOLDS
    ]

    results = [evaluate_strategy(matches, config) for config in configs]

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

    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    filter_msg = (
        f" for championships {sorted(championship_filter)}"
        if championship_filter
        else ""
    )
    print(
        f"Wrote {len(results)} rows to {args.output}{filter_msg}"
    )


if __name__ == "__main__":
    main()
