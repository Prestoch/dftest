## OpenDota Pro Match Fetcher

`fetch_pro_matches.py` downloads professional Dota 2 match data from OpenDota and stores one CSV row per hero with the following fields:

- match metadata: `match_id`, `tournament`, `radiant_team`, `dire_team`, `duration_minutes`, `winner`
- hero information: `hero_id`, `hero_name`, `player_team`
- performance stats: `gpm`, `xpm`, `tower_damage`, `hero_damage`, `hero_healing`, `lane_efficiency_pct`, `kda`, `last_hits`, `denies`, `net_worth`, `actions_per_min`, `damage_taken`, `teamfight_participation`

### Requirements

- Python 3.10+
- `requests` (`pip install requests`)
- Optional: OpenDota API key for higher rate limits (1000 requests/minute)

### Usage

```bash
python3 fetch_pro_matches.py \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --exclude "DreamLeague Season 22" --exclude "Random Cup" \
  --output january_pro_matches.csv \
  --save-interval 10 \
  --max-matches 500 \
  --api-key "$OPENDOTA_API_KEY"
```

#### Key flags

- `--start-date` / `--end-date` (required): Inclusive UTC date range in `YYYY-MM-DD` form.
- `--exclude`: Repeatable flag for tournament (league) names to skip.
- `--save-interval`: Flush buffered rows to disk every N matches (default 10) to guard against crashes.
- `--max-matches`: Stop after processing a fixed number of matches (useful for sampling).
- `--api-key`: Provide your OpenDota key; defaults to the `OPENDOTA_API_KEY` environment variable.
- `--rate-limit-wait`: Delay between `proMatches` pagination requests. Defaults to 1.0s for anonymous use; automatically drops to 0.1s when an API key is supplied unless you override it.

### Resilience and retry behavior

- Automatic retry logic handles transient `429`/`5xx` responses with exponential backoff.
- A progress bar shows matches processed and remaining.
- Partial results are saved every `--save-interval` matches; if the script stops mid-run, simply rerun it with the same arguments and it will append to the CSV without duplicating headers.

### Environment variables

Set `OPENDOTA_API_KEY` to avoid passing the key each time:

```bash
export OPENDOTA_API_KEY=your_token_here
python3 fetch_pro_matches.py --start-date 2024-02-01 --end-date 2024-02-15
```

### Troubleshooting tips

- If you still encounter rate limits, increase `--rate-limit-wait` (e.g., `--rate-limit-wait 0.5`).
- To resume after a crash, rerun with the same arguments. Already saved data remains in the CSV; remove or rename the file to start fresh.
- Use `--quiet` to suppress informational logs when running the script inside larger automation.
