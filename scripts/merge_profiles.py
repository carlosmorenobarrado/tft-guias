#!/usr/bin/env python3
"""
merge_profiles.py - Merge enriched profiles into guide JSONs

Reads comp_profiles.json and updates each JSON in src/data/guides/
adding the new fields without touching existing content.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
PROFILES_FILE = ROOT / "comp_profiles.json"
GUIDES_DIR = ROOT / "src" / "data" / "guides"


def normalize_unit_name(name: str) -> str:
    """Convert TFT16_AnnieTibbers -> annietibbers for matching"""
    return name.lower().replace("tft16_", "").replace("_", "")


def guide_slug_to_units(slug: str) -> set:
    """Convert guide slug to set of normalized unit names"""
    # slug format: annie-tibbers-sylas
    parts = slug.split("-")
    # Handle multi-word units like "annie-tibbers" -> "annietibbers"
    # We need to be smarter - join all parts and check against known units
    return set(parts)


def profile_id_to_units(comp_id: str) -> set:
    """Convert profile comp_id to set of normalized unit names"""
    # comp_id format: TFT16_Annie | TFT16_AnnieTibbers | TFT16_Sylas
    units = [u.strip() for u in comp_id.split("|")]
    return set(normalize_unit_name(u) for u in units)


def match_guide_to_profile(guide_data: dict, profiles: dict) -> dict | None:
    """Find matching profile for a guide based on core units in board_completo"""
    if "board_completo" not in guide_data:
        return None

    # Get core units from the guide
    core_units = set()
    for unit in guide_data["board_completo"].get("units", []):
        if unit.get("es_core", False):
            core_units.add(normalize_unit_name(unit["character_id"]))

    if not core_units:
        return None

    # Find matching profile
    for comp_id, profile in profiles.items():
        profile_units = profile_id_to_units(comp_id)
        if core_units == profile_units:
            return profile

    # Try partial match if exact match fails (at least 2 units match)
    best_match = None
    best_overlap = 0
    for comp_id, profile in profiles.items():
        profile_units = profile_id_to_units(comp_id)
        overlap = len(core_units & profile_units)
        if overlap >= 2 and overlap > best_overlap:
            best_match = profile
            best_overlap = overlap

    return best_match


def generate_insight(profile: dict) -> str:
    """Generate execution insight text from profile stats"""
    stats = profile["stats"]
    estilo = profile["estilo"]
    economia = profile["economia"]

    parts = []

    # Level insight
    pct_9 = stats["pct_nivel_9_top4"]
    if pct_9 >= 90:
        parts.append(f"El {pct_9:.0f}% de los top-4 llegan a nivel 9+")
    elif pct_9 >= 50:
        parts.append(f"El {pct_9:.0f}% de los top-4 llegan a nivel 9")
    else:
        parts.append(f"Solo el {pct_9:.0f}% necesitan nivel 9 - comp de nivel {profile['nivel_optimo']}")

    # Survival insight
    round_diff = stats["avg_last_round_top4"] - stats["avg_last_round_bottom4"]
    parts.append(f"Los ganadores aguantan {round_diff:.0f} rondas mas de media (hasta ronda {stats['avg_last_round_top4']:.0f})")

    # Economy insight
    gold_top4 = stats["avg_gold_left_top4"]
    gold_bottom4 = stats["avg_gold_left_bottom4"]
    if gold_top4 < gold_bottom4 - 2:
        parts.append(f"Los top-4 terminan con {gold_top4:.0f} oro - rollean mas agresivo que los bottom-4 ({gold_bottom4:.0f} oro)")
    elif gold_top4 > gold_bottom4 + 2:
        parts.append(f"Los top-4 conservan mas oro ({gold_top4:.0f} vs {gold_bottom4:.0f}) - juegan mas econ")

    return ". ".join(parts) + "."


def main():
    print("=" * 60)
    print("Merge Profiles - Integrando perfiles enriquecidos en guias")
    print("=" * 60)

    # Load profiles
    print("\n[1/3] Cargando comp_profiles.json...")
    with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
        profiles = json.load(f)
    print(f"  - {len(profiles)} perfiles cargados")

    # Process each guide
    print("\n[2/3] Procesando guias...")
    guide_files = list(GUIDES_DIR.glob("*.json"))
    print(f"  - {len(guide_files)} guias encontradas")

    updated = 0
    for guide_file in guide_files:
        with open(guide_file, 'r', encoding='utf-8') as f:
            guide = json.load(f)

        # Find matching profile
        profile = match_guide_to_profile(guide, profiles)

        if profile:
            # Add enriched fields
            guide["estilo"] = profile["estilo"]
            guide["economia"] = profile["economia"]
            guide["presion"] = profile["presion"]
            guide["nivel_optimo"] = profile["nivel_optimo"]
            guide["stats_enriquecidas"] = {
                "avg_last_round_top4": profile["stats"]["avg_last_round_top4"],
                "avg_last_round_bottom4": profile["stats"]["avg_last_round_bottom4"],
                "avg_level_top4": profile["stats"]["avg_level_top4"],
                "pct_nivel_9_top4": round(profile["stats"]["pct_nivel_9_top4"] / 100, 2),
                "pct_nivel_10_top4": round(profile["stats"]["pct_nivel_10_top4"] / 100, 2),
                "avg_gold_left_top4": profile["stats"]["avg_gold_left_top4"],
                "avg_players_elim_top4": profile["stats"]["avg_players_elim_top4"],
                "avg_damage_top4": profile["stats"]["avg_damage_top4"]
            }
            guide["insight_ejecucion"] = generate_insight(profile)

            # Write back
            with open(guide_file, 'w', encoding='utf-8') as f:
                json.dump(guide, f, indent=2, ensure_ascii=False)

            print(f"  [OK] {guide_file.name} <- {profile['estilo']}, {profile['economia']}, {profile['presion']}")
            updated += 1
        else:
            print(f"  [--] {guide_file.name} - no matching profile found")

    print(f"\n[3/3] Resumen")
    print(f"  - Guias actualizadas: {updated}/{len(guide_files)}")
    print("\n" + "=" * 60)
    print("[COMPLETADO]")
    print("=" * 60)


if __name__ == "__main__":
    main()
