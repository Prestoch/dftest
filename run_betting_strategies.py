import ast
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

START_BANKROLL = 1000.0
MAX_BET = 10_000.0
DELTA_THRESHOLDS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 75]
HERO_FILTERS = {"none", "4+4-", "5+5-"}


@dataclass
class StrategyConfig:
    name: str
    hero_filter: str
    odds_condition: str
    stake_type: str  # flat, pct, fib
    stake_value: float


def load_cs_data(path: Path):
    text = path.read_text()

    def extract(block_start: str, block_end: str) -> str:
        start = text.index(block_start) + len(block_start)
        end = text.index(block_end, start)
        return text[start:end]

    heroes = ast.literal_eval(extract("var heroes = ", "], heroes_bg") + "]")
    heroes_wr = ast.literal_eval(extract("heroes_wr = ", "], win_rates") + "]")
    raw_win_rates = extract("win_rates = ", "], update_time") + "]"
    raw_win_rates = re.sub(r"\bnull\b", "None", raw_win_rates)
    win_rates = ast.literal_eval(raw_win_rates)
    hero_index = {normalize_name(name): idx for idx, name in enumerate(heroes)}
    return heroes_wr, win_rates, hero_index


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def to_float(value: str) -> Optional[float]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def hero_indices(hero_names: Sequence[str], hero_index: Dict[str, int]) -> Optional[List[int]]:
    indices = []
    for name in hero_names:
        key = normalize_name(name)
        idx = hero_index.get(key)
        if idx is None:
            return None
        indices.append(idx)
    return indices


def hero_advantages(hero_ids: Sequence[int], opp_ids: Sequence[int], win_rates: List[List]) -> List[float]:
    advs: List[float] = []
    for hid in hero_ids:
        adv_value = 0.0
        for opp in opp_ids:
            if opp >= len(win_rates):
                continue
            row = win_rates[opp]
            if not isinstance(row, list) or hid >= len(row):
                continue
            cell = row[hid]
            if not cell:
                continue
            raw_adv = cell[0]
            if raw_adv is None:
                continue
            try:
                adv_value += float(raw_adv)
            except (ValueError, TypeError):
                continue
        advs.append(adv_value)
    return advs


def count_thresholds(advs: Sequence[float], threshold: float) -> Tuple[int, int]:
    plus = sum(1 for value in advs if value >= threshold)
    minus = sum(1 for value in advs if value <= -threshold)
    return plus, minus


def build_match_book(csv_path: Path, hero_index, win_rates, heroes_wr):
    rows = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            delta = to_float(row.get("delta"))
            favored_team = row.get("delta_favored_team", "").strip()
            winner = row.get("winner", "").strip()
            team1 = row.get("team1", "").strip()
            team2 = row.get("team2", "").strip()
            if delta is None or not favored_team or not winner or not team1 or not team2:
                continue
            fav = favored_team
            team1_odds = to_float(row.get("team1_odds"))
            team2_odds = to_float(row.get("team2_odds"))
            if team1_odds is None or team2_odds is None:
                continue
            heroes1 = [h.strip() for h in row.get("team1_heroes", "").split("|") if h.strip()]
            heroes2 = [h.strip() for h in row.get("team2_heroes", "").split("|") if h.strip()]
            if len(heroes1) != 5 or len(heroes2) != 5:
                continue
            indices1 = hero_indices(heroes1, hero_index)
            indices2 = hero_indices(heroes2, hero_index)
            if indices1 is None or indices2 is None:
                continue
            adv1 = hero_advantages(indices1, indices2, win_rates)
            adv2 = hero_advantages(indices2, indices1, win_rates)
            plus4_t1, minus4_t1 = count_thresholds(adv1, 4.0)
            plus4_t2, minus4_t2 = count_thresholds(adv2, 4.0)
            plus5_t1, minus5_t1 = count_thresholds(adv1, 5.0)
            plus5_t2, minus5_t2 = count_thresholds(adv2, 5.0)
            favored_odds = team1_odds if fav == team1 else team2_odds if fav == team2 else None
            opp_odds = team2_odds if fav == team1 else team1_odds if fav == team2 else None
            if favored_odds is None or opp_odds is None:
                continue
            favored_stats = {
                "plus4": plus4_t1 if fav == team1 else plus4_t2,
                "minus4": minus4_t1 if fav == team1 else minus4_t2,
                "plus5": plus5_t1 if fav == team1 else plus5_t2,
                "minus5": minus5_t1 if fav == team1 else minus5_t2,
            }
            opp_stats = {
                "plus4": plus4_t2 if fav == team1 else plus4_t1,
                "minus4": minus4_t2 if fav == team1 else minus4_t1,
                "plus5": plus5_t2 if fav == team1 else plus5_t1,
                "minus5": minus5_t2 if fav == team1 else minus5_t1,
            }
            rows.append(
                {
                    "date": row.get("date", ""),
                    "championship": row.get("championship", ""),
                    "series_id": row.get("series_id", ""),
                    "map_number": row.get("map_number", ""),
                    "match_id": row.get("hawk_match_id", ""),
                    "delta": delta,
                    "abs_delta": abs(delta),
                    "favored_team": fav,
                    "winner": winner,
                    "favored_odds": favored_odds,
                    "opp_odds": opp_odds,
                    "favored_stats": favored_stats,
                    "opp_stats": opp_stats,
                    "is_underdog": favored_odds > opp_odds,
                    "is_favorite": favored_odds < opp_odds,
                }
            )
    rows.sort(key=lambda r: (r["date"], r["championship"], r["series_id"], int_or_zero(r["map_number"]), r["match_id"]))
    return rows


