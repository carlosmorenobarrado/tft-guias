#!/usr/bin/env python3
"""
TFT Meta Update Script

Automates the full update cycle when a new patch drops:
1. Downloads new matches from Riot API
2. Regenerates comp_summaries.json
3. Updates guide JSONs with new stats (preserving gameplan/variantes/pivotAlerts)
4. Builds the Astro site
5. Deploys to Cloud Run

Usage:
    python scripts/update-meta.py                    # Full update
    python scripts/update-meta.py --dry-run          # Skip build and deploy
    python scripts/update-meta.py --guides-only      # Only update guide JSONs

Requires:
    RIOT_API_KEY environment variable
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("Error: pandas library not found. Install with: pip install pandas")
    sys.exit(1)


# === Configuration ===
RIOT_API_BASE = "https://europe.api.riotgames.com"
TFT_QUEUE_ID = 1100  # TFT Ranked
MATCHES_PER_PLAYER = 20
RATE_LIMIT_DELAY = 1.2  # seconds between requests
MAX_RETRIES = 3
RETRY_DELAY = 120  # seconds to wait on 429

# Paths
TOP_PLAYERS_CSV = PROJECT_ROOT / "top_players.csv"
COMP_SUMMARIES_JSON = PROJECT_ROOT / "comp_summaries.json"
GUIDES_DIR = PROJECT_ROOT / "src" / "data" / "guides"


class RiotAPIClient:
    """Riot API client with rate limiting and retry logic."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-Riot-Token": api_key,
            "Accept": "application/json"
        })
        self.last_request_time = 0

    def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

    def _request(self, url: str, retries: int = MAX_RETRIES) -> Optional[dict]:
        """Make a request with retry logic for 429 errors."""
        for attempt in range(retries):
            self._rate_limit()

            try:
                response = self.session.get(url)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", RETRY_DELAY))
                    print(f"  Rate limited. Waiting {retry_after}s...")
                    time.sleep(retry_after)
                elif response.status_code == 404:
                    return None
                else:
                    print(f"  Error {response.status_code}: {response.text[:100]}")
                    return None

            except requests.RequestException as e:
                print(f"  Request error: {e}")
                if attempt < retries - 1:
                    time.sleep(5)

        return None

    def get_match_ids(self, puuid: str, count: int = MATCHES_PER_PLAYER) -> list:
        """Get recent match IDs for a player."""
        url = f"{RIOT_API_BASE}/tft/match/v1/matches/by-puuid/{puuid}/ids"
        url += f"?queue={TFT_QUEUE_ID}&count={count}"
        result = self._request(url)
        return result if result else []

    def get_match(self, match_id: str) -> Optional[dict]:
        """Get match details."""
        url = f"{RIOT_API_BASE}/tft/match/v1/matches/{match_id}"
        return self._request(url)


def load_top_players() -> pd.DataFrame:
    """Load top players from CSV."""
    if not TOP_PLAYERS_CSV.exists():
        print(f"Error: {TOP_PLAYERS_CSV} not found")
        sys.exit(1)

    df = pd.read_csv(TOP_PLAYERS_CSV)
    print(f"Loaded {len(df)} top players")
    return df


def download_matches(client: RiotAPIClient, players_df: pd.DataFrame) -> list:
    """Download recent matches for all top players."""
    all_matches = []
    seen_match_ids = set()

    print(f"\nDownloading matches for {len(players_df)} players...")

    for idx, row in players_df.iterrows():
        puuid = row.get("puuid")
        summoner = row.get("summonerName", row.get("gameName", f"Player {idx}"))

        if not puuid:
            print(f"  Skipping {summoner}: no PUUID")
            continue

        print(f"  [{idx+1}/{len(players_df)}] {summoner}...", end=" ", flush=True)

        match_ids = client.get_match_ids(puuid)
        new_matches = 0

        for match_id in match_ids:
            if match_id in seen_match_ids:
                continue

            seen_match_ids.add(match_id)
            match_data = client.get_match(match_id)

            if match_data:
                all_matches.append(match_data)
                new_matches += 1

        print(f"{new_matches} new matches")

    print(f"\nTotal unique matches downloaded: {len(all_matches)}")
    return all_matches


