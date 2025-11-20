#!/usr/bin/env python3
"""
Build a cs.json-style matrix enriched with hero performance metrics.

The script ingests:
  * The open-dota detailed match dump (JSON array, potentially huge)
  * hero_id_map.json to align hero IDs with the ordering used in cs.json
  * derived/hero_summary.json (produced by extract_hero_match_stats.py)
  * An existing cs.json to reuse the hero ordering and hero background images

Outputs a new cs.json (or a file of your choosing) that defines:
  - var heroes / heroes_bg
  - var heroes_wr (overall win rates from the new sample)
  - var win_rates (pairwise matchup deltas derived from the sample)
  - Additional arrays such as heroes_gpm, heroes_xpm, etc.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ijson

DEFAULT_TEMPLATE = "cs.json"
DEFAULT_MATCHES = "opendota_pro_matches_3months_detailed_20251118_173427.json"
DEFAULT_HERO_SUMMARY = "derived/hero_summary.json"
DEFAULT_OUTPUT = "cs.json"
HERO_ID_MAP = "hero_id_map.json"

METRIC_DEFS = [
    ("heroes_gpm", "gold_per_min", 0),
    ("heroes_xpm", "xp_per_min", 0),
    ("heroes_hero_damage", "hero_damage", 0),
    ("heroes_tower_damage", "tower_damage", 0),
    ("heroes_damage_taken", "damage_taken_total", 0),
    ("heroes_match_duration", "duration", 1, lambda v: v / 60.0),  # seconds -> minutes
    ("heroes_teamfight_participation", "teamfight_participation", 3),
    ("heroes_stuns", "stuns", 2),
    ("heroes_lane_efficiency", "lane_efficiency", 3),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build cs.json-style matrix with extra hero metrics.")
    parser.add_argument("--template", default=DEFAULT_TEMPLATE, help="Existing cs.json to copy hero ordering from.")
    parser.add_argument("--matches", default=DEFAULT_MATCHES, help="OpenDota match JSON (array).")
    parser.add_argument("--hero-summary", default=DEFAULT_HERO_SUMMARY, help="Hero summary JSON path.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Destination file for the generated matrix.")
    parser.add_argument("--progress-every", type=int, default=500, help="Progress log frequency.")
    return parser.parse_args()


def extract_array(text: str, var_name: str) -> List:
    pattern = rf"(?:var\s+)?{var_name}\s*=\s*(\[.*?\])(?:;|,)"
    match = re.search(pattern, text, re.S)
    if not match:
        raise RuntimeError(f"Unable to locate `{var_name}` array in template.")
    return ast.literal_eval(match.group(1))


def load_template_assets(path: Path) -> Tuple[List[str], List[str]]:
    text = path.read_text()
    heroes = extract_array(text, "heroes")
    heroes_bg = extract_array(text, "heroes_bg")
    return heroes, heroes_bg


def load_hero_id_map(path: Path, hero_count: int) -> Tuple[Dict[int, int], List[Optional[int]]]:
    mapping = json.loads(path.read_text())
    hero_id_to_idx: Dict[int, int] = {}
    idx_to_hero_id: List[Optional[int]] = [None] * hero_count
    for hero_id_str, idx in mapping.items():
        hero_id = int(hero_id_str)
        hero_id_to_idx[hero_id] = idx
        if 0 <= idx < hero_count:
            idx_to_hero_id[idx] = hero_id
    return hero_id_to_idx, idx_to_hero_id


def load_hero_summary(path: Path) -> Dict[int, dict]:
    data = json.loads(path.read_text())
    return {int(entry["hero_id"]): entry for entry in data}


def build_metric_array(
    idx_to_hero_id: List[Optional[int]],
    hero_summary: Dict[int, dict],
    metric_key: str,
    round_digits: Optional[int] = None,
    transform=None,
) -> List[Optional[float]]:
    values: List[Optional[float]] = []
    for hero_id in idx_to_hero_id:
        if hero_id is None:
            values.append(None)
            continue
        entry = hero_summary.get(hero_id)
        metric = (entry or {}).get("metrics", {}).get(metric_key)
        val = None if metric is None else metric.get("avg")
        if val is None:
            values.append(None)
            continue
        if transform:
            val = transform(val)
        if round_digits is not None and val is not None:
            val = round(val, round_digits)
        values.append(val)
    return values


def build_matchup_matrix(
    matches_path: Path,
    hero_id_to_idx: Dict[int, int],
    hero_count: int,
    progress_every: int,
) -> Tuple[List[List[Optional[List]]], List[str]]:
    wins = [[0] * hero_count for _ in range(hero_count)]
    totals = [[0] * hero_count for _ in range(hero_count)]
    hero_wins = [0] * hero_count
    hero_total = [0] * hero_count

    processed = 0
    with matches_path.open("rb") as source:
        for match in ijson.items(source, "item"):
            processed += 1
            radiant = []
            dire = []
            for player in match.get("players", []):
                hero_id = player.get("hero_id")
                idx = hero_id_to_idx.get(hero_id)
                if idx is None or idx >= hero_count:
                    continue
                hero_total[idx] += 1
                if player.get("win"):
                    hero_wins[idx] += 1
                if player.get("isRadiant"):
                    radiant.append(idx)
                else:
                    dire.append(idx)

            if not radiant or not dire:
                continue

            radiant_win = bool(match.get("radiant_win"))
            for rad in radiant:
                for dr in dire:
                    totals[rad][dr] += 1
                    totals[dr][rad] += 1
                    if radiant_win:
                        wins[rad][dr] += 1
                    else:
                        wins[dr][rad] += 1

            if progress_every and processed % progress_every == 0:
                print(f"Processed {processed:,} matches...")

    win_rates: List[List[Optional[List]]] = []
    heroes_wr: List[str] = []

    for hero_idx in range(hero_count):
        if hero_total[hero_idx]:
            wr = hero_wins[hero_idx] / hero_total[hero_idx] * 100.0
        else:
            wr = 50.0
        heroes_wr.append(f"{wr:.2f}")

    for i in range(hero_count):
        row: List[Optional[List]] = []
        for j in range(hero_count):
            if i == j or totals[i][j] == 0:
                row.append(None)
                continue
            wr = wins[i][j] / totals[i][j] * 100.0
            adv = wr - 50.0
            adv = 0.0 if abs(adv) < 1e-9 else adv
            row.append([f"{adv:.4f}", f"{wr:.4f}", totals[i][j]])
        win_rates.append(row)

    return win_rates, heroes_wr


def main() -> None:
    args = parse_args()
    template_path = Path(args.template)
    matches_path = Path(args.matches)
    output_path = Path(args.output)
    hero_summary_path = Path(args.hero_summary)
    hero_map_path = Path(HERO_ID_MAP)

    heroes, heroes_bg = load_template_assets(template_path)
    hero_count = len(heroes)

    hero_id_to_idx, idx_to_hero_id = load_hero_id_map(hero_map_path, hero_count)

    hero_summary = load_hero_summary(hero_summary_path)
    print(f"Loaded template with {hero_count} heroes.")

    win_rates, heroes_wr = build_matchup_matrix(
        matches_path=matches_path,
        hero_id_to_idx=hero_id_to_idx,
        hero_count=hero_count,
        progress_every=args.progress_every,
    )

    metric_arrays = {}
    for definition in METRIC_DEFS:
        if len(definition) == 3:
            var_name, metric_key, round_digits = definition
            transform = None
        else:
            var_name, metric_key, round_digits, transform = definition
        metric_arrays[var_name] = build_metric_array(
            idx_to_hero_id, hero_summary, metric_key, round_digits, transform
        )

    update_time = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def dump(var_name: str, value) -> str:
        return f"var {var_name} = {json.dumps(value, separators=(',', ':'))};"

    sections = [
        dump("heroes", heroes),
        dump("heroes_bg", heroes_bg),
        dump("heroes_wr", heroes_wr),
    ]
    for var_name, values in metric_arrays.items():
        sections.append(dump(var_name, values))
    sections.append(dump("win_rates", win_rates))
    sections.append(f'var update_time = "{update_time}";')

    output_path.write_text("\n".join(sections))
    print(f"Wrote extended matrix to {output_path}")


if __name__ == "__main__":
    main()