def int_or_zero(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def hero_filter_passes(filter_name: str, favored_stats: Dict[str, int], opp_stats: Dict[str, int]) -> bool:
    if filter_name == "none":
        return True
    if filter_name == "4+4-":
        return favored_stats["plus4"] >= 4 and opp_stats["minus4"] >= 4
    if filter_name == "5+5-":
        return favored_stats["plus5"] >= 5 and opp_stats["minus5"] >= 5
    raise ValueError(f"Unknown hero filter {filter_name}")


def odds_condition_passes(condition: str, match: Dict) -> bool:
    if condition == "any":
        return True
    if condition == "underdog":
        return match["is_underdog"]
    if condition == "favorite":
        return match["is_favorite"]
    raise ValueError(f"Unknown odds condition {condition}")


def fibonacci_sequence_until(limit: float) -> List[int]:
    seq = [1, 1]
    while seq[-1] + seq[-2] <= limit:
        seq.append(seq[-1] + seq[-2])
    return seq


def simulate_strategy(matches: List[Dict], cfg: StrategyConfig, delta_threshold: float) -> Dict[str, float]:
    bank = START_BANKROLL
    peak = bank
    max_drawdown = 0.0
    bets = 0
    wins = 0
    max_stake = 0.0
    max_step = 0
    fib_seq = fibonacci_sequence_until(int(MAX_BET / max(cfg.stake_value, 1)))
    fib_index = 0

    for match in matches:
        if bank <= 0:
            break
        if match["abs_delta"] < delta_threshold:
            continue
        if not odds_condition_passes(cfg.odds_condition, match):
            continue
        if not hero_filter_passes(cfg.hero_filter, match["favored_stats"], match["opp_stats"]):
            continue

        stake, fib_index = determine_stake(cfg, bank, fib_seq, fib_index)
        if stake is None or stake <= 0:
            break
        if stake > bank + 1e-9:
            if cfg.stake_type in {"flat", "fib"}:
                break
            stake = bank
        stake = min(stake, MAX_BET, bank)
        if stake < 1e-9:
            break

        bets += 1
        max_stake = max(max_stake, stake)
        hit = match["favored_team"] == match["winner"]
        if hit:
            wins += 1
            profit = stake * (match["favored_odds"] - 1)
            bank += profit
            if cfg.stake_type == "fib":
                fib_index = max(fib_index - 2, 0)
        else:
            bank -= stake
            if bank < 0:
                bank = 0
            if cfg.stake_type == "fib":
                fib_index = min(fib_index + 1, len(fib_seq) - 1)
        if bank > peak:
            peak = bank
        else:
            drawdown = peak - bank
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        if cfg.stake_type == "fib":
            max_step = max(max_step, fib_index)

    win_pct = round((wins / bets) * 100) if bets else 0
    return {
        "strategy_group": cfg.name,
        "hero_filter": cfg.hero_filter,
        "odds_condition": cfg.odds_condition,
        "delta_threshold": delta_threshold,
        "bets": bets,
        "wins": wins,
        "win_pct": win_pct,
        "final_bank": round(bank),
        "max_drawdown": round(max_drawdown),
        "max_stake": round(max_stake),
        "max_step": max_step if cfg.stake_type == "fib" else 0,
    }


def determine_stake(cfg: StrategyConfig, bank: float, fib_seq: List[int], fib_index: int) -> Tuple[Optional[float], int]:
    if cfg.stake_type == "flat":
        if bank < cfg.stake_value:
            return None, fib_index
        return cfg.stake_value, fib_index
    if cfg.stake_type == "pct":
        stake = bank * cfg.stake_value
        return stake, fib_index
    if cfg.stake_type == "fib":
        if not fib_seq:
            return None, fib_index
        stake = fib_seq[fib_index] * cfg.stake_value
        return stake, fib_index
    raise ValueError(f"Unknown stake type {cfg.stake_type}")


def build_strategy_configs() -> List[StrategyConfig]:
    configs: List[StrategyConfig] = []
    ordered_specs = [
        ("Flat100", "none", "flat", 100.0),
        ("Pct5", "none", "pct", 0.05),
        ("Flat100", "4+4-", "flat", 100.0),
        ("Pct5", "4+4-", "pct", 0.05),
        ("Flat100", "5+5-", "flat", 100.0),
        ("Pct5", "5+5-", "pct", 0.05),
        ("Fib1", "none", "fib", 1.0),
        ("Fib1", "4+4-", "fib", 1.0),
        ("Fib1", "5+5-", "fib", 1.0),
        ("Fib5", "none", "fib", 5.0),
        ("Fib5", "4+4-", "fib", 5.0),
        ("Fib5", "5+5-", "fib", 5.0),
    ]
    odds_order = ["any", "underdog", "favorite"]
    for name, hero_filter, stake_type, value in ordered_specs:
        for odds_condition in odds_order:
            configs.append(
                StrategyConfig(
                    name=name,
                    hero_filter=hero_filter,
                    odds_condition=odds_condition,
                    stake_type=stake_type,
                    stake_value=value,
                )
            )
    return configs


def main():
    heroes_wr, win_rates, hero_index = load_cs_data(Path("cs.json"))
    matches = build_match_book(Path("hawk_matches_merged.csv"), hero_index, win_rates, heroes_wr)
    configs = build_strategy_configs()
    results: List[Dict[str, float]] = []
    for cfg in configs:
        for threshold in DELTA_THRESHOLDS:
            stats = simulate_strategy(matches, cfg, threshold)
            results.append(stats)

    out_path = Path("strategy_results_hawk.csv")
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
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    print(f"Wrote {len(results)} rows to {out_path}")


if __name__ == "__main__":
    main()
