#!/usr/bin/env python3
"""
fix_items.py - Fix invented items in guide JSONs

Replaces invented items with the most frequent real item for each champion
based on top-4 placement data from matches_raw.ndjson.
"""

import json
import glob
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
MATCHES_FILE = ROOT / "matches_raw.ndjson"
GUIDES_DIR = ROOT / "src" / "data" / "guides"


def load_real_items():
    """Load all real item names from the dataset"""
    items = set()
    with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            m = json.loads(line)
            for p in m['info']['participants']:
                for u in p.get('units', []):
                    for item in u.get('itemNames', []):
                        items.add(item)
    return items


def load_champion_items_top4():
    """Load most frequent items per champion in top-4 placements"""
    champion_items = defaultdict(Counter)

    with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            m = json.loads(line)
            for p in m['info']['participants']:
                if p['placement'] <= 4:
                    for u in p.get('units', []):
                        char_id = u.get('character_id', '')
                        for item in u.get('itemNames', []):
                            champion_items[char_id][item] += 1

    return champion_items


def get_best_replacement(champion_id, current_items, champion_items, real_items):
    """Get the best replacement item for a champion that isn't already in their build"""
    if champion_id not in champion_items:
        return None

    # Get items already in the build (real ones)
    existing_items = set(i for i in current_items if i in real_items)

    # Find most frequent item not already in build
    for item, count in champion_items[champion_id].most_common():
        if item not in existing_items:
            return item

    return None


def main():
    print("=" * 60)
    print("Fix Items - Corrigiendo items inventados en guias")
    print("=" * 60)

    # Load data
    print("\n[1/4] Cargando items reales del dataset...")
    real_items = load_real_items()
    print(f"  - {len(real_items)} items reales encontrados")

    print("\n[2/4] Cargando items por campeon en top-4...")
    champion_items = load_champion_items_top4()
    print(f"  - {len(champion_items)} campeones con datos de items")

    # Process guides
    print("\n[3/4] Procesando guias...")
    guide_files = list(GUIDES_DIR.glob("*.json"))

    total_fixes = 0
    fixes_log = []

    for guide_file in guide_files:
        with open(guide_file, 'r', encoding='utf-8') as f:
            guide = json.load(f)

        modified = False

        # Fix board_completo items
        if 'board_completo' in guide and 'units' in guide['board_completo']:
            for unit in guide['board_completo']['units']:
                char_id = unit.get('character_id', '')
                items = unit.get('items', [])

                new_items = []
                for item in items:
                    if item and item not in real_items:
                        replacement = get_best_replacement(char_id, items, champion_items, real_items)
                        if replacement:
                            fixes_log.append(f"  {guide_file.name} | {char_id}: {item} -> {replacement}")
                            new_items.append(replacement)
                            total_fixes += 1
                            modified = True
                        else:
                            new_items.append(item)  # Keep if no replacement found
                    else:
                        new_items.append(item)

                unit['items'] = new_items

        # Fix carries items if present
        if 'carries' in guide:
            for carry in guide['carries']:
                char_id = carry.get('unidad', '')

                for items_key in ['items_ideales', 'items_alternativos']:
                    items = carry.get(items_key, [])
                    new_items = []

                    for item in items:
                        if item and item not in real_items:
                            replacement = get_best_replacement(char_id, items, champion_items, real_items)
                            if replacement:
                                fixes_log.append(f"  {guide_file.name} | {char_id}: {item} -> {replacement}")
                                new_items.append(replacement)
                                total_fixes += 1
                                modified = True
                            else:
                                new_items.append(item)
                        else:
                            new_items.append(item)

                    if items_key in carry:
                        carry[items_key] = new_items

        # Save if modified
        if modified:
            with open(guide_file, 'w', encoding='utf-8') as f:
                json.dump(guide, f, indent=2, ensure_ascii=False)

    print("\n[4/4] Correcciones aplicadas:")
    for fix in fixes_log:
        print(fix)

    print("\n" + "=" * 60)
    print(f"[COMPLETADO] {total_fixes} items corregidos en {len(guide_files)} guias")
    print("=" * 60)


if __name__ == "__main__":
    main()
