#!/usr/bin/env python3
"""
Fetch pro matches from OpenDota API for the last 3 months.
Rate limited to stay well below 1200 calls/minute (targeting ~600 calls/min).
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys
from tqdm import tqdm


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
            
            detailed_matches = []
            failed_matches = []
            
            # Progress bar for detailed fetching
            with tqdm(total=len(all_matches), desc="Fetching details", unit=" matches", dynamic_ncols=True) as pbar:
                for match in all_matches:
                    match_id = match['match_id']
                    details = self.get_match_details(match_id)
                    if details:
                        detailed_matches.append(details)
                    else:
                        failed_matches.append(match_id)
                    
                    pbar.update(1)
                    pbar.set_postfix_str(f"{len(detailed_matches)} success, {len(failed_matches)} failed")
                    
            print(f"\n✓ Fetched details for {len(detailed_matches)}/{len(all_matches)} matches")
            if failed_matches:
                print(f"  ⚠ Failed to fetch {len(failed_matches)} matches: {failed_matches[:5]}{'...' if len(failed_matches) > 5 else ''}")
            
            return detailed_matches
            
        return all_matches
        
    def save_matches(self, matches: List[Dict], filename: str):
        """Save matches to JSON file."""
        with open(filename, 'w') as f:
            json.dump(matches, f, indent=2)
        print(f"\nSaved {len(matches)} matches to {filename}")
        

def main():
    """Main function to fetch pro matches."""
    # Check for API key
    if len(sys.argv) < 2:
        print("Usage: python fetch_opendota_matches.py <API_KEY> [months] [include_details]")
        print("  API_KEY: Your OpenDota API key")
        print("  months: Number of months to look back (default: 3)")
        print("  include_details: 'yes' to fetch full match details (default: no)")
        sys.exit(1)
        
    api_key = sys.argv[1]
    months = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    include_details = len(sys.argv) > 3 and sys.argv[3].lower() in ['yes', 'true', '1']
    
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
    
    # Print some statistics
    if matches:
        print("\nMatch Statistics:")
        print(f"  Total matches: {len(matches)}")
        if matches:
            first_match = matches[0]
            last_match = matches[-1]
            print(f"  Newest match: {datetime.fromtimestamp(first_match.get('start_time', 0)).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Oldest match: {datetime.fromtimestamp(last_match.get('start_time', 0)).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Match ID range: {first_match.get('match_id')} to {last_match.get('match_id')}")
    
    print("\nDone!")
    

if __name__ == "__main__":
    main()
