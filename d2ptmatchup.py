#!/usr/bin/env python3
"""
Fetch hero matchup data from dota2protracker.com and emit a JSON matrix.

Requires cloudscraper (`pip install cloudscraper`) to bypass Cloudflare checks.
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

import cloudscraper


BASE_URL = "https://dota2protracker.com/api"
CS_OUTPUT_PATH = Path("cs.json")
REQUEST_DELAY_SECONDS = 0.35

HERO_INDEX_MAP: dict[int, int] = {
    1: 3,
    2: 5,
    3: 6,
    4: 9,
    5: 19,
    6: 28,
    7: 30,
    8: 43,
    9: 61,
    10: 63,
    11: 89,
    12: 76,
    13: 79,
    14: 80,
    15: 83,
    16: 87,
    17: 99,
    18: 100,
    19: 107,
    20: 114,
    21: 121,
    22: 125,
    23: 46,
    25: 51,
    26: 52,
    27: 90,
    28: 93,
    29: 104,
    30: 123,
    31: 49,
    32: 84,
    33: 34,
    34: 106,
    35: 96,
    36: 67,
    37: 119,
    38: 8,
    39: 82,
    40: 115,
    41: 35,
    42: 124,
    43: 24,
    44: 75,
    45: 81,
    46: 102,
    47: 116,
    48: 54,
    49: 27,
    50: 23,
    51: 18,
    52: 48,
    53: 66,
    54: 50,
    55: 20,
    56: 17,
    57: 71,
    58: 33,
    59: 39,
    60: 68,
    61: 13,
    62: 10,
    63: 120,
    64: 42,
    65: 7,
    66: 16,
    67: 97,
    68: 2,
    69: 26,
    70: 113,
    71: 98,
    72: 37,
    73: 1,
    74: 40,
    75: 91,
    76: 73,
    77: 55,
    78: 11,
    79: 88,
    80: 53,
    81: 15,
    82: 60,
    83: 108,
    84: 70,
    85: 112,
    86: 86,
    87: 25,
    88: 69,
    89: 65,
    90: 44,
    91: 41,
    92: 117,
    93: 94,
    94: 59,
    95: 109,
    96: 14,
    97: 56,
    98: 105,
    99: 12,
    100: 110,
    101: 92,
    102: 0,
    103: 31,
    104: 47,
    105: 101,
    106: 32,
    107: 29,
    108: 111,
    109: 103,
    110: 77,
    111: 72,
    112: 122,
    113: 4,
    114: 62,
    119: 21,
    120: 74,
    121: 36,
    123: 38,
    126: 118,
    128: 95,
    129: 58,
    131: 85,
    135: 22,
    136: 57,
    137: 78,
    138: 64,
    145: 45,
}


def build_scraper() -> cloudscraper.CloudScraper:
    return cloudscraper.create_scraper(
        browser={"browser": "firefox", "platform": "windows", "mobile": False}
    )


def fetch_heroes(scraper: cloudscraper.CloudScraper) -> list[dict]:
    response = scraper.get(f"{BASE_URL}/heroes/list")
    response.raise_for_status()
    return response.json()


def fetch_matchups(
    scraper: cloudscraper.CloudScraper, hero_id: int, hero_slug: str
) -> dict:
    response = scraper.get(
        f"{BASE_URL}/hero/{hero_id}/matchups",
        params={"minified": "true", "min_matches": 0},
        headers={
            "Referer": f"https://dota2protracker.com/hero/{hero_slug}",
            "Origin": "https://dota2protracker.com",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def build_matrix(heroes: list[dict], scraper: cloudscraper.CloudScraper) -> dict:
    matrix: dict[int, dict[int, dict[str, float]]] = {}

    for hero in heroes:
        hero_id = hero["hero_id"]
        hero_slug = hero["npc"]

        scraper.get(
            f"https://dota2protracker.com/hero/{hero_slug}",
            headers={"Referer": "https://dota2protracker.com"},
            timeout=10,
        )

        data = fetch_matchups(scraper, hero_id, hero_slug)
        fields = {name: idx for idx, name in enumerate(data["fields"])}

        for row in data["data"]:
            if row[fields["position"]] != "all":
                continue

            other_id = row[fields["other_hero_id"]]
            matches = row[fields["matches"]]
            wins = row[fields["wins"]]

            if matches == 0:
                win_rate = 0.0
                delta = 0.0
            else:
                win_rate = wins / matches
                delta = (win_rate - 0.5) * 100

            matrix.setdefault(hero_id, {})[other_id] = {
                "win_rate": win_rate,
                "delta": delta,
                "matches": matches,
            }

        time.sleep(REQUEST_DELAY_SECONDS)

    return matrix


def normalize_name(raw_name: str) -> str:
    cleaned = raw_name.replace("-", " ").replace("'", "")
    words = cleaned.split()
    return " ".join(word.capitalize() for word in words)


def slugify(display_name: str) -> str:
    return display_name.lower().replace(" ", "-")


def build_cs_payload(
    hero_map: dict[int, str], matrix: dict[int, dict[int, dict[str, float]]]
) -> str:
    hero_ids_sorted = [
        hero_id for hero_id, _ in sorted(HERO_INDEX_MAP.items(), key=lambda item: item[1])
    ]

    heroes: list[str] = []
    heroes_bg: list[str] = []
    heroes_wr: list[str] = []
    win_rates: list[list[object]] = []

    for hero_id in hero_ids_sorted:
        display_name = normalize_name(hero_map[hero_id])
        heroes.append(display_name)
        heroes_bg.append(
            f"https://www.dotabuff.com/assets/heroes/{slugify(display_name)}.jpg"
        )

    for hero_id in hero_ids_sorted:
        row: list[object] = []
        total_matches = 0
        total_wins = 0.0
        hero_row = matrix.get(hero_id, {})

        for other_id in hero_ids_sorted:
            if hero_id == other_id:
                row.append(None)
                continue

            matchup = hero_row.get(other_id)
            if matchup is None:
                inverse = matrix.get(other_id, {}).get(hero_id)
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

        overall_wr = (total_wins / total_matches) * 100 if total_matches else 50.0
        heroes_wr.append(f"{overall_wr:.2f}")
        win_rates.append(row)

    payload_lines = [
        "var heroes = " + json.dumps(heroes, separators=(",", ":")) + ",",
        "heroes_bg = " + json.dumps(heroes_bg, separators=(",", ":")) + ",",
        "heroes_wr = " + json.dumps(heroes_wr, separators=(",", ":")) + ",",
        "win_rates = " + json.dumps(win_rates, separators=(",", ":")) + ",",
        f'update_time = "{date.today().isoformat()}";',
        "",
    ]

    return "\n".join(payload_lines)


def main() -> None:
    scraper = build_scraper()
    heroes = fetch_heroes(scraper)

    id_to_name = {hero["hero_id"]: hero["displayName"] for hero in heroes}
    matrix = build_matrix(heroes, scraper)

    # Generate Dotabuff Counter Picker matrix
    missing_ids = [hero_id for hero_id in id_to_name if hero_id not in HERO_INDEX_MAP]
    if missing_ids:
        raise ValueError(
            f"Hero index map missing entries for hero IDs: {', '.join(map(str, missing_ids))}"
        )

    cs_payload = build_cs_payload(id_to_name, matrix)
    CS_OUTPUT_PATH.write_text(cs_payload)
    print(f"Wrote Dotabuff counter matrix to {CS_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
