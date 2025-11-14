#!/usr/bin/env python3
"""
Generate a Dotabuff-style hero matchup matrix from filtered Stratz match data.

The output mirrors the structure of `cs_original.json`, using the hero ordering
defined in `hero_id_map.json` and the hero metadata (names/background URLs)
from the existing matrix file.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT = Path(__file__).parent
STRATZ_PATH = ROOT / "stratz_with_tiers_filtered.json"
HERO_MAP_PATH = ROOT / "hero_id_map.json"
CS_ORIGINAL_PATH = ROOT / "cs_original.json"
OUTPUT_PATH = ROOT / "cs_stratz.json"


def load_stratz_matches() -> Dict[str, Any]:
    return json.loads(STRATZ_PATH.read_text())


def load_hero_order() -> List[int]:
    hero_map_raw = json.loads(HERO_MAP_PATH.read_text())
    hero_index_map = {int(hero_id): int(index) for hero_id, index in hero_map_raw.items()}
    # Sort hero IDs by their target column index
    return [hero_id for hero_id, _ in sorted(hero_index_map.items(), key=lambda item: item[1])]


def extract_js_array(content: str, current_var: str, next_var: str) -> List[Any]:
    """
    Extract a JavaScript array literal that is defined as `current_var = [...]`
    and followed by `next_var`.
    """
    pattern = rf"{current_var}\s*=\s*(\[[\s\S]*?\]),\s*{next_var}"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        raise ValueError(f"Failed to locate array for {current_var!r}")
    return json.loads(match.group(1))


def load_hero_metadata(hero_ids: Iterable[int]) -> tuple[List[str], List[str]]:
    content = CS_ORIGINAL_PATH.read_text()
    hero_names = extract_js_array(content, r"var heroes", r"heroes_bg")
    hero_backgrounds = extract_js_array(content, r"heroes_bg", r"heroes_wr")

    hero_ids_list = list(hero_ids)
    if len(hero_names) != len(hero_ids_list) or len(hero_backgrounds) != len(hero_ids_list):
        raise ValueError("Hero metadata length does not match hero ordering")

    return hero_names, hero_backgrounds


def format_matrix(
    hero_ids_sorted: List[int],
    hero_names: List[str],
    hero_backgrounds: List[str],
    hero_totals: Dict[int, Dict[str, float]],
    hero_vs: Dict[int, Dict[int, Dict[str, float]]],
) -> str:
    heroes_wr: List[str] = []
    win_rates: List[List[Any]] = []

    for idx, hero_id in enumerate(hero_ids_sorted):
        totals = hero_totals.get(hero_id, {"matches": 0, "wins": 0})
        matches_total = totals["matches"]
        wins_total = totals["wins"]
        overall_wr = (wins_total / matches_total * 100) if matches_total else 50.0
        heroes_wr.append(f"{overall_wr:.2f}")

        row: List[Any] = []
        opponents = hero_vs.get(hero_id, {})
        for other_id in hero_ids_sorted:
            if hero_id == other_id:
                row.append(None)
                continue

            matchup = opponents.get(other_id)
            matches = matchup["matches"] if matchup else 0
            wins = matchup["wins"] if matchup else 0
            win_rate = wins / matches if matches else 0.0
            delta = (0.5 - win_rate) * 100

            row.append([f"{delta:.4f}", f"{win_rate * 100:.4f}", matches])

        win_rates.append(row)

    payload_lines = [
        "var heroes = " + json.dumps(hero_names, separators=(",", ":")) + ",",
        "heroes_bg = " + json.dumps(hero_backgrounds, separators=(",", ":")) + ",",
        "heroes_wr = " + json.dumps(heroes_wr, separators=(",", ":")) + ",",
        "win_rates = " + json.dumps(win_rates, separators=(",", ":")) + ",",
        f'update_time = "{date.today().isoformat()}";',
        "",
    ]

    return "\n".join(payload_lines)


def build_statistics(matches: Dict[str, Any]) -> tuple[
    Dict[int, Dict[str, float]], Dict[int, Dict[int, Dict[str, float]]]
]:
    hero_totals: Dict[int, Dict[str, float]] = defaultdict(lambda: {"matches": 0, "wins": 0})
    hero_vs: Dict[int, Dict[int, Dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"matches": 0, "wins": 0})
    )

    for match in matches.values():
        radiant = [entry["heroId"] for entry in match["radiantRoles"]]
        dire = [entry["heroId"] for entry in match["direRoles"]]
        radiant_win = match["radiantWin"]

        for hero_id in radiant:
            totals = hero_totals[hero_id]
            totals["matches"] += 1
            if radiant_win:
                totals["wins"] += 1

            for opponent_id in dire:
                matchup = hero_vs[hero_id][opponent_id]
                matchup["matches"] += 1
                if radiant_win:
                    matchup["wins"] += 1

        for hero_id in dire:
            totals = hero_totals[hero_id]
            totals["matches"] += 1
            if not radiant_win:
                totals["wins"] += 1

            for opponent_id in radiant:
                matchup = hero_vs[hero_id][opponent_id]
                matchup["matches"] += 1
                if not radiant_win:
                    matchup["wins"] += 1

    # Convert nested defaultdicts to plain dicts for predictable iteration
    hero_totals_plain = {hero_id: dict(stats) for hero_id, stats in hero_totals.items()}
    hero_vs_plain = {
        hero_id: {opponent_id: dict(stats) for opponent_id, stats in opponents.items()}
        for hero_id, opponents in hero_vs.items()
    }

    return hero_totals_plain, hero_vs_plain


def main() -> None:
    matches = load_stratz_matches()
    hero_ids_sorted = load_hero_order()
    hero_names, hero_backgrounds = load_hero_metadata(hero_ids_sorted)

    hero_totals, hero_vs = build_statistics(matches)
    payload = format_matrix(
        hero_ids_sorted=hero_ids_sorted,
        hero_names=hero_names,
        hero_backgrounds=hero_backgrounds,
        hero_totals=hero_totals,
        hero_vs=hero_vs,
    )

    OUTPUT_PATH.write_text(payload)
    print(f"Wrote Stratz counter matrix to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

