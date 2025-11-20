#!/usr/bin/env python3
"""
List tournaments from OpenDota match data to help you decide which to skip.
"""

import json
import sys
from collections import Counter


def list_tournaments_from_file(filename: str):
    """List all tournaments in a JSON file with match counts."""
    print(f"Reading: {filename}")
    
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found!")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file: {e}")
        return
    
    # Ensure it's a list
    if not isinstance(data, list):
        data = [data]
    
    # Count matches per tournament
    tournament_counts = Counter()
    for match in data:
        tournament = match.get('tournament', 'Unknown')
        tournament_counts[tournament] += 1
    
    # Display results
    print("\n" + "="*70)
    print("TOURNAMENTS IN FILE")
    print("="*70)
    print(f"{'Matches':<10} {'Tournament Name':<60}")
    print("-"*70)
    
    for tournament, count in tournament_counts.most_common():
        print(f"{count:<10} {tournament:<60}")
    
    print("-"*70)
    print(f"Total: {len(tournament_counts)} unique tournaments, {sum(tournament_counts.values())} matches")
    print()
    
    # Show examples for skip list
    print("="*70)
    print("TO SKIP TOURNAMENTS, USE:")
    print("="*70)
    print()
    print("When running fetch_opendota_matches.py, use the 4th parameter:")
    print()
    print("Examples:")
    print('  python fetch_opendota_matches.py YOUR_KEY 3 yes "DPC"')
    print('  python fetch_opendota_matches.py YOUR_KEY 3 yes "Regional,Qualifier"')
    print('  python fetch_opendota_matches.py YOUR_KEY 3 yes "BTS,ESL"')
    print()
    print("Tips:")
    print("  • Use partial names (case-insensitive)")
    print("  • Comma-separate multiple terms")
    print("  • 'dpc' will match 'DPC WEU 2023', 'DPC CN', etc.")
    print("  • Saves API credits by not fetching match details")
    print()


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python list_tournaments.py <json_file>")
        print()
        print("This script lists all tournaments in your match data file.")
        print("Use it to decide which tournaments to skip when fetching new data.")
        print()
        print("Example:")
        print("  python list_tournaments.py opendota_pro_matches_3months_detailed_20231119.json")
        sys.exit(1)
    
    filename = sys.argv[1]
    list_tournaments_from_file(filename)


if __name__ == "__main__":
    main()
