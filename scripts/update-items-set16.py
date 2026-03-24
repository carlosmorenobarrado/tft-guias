#!/usr/bin/env python3
"""
Script to update all item references from old TFT sets to Set 16 items.
This updates both the item IDs in board_completo and the text names in items section.
"""

import json
import os
from pathlib import Path

# Mapping of old item IDs to new Set 16 item IDs
ITEM_ID_MAPPING = {
    # Core items that were removed/replaced
    "TFT_Item_StatikkShiv": "TFT_Item_VoidStaff",
    "TFT_Item_Redemption": "TFT_Item_SpiritVisage",
    "TFT_Item_RunaansHurricane": "TFT_Item_KrakensFury",
    "TFT_Item_FrozenHeart": "TFT_Item_SteadfastHeart",  # Puño de Acero (Sparring Gloves + Chain Vest)
    "TFT_Item_Evenshroud": "TFT_Item_SteadfastHeart",   # Evenshroud no existe, es Steadfast Heart
    "TFT_Item_Leviathan": "TFT_Item_ArchangelsStaff",
    "TFT_Item_NightHarvester": "TFT_Item_Crownguard",
    "TFT_Item_GuardianAngel": "TFT_Item_EdgeOfNight",
    "TFT_Item_SpectralGauntlet": "TFT_Item_SteadfastHeart",
    "TFT_Item_PowerGauntlet": "TFT_Item_SteadfastHeart",
    "TFT_Item_TacticiansRing": "TFT_Item_TacticiansCrown",
    "TFT_Item_EmptyBag": "TFT_Item_ThiefsGloves",  # Empty bag is a placeholder

    # Base components should not appear as final items - replace with appropriate combined items
    "TFT_Item_ChainVest": "TFT_Item_BrambleVest",
    "TFT_Item_BFSword": "TFT_Item_Deathblade",
}

# Mapping of old item names (text) to new Set 16 names
ITEM_NAME_MAPPING = {
    # Core replacements
    "Statikk Shiv": "Void Staff",
    "Redemption": "Spirit Visage",
    "Runaan's Hurricane": "Kraken's Fury",
    "Frozen Heart": "Steadfast Heart",  # Puño de Acero
    "Evenshroud": "Steadfast Heart",    # Evenshroud no existe
    "Leviathan": "Archangel's Staff",
    "Night Harvester": "Crownguard",
    "Guardian Angel": "Edge of Night",
    "Spectral Gauntlet": "Steadfast Heart",
    "Power Gauntlet": "Steadfast Heart",
    "Tactician's Ring": "Tactician's Crown",

    # Also handle variations
    "Statikk": "Void Staff",
    "Shiv": "Void Staff",
}

def update_item_ids_in_units(units: list) -> list:
    """Update item IDs in units list."""
    for unit in units:
        if "items" in unit:
            unit["items"] = [
                ITEM_ID_MAPPING.get(item_id, item_id)
                for item_id in unit["items"]
            ]
    return units

def update_item_names_in_items(items: dict) -> dict:
    """Update item names in the items recommendation section."""
    for carry, item_data in items.items():
        if "core" in item_data:
            item_data["core"] = [
                ITEM_NAME_MAPPING.get(item, item)
                for item in item_data["core"]
            ]
        if "alternativas" in item_data:
            item_data["alternativas"] = [
                ITEM_NAME_MAPPING.get(item, item)
                for item in item_data["alternativas"]
            ]
    return items

def update_tips_text(tips: list) -> list:
    """Update item names mentioned in tips text."""
    updated_tips = []
    for tip in tips:
        for old_name, new_name in ITEM_NAME_MAPPING.items():
            tip = tip.replace(old_name, new_name)
        updated_tips.append(tip)
    return updated_tips

def update_gameplan(gameplan: dict) -> dict:
    """Update item names in gameplan tips."""
    for phase, data in gameplan.items():
        if "tips" in data:
            data["tips"] = update_tips_text(data["tips"])
        if "descripcion" in data:
            for old_name, new_name in ITEM_NAME_MAPPING.items():
                data["descripcion"] = data["descripcion"].replace(old_name, new_name)
    return gameplan

def update_pivot_alerts(alerts: list) -> list:
    """Update item names in pivot alerts."""
    for alert in alerts:
        for old_name, new_name in ITEM_NAME_MAPPING.items():
            if "senal" in alert:
                alert["senal"] = alert["senal"].replace(old_name, new_name)
            if "alternativa" in alert:
                alert["alternativa"] = alert["alternativa"].replace(old_name, new_name)
    return alerts

def update_guide_file(filepath: Path) -> dict:
    """Update a single guide JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        guide = json.load(f)

    changes = []

    # Update board_completo items
    if "board_completo" in guide and "units" in guide["board_completo"]:
        old_units = json.dumps(guide["board_completo"]["units"])
        guide["board_completo"]["units"] = update_item_ids_in_units(guide["board_completo"]["units"])
        if json.dumps(guide["board_completo"]["units"]) != old_units:
            changes.append("board_completo items")

    # Update items recommendations
    if "items" in guide:
        old_items = json.dumps(guide["items"])
        guide["items"] = update_item_names_in_items(guide["items"])
        if json.dumps(guide["items"]) != old_items:
            changes.append("item recommendations")

    # Update gameplan
    if "gameplan" in guide:
        old_gameplan = json.dumps(guide["gameplan"])
        guide["gameplan"] = update_gameplan(guide["gameplan"])
        if json.dumps(guide["gameplan"]) != old_gameplan:
            changes.append("gameplan")

    # Update pivot alerts
    if "pivotAlerts" in guide:
        old_alerts = json.dumps(guide["pivotAlerts"])
        guide["pivotAlerts"] = update_pivot_alerts(guide["pivotAlerts"])
        if json.dumps(guide["pivotAlerts"]) != old_alerts:
            changes.append("pivotAlerts")

    # Save updated guide
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(guide, f, indent=2, ensure_ascii=False)

    return changes

def main():
    script_dir = Path(__file__).parent
    guides_dir = script_dir.parent / "src" / "data" / "guides"

    print("=" * 60)
    print("TFT Set 16 Item Update Script")
    print("=" * 60)
    print()
    print("Item ID Mappings:")
    for old, new in ITEM_ID_MAPPING.items():
        print(f"  {old.replace('TFT_Item_', '')} -> {new.replace('TFT_Item_', '')}")
    print()
    print("Item Name Mappings:")
    for old, new in ITEM_NAME_MAPPING.items():
        print(f"  {old} -> {new}")
    print()
    print("=" * 60)
    print()

    if not guides_dir.exists():
        print(f"Error: Guides directory not found: {guides_dir}")
        return

    json_files = list(guides_dir.glob("*.json"))
    print(f"Found {len(json_files)} guide files to update")
    print()

    for filepath in json_files:
        print(f"Processing: {filepath.name}")
        changes = update_guide_file(filepath)
        if changes:
            print(f"  Updated: {', '.join(changes)}")
        else:
            print(f"  No changes needed")

    print()
    print("=" * 60)
    print("Update complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
