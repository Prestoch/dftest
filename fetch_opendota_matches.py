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
    
    def __init__(self, api_key: str, rate_limit: int = 600):
        """
        Initialize the fetcher.
        
        Args:
            api_key: OpenDota API key
            rate_limit: Maximum requests per minute (default 600, well below 1200 limit)
        """
        self.api_key = api_key
        self.base_url = "https://api.opendota.com/api"
        self.rate_limit = rate_limit
        self.min_delay = 60.0 / rate_limit  # Minimum seconds between requests
        self.last_request_time = 0
        self.request_count = 0
        self.session = requests.Session()
        self.hero_names = self._load_hero_names()
        
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
        
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a rate-limited request to OpenDota API.
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            
        Returns:
            JSON response or None if failed
        """
        self._rate_limit_wait()
        
        if params is None:
            params = {}
        params['api_key'] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            self.request_count += 1
            
            if self.request_count % 100 == 0:
                print(f"  Progress: {self.request_count} requests made")
                
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {endpoint}: {e}")
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
    
    def _get_role_name(self, lane_role: Optional[int], player_slot: int, is_roaming: bool = False) -> str:
        """
        Determine role name from available data.
        
        In OpenDota API:
        - lane_role: 1=Safe Lane, 2=Mid, 3=Off Lane, 4=Jungle
        - player_slot: Can be 0-9 (sequential) or 0-4, 128-132 (encoded)
        - Players within each team are typically ordered by farm priority (pos 1-5)
        
        Args:
            lane_role: Lane role from API (1-4)
            player_slot: Player slot number (0-9 or encoded 0-4, 128-132)
            is_roaming: Whether player was roaming
        """
        # Decode player_slot to get position within team (0-4)
        if player_slot >= 128:
            # Encoded format: Dire is 128-132
            team_position = player_slot - 128
        elif player_slot >= 5:
            # Sequential format: Dire is 5-9
            team_position = player_slot - 5
        else:
            # Radiant is always 0-4
            team_position = player_slot
        
        # Try to determine role from lane_role first
        if lane_role == 1:
            return "Carry (pos 1)"
        elif lane_role == 2:
            return "Mid (pos 2)"
        elif lane_role == 3:
            return "Offlane (pos 3)"
        elif lane_role == 4 or is_roaming:
            # Jungle or roaming - could be pos 4 or 5
            # Use team position to distinguish
            if team_position >= 4:
                return "Hard Support (pos 5)"
            else:
                return "Support (pos 4)"
        
        # Fallback: use team position (farm priority order)
        # Players are typically ordered by position within their team
        position_map = {
            0: "Carry (pos 1)",
            1: "Mid (pos 2)",
            2: "Offlane (pos 3)",
            3: "Support (pos 4)",
            4: "Hard Support (pos 5)"
        }
        
        return position_map.get(team_position, f"Unknown (slot {player_slot})")
    
    def extract_match_data(self, match_details: Dict) -> Optional[Dict]:
        """
        Extract only the required fields from match details.
        
        Args:
            match_details: Full match details from API
            
        Returns:
            Dictionary with only required fields
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
                lane_data = player.get('lane', {})
                
                # Get player slot and role information
                player_slot = player.get('player_slot', i)
                lane_role = player.get('lane_role')
                is_roaming = player.get('is_roaming', False)
                
                player_data = {
                    'hero_name': hero_name,
                    'hero_id': hero_id,
                    'team': team_name,
                    'role': self._get_role_name(lane_role, player_slot, is_roaming),
                    'player_slot': player_slot,  # Adding this for debugging
                    'gpm': player.get('gold_per_min', 0),
                    'xpm': player.get('xp_per_min', 0),
                    'tower_damage': player.get('tower_damage', 0),
                    'hero_healing': player.get('hero_healing', 0),
                    'lane_efficiency_pct': lane_efficiency,
                    'kills': player.get('kills', 0),
                    'deaths': player.get('deaths', 0),
                    'assists': player.get('assists', 0),
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
        
    def fetch_recent_pro_matches(self, months: int = 3, include_details: bool = False) -> List[Dict]:
        """
        Fetch all pro matches from the last N months.
        
        Args:
            months: Number of months to look back
            include_details: Whether to fetch full match details (much slower)
            
        Returns:
            List of all pro matches
        """
        # Calculate timestamp for N months ago
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        cutoff_timestamp = int(cutoff_date.timestamp())
        
        print(f"Fetching pro matches since {cutoff_date.strftime('%Y-%m-%d')}")
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
                
            # Filter matches by date
            recent_matches = []
            for match in matches:
                match_time = match.get('start_time', 0)
                if match_time >= cutoff_timestamp:
                    recent_matches.append(match)
                else:
                    pbar.set_postfix_str(f"Reached cutoff date - {len(all_matches)} total matches")
                    break
                    
            if not recent_matches:
                pbar.set_postfix_str(f"Complete - {len(all_matches)} total matches")
                break
                
            all_matches.extend(recent_matches)
            pbar.update(1)
            
            # If we got fewer recent matches than total matches, we've gone past our cutoff
            if len(recent_matches) < len(matches):
                break
                
            # Set up for next page
            less_than_match_id = matches[-1]['match_id']
            
            # Safety check: don't fetch more than 10,000 matches
            if len(all_matches) >= 10000:
                pbar.set_postfix_str(f"Reached 10k limit - {len(all_matches)} matches")
                break
        
        pbar.close()
                
        elapsed_time = time.time() - start_time
        print(f"✓ Fetched {len(all_matches)} pro matches in {elapsed_time:.1f} seconds")
        print(f"  Made {self.request_count} API requests")
        print(f"  Average rate: {self.request_count / (elapsed_time / 60):.1f} requests/minute")
        
        # Optionally fetch detailed match data
        if include_details and all_matches:
            print(f"\nPhase 2: Fetching detailed data for {len(all_matches)} matches...")
            print("This will take a while...\n")
            
            extracted_matches = []
            failed_matches = []
            
            # Progress bar for detailed fetching
            with tqdm(total=len(all_matches), desc="Fetching details", unit=" matches", dynamic_ncols=True) as pbar:
                for match in all_matches:
                    match_id = match['match_id']
                    details = self.get_match_details(match_id)
                    
                    if details:
                        # Extract only the required fields
                        extracted = self.extract_match_data(details)
                        if extracted:
                            extracted_matches.append(extracted)
                        else:
                            failed_matches.append(match_id)
                    else:
                        failed_matches.append(match_id)
                    
                    pbar.update(1)
                    pbar.set_postfix_str(f"{len(extracted_matches)} success, {len(failed_matches)} failed")
                    
            print(f"\n✓ Fetched details for {len(extracted_matches)}/{len(all_matches)} matches")
            if failed_matches:
                print(f"  ⚠ Failed to fetch {len(failed_matches)} matches: {failed_matches[:5]}{'...' if len(failed_matches) > 5 else ''}")
            
            return extracted_matches
            
        return all_matches
        
    def save_matches(self, matches: List[Dict], filename: str):
        """Save matches to JSON file."""
        with open(filename, 'w') as f:
            json.dump(matches, f, indent=2)
        print(f"\nSaved {len(matches)} matches to {filename}")
    
    def save_matches_csv(self, matches: List[Dict], filename: str):
        """Save matches to CSV file with flattened player data."""
        import csv
        
        if not matches:
            print("No matches to save to CSV")
            return
        
        csv_filename = filename.replace('.json', '.csv')
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            # Define CSV columns
            fieldnames = [
                'match_id', 'tournament', 'radiant_team', 'dire_team',
                'duration_minutes', 'winner', 'radiant_win',
                'hero_name', 'hero_id', 'team', 'role', 'player_slot',
                'gpm', 'xpm', 'tower_damage', 'hero_healing',
                'lane_efficiency_pct', 'kills', 'deaths', 'assists', 'won'
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Flatten data: one row per player
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
        

def main():
    """Main function to fetch pro matches."""
    # Check for API key
    if len(sys.argv) < 2:
        print("Usage: python fetch_opendota_matches.py <API_KEY> [months] [include_details]")
        print("  API_KEY: Your OpenDota API key")
        print("  months: Number of months to look back (default: 3)")
        print("  include_details: 'yes' to fetch detailed match data (default: yes)")
        print("\nFetched data includes:")
        print("  - Match ID, Team/Tournament Names")
        print("  - Hero names, roles (Carry, Mid, Offlane, Support)")
        print("  - GPM, XPM, Tower Damage, Healing")
        print("  - Lane advantages, K/D/A")
        print("  - Game Duration, Match Winner")
        sys.exit(1)
        
    api_key = sys.argv[1]
    months = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    # Default to fetching details (include_details=True by default)
    include_details = True
    if len(sys.argv) > 3:
        include_details = sys.argv[3].lower() not in ['no', 'false', '0']
    
    # Create fetcher with rate limit of 600 req/min (50% of max)
    fetcher = OpenDotaFetcher(api_key, rate_limit=600)
    
    # Fetch matches
    print("="*60)
    matches = fetcher.fetch_recent_pro_matches(months=months, include_details=include_details)
    print("="*60)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    detail_suffix = "_detailed" if include_details else "_summary"
    filename = f"opendota_pro_matches_{months}months{detail_suffix}_{timestamp}.json"
    
    # Save to file
    fetcher.save_matches(matches, filename)
    
    # Also save as CSV if we have detailed data
    if include_details and matches:
        fetcher.save_matches_csv(matches, filename)
    
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