def analyze_comps(matches: list) -> dict:
    """Analyze compositions from match data."""
    comp_stats = defaultdict(lambda: {
        "games": [],
        "placements": [],
        "levels": [],
        "traits": defaultdict(int),
        "items": defaultdict(int)
    })

    for match in matches:
        info = match.get("info", {})
        participants = info.get("participants", [])

        for participant in participants:
            placement = participant.get("placement", 8)
            level = participant.get("level", 8)
            units = participant.get("units", [])
            traits = participant.get("traits", [])

            # Extract core units (4+ cost units)
            core_units = []
            for unit in units:
                char_id = unit.get("character_id", "")
                tier = unit.get("tier", 1)
                # Consider 4+ cost units as core
                if any(x in char_id for x in ["TFT16_"]):
                    core_units.append(char_id)

            # Sort and create comp key (top 3 units by frequency in high elo)
            if len(core_units) >= 3:
                # Take first 3 unique units alphabetically for consistency
                core_key = " | ".join(sorted(set(core_units))[:3])

                stats = comp_stats[core_key]
                stats["games"].append(1)
                stats["placements"].append(placement)
                stats["levels"].append(level)

                # Track traits
                for trait in traits:
                    trait_name = trait.get("name", "")
                    if trait.get("tier_current", 0) > 0:
                        stats["traits"][trait_name] += 1

                # Track items on units
                for unit in units:
                    char_id = unit.get("character_id", "")
                    for item in unit.get("items", []):
                        item_key = f"{char_id}:{item}"
                        stats["items"][item_key] += 1

    # Calculate summary statistics
    summaries = {}
    for comp_key, stats in comp_stats.items():
        n_games = len(stats["games"])
        if n_games < 10:  # Filter low sample size
            continue

        placements = stats["placements"]
        top4_count = sum(1 for p in placements if p <= 4)
        win_count = sum(1 for p in placements if p == 1)

        top4_levels = [stats["levels"][i] for i, p in enumerate(placements) if p <= 4]
        bottom_levels = [stats["levels"][i] for i, p in enumerate(placements) if p > 4]

        # Sort traits and items by frequency
        top_traits = sorted(stats["traits"].items(), key=lambda x: -x[1])[:6]
        top_items = sorted(stats["items"].items(), key=lambda x: -x[1])[:10]

        summaries[comp_key] = {
            "core_units": comp_key.split(" | "),
            "n_games": n_games,
            "top4_rate": round(top4_count / n_games, 3),
            "avg_placement": round(sum(placements) / n_games, 2),
            "win_rate": round(win_count / n_games, 3),
            "avg_level_top4": round(sum(top4_levels) / len(top4_levels), 1) if top4_levels else 0,
            "avg_level_bottom": round(sum(bottom_levels) / len(bottom_levels), 1) if bottom_levels else 0,
            "top_traits": top_traits,
            "top_carry_items": top_items
        }

    # Sort by top4_rate
    summaries = dict(sorted(summaries.items(), key=lambda x: -x[1]["top4_rate"]))

    print(f"\nAnalyzed {len(summaries)} compositions with 10+ games")
    return summaries


def save_comp_summaries(summaries: dict):
    """Save comp summaries to JSON."""
    with open(COMP_SUMMARIES_JSON, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2, ensure_ascii=False)
    print(f"Saved comp summaries to {COMP_SUMMARIES_JSON}")


