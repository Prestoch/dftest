#!/usr/bin/env python3
"""
Generate a Dotabuff Counter Picker compatible `cs.json` file from the
`protracker_matchups.json` payload produced by `d2ptmatchup.py`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import json


PROTRACKER_PATH = Path("protracker_matchups.json")
HERO_ID_MAP_PATH = Path("hero_id_map.json")
OUTPUT_PATH = Path("cs.json")


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    with path.open() as f:
        return json.load(f)


def normalize_name(raw_name: str) -> str:
    cleaned = raw_name.replace("-", " ").replace("'", "")
    words = cleaned.split()
    return " ".join(word.capitalize() for word in words)


def slugify(display_name: str) -> str:
    return display_name.lower().replace(" ", "-")


def build_matrix_payload(
    protracker: dict,
    hero_id_map: dict[int, int],
) -> tuple[list[str], list[str], list[str], list[list[object]]]:
    hero_names = {int(k): v for k, v in protracker["hero_map"].items()}
    matrix_raw = {
        int(hero_id): {int(other_id): values for other_id, values in opponents.items()}
        for hero_id, opponents in protracker["matrix"].items()
    }

    hero_ids_sorted = [
        hero_id for hero_id, _ in sorted(hero_id_map.items(), key=lambda item: item[1])
    ]

    size = len(hero_ids_sorted)

    heroes: list[str] = []
    heroes_bg: list[str] = []
    heroes_wr: list[str] = []
    win_rates: list[list[object]] = []

    for hero_id in hero_ids_sorted:
        display_name = normalize_name(hero_names[hero_id])
        heroes.append(display_name)
        heroes_bg.append(
            f"https://www.dotabuff.com/assets/heroes/{slugify(display_name)}.jpg"
        )

    for hero_id in hero_ids_sorted:
        row: list[object] = []
        total_matches = 0
        total_wins = 0.0
        hero_row = matrix_raw.get(hero_id, {})

        for other_id in hero_ids_sorted:
            if hero_id == other_id:
                row.append(None)
                continue

            matchup = hero_row.get(other_id)
            if matchup is None:
                inverse = matrix_raw.get(other_id, {}).get(hero_id)
                if inverse is None:
                    win_rate = 0.0
                    matches = 0
                else:
                    win_rate = 1.0 - inverse["win_rate"]
                    matches = inverse["matches"]
            else:
                win_rate = matchup["win_rate"]
                matches = matchup["matches"]

            if matches:
                total_matches += matches
                total_wins += win_rate * matches

            delta = (0.5 - win_rate) * 100
            row.append([f"{delta:.4f}", f"{win_rate * 100:.4f}", matches])

        if total_matches:
            overall_wr = (total_wins / total_matches) * 100
        else:
            overall_wr = 50.0

        heroes_wr.append(f"{overall_wr:.2f}")
        win_rates.append(row)

    return heroes, heroes_bg, heroes_wr, win_rates


def main() -> None:
    protracker = load_json(PROTRACKER_PATH)
    hero_id_map_raw = load_json(HERO_ID_MAP_PATH)
    hero_id_map = {int(hero_id): index for hero_id, index in hero_id_map_raw.items()}

    heroes, heroes_bg, heroes_wr, win_rates = build_matrix_payload(
        protracker, hero_id_map
    )

    payload_lines = [
        "var heroes = "
        + json.dumps(heroes, separators=(",", ":"))
        + ",",
        "heroes_bg = "
        + json.dumps(heroes_bg, separators=(",", ":"))
        + ",",
        "heroes_wr = "
        + json.dumps(heroes_wr, separators=(",", ":"))
        + ",",
        "win_rates = "
        + json.dumps(win_rates, separators=(",", ":"))
        + ",",
        f'update_time = "{date.today().isoformat()}";',
        "",
    ]

    OUTPUT_PATH.write_text("\n".join(payload_lines))
    print(f"Wrote {len(heroes)} heroes to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
