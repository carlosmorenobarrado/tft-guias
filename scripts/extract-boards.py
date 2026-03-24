#!/usr/bin/env python3
"""
Extract complete boards for each comp core from match data.

For each comp core (defined by 3 main units):
- Filters all top-4 matches with that core
- Counts which units accompany the core
- Builds optimal board: 3 core + 6 most frequent support units
- For each unit: character_id, frequency, is_core, tier_habitual, items

Output:
- Enriches comp_summaries.json with board_completo field
- Updates guide JSONs in src/data/guides/ with board_completo section
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

PROJECT_ROOT = Path(__file__).parent.parent
MATCHES_FILE = PROJECT_ROOT / "matches_raw.ndjson"
COMP_SUMMARIES = PROJECT_ROOT / "comp_summaries.json"
GUIDES_DIR = PROJECT_ROOT / "src" / "data" / "guides"

# Mapping from comp slug to comp key in summaries
SLUG_TO_COMP = {
    "annie-tibbers-sylas": "TFT16_Annie | TFT16_AnnieTibbers | TFT16_Sylas",
    "azir-ryze-sylas": "TFT16_Azir | TFT16_Ryze | TFT16_Sylas",
    "kindred-lucian-ornn": "TFT16_Kindred | TFT16_Lucian | TFT16_Ornn",
    "ryze-taric-volibear": "TFT16_Ryze | TFT16_Taric | TFT16_Volibear",
    "fiddlesticks-kindred-lucian": "TFT16_Fiddlesticks | TFT16_Kindred | TFT16_Lucian",
    "annie-tibbers-galio": "TFT16_Annie | TFT16_AnnieTibbers | TFT16_Galio",
}

# Reverse mapping
COMP_TO_SLUG = {v: k for k, v in SLUG_TO_COMP.items()}


def load_matches():
    """Load all matches from NDJSON file."""
    matches = []
    with open(MATCHES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                matches.append(json.loads(line))
    print(f"Loaded {len(matches)} matches")
    return matches


def load_comp_summaries():
    """Load comp summaries."""
    with open(COMP_SUMMARIES, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_top4_participants(matches):
    """Extract all top-4 participants from matches."""
    participants = []
    for match in matches:
        for p in match.get("info", {}).get("participants", []):
            if p.get("placement", 8) <= 4:
                participants.append(p)
    print(f"Found {len(participants)} top-4 participants")
    return participants


def get_participant_units(participant):
    """Get units from a participant with their details."""
    units = []
    for unit in participant.get("units", []):
        units.append({
            "character_id": unit.get("character_id", ""),
            "tier": unit.get("tier", 1),
            "items": unit.get("itemNames", [])
        })
    return units


def has_core(units, core_units):
    """Check if participant has all core units."""
    unit_ids = {u["character_id"] for u in units}
    return all(core in unit_ids for core in core_units)


def analyze_comp_boards(participants, comp_key, core_units):
    """Analyze boards for a specific comp core."""
    # Filter participants with this core
    matching = []
    for p in participants:
        units = get_participant_units(p)
        if has_core(units, core_units):
            matching.append(units)

    if not matching:
        return None

    # Count support unit frequencies
    support_counts = Counter()
    unit_tiers = defaultdict(list)
    unit_items = defaultdict(list)

    for board in matching:
        for unit in board:
            char_id = unit["character_id"]
            support_counts[char_id] += 1
            unit_tiers[char_id].append(unit["tier"])
            unit_items[char_id].extend(unit["items"])

    # Build complete board
    total_games = len(matching)
    board_completo = []

    # First add core units
    for core_id in core_units:
        freq = support_counts[core_id] / total_games if total_games > 0 else 0
        tiers = unit_tiers[core_id]
        tier_habitual = max(set(tiers), key=tiers.count) if tiers else 2

        # Get top 2 items
        items = unit_items[core_id]
        item_counts = Counter(items)
        top_items = [item for item, _ in item_counts.most_common(2)]

        board_completo.append({
            "character_id": core_id,
            "frecuencia": round(freq * 100, 1),
            "es_core": True,
            "tier_habitual": tier_habitual,
            "items": top_items
        })

    # Then add top 6 support units (excluding core)
    support_only = {k: v for k, v in support_counts.items() if k not in core_units}
    top_support = sorted(support_only.items(), key=lambda x: -x[1])[:6]

    for char_id, count in top_support:
        freq = count / total_games if total_games > 0 else 0
        tiers = unit_tiers[char_id]
        tier_habitual = max(set(tiers), key=tiers.count) if tiers else 2

        items = unit_items[char_id]
        item_counts = Counter(items)
        top_items = [item for item, _ in item_counts.most_common(2)]

        board_completo.append({
            "character_id": char_id,
            "frecuencia": round(freq * 100, 1),
            "es_core": False,
            "tier_habitual": tier_habitual,
            "items": top_items
        })

    return {
        "n_games_analyzed": total_games,
        "units": board_completo
    }


def format_item_name(item_id):
    """Convert item ID to readable name."""
    # Remove prefix and convert to readable
    name = item_id.replace("TFT_Item_", "").replace("TFT16_Item_", "")
    # Add spaces before capitals
    result = ""
    for i, c in enumerate(name):
        if c.isupper() and i > 0 and name[i-1].islower():
            result += " "
        result += c
    return result


def format_unit_name(char_id):
    """Convert character ID to readable name."""
    return char_id.replace("TFT16_", "")


def print_board(comp_key, board_data):
    """Print board in readable format."""
    print(f"\n{'='*60}")
    print(f"BOARD COMPLETO: {comp_key}")
    print(f"Partidas analizadas: {board_data['n_games_analyzed']}")
    print(f"{'='*60}")

    print(f"\n{'Unit':<20} {'Freq':<8} {'Core':<6} {'Tier':<6} {'Items'}")
    print("-" * 70)

    for unit in board_data["units"]:
        name = format_unit_name(unit["character_id"])
        freq = f"{unit['frecuencia']}%"
        core = "Yes" if unit["es_core"] else "No"
        tier = f"{unit['tier_habitual']}*"
        items = ", ".join(format_item_name(i) for i in unit["items"][:2]) or "-"
        print(f"{name:<20} {freq:<8} {core:<6} {tier:<6} {items}")


def update_comp_summaries(summaries, boards):
    """Update comp_summaries.json with board data."""
    updated = 0
    for comp_key, board_data in boards.items():
        if comp_key in summaries:
            summaries[comp_key]["board_completo"] = board_data
            updated += 1

    with open(COMP_SUMMARIES, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2, ensure_ascii=False)

    print(f"\nUpdated {updated} comps in comp_summaries.json")


def update_guides(boards):
    """Update guide JSONs with board data."""
    updated = 0

    for guide_file in GUIDES_DIR.glob("*.json"):
        slug = guide_file.stem
        comp_key = SLUG_TO_COMP.get(slug)

        if not comp_key or comp_key not in boards:
            continue

        with open(guide_file, "r", encoding="utf-8") as f:
            guide = json.load(f)

        guide["board_completo"] = boards[comp_key]

        with open(guide_file, "w", encoding="utf-8") as f:
            json.dump(guide, f, indent=2, ensure_ascii=False)

        print(f"  Updated {slug}")
        updated += 1

    print(f"Updated {updated} guide files")


def main():
    print("=" * 60)
    print("TFT Board Extractor")
    print("=" * 60)

    # Load data
    matches = load_matches()
    summaries = load_comp_summaries()
    participants = extract_top4_participants(matches)

    # Analyze boards for each comp
    boards = {}

    print("\nAnalyzing comp boards...")
    for comp_key, comp_data in summaries.items():
        core_units = comp_data.get("core_units", [])
        if len(core_units) < 3:
            continue

        board_data = analyze_comp_boards(participants, comp_key, core_units)
        if board_data and board_data["n_games_analyzed"] >= 10:
            boards[comp_key] = board_data

    print(f"\nExtracted boards for {len(boards)} comps")

    # Print Annie+Tibbers+Sylas board for verification
    annie_key = "TFT16_Annie | TFT16_AnnieTibbers | TFT16_Sylas"
    if annie_key in boards:
        print_board(annie_key, boards[annie_key])
    else:
        print(f"\nWARNING: No board data for {annie_key}")

    # Update files
    print("\n" + "=" * 60)
    print("Updating files...")
    print("=" * 60)

    update_comp_summaries(summaries, boards)
    update_guides(boards)

    print("\nDone!")


if __name__ == "__main__":
    main()
