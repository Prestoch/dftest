#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import math
import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

CS_TEST_PATH = Path("cs_test.json")
CS_FALLBACK_PATH = Path("cs.json")
D2PTMATCHUP_PATH = Path("d2ptmatchup.py")
OUTPUT_PATH = Path("cs_test_matrix.json")


def load_hero_index_map() -> Dict[int, int]:
    source = D2PTMATCHUP_PATH.read_text(encoding="utf-8")
    module = ast.parse(source)
    for node in module.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "HERO_INDEX_MAP"
        ):
            return ast.literal_eval(node.value)
    raise ValueError("HERO_INDEX_MAP not found in d2ptmatchup.py")


def slugify(name: str) -> str:
    slug = name.lower()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def format_float(value: float, decimals: int) -> str:
    fmt = f"{{:.{decimals}f}}"
    return fmt.format(value)


def load_fallback_names(hero_index_map: Dict[int, int]) -> Dict[int, str]:
    if not CS_FALLBACK_PATH.exists():
        return {}
    text = CS_FALLBACK_PATH.read_text(encoding="utf-8")
    marker = "var heroes = "
    if marker not in text:
        return {}
    start = text.index(marker) + len(marker)
    while start < len(text) and text[start] != "[":
        start += 1
    depth = 0
    for idx in range(start, len(text)):
        ch = text[idx]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = idx + 1
                break
    else:
        return {}
    try:
        heroes = json.loads(text[start:end])
    except json.JSONDecodeError:
        return {}
    ordered_items = sorted(hero_index_map.items(), key=lambda kv: kv[1])
    return {
        hero_id: heroes[pos]
        for pos, (hero_id, _) in enumerate(ordered_items)
        if pos < len(heroes)
    }


def main() -> None:
    hero_index_map = load_hero_index_map()

    data = json.loads(CS_TEST_PATH.read_text(encoding="utf-8"))
    heroes_by_id: Dict[int, dict] = {hero["id"]: hero for hero in data}

    ordered_ids: List[int] = [
        hero_id for hero_id, _ in sorted(hero_index_map.items(), key=lambda item: item[1])
    ]

    fallback_names = load_fallback_names(hero_index_map)
    missing_ids = [hero_id for hero_id in ordered_ids if hero_id not in heroes_by_id]
    if missing_ids:
        print(
            "Warning: missing hero data in cs_test.json for IDs:",
            ", ".join(map(str, missing_ids)),
        )

    heroes: List[str] = []
    heroes_bg: List[str] = []
    heroes_wr: List[str] = []
    win_rates: List[List[Optional[List[object]]]] = []

    # Precompute matchup lookup per hero
    matchup_lookup: Dict[int, Dict[int, dict]] = {}
    for hero_id, hero in heroes_by_id.items():
        enemies = hero.get("rankAll", {}).get("ens", [])
        matchup_lookup[hero_id] = {entry["id"]: entry for entry in enemies}

    for hero_id in ordered_ids:
        hero = heroes_by_id.get(hero_id)
        if hero:
            display_name = hero["dName"]
            overall_wr = hero.get("rankAll", {}).get("wr", 50.0)
            if overall_wr is None or math.isnan(overall_wr):
                overall_wr = 50.0
        else:
            display_name = fallback_names.get(hero_id, f"Hero {hero_id}")
            overall_wr = 50.0

        heroes.append(display_name)
        heroes_bg.append(
            f"https://www.dotabuff.com/assets/heroes/{slugify(display_name)}.jpg"
        )

        heroes_wr.append(format_float(overall_wr, 2))

    for hero_id in ordered_ids:
        row: List[Optional[List[object]]] = []
        lookup = matchup_lookup.get(hero_id, {})
        for opponent_id in ordered_ids:
            if hero_id == opponent_id:
                row.append(None)
                continue

            entry = lookup.get(opponent_id)
            if entry is None:
                row.append(["0.0000", "50.0000", 0])
                continue

            wr = entry.get("wr", 50.0) or 50.0
            if math.isnan(wr):
                wr = 50.0
            delta = 50.0 - wr
            row.append(
                [
                    format_float(delta, 4),
                    format_float(wr, 4),
                    int(entry.get("m", 0) or 0),
                ]
            )
        win_rates.append(row)

    payload = "\n".join(
        [
            "var heroes = " + json.dumps(heroes, separators=(",", ":")) + ",",
            "heroes_bg = " + json.dumps(heroes_bg, separators=(",", ":")) + ",",
            "heroes_wr = " + json.dumps(heroes_wr, separators=(",", ":")) + ",",
            "win_rates = " + json.dumps(win_rates, separators=(",", ":")) + ",",
            f'update_time = "{date.today().isoformat()}";',
            "",
        ]
    )

    OUTPUT_PATH.write_text(payload, encoding="utf-8")
    print(f"Wrote matrix to {OUTPUT_PATH} with {len(ordered_ids)} heroes")


if __name__ == "__main__":
    main()
