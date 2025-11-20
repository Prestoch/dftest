#!/usr/bin/env python3
"""
Fetch pro match data from OpenDota with resumable saves and filtering.

Features:
* Restrict results to a user-provided date range.
* Skip specific tournaments (leagues) by name.
* Retrieve detailed hero-level stats for each match.
* Persist progress every N matches (default: 10) to withstand failures.
* Display a progress bar showing processed and remaining matches.
* Automatically retry failed requests (e.g., HTTP 500s).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RetryError
from urllib3.util.retry import Retry

API_ROOT = "https://api.opendota.com/api"
PRO_MATCHES_URL = f"{API_ROOT}/proMatches"
MATCH_URL_TEMPLATE = f"{API_ROOT}/matches/{{match_id}}"
HEROES_URL = f"{API_ROOT}/constants/heroes"

DEFAULT_SAVE_INTERVAL = 10  # matches
PRO_MATCHES_BATCH_SIZE = 100
DEFAULT_RATE_LIMIT_WAIT = 1.0  # seconds without API key
FAST_RATE_LIMIT_WAIT = 0.1  # seconds with API key
COLLECT_LOG_INTERVAL = 1000  # matches between log updates

FIELDNAMES = [
    "match_id",
    "tournament",
    "radiant_team",
    "dire_team",
    "duration_minutes",
    "winner",
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


@dataclass(frozen=True)
class MatchMeta:
    match_id: int
    tournament: str
    radiant_team: str
    dire_team: str
    start_time: int
    duration: int
    radiant_win: Optional[bool]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch pro matches from OpenDota with hero-level stats."
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Inclusive start date (UTC) in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end-date",
        required=True,
        help="Inclusive end date (UTC) in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Tournament (league) name to skip. Repeat the flag for multiple names.",
    )
    parser.add_argument(
        "--output",
        default="pro_matches.csv",
        help="Destination CSV file for the aggregated data.",
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=DEFAULT_SAVE_INTERVAL,
        help="Number of matches to process before flushing results to disk.",
    )
    parser.add_argument(
        "--max-matches",
        type=int,
        default=None,
        help="Process at most this many matches (after filtering).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=4,
        help="Number of retry attempts for transient HTTP errors (>=500).",
    )
    parser.add_argument(
        "--rate-limit-wait",
        type=float,
        default=DEFAULT_RATE_LIMIT_WAIT,
        help="Delay between paginated proMatches requests to avoid rate limits.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("OPENDOTA_API_KEY"),
        help="OpenDota API key (default: OPENDOTA_API_KEY env var).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce log verbosity.",
    )
    return parser.parse_args()


def utc_timestamp(date_str: str, end_of_day: bool = False) -> int:
    date = dt.datetime.strptime(date_str, "%Y-%m-%d")
    if end_of_day:
        date = date + dt.timedelta(days=1) - dt.timedelta(seconds=1)
    return int(date.replace(tzinfo=dt.timezone.utc).timestamp())


def build_session(retries: int, api_key: Optional[str]) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        status=retries,
        status_forcelist=(429, 500, 502, 503, 504),
        backoff_factor=1.0,
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    if api_key:
        session.params = session.params or {}
        session.params["api_key"] = api_key
    return session


def fetch_hero_map(session: requests.Session) -> Dict[int, str]:
    response = session.get(HEROES_URL, timeout=30)
    response.raise_for_status()
    payload = response.json()
    hero_map: Dict[int, str] = {}
    for hero_id, data in payload.items():
        try:
            hid = int(hero_id)
        except (TypeError, ValueError):
            continue
        hero_map[hid] = data.get("localized_name") or data.get("name") or str(hid)
    return hero_map


def collect_matches(
    session: requests.Session,
    start_ts: int,
    end_ts: int,
    excluded_terms: Sequence[str],
    rate_limit_wait: float,
    quiet: bool,
    max_matches: Optional[int] = None,
) -> List[MatchMeta]:
    excluded_terms = [term for term in excluded_terms if term]
    matches: List[MatchMeta] = []
    seen_ids: set[int] = set()
    less_than_id: Optional[int] = None
    stop_fetching = False
    last_reported = 0
    reported_progress = False

    while not stop_fetching:
        params = {"less_than_match_id": less_than_id} if less_than_id else {}
        try:
            response = session.get(PRO_MATCHES_URL, params=params, timeout=30)
        except RetryError:
            wait_time = max(5.0, rate_limit_wait * 4)
            if not quiet:
                print(f"Hit API rate limit, sleeping for {wait_time:.1f}s...")
            time.sleep(wait_time)
            continue

        if response.status_code == 429:
            wait_time = float(response.headers.get("Retry-After", 5))
            if not quiet:
                print(f"OpenDota returned 429. Waiting {wait_time:.1f}s before retrying...")
            time.sleep(wait_time)
            continue

        response.raise_for_status()
        batch = response.json() or []
        if not batch:
            break

        for item in batch:
            match_id = item.get("match_id")
            start_time = item.get("start_time")
            if not match_id or start_time is None:
                continue
            if match_id in seen_ids:
                continue
            seen_ids.add(match_id)

            if start_time > end_ts:
                continue
            if start_time < start_ts:
                stop_fetching = True
                break

            tournament = (item.get("league_name") or "").strip()
            tournament_lower = tournament.lower()
            if any(term in tournament_lower for term in excluded_terms):
                continue

            match_meta = MatchMeta(
                match_id=int(match_id),
                tournament=tournament or "Unknown",
                radiant_team=(item.get("radiant_name") or "Radiant").strip() or "Radiant",
                dire_team=(item.get("dire_name") or "Dire").strip() or "Dire",
                start_time=int(start_time),
                duration=int(item.get("duration") or 0),
                radiant_win=item.get("radiant_win"),
            )
            matches.append(match_meta)
            if (
                not quiet
                and len(matches) >= last_reported + COLLECT_LOG_INTERVAL
            ):
                latest_date = dt.datetime.fromtimestamp(
                    start_time, tz=dt.timezone.utc
                ).strftime("%Y-%m-%d")
                print(
                    f"\r  Collected {len(matches)} matches so far "
                    f"(most recent start date {latest_date})",
                    end="",
                )
                last_reported = len(matches)
                reported_progress = True
            if max_matches and len(matches) >= max_matches:
                stop_fetching = True
                break

        if stop_fetching:
            break

        last_id = batch[-1].get("match_id")
        if not last_id or len(batch) < PRO_MATCHES_BATCH_SIZE:
            break
        less_than_id = last_id
        time.sleep(rate_limit_wait)

    if reported_progress and not quiet:
        print()

    matches.sort(key=lambda meta: meta.start_time)
    if not quiet:
        print(f"Discovered {len(matches)} matches between the selected dates.")
    return matches


def ensure_output_file(path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            writer.writeheader()


def append_rows(path: str, rows: Iterable[Dict[str, Any]]) -> None:
    if not rows:
        return
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writerows(rows)


def format_kda(kills: Optional[int], deaths: Optional[int], assists: Optional[int]) -> str:
    k = kills if kills is not None else 0
    d = deaths if deaths is not None else 0
    a = assists if assists is not None else 0
    return f"{k}/{d}/{a}"


def sum_damage_taken(raw_value: Any) -> Optional[int]:
    if raw_value is None:
        return None
    total = 0
    stack = [raw_value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
        elif isinstance(current, (int, float)) and not isinstance(current, bool):
            total += int(current)
    return total


def build_rows(
    match_data: Dict[str, Any],
    meta: MatchMeta,
    hero_map: Dict[int, str],
) -> List[Dict[str, Any]]:
    winner = meta.radiant_team if meta.radiant_win else meta.dire_team
    if meta.radiant_win is None:
        winner = meta.radiant_team if match_data.get("radiant_win") else meta.dire_team

    duration_seconds = match_data.get("duration", meta.duration)
    duration_minutes = round((duration_seconds or 0) / 60, 2)

    rows: List[Dict[str, Any]] = []
    for player in match_data.get("players", []):
        hero_id = player.get("hero_id")
        hero_name = hero_map.get(hero_id or -1, f"Hero {hero_id}")
        lane_eff = player.get("lane_efficiency")
        lane_eff_pct = round(lane_eff * 100, 2) if isinstance(lane_eff, (int, float)) else None
        damage_taken = sum_damage_taken(player.get("damage_taken"))
        row = {
            "match_id": meta.match_id,
            "tournament": meta.tournament,
            "radiant_team": meta.radiant_team,
            "dire_team": meta.dire_team,
            "duration_minutes": duration_minutes,
            "winner": winner,
            "hero_id": hero_id,
            "hero_name": hero_name,
            "player_team": meta.radiant_team if player.get("isRadiant") else meta.dire_team,
            "gpm": player.get("gold_per_min"),
            "xpm": player.get("xp_per_min"),
            "tower_damage": player.get("tower_damage"),
            "hero_damage": player.get("hero_damage"),
            "hero_healing": player.get("hero_healing"),
            "lane_efficiency_pct": lane_eff_pct,
            "kda": format_kda(player.get("kills"), player.get("deaths"), player.get("assists")),
            "last_hits": player.get("last_hits"),
            "denies": player.get("denies"),
            "net_worth": player.get("net_worth"),
            "actions_per_min": player.get("actions_per_min"),
            "damage_taken": damage_taken,
            "teamfight_participation": player.get("teamfight_participation"),
        }
        rows.append(row)
    return rows


def parse_exclusions(values: Sequence[str]) -> List[str]:
    terms: List[str] = []
    for value in values:
        if not value:
            continue
        for chunk in value.split(","):
            normalized = chunk.strip().lower()
            if normalized:
                terms.append(normalized)
    return terms


class ProgressBar:
    def __init__(self, total: int, width: int = 40, label: str = "Progress") -> None:
        self.total = total
        self.width = width
        self.current = 0
        self.label = label
        self.start_time = time.time()

    def update(self, successes: int, failures: int, step: int = 1) -> None:
        if self.total <= 0:
            return
        self.current = min(self.total, self.current + step)
        filled = int(self.width * self.current / self.total)
        bar = "#" * filled + "-" * (self.width - filled)
        remaining = self.total - self.current
        elapsed = max(time.time() - self.start_time, 1e-6)
        rate = self.current / elapsed
        sys.stdout.write(
            f"\r{self.label} [{bar}] {self.current}/{self.total} matches "
            f"({remaining} left, {rate:.2f}/s, {successes} ok, {failures} failed)"
        )
        sys.stdout.flush()
        if self.current == self.total:
            sys.stdout.write("\n")


def fetch_match_details(session: requests.Session, match_id: int) -> Dict[str, Any]:
    response = session.get(MATCH_URL_TEMPLATE.format(match_id=match_id), timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> None:
    args = parse_args()
    if args.api_key and args.rate_limit_wait == DEFAULT_RATE_LIMIT_WAIT:
        args.rate_limit_wait = FAST_RATE_LIMIT_WAIT
    excluded_terms = parse_exclusions(args.exclude)

    start_ts = utc_timestamp(args.start_date)
    end_ts = utc_timestamp(args.end_date, end_of_day=True)
    if start_ts > end_ts:
        raise SystemExit("Start date must be before or equal to end date.")

    session = build_session(args.retries, api_key=args.api_key)
    if not args.quiet:
        if args.api_key:
            print("Using provided OpenDota API key.")
        print("Downloading hero list...")
    hero_map = fetch_hero_map(session)

    if not args.quiet:
        print("Collecting pro match IDs...")
    matches = collect_matches(
        session=session,
        start_ts=start_ts,
        end_ts=end_ts,
        excluded_terms=excluded_terms,
        rate_limit_wait=args.rate_limit_wait,
        quiet=args.quiet,
        max_matches=args.max_matches,
    )
    if not matches:
        print("No matches found for the specified filters.")
        return

    ensure_output_file(args.output)
    if not args.quiet:
        print("Fetching match details...")
    progress = ProgressBar(total=len(matches), label="Fetching details")

    pending_rows: List[Dict[str, Any]] = []
    matches_since_flush = 0
    total_rows_written = 0
    successes = 0
    failures = 0

    for meta in matches:
        try:
            match_data = fetch_match_details(session, meta.match_id)
        except requests.HTTPError as exc:
            print(f"\nWarning: failed to fetch match {meta.match_id}: {exc}", file=sys.stderr)
            failures += 1
            progress.update(successes, failures)
            continue
        except requests.RequestException as exc:
            print(f"\nWarning: request issue for match {meta.match_id}: {exc}", file=sys.stderr)
            failures += 1
            progress.update(successes, failures)
            continue

        rows = build_rows(match_data, meta, hero_map)
        pending_rows.extend(rows)
        matches_since_flush += 1
        successes += 1
        progress.update(successes, failures)

        if matches_since_flush >= max(1, args.save_interval):
            append_rows(args.output, pending_rows)
            total_rows_written += len(pending_rows)
            pending_rows.clear()
            matches_since_flush = 0

    if pending_rows:
        append_rows(args.output, pending_rows)
        total_rows_written += len(pending_rows)

    print(
        f"Completed. Processed {len(matches)} matches "
        f"and wrote {total_rows_written} hero rows to {args.output}."
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
