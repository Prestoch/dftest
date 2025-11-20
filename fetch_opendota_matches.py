#!/usr/bin/env python3
"""
Fetch pro matches from OpenDota API with specific data fields.
Rate limited to stay well below 1200 calls/minute (targeting ~600 calls/min).
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys
from tqdm import tqdm
import os


class OpenDotaFetcher:
    """Fetches pro matches from OpenDota API with rate limiting."""
    
    def __init__(self, api_key: str, rate_limit: int = 600, skip_tournaments: List[str] = None, checkpoint_file: str = None):
        """
        Initialize the fetcher.
        
        Args:
            api_key: OpenDota API key
            rate_limit: Maximum requests per minute (default 600, well below 1200 limit)
            skip_tournaments: List of tournament names to skip (saves API credits)
            checkpoint_file: File to save/resume progress (for crash recovery)
        """
        self.api_key = api_key
        self.base_url = "https://api.opendota.com/api"
        self.rate_limit = rate_limit
        self.min_delay = 60.0 / rate_limit  # Minimum seconds between requests
        self.last_request_time = 0
        self.request_count = 0
        self.session = requests.Session()
        self.hero_names = self._load_hero_names()
        self.skip_tournaments = [t.lower() for t in (skip_tournaments or [])]
        self.skipped_matches = 0
        self.checkpoint_file = checkpoint_file
        self.fetched_match_ids = set()
        
    def _load_hero_names(self) -> Dict[int, str]:
        """Load hero ID to name mapping."""
        # Try to load from local file first
        if os.path.exists('hero_id_map.json'):
            try:
                with open('hero_id_map.json', 'r') as f:
                    hero_map = json.load(f)
                    # Convert string keys to integers
                    return {int(k): v for k, v in hero_map.items()}
            except Exception as e:
                print(f"Warning: Could not load hero_id_map.json: {e}")
        
        # Fallback: fetch from API
        print("Fetching hero list from OpenDota API...")
        try:
            response = self.session.get(f"{self.base_url}/heroes", timeout=30)
            response.raise_for_status()
            heroes = response.json()
            return {hero['id']: hero['localized_name'] for hero in heroes}
        except Exception as e:
            print(f"Warning: Could not fetch heroes from API: {e}")
            return {}
        
    def _rate_limit_wait(self):
        """Ensure we don't exceed rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            wait_time = self.min_delay - elapsed
            time.sleep(wait_time)
        self.last_request_time = time.time()
        
    def _make_request(self, endpoint: str, params: Optional[Dict] = None, retries: int = 3) -> Optional[Dict]:
        """
        Make a rate-limited request to OpenDota API with automatic retry.
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            retries: Number of retry attempts for 500 errors (default: 3)
            
        Returns:
            JSON response or None if failed
        """
        if params is None:
            params = {}
        params['api_key'] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        
        for attempt in range(retries):
            self._rate_limit_wait()
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                self.request_count += 1
                
                if self.request_count % 100 == 0:
                    print(f"  Progress: {self.request_count} requests made")
                    
                return response.json()
                
            except requests.exceptions.HTTPError as e:
                # Handle 500 errors with retry
                if response.status_code == 500 and attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"  ⚠ 500 error on {endpoint}, retrying in {wait_time}s (attempt {attempt + 1}/{retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Final attempt failed or other HTTP error
                    if response.status_code == 500:
                        print(f"  ✗ 500 error on {endpoint} after {retries} attempts - skipping")
                    else:
                        print(f"  ✗ HTTP {response.status_code} error on {endpoint}: {e}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                # Network errors, timeouts, etc.
                print(f"  ✗ Request error on {endpoint}: {e}")
                return None
        
        return None
            
    def get_pro_matches(self, less_than_match_id: Optional[int] = None) -> List[Dict]:
        """
        Get a batch of pro matches.
        
        Args:
            less_than_match_id: Get matches with ID less than this (for pagination)
            
        Returns:
            List of pro match summaries
        """
        params = {}
        if less_than_match_id:
            params['less_than_match_id'] = less_than_match_id
            
        matches = self._make_request("proMatches", params)
        return matches if matches else []
        
    def get_match_details(self, match_id: int) -> Optional[Dict]:
        """
        Get detailed information for a specific match.
        
        Args:
            match_id: Match ID to fetch
            
        Returns:
            Match details or None if failed
        """
        return self._make_request(f"matches/{match_id}")
    
    def _should_skip_tournament(self, league_name: str) -> bool:
        """Check if tournament should be skipped."""
        if not self.skip_tournaments:
            return False
        league_lower = league_name.lower()
        return any(skip_term in league_lower for skip_term in self.skip_tournaments)
    
    def _load_checkpoint(self) -> set:
        """Load checkpoint file if exists, returns set of fetched match IDs."""
        if not self.checkpoint_file or not os.path.exists(self.checkpoint_file):
            return set()
        
        try:
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)
                match_ids = set(data.get('fetched_match_ids', []))
                print(f"📁 Loaded checkpoint: {len(match_ids)} matches already fetched")
                return match_ids
        except Exception as e:
            print(f"⚠ Could not load checkpoint: {e}")
            return set()
    
    def _save_checkpoint(self, fetched_match_ids: set):
        """Save only match IDs to checkpoint (lightweight)."""
        if not self.checkpoint_file:
            return
        
        try:
            checkpoint_data = {
                'fetched_match_ids': list(fetched_match_ids),
                'timestamp': datetime.now().isoformat(),
                'total_matches': len(fetched_match_ids)
            }
            
            # Write to temp file first, then rename (atomic operation)
            temp_file = self.checkpoint_file + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(checkpoint_data, f)
            
            # Atomic rename
            os.replace(temp_file, self.checkpoint_file)
            
        except Exception as e:
            print(f"⚠ Could not save checkpoint: {e}")
    
    def extract_match_data(self, match_details: Dict) -> Optional[Dict]:
        """
        Extract only the required fields from match details.
        
        Args:
            match_details: Full match details from API
            
        Returns:
            Dictionary with only required fields, or None if tournament should be skipped
        """
        if not match_details:
            return None
        
        try:
            # Extract match-level information
            match_id = match_details.get('match_id')
            duration = match_details.get('duration', 0)
            radiant_win = match_details.get('radiant_win', False)
            
            # Extract team/tournament information
            league_name = match_details.get('league', {}).get('name', 'Unknown')
            radiant_team_name = match_details.get('radiant_team', {}).get('name', 'Radiant')
            dire_team_name = match_details.get('dire_team', {}).get('name', 'Dire')
            
            # Check if we should skip this tournament
            if self._should_skip_tournament(league_name):
                self.skipped_matches += 1
                return None
            
            # Extract player/hero data
            players_data = []
            players = match_details.get('players', [])
            
            for i, player in enumerate(players):
                hero_id = player.get('hero_id')
                hero_name = self.hero_names.get(hero_id, f"Hero {hero_id}")
                
                # Determine team
                is_radiant = player.get('isRadiant', i < 5)
                team_name = radiant_team_name if is_radiant else dire_team_name
                
                # Determine if this player won
                player_won = (is_radiant and radiant_win) or (not is_radiant and not radiant_win)
                
                # Extract lane advantages (from laning phase)
                lane_efficiency = player.get('lane_efficiency_pct')
                
                player_data = {
                    'hero_name': hero_name,
                    'hero_id': hero_id,
                    'team': team_name,
                    'gpm': player.get('gold_per_min', 0),
                    'xpm': player.get('xp_per_min', 0),
                    'tower_damage': player.get('tower_damage', 0),
                    'hero_healing': player.get('hero_healing', 0),
                    'lane_efficiency_pct': lane_efficiency,
                    'kills': player.get('kills', 0),
                    'deaths': player.get('deaths', 0),
                    'assists': player.get('assists', 0),
                    'last_hits': player.get('last_hits', 0),
                    'denies': player.get('denies', 0),
                    'net_worth': player.get('net_worth', 0),
                    'hero_damage': player.get('hero_damage', 0),
                    'damage_taken': player.get('damage_taken', 0),
                    'teamfight_participation': player.get('teamfight_participation', 0),
                    'actions_per_min': player.get('actions_per_min', 0),
                    'won': player_won
                }
                
                players_data.append(player_data)
            
            # Compile final match data
            extracted_data = {
                'match_id': match_id,
                'tournament': league_name,
                'radiant_team': radiant_team_name,
                'dire_team': dire_team_name,
                'duration_seconds': duration,
                'duration_minutes': round(duration / 60, 2),
                'radiant_win': radiant_win,
                'winner': radiant_team_name if radiant_win else dire_team_name,
                'players': players_data
            }
            
            return extracted_data
            
        except Exception as e:
            print(f"Error extracting data from match {match_details.get('match_id', 'unknown')}: {e}")
            return None
        
    def fetch_recent_pro_matches(self, months: int = 3, include_details: bool = False, 
                                 start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """
        Fetch pro matches from specified date range or last N months.
        
        Args:
            months: Number of months to look back (if start_date not specified)
            include_details: Whether to fetch full match details (much slower)
            start_date: Start date for fetching (inclusive)
            end_date: End date for fetching (inclusive), defaults to now
            
        Returns:
            List of all pro matches
        """
        # Determine date range
        if start_date:
            cutoff_date = start_date
            cutoff_timestamp = int(cutoff_date.timestamp())
            end_timestamp = int(end_date.timestamp()) if end_date else None
        else:
            # Calculate timestamp for N months ago
            cutoff_date = datetime.now() - timedelta(days=months * 30)
            cutoff_timestamp = int(cutoff_date.timestamp())
            end_timestamp = None
        
        print(f"Fetching pro matches from {cutoff_date.strftime('%Y-%m-%d')}", end='')
        if end_date:
            print(f" to {end_date.strftime('%Y-%m-%d')}")
        else:
            print(" to now")
        print(f"Rate limit: {self.rate_limit} requests/minute")
        print(f"Include details: {include_details}")
        print()
        
        all_matches = []
        less_than_match_id = None
        page = 0
        
        start_time = time.time()
        
        # Phase 1: Fetch match list with progress bar
        print("Phase 1: Fetching match list...")
        pbar = tqdm(desc="Fetching pages", unit=" pages", dynamic_ncols=True)
        
        while True:
            page += 1
            pbar.set_postfix_str(f"{len(all_matches)} matches found")
            
            matches = self.get_pro_matches(less_than_match_id)
            
            if not matches:
                pbar.set_postfix_str(f"Complete - {len(all_matches)} total matches")
                break
                
            # Filter matches by date range
            recent_matches = []
            for match in matches:
                match_time = match.get('start_time', 0)
                
                # Check if before cutoff date
                if match_time < cutoff_timestamp:
                    pbar.set_postfix_str(f"Reached start date - {len(all_matches)} total matches")
                    break
                
                # Check if after end date (if specified)
                if end_timestamp and match_time > end_timestamp:
                    continue  # Skip this match, it's too recent
                
                recent_matches.append(match)
                    
            if not recent_matches:
                pbar.set_postfix_str(f"Complete - {len(all_matches)} total matches")
                break
                
            all_matches.extend(recent_matches)
            pbar.update(1)
                
            # Set up for next page
            less_than_match_id = matches[-1]['match_id']
        
        pbar.close()
                
        elapsed_time = time.time() - start_time
        print(f"✓ Fetched {len(all_matches)} pro matches in {elapsed_time:.1f} seconds")
        print(f"  Made {self.request_count} API requests")
        print(f"  Average rate: {self.request_count / (elapsed_time / 60):.1f} requests/minute")
        
        # Optionally fetch detailed match data
        if include_details and all_matches:
            print(f"\nPhase 2: Fetching detailed data for {len(all_matches)} matches...")
            print("Data will be written incrementally to save memory")
            
            # Load checkpoint if exists
            self.fetched_match_ids = self._load_checkpoint()
            already_fetched = len(self.fetched_match_ids)
            
            if already_fetched > 0:
                print(f"  Resuming from checkpoint ({already_fetched} already fetched)")
            
            print("This will take a while...\n")
            
            # Return metadata for caller to handle file writing
            return {
                'match_list': all_matches,
                'already_fetched': already_fetched,
                'needs_streaming': True
            }
            
        return all_matches
        
    def fetch_and_stream_matches(self, all_matches: List[Dict], json_filename: str, csv_filename: str, already_fetched: int = 0):
        """
        Fetch match details and write incrementally to files (low memory footprint).
        
        Args:
            all_matches: List of match summaries to fetch
            json_filename: Output JSON file
            csv_filename: Output CSV file
            already_fetched: Number of matches already fetched (from checkpoint)
        """
        import csv
        
        failed_matches = []
        success_count = 0
        checkpoint_interval = 100  # Save checkpoint every 100 matches
        last_checkpoint_count = already_fetched
        
        # CSV fieldnames
        fieldnames = [
            'match_id', 'tournament', 'radiant_team', 'dire_team',
            'duration_minutes', 'winner', 'radiant_win',
            'hero_name', 'hero_id', 'team',
            'gpm', 'xpm', 'tower_damage', 'hero_healing',
            'lane_efficiency_pct', 'kills', 'deaths', 'assists',
            'last_hits', 'denies', 'net_worth', 'hero_damage', 'damage_taken',
            'teamfight_participation', 'actions_per_min', 'won'
        ]
        
        # Open files for appending/writing
        json_mode = 'a' if already_fetched > 0 else 'w'
        csv_mode = 'a' if already_fetched > 0 else 'w'
        
        json_file = open(json_filename, json_mode, encoding='utf-8')
        csv_file = open(csv_filename, csv_mode, newline='', encoding='utf-8')
        csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        
        try:
            # Write JSON array opening bracket
            if already_fetched == 0:
                json_file.write('[\n')
                csv_writer.writeheader()
            
            # Progress bar for detailed fetching
            with tqdm(total=len(all_matches), desc="Fetching details", unit=" matches", 
                     dynamic_ncols=True, initial=already_fetched) as pbar:
                
                for i, match in enumerate(all_matches):
                    match_id = match['match_id']
                    
                    # Skip if already fetched
                    if match_id in self.fetched_match_ids:
                        pbar.update(1)
                        continue
                    
                    details = self.get_match_details(match_id)
                    
                    if details:
                        # Extract only the required fields
                        extracted = self.extract_match_data(details)
                        if extracted:
                            # Write to JSON (with comma separator)
                            if success_count > 0 or already_fetched > 0:
                                json_file.write(',\n')
                            json_file.write('  ' + json.dumps(extracted))
                            json_file.flush()  # Force write to disk
                            
                            # Write to CSV (one row per player)
                            match_info = {
                                'match_id': extracted['match_id'],
                                'tournament': extracted['tournament'],
                                'radiant_team': extracted['radiant_team'],
                                'dire_team': extracted['dire_team'],
                                'duration_minutes': extracted['duration_minutes'],
                                'winner': extracted['winner'],
                                'radiant_win': extracted['radiant_win']
                            }
                            
                            for player in extracted['players']:
                                row = {**match_info, **player}
                                csv_writer.writerow(row)
                            csv_file.flush()  # Force write to disk
                            
                            success_count += 1
                            self.fetched_match_ids.add(match_id)
                            
                            # Save checkpoint periodically
                            if len(self.fetched_match_ids) - last_checkpoint_count >= checkpoint_interval:
                                self._save_checkpoint(self.fetched_match_ids)
                                last_checkpoint_count = len(self.fetched_match_ids)
                        else:
                            # Tournament was skipped
                            self.fetched_match_ids.add(match_id)
                    else:
                        failed_matches.append(match_id)
                    
                    pbar.update(1)
                    pbar.set_postfix_str(f"{success_count} success, {len(failed_matches)} failed")
            
            # Write JSON array closing bracket
            json_file.write('\n]')
            
        finally:
            json_file.close()
            csv_file.close()
        
        # Final checkpoint save
        self._save_checkpoint(self.fetched_match_ids)
        
        # Print summary
        total_fetched = success_count + already_fetched
        print(f"\n✓ Fetched details for {total_fetched}/{len(all_matches)} matches")
        if already_fetched > 0:
            print(f"  ({success_count} newly fetched, {already_fetched} from checkpoint)")
        if failed_matches:
            print(f"  ⚠ Failed to fetch {len(failed_matches)} matches (likely 500 errors from OpenDota)")
            print(f"    Match IDs: {failed_matches[:10]}{'...' if len(failed_matches) > 10 else ''}")
            print(f"    These matches may be corrupted in OpenDota's database")
        
        return total_fetched
    
    def save_matches(self, matches: List[Dict], filename: str):
        """Save matches to JSON file."""
        with open(filename, 'w') as f:
            json.dump(matches, f, indent=2)
        print(f"\nSaved {len(matches)} matches to {filename}")
        

def main():
    """Main function to fetch pro matches."""
    # Check for API key
    if len(sys.argv) < 2:
        print("Usage: python fetch_opendota_matches.py <API_KEY> [options]")
        print("\nOptions:")
        print("  months=N              Number of months to look back (default: 3)")
        print("  from=YYYY-MM-DD       Start date (inclusive)")
        print("  to=YYYY-MM-DD         End date (inclusive, defaults to today)")
        print("  details=yes/no        Fetch detailed match data (default: yes)")
        print("  skip=tournaments      Comma-separated tournament names to skip")
        print("\nFetched data includes:")
        print("  - Match ID, Team/Tournament Names, Hero names")
        print("  - GPM, XPM, Tower Damage, Healing, Lane advantages")
        print("  - K/D/A, Last Hits, Denies, Net Worth")
        print("  - Hero Damage, Damage Taken, Teamfight Participation, Actions Per Min")
        print("  - Game Duration, Match Winner")
        print("\nExamples:")
        print("  # Last 3 months (default)")
        print("  python fetch_opendota_matches.py YOUR_KEY")
        print()
        print("  # Last 6 months")
        print("  python fetch_opendota_matches.py YOUR_KEY months=6")
        print()
        print("  # Specific date range")
        print("  python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 to=2023-12-31")
        print()
        print("  # From specific date to now")
        print("  python fetch_opendota_matches.py YOUR_KEY from=2023-01-01")
        print()
        print("  # Skip tournaments")
        print("  python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 skip=DPC,Regional")
        print()
        print("  # Continue from existing checkpoint (after conversion)")
        print("  python fetch_opendota_matches.py YOUR_KEY from=2023-01-01 continue=yes")
        print()
        print("  # Old format still works")
        print("  python fetch_opendota_matches.py YOUR_KEY 6 yes \"DPC,BTS\"")
        print("\nFeatures:")
        print("  ✓ Auto-checkpoint every 100 matches (network failure protection)")
        print("  ✓ Auto-resume if interrupted (just run the same command again)")
        print("  ✓ Streaming writes to disk (low memory usage, no crashes)")
        print("  ✓ Tournament filtering (saves API credits)")
        print("  ✓ Date range filtering (from=YYYY-MM-DD to=YYYY-MM-DD)")
        print("  ✓ Automatic retry on 500 errors (handles OpenDota glitches)")
        sys.exit(1)
        
    api_key = sys.argv[1]
    
    # Parse arguments - support both old and new format
    months = 3
    include_details = True
    skip_tournaments = []
    start_date = None
    end_date = None
    continue_mode = False
    
    # Check if using new key=value format or old positional format
    if len(sys.argv) > 2 and '=' in sys.argv[2]:
        # New format: key=value
        for arg in sys.argv[2:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                key = key.lower().strip()
                value = value.strip()
                
                if key == 'months':
                    months = int(value)
                elif key == 'from':
                    try:
                        start_date = datetime.strptime(value, '%Y-%m-%d')
                    except ValueError:
                        print(f"Error: Invalid date format for 'from': {value}")
                        print("Use YYYY-MM-DD format, e.g., from=2023-01-01")
                        sys.exit(1)
                elif key == 'to':
                    try:
                        end_date = datetime.strptime(value, '%Y-%m-%d')
                        # Set to end of day
                        end_date = end_date.replace(hour=23, minute=59, second=59)
                    except ValueError:
                        print(f"Error: Invalid date format for 'to': {value}")
                        print("Use YYYY-MM-DD format, e.g., to=2023-12-31")
                        sys.exit(1)
                elif key == 'details':
                    include_details = value.lower() not in ['no', 'false', '0']
                elif key == 'skip':
                    skip_tournaments = [t.strip() for t in value.split(',') if t.strip()]
                elif key == 'continue':
                    continue_mode = value.lower() in ['yes', 'true', '1']
    else:
        # Old format: positional arguments
        if len(sys.argv) > 2:
            months = int(sys.argv[2])
        if len(sys.argv) > 3:
            include_details = sys.argv[3].lower() not in ['no', 'false', '0']
        if len(sys.argv) > 4:
            skip_tournaments = [t.strip() for t in sys.argv[4].split(',') if t.strip()]
    
    # Validate date range
    if start_date and end_date and start_date > end_date:
        print("Error: 'from' date must be before 'to' date!")
        sys.exit(1)
    
    # Check for continuation mode
    continuation_files = None
    if continue_mode:
        metadata_file = '.continuation_metadata.json'
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    continuation_files = json.load(f)
                print(f"✓ Continuation mode: Loading metadata from {metadata_file}")
                print(f"  Will append to existing files:")
                print(f"    - {continuation_files['json_output']}")
                print(f"    - {continuation_files['csv_output']}")
                print(f"  Already have: {continuation_files['matches_saved']} matches")
                print()
            except Exception as e:
                print(f"⚠ Warning: Could not load continuation metadata: {e}")
                print(f"  Run setup_continuation.py first!")
                sys.exit(1)
        else:
            print(f"✗ Error: Continuation mode requested but no metadata file found!")
            print(f"  Please run: python setup_continuation.py <checkpoint_file>")
            sys.exit(1)
    
    # Generate checkpoint filename (based on parameters for consistency)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    detail_suffix = "_detailed" if include_details else "_summary"
    
    if start_date:
        # Date range based checkpoint
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d") if end_date else "now"
        checkpoint_file = f".opendota_checkpoint_{start_str}_to_{end_str}{detail_suffix}.json"
    else:
        # Months based checkpoint
        checkpoint_file = f".opendota_checkpoint_{months}months{detail_suffix}.json"
    
    # Create fetcher with rate limit of 600 req/min (50% of max)
    fetcher = OpenDotaFetcher(
        api_key, 
        rate_limit=600, 
        skip_tournaments=skip_tournaments,
        checkpoint_file=checkpoint_file if include_details else None
    )
    
    # Fetch matches
    print("="*60)
    if include_details and checkpoint_file:
        if os.path.exists(checkpoint_file):
            print(f"💾 Checkpoint file found: will resume if interrupted")
        else:
            print(f"💾 Checkpoint enabled: progress saved every 100 matches")
        print(f"   (Checkpoint file: {checkpoint_file})")
        print(f"   ⚡ Streaming mode: data written incrementally (low memory)")
        print()
    
    if skip_tournaments:
        print(f"Skipping tournaments containing: {', '.join(skip_tournaments)}")
        print()
    
    try:
        matches = fetcher.fetch_recent_pro_matches(
            months=months, 
            include_details=include_details,
            start_date=start_date,
            end_date=end_date
        )
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user!")
        print(f"💾 Progress saved in checkpoint: {checkpoint_file}")
        print(f"   To resume, run the same command again:")
        print(f"   python fetch_opendota_matches.py {' '.join(sys.argv[1:])}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        print(f"💾 Progress saved in checkpoint: {checkpoint_file}")
        print(f"   To resume, run the same command again")
        raise
    
    print("="*60)
    
    # Show skipped tournament info
    if fetcher.skipped_matches > 0:
        print(f"\n⚠ Skipped {fetcher.skipped_matches} matches from filtered tournaments")
    
    # Generate filename with timestamp (or use continuation files)
    if continuation_files:
        # Use existing files from continuation setup
        filename = continuation_files['json_output']
        csv_filename = continuation_files['csv_output']
        print(f"📝 Continuing with existing files:")
        print(f"   {filename}")
        print(f"   {csv_filename}")
        print()
    else:
        # Generate new filenames with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        detail_suffix = "_detailed" if include_details else "_summary"
        
        if start_date:
            # Date range based filename
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d") if end_date else "now"
            filename = f"opendota_pro_matches_{start_str}_to_{end_str}{detail_suffix}_{timestamp}.json"
        else:
            # Months based filename
            filename = f"opendota_pro_matches_{months}months{detail_suffix}_{timestamp}.json"
        
        csv_filename = filename.replace('.json', '.csv')
    
    # Handle streaming vs non-streaming modes
    if isinstance(matches, dict) and matches.get('needs_streaming'):
        # Streaming mode: fetch and write incrementally (low memory)
        total_matches = fetcher.fetch_and_stream_matches(
            matches['match_list'],
            filename,
            csv_filename,
            matches['already_fetched']
        )
        
        print(f"\nSaved {total_matches} matches to {filename}")
        print(f"Saved {total_matches} matches to CSV: {csv_filename}")
        
        matches = []  # Clear for statistics (already written to files)
    else:
        # Legacy mode: save all at once
        fetcher.save_matches(matches, filename)
        
        # Also save as CSV if we have detailed data
        if include_details and matches:
            csv_filename = filename.replace('.json', '.csv')
            # Use simple CSV writer for backward compatibility
            import csv
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'match_id', 'tournament', 'radiant_team', 'dire_team',
                    'duration_minutes', 'winner', 'radiant_win',
                    'hero_name', 'hero_id', 'team',
                    'gpm', 'xpm', 'tower_damage', 'hero_healing',
                    'lane_efficiency_pct', 'kills', 'deaths', 'assists',
                    'last_hits', 'denies', 'net_worth', 'hero_damage', 'damage_taken',
                    'teamfight_participation', 'actions_per_min', 'won'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for match in matches:
                    match_info = {
                        'match_id': match['match_id'],
                        'tournament': match['tournament'],
                        'radiant_team': match['radiant_team'],
                        'dire_team': match['dire_team'],
                        'duration_minutes': match['duration_minutes'],
                        'winner': match['winner'],
                        'radiant_win': match['radiant_win']
                    }
                    for player in match['players']:
                        row = {**match_info, **player}
                        writer.writerow(row)
            print(f"Saved {len(matches)} matches to CSV: {csv_filename}")
    
    # Clean up checkpoint file on successful completion
    if checkpoint_file and os.path.exists(checkpoint_file):
        try:
            os.remove(checkpoint_file)
            print(f"✓ Cleaned up checkpoint file")
        except:
            pass  # Not critical if cleanup fails
    
    # Print some statistics
    if matches:
        print("\nMatch Statistics:")
        print(f"  Total matches: {len(matches)}")
        
        if include_details and matches:
            # Statistics for detailed data
            total_players = sum(len(m.get('players', [])) for m in matches)
            print(f"  Total players/heroes: {total_players}")
            
            # Count unique tournaments
            tournaments = set(m.get('tournament', 'Unknown') for m in matches)
            print(f"  Unique tournaments: {len(tournaments)}")
            
            # Show sample of data structure
            if matches[0].get('players'):
                print(f"\n  Sample data from first match (ID: {matches[0]['match_id']}):")
                print(f"    Tournament: {matches[0]['tournament']}")
                print(f"    Teams: {matches[0]['radiant_team']} vs {matches[0]['dire_team']}")
                print(f"    Winner: {matches[0]['winner']}")
                print(f"    Duration: {matches[0]['duration_minutes']} minutes")
                print(f"    Players: {len(matches[0]['players'])} heroes")
                print(f"\n  Sample hero data (first player):")
                first_player = matches[0]['players'][0]
                print(f"    Hero: {first_player['hero_name']}")
                print(f"    Team: {first_player['team']}")
                print(f"    GPM: {first_player['gpm']}, XPM: {first_player['xpm']}")
                print(f"    K/D/A: {first_player['kills']}/{first_player['deaths']}/{first_player['assists']}")
                print(f"    Last Hits: {first_player['last_hits']}, Denies: {first_player['denies']}")
                print(f"    Net Worth: {first_player['net_worth']}")
                print(f"    Hero Damage: {first_player['hero_damage']}, Damage Taken: {first_player['damage_taken']}")
                print(f"    APM: {first_player['actions_per_min']}")
        else:
            # Statistics for summary data
            if matches:
                first_match = matches[0]
                last_match = matches[-1]
                print(f"  Newest match: {datetime.fromtimestamp(first_match.get('start_time', 0)).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Oldest match: {datetime.fromtimestamp(last_match.get('start_time', 0)).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Match ID range: {first_match.get('match_id')} to {last_match.get('match_id')}")
    
    print("\nDone!")
    

if __name__ == "__main__":
    main()
