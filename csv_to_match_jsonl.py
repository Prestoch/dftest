#!/usr/bin/env python3
"""
Convert a CSV exported by fetch_pro_matches.py into newline-delimited match JSON.

Each line of the output mirrors a single match with the same metadata fields as the CSV
and a `players` array populated with the per-hero stats columns.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional

MATCH_FIELDS = [
    "match_id",
    "tournament",
    "radiant_team",
    "dire_team",
    "duration_minutes",
    "winner",
]

PLAYER_FIELDS = [
    "hero_id",
    "hero_name",
    "player_team",
    "gpm",
    "xpm",
    "tower_damage",
    "hero_damage",
    "hero_healing",
    "lane_efficiency_pct",
    "kda",
    "last_hits",
    "denies",
    "net_worth",
    "actions_per_min",
    "damage_taken",
    "teamfight_participation",
]

INT_FIELDS = {
    "match_id",
    "hero_id",
    "gpm",
    "xpm",
    "tower_damage",
    "hero_damage",
    "hero_healing",
    "last_hits",
    "denies",
    "net_worth",
    "actions_per_min",
    "damage_taken",
}

FLOAT_FIELDS = {
    "duration_minutes",
    "lane_efficiency_pct",
    "teamfight_participation",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert pro match CSV to newline-delimited JSON (one match per line)."
    )
    parser.add_argument("--input", required=True, help="Input CSV file path.")
    parser.add_argument("--output", required=True, help="Destination JSONL file path.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing output file (default: fail if exists).",
    )
    return parser.parse_args()


def parse_numeric(field: str, value: Optional[str]) -> Optional[Any]:
    if value is None or value == "":
        return None
    try:
        if field in INT_FIELDS:
            return int(float(value))
        if field in FLOAT_FIELDS:
            return round(float(value), 4)
    except ValueError:
        return None
    return value


def sanitize_row(row: Dict[str, str]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for field, value in row.items():
        if field in INT_FIELDS or field in FLOAT_FIELDS:
            cleaned[field] = parse_numeric(field, value)
        else:
            cleaned[field] = value if value != "" else None
    return cleaned


def convert(input_path: str, output_path: str, overwrite: bool) -> None:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input CSV not found: {input_path}")
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(
            f"Output file {output_path} already exists. Use --overwrite to replace it."
        )

    match_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"meta": {}, "players": []})

    with open(input_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in MATCH_FIELDS + PLAYER_FIELDS if field not in reader.fieldnames]
        if missing:
            raise ValueError(f"Input CSV missing required columns: {', '.join(missing)}")

        for row in reader:
            sanitized = sanitize_row(row)
            match_id = str(sanitized.get("match_id") or "")
            if not match_id:
                continue

            match_entry = match_map[match_id]
            if not match_entry["meta"]:
                match_entry["meta"] = {field: sanitized.get(field) for field in MATCH_FIELDS}

            player_entry = {field: sanitized.get(field) for field in PLAYER_FIELDS}
            match_entry["players"].append(player_entry)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        for match_id in sorted(match_map.keys(), key=int):
            entry = match_map[match_id]
            payload = {**entry["meta"], "players": entry["players"]}
            json.dump(payload, handle, ensure_ascii=False)
            handle.write("\n")

    print(f"Wrote {len(match_map)} matches to {output_path}")


def main() -> None:
    args = parse_args()
    try:
        convert(args.input, args.output, args.overwrite)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
