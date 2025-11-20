#!/usr/bin/env python3
"""
Extract hero-level stats from a large OpenDota pro match dump.

Outputs:
1. A per-player CSV with curated match stats (GPM, XPM, damage, etc.).
2. A hero summary JSON aggregating averages/min/max/std for the same metrics.

This is intended to be the staging dataset for building future matchup matrices
similar to `cs.json`, while exposing additional performance signals.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import ijson

DEFAULT_INPUT = "opendota_pro_matches_3months_detailed_20251118_173427.json"
DEFAULT_CSV = "derived/hero_match_stats.csv"
DEFAULT_SUMMARY = "derived/hero_summary.json"
CS_FILE = "cs.json"
HERO_ID_MAP = "hero_id_map.json"

LANE_NAMES = {
    1: "Safe",
    2: "Mid",
    3: "Offlane",
    4: "Jungle",
    5: "Roam",
}

LANE_ROLE_NAMES = {
    1: "Safe Core",
    2: "Mid",
    3: "Offlane",
    4: "Support",
    5: "Roamer",
}

CSV_FIELDS: List[str] = [
    "match_id",
    "start_time",
    "duration",
    "league_id",
    "series_id",
    "series_type",
    "patch",
    "region",
    "radiant_win",
    "player_slot",
    "is_radiant",
    "win",
    "hero_id",
    "hero_name",
    "kills",
    "deaths",
    "assists",
    "kda",
    "gold_per_min",
    "xp_per_min",
    "net_worth",
    "total_gold",
    "total_xp",
    "hero_damage",
    "tower_damage",
    "hero_healing",
    "damage_taken_total",
    "last_hits",
    "denies",
    "gold",
    "gold_spent",
    "kills_per_min",
    "teamfight_participation",
    "stuns",
    "actions_per_min",
    "lane",
    "lane_name",
    "lane_role",
    "lane_role_name",
    "lane_efficiency",
    "lane_efficiency_pct",
    "neutral_kills",
    "tower_kills",
    "roshan_kills",
    "courier_kills",
    "camps_stacked",
    "creeps_stacked",
    "rune_pickups",
    "obs_placed",
    "sen_placed",
    "towers_killed",
    "roshans_killed",
]

# Metrics we aggregate per hero for the summary output.
AGGREGATED_FIELDS = [
    "kills",
    "deaths",
    "assists",
    "kda",
    "gold_per_min",
    "xp_per_min",
    "net_worth",
    "hero_damage",
    "tower_damage",
    "hero_healing",
    "damage_taken_total",
    "last_hits",
    "denies",
    "gold",
    "gold_spent",
    "kills_per_min",
    "teamfight_participation",
    "stuns",
    "actions_per_min",
    "lane_efficiency",
    "lane_efficiency_pct",
    "neutral_kills",
    "tower_kills",
    "roshan_kills",
    "courier_kills",
    "camps_stacked",
    "creeps_stacked",
    "rune_pickups",
    "obs_placed",
    "sen_placed",
    "towers_killed",
    "roshans_killed",
    "duration",
]


@dataclass
class MetricTracker:
    count: int = 0
    total: float = 0.0
    total_sq: float = 0.0
    min_val: Optional[float] = None
    max_val: Optional[float] = None

    def update(self, value: float) -> None:
        if value is None:
            return
        self.count += 1
        self.total += value
        self.total_sq += value * value
        self.min_val = value if self.min_val is None else min(self.min_val, value)
        self.max_val = value if self.max_val is None else max(self.max_val, value)

    def snapshot(self) -> Optional[dict]:
        if self.count == 0:
            return None
        mean = self.total / self.count
        variance = max(self.total_sq / self.count - mean * mean, 0.0)
        return {
            "avg": mean,
            "min": self.min_val,
            "max": self.max_val,
            "std": math.sqrt(variance),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract hero match stats and aggregate per-hero summaries."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to the OpenDota JSON dump.")
    parser.add_argument(
        "--match-stats-out",
        default=DEFAULT_CSV,
        help="Where to write the per-player CSV.",
    )
    parser.add_argument(
        "--hero-summary-out",
        default=DEFAULT_SUMMARY,
        help="Where to write the aggregated hero summary JSON.",
    )
    parser.add_argument(
        "--max-matches",
        type=int,
        help="Optional limit useful for quicker iterations/testing.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=200,
        help="Print a progress message every N matches processed.",
    )
    return parser.parse_args()


def coerce_number(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def read_hero_names(cs_path: Path, mapping_path: Path) -> Dict[int, str]:
    text = cs_path.read_text()
    match = re.search(r"var heroes = (\[.*?\]), heroes_bg", text, re.S)
    if not match:
        raise RuntimeError("Unable to locate hero list inside cs.json")
    heroes = ast.literal_eval(match.group(1))
    hero_id_map = json.loads(mapping_path.read_text())
    mapping = {}
    for hero_id_str, idx in hero_id_map.items():
        hero_id = int(hero_id_str)
        if idx < 0 or idx >= len(heroes):
            continue
        mapping[hero_id] = heroes[idx]
    return mapping


def init_metric_tracker() -> Dict[str, MetricTracker]:
    return {field: MetricTracker() for field in AGGREGATED_FIELDS}


def update_hero_summary(
    hero_stats: Dict[int, dict], hero_id: int, row: dict
) -> None:
    entry = hero_stats.setdefault(
        hero_id,
        {
            "matches": 0,
            "wins": 0,
            "metrics": init_metric_tracker(),
            "lane_counts": defaultdict(int),
            "lane_role_counts": defaultdict(int),
        },
    )
    entry["matches"] += 1
    if row["win"]:
        entry["wins"] += 1
    lane = row.get("lane")
    if isinstance(lane, int):
        entry["lane_counts"][lane] += 1
    lane_role = row.get("lane_role")
    if isinstance(lane_role, int):
        entry["lane_role_counts"][lane_role] += 1

    for field in AGGREGATED_FIELDS:
        value = row.get(field)
        if value is None:
            continue
        tracker = entry["metrics"][field]
        tracker.update(float(value))


def finalize_summary(hero_stats: Dict[int, dict], hero_name_map: Dict[int, str]) -> List[dict]:
    summary: List[dict] = []
    for hero_id, entry in hero_stats.items():
        hero_entry = {
            "hero_id": hero_id,
            "hero_name": hero_name_map.get(hero_id, f"hero_{hero_id}"),
            "matches": entry["matches"],
            "win_rate": entry["wins"] / entry["matches"] if entry["matches"] else None,
            "lanes": {
                LANE_NAMES.get(k, str(k)): v for k, v in sorted(entry["lane_counts"].items())
            },
            "lane_roles": {
                LANE_ROLE_NAMES.get(k, str(k)): v
                for k, v in sorted(entry["lane_role_counts"].items())
            },
            "metrics": {},
        }
        for field, tracker in entry["metrics"].items():
            snap = tracker.snapshot()
            if snap:
                hero_entry["metrics"][field] = snap
        summary.append(hero_entry)
    summary.sort(key=lambda item: item["hero_name"])
    return summary


def extract_rows(match: dict, hero_name_map: Dict[int, str]) -> Iterable[dict]:
    base = {
        "match_id": match.get("match_id"),
        "start_time": match.get("start_time"),
        "duration": match.get("duration"),
        "league_id": match.get("leagueid"),
        "series_id": match.get("series_id"),
        "series_type": match.get("series_type"),
        "patch": match.get("patch"),
        "region": match.get("region"),
        "radiant_win": match.get("radiant_win"),
    }
    for player in match.get("players", []):
        damage_taken = player.get("damage_taken")
        if isinstance(damage_taken, dict):
            damage_taken_total = sum(damage_taken.values())
        else:
            damage_taken_total = damage_taken
        row = dict(base)
        row.update(
            {
                "player_slot": player.get("player_slot"),
                "is_radiant": player.get("isRadiant"),
                "win": bool(player.get("win")),
                "hero_id": player.get("hero_id"),
                "hero_name": hero_name_map.get(player.get("hero_id"), "Unknown"),
                "kills": player.get("kills"),
                "deaths": player.get("deaths"),
                "assists": player.get("assists"),
                "kda": coerce_number(player.get("kda")),
                "gold_per_min": player.get("gold_per_min"),
                "xp_per_min": player.get("xp_per_min"),
                "net_worth": player.get("net_worth"),
                "total_gold": player.get("total_gold"),
                "total_xp": player.get("total_xp"),
                "hero_damage": player.get("hero_damage"),
                "tower_damage": player.get("tower_damage"),
                "hero_healing": player.get("hero_healing"),
                "damage_taken_total": damage_taken_total,
                "last_hits": player.get("last_hits"),
                "denies": player.get("denies"),
                "gold": player.get("gold"),
                "gold_spent": player.get("gold_spent"),
                "kills_per_min": coerce_number(player.get("kills_per_min")),
                "teamfight_participation": coerce_number(player.get("teamfight_participation")),
                "stuns": coerce_number(player.get("stuns")),
                "actions_per_min": player.get("actions_per_min"),
                "lane": player.get("lane"),
                "lane_name": LANE_NAMES.get(player.get("lane")),
                "lane_role": player.get("lane_role"),
                "lane_role_name": LANE_ROLE_NAMES.get(player.get("lane_role")),
                "lane_efficiency": coerce_number(player.get("lane_efficiency")),
                "lane_efficiency_pct": coerce_number(player.get("lane_efficiency_pct")),
                "neutral_kills": player.get("neutral_kills"),
                "tower_kills": player.get("tower_kills"),
                "roshan_kills": player.get("roshan_kills"),
                "courier_kills": player.get("courier_kills"),
                "camps_stacked": player.get("camps_stacked"),
                "creeps_stacked": player.get("creeps_stacked"),
                "rune_pickups": player.get("rune_pickups"),
                "obs_placed": player.get("obs_placed"),
                "sen_placed": player.get("sen_placed"),
                "towers_killed": player.get("towers_killed"),
                "roshans_killed": player.get("roshans_killed"),
            }
        )
        yield row


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    csv_path = Path(args.match_stats_out)
    summary_path = Path(args.hero_summary_out)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    hero_name_map = read_hero_names(Path(CS_FILE), Path(HERO_ID_MAP))
    hero_stats: Dict[int, dict] = {}
    matches_processed = 0
    players_written = 0

    with input_path.open("rb") as source, csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for match in ijson.items(source, "item"):
            matches_processed += 1
            for row in extract_rows(match, hero_name_map):
                writer.writerow(row)
                hero_id = row["hero_id"]
                if hero_id is not None:
                    update_hero_summary(hero_stats, hero_id, row)
                players_written += 1

            if args.progress_every and matches_processed % args.progress_every == 0:
                print(
                    f"Processed {matches_processed:,} matches "
                    f"({players_written:,} player-rows)..."
                )

            if args.max_matches and matches_processed >= args.max_matches:
                print("Reached max-matches cap; stopping early.")
                break

    summary = finalize_summary(hero_stats, hero_name_map)
    for hero_entry in summary:
        if hero_entry["win_rate"] is not None:
            hero_entry["win_rate"] = round(hero_entry["win_rate"], 4)
        for metric_values in hero_entry["metrics"].values():
            metric_values["avg"] = round(metric_values["avg"], 2)
            metric_values["std"] = round(metric_values["std"], 2)
            if metric_values["min"] is not None:
                metric_values["min"] = round(metric_values["min"], 2)
            if metric_values["max"] is not None:
                metric_values["max"] = round(metric_values["max"], 2)

    summary_path.write_text(json.dumps(summary, indent=2))
    print(
        f"Done. Matches: {matches_processed:,}, player rows: {players_written:,}. "
        f"CSV -> {csv_path}, summary -> {summary_path}"
    )


if __name__ == "__main__":
    main()