def load_comp_summaries() -> dict:
    """Load existing comp summaries."""
    if not COMP_SUMMARIES_JSON.exists():
        print(f"Error: {COMP_SUMMARIES_JSON} not found")
        sys.exit(1)

    with open(COMP_SUMMARIES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def update_guide_stats(summaries: dict):
    """Update guide JSONs with new stats, preserving content."""
    if not GUIDES_DIR.exists():
        print(f"Error: {GUIDES_DIR} not found")
        return

    # Create mapping from guide slug to comp key
    slug_to_comp = {
        "annie-tibbers-sylas": "TFT16_Annie | TFT16_AnnieTibbers | TFT16_Sylas",
        "azir-ryze-sylas": "TFT16_Azir | TFT16_Ryze | TFT16_Sylas",
        "kindred-lucian-ornn": "TFT16_Kindred | TFT16_Lucian | TFT16_Ornn",
        "ryze-taric-volibear": "TFT16_Ryze | TFT16_Taric | TFT16_Volibear",
        "fiddlesticks-kindred-lucian": "TFT16_Fiddlesticks | TFT16_Kindred | TFT16_Lucian",
        "annie-tibbers-galio": "TFT16_Annie | TFT16_AnnieTibbers | TFT16_Galio",
    }

    updated_count = 0

    for guide_file in GUIDES_DIR.glob("*.json"):
        slug = guide_file.stem
        comp_key = slug_to_comp.get(slug)

        if not comp_key or comp_key not in summaries:
            print(f"  Skipping {slug}: no matching comp data")
            continue

        # Load existing guide
        with open(guide_file, "r", encoding="utf-8") as f:
            guide = json.load(f)

        comp_data = summaries[comp_key]

        # Update only stats fields
        guide["nGames"] = comp_data["n_games"]
        guide["top4Rate"] = comp_data["top4_rate"]
        guide["winRate"] = comp_data["win_rate"]
        guide["avgPlacement"] = comp_data["avg_placement"]
        guide["avgLevel"] = comp_data["avg_level_top4"]

        # Update traits from data
        trait_map = {
            "TFT16_DarkChild": "Dark Child",
            "TFT16_Sorcerer": "Sorcerer",
            "TFT16_SylasTrait": "Sylas Trait",
            "TFT16_Defender": "Defender",
            "TFT16_Juggernaut": "Juggernaut",
            "TFT16_ShyvanaUnique": "Shyvana Unique",
            "TFT16_Emperor": "Emperor",
            "TFT16_RuneMage": "Rune Mage",
            "TFT16_Shurima": "Shurima",
            "TFT16_Harvester": "Harvester",
            "TFT16_KindredUnique": "Kindred Unique",
            "TFT16_Soulbound": "Soulbound",
            "TFT16_Rapidfire": "Rapidfire",
            "TFT16_Blacksmith": "Blacksmith",
            "TFT16_Warden": "Warden",
            "TFT16_Brawler": "Brawler",
            "TFT16_Freljord": "Freljord",
            "TFT16_Targon": "Targon",
            "TFT16_Invoker": "Invoker",
            "TFT16_Yordle": "Yordle",
            "TFT16_Heroic": "Heroic",
            "TFT16_Demacia": "Demacia",
        }

        new_traits = []
        for trait_id, count in comp_data["top_traits"][:6]:
            trait_name = trait_map.get(trait_id, trait_id.replace("TFT16_", ""))
            # Estimate active count based on frequency
            active_count = 2 if count > comp_data["n_games"] * 0.5 else 1
            new_traits.append({"nombre": trait_name, "count": active_count})

        guide["traits"] = new_traits

        # Save updated guide
        with open(guide_file, "w", encoding="utf-8") as f:
            json.dump(guide, f, indent=2, ensure_ascii=False)

        print(f"  Updated {slug}: {comp_data['n_games']} games, {comp_data['top4_rate']*100:.1f}% top4")
        updated_count += 1

    print(f"\nUpdated {updated_count} guides")


def run_build():
    """Run npm build."""
    print("\nRunning npm build...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Build failed:\n{result.stderr}")
        sys.exit(1)

    print("Build successful")


def run_deploy():
    """Run Cloud Build deploy."""
    print("\nDeploying to Cloud Run...")
    result = subprocess.run(
        ["gcloud", "builds", "submit", "--config", "cloudbuild.yaml"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Deploy failed:\n{result.stderr}")
        sys.exit(1)

    print("Deploy successful")


def main():
    parser = argparse.ArgumentParser(description="Update TFT meta data and deploy")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip build and deploy steps")
    parser.add_argument("--guides-only", action="store_true",
                        help="Only update guide JSONs from existing comp_summaries.json")
    args = parser.parse_args()

    print("=" * 60)
    print("TFT Meta Update Script")
    print(f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if args.guides_only:
        print("\n[--guides-only] Skipping match download, using existing data")
        summaries = load_comp_summaries()
    else:
        # Check for API key
        api_key = os.environ.get("RIOT_API_KEY")
        if not api_key:
            print("Error: RIOT_API_KEY environment variable not set")
            sys.exit(1)

        # Step 1: Download matches
        print("\n[Step 1/5] Downloading matches from Riot API...")
        client = RiotAPIClient(api_key)
        players_df = load_top_players()
        matches = download_matches(client, players_df)

        if not matches:
            print("Error: No matches downloaded")
            sys.exit(1)

        # Step 2: Analyze and save comp summaries
        print("\n[Step 2/5] Analyzing compositions...")
        summaries = analyze_comps(matches)
        save_comp_summaries(summaries)

    # Step 3: Update guides
    print("\n[Step 3/5] Updating guide statistics...")
    update_guide_stats(summaries)

    if args.dry_run:
        print("\n[--dry-run] Skipping build and deploy")
    else:
        # Step 4: Build
        print("\n[Step 4/5] Building site...")
        run_build()

        # Step 5: Deploy
        print("\n[Step 5/5] Deploying to production...")
        run_deploy()

    print("\n" + "=" * 60)
    print("Update complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
