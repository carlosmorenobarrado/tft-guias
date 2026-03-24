#!/usr/bin/env python3
"""
cluster_by_traits.py - Agrupa campeones por trait dominante de cada comp

Lee champions_set16.json y comp_summaries.json para generar caminos
de early/mid/late game basados en traits compartidos.

Soporta overrides humanos desde comp_overrides.json.

Output: comp_paths.json
"""

import json
import os
from collections import Counter, defaultdict

# Traits únicos de campeones específicos (1 solo campeón los tiene)
UNIQUE_TRAITS = {
    "TFT16_Harvester",      # Fiddlesticks
    "TFT16_KindredUnique",  # Kindred
    "TFT16_Soulbound",      # Lucian (Kindred) - pareja única
    "TFT16_ShyvanaUnique",  # Shyvana
    "TFT16_DarkChild",      # Annie
    "TFT16_SylasTrait",     # Sylas
    "TFT16_Glutton",        # Tahm Kench
    "TFT16_TheBoss",        # Sett
    "TFT16_Eternal",        # Kindred
    "TFT16_Blacksmith",     # Ornn
    "TFT16_Emperor",        # Azir
    "TFT16_Chronokeeper",   # Zilean
    "TFT16_Dragonborn",     # Shyvana
    "TFT16_Heroic",         # Braum
    "TFT16_HexMech",        # Rumble+Tristana
    "TFT16_StarForger",     # Aurelion Sol
    "TFT16_Riftscourge",    # Baron Nashor
    "TFT16_WorldEnder",     # Aatrox
    "TFT16_Chainbreaker",   # Sylas
    "TFT16_RuneMage",       # Ryze
    "TFT16_Huntress",       # Diana
    "TFT16_Assimilator",    # Kayn
    "TFT16_Ascendant",      # Xerath
    "TFT16_Caretaker",      # Maokai
    "TFT16_Immortal",       # Fiddlesticks
    "TFT16_Teamup_SingedTeemo",  # Team-up
}

# Mapeo de traits API (Riot) a traits de CommunityDragon
TRAIT_API_TO_CDRAGON = {
    "TFT16_Sorcerer": "TFT16_Sorcerer",  # En API es Sorcerer, en CDragon también
    "TFT16_Arcanist": "TFT16_Sorcerer",  # Arcanist es el nombre display, API usa Sorcerer
    "TFT16_Rapidfire": "TFT16_Rapidfire",
    "TFT16_Quickstriker": "TFT16_Rapidfire",
}


def load_overrides():
    """Carga overrides humanos si existen"""
    override_path = "comp_overrides.json"
    if os.path.exists(override_path):
        with open(override_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_matches_frequency():
    """
    Lee matches_raw.ndjson y calcula frecuencia de cada campeón en top-4.
    Retorna dict: {character_id: frecuencia_top4}
    """
    print("Cargando frecuencias de matches_raw.ndjson...")

    champion_top4 = Counter()
    champion_total = Counter()

    with open("matches_raw.ndjson", "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            match = json.loads(line)

            for participant in match.get("info", {}).get("participants", []):
                placement = participant.get("placement", 8)
                is_top4 = placement <= 4

                for unit in participant.get("units", []):
                    char_id = unit.get("character_id", "")
                    if char_id.startswith("TFT16_"):
                        champion_total[char_id] += 1
                        if is_top4:
                            champion_top4[char_id] += 1

    # Calcular frecuencia como ratio
    frequencies = {}
    for char_id, total in champion_total.items():
        if total > 0:
            frequencies[char_id] = champion_top4[char_id] / total

    print(f"  Procesados {len(frequencies)} campeones únicos")
    return frequencies


def find_dominant_trait(comp_data, champions_by_trait):
    """
    Encuentra el trait dominante de una comp usando top_traits.
    Excluye traits únicos y busca el trait con más unidades
    que tenga campeones en múltiples costes.
    """
    top_traits = comp_data.get("top_traits", [])

    for trait_tuple in top_traits:
        trait = trait_tuple[0]  # El apiName del trait

        # Saltar traits únicos
        if trait in UNIQUE_TRAITS or "Unique" in trait:
            continue

        # Verificar que el trait tenga campeones en diferentes costes
        trait_champs = champions_by_trait.get(trait, [])
        if not trait_champs:
            continue

        costs = set(c["coste"] for c in trait_champs)

        # Preferir traits con campeones en al menos 2 rangos de coste
        if len(costs) >= 2:
            trait_display = trait.replace("TFT16_", "")
            return trait, trait_display

    # Fallback: usar el primer trait no-único
    for trait_tuple in top_traits:
        trait = trait_tuple[0]
        if trait not in UNIQUE_TRAITS and "Unique" not in trait:
            trait_display = trait.replace("TFT16_", "")
            return trait, trait_display

    return None, None


def normalize_comp_key(comp_key):
    """Normaliza el key de la comp para matching con overrides"""
    # Reemplazar " | " con "|" para matching
    return comp_key.replace(" | ", "|")


def main():
    # 1. Cargar datos
    print("Cargando champions_set16.json...")
    with open("champions_set16.json", "r", encoding="utf-8") as f:
        champions = json.load(f)

    print("Cargando comp_summaries.json...")
    with open("comp_summaries.json", "r", encoding="utf-8") as f:
        comp_summaries = json.load(f)

    # Cargar overrides humanos
    overrides = load_overrides()
    if overrides:
        print(f"Cargados {len(overrides)} overrides humanos")

    # Crear índices
    champions_by_id = {c["id"]: c for c in champions}
    champions_by_trait = defaultdict(list)
    for champ in champions:
        for trait in champ.get("traits_raw", []):
            champions_by_trait[trait].append(champ)

    # Debug: mostrar traits disponibles
    print(f"  Traits con campeones: {len(champions_by_trait)}")

    # Cargar frecuencias de partidas reales
    frequencies = load_matches_frequency()

    # 2. Procesar cada comp
    print(f"\nProcesando {len(comp_summaries)} comps...")
    comp_paths = {}

    for comp_key, comp_data in comp_summaries.items():
        core_units = comp_data.get("core_units", [])

        if not core_units:
            continue

        # Verificar si hay override para esta comp
        normalized_key = normalize_comp_key(comp_key)
        override = overrides.get(normalized_key, {})
        has_override = bool(override.get("trait_dominante_override"))

        if has_override:
            # Usar trait del override
            dominant_trait = override["trait_dominante_override"]
            trait_display = override.get("trait_display_override", dominant_trait.replace("TFT16_", ""))
            print(f"  OVERRIDE: {comp_key} -> {trait_display}")
        else:
            # Detectar automáticamente
            dominant_trait, trait_display = find_dominant_trait(
                comp_data, champions_by_trait
            )

        if not dominant_trait:
            print(f"  SKIP: {comp_key} - no se encontró trait dominante")
            continue

        # Obtener todos los campeones con ese trait
        trait_champions = champions_by_trait.get(dominant_trait, [])

        if not trait_champions:
            # Intentar sin prefijo o con mapeo
            mapped_trait = TRAIT_API_TO_CDRAGON.get(dominant_trait, dominant_trait)
            trait_champions = champions_by_trait.get(mapped_trait, [])

        if not trait_champions:
            print(f"  SKIP: {comp_key} - no hay campeones con trait {dominant_trait}")
            continue

        # Agrupar por coste y añadir frecuencias
        early = []  # coste 1-2
        mid = []    # coste 3
        core = []   # coste 4-5+

        for champ in trait_champions:
            champ_id = champ["id"]
            freq = frequencies.get(champ_id, 0)

            champ_entry = {
                "character_id": champ_id,
                "nombre": champ["nombre"],
                "coste": champ["coste"],
                "traits": champ["traits"],
                "frecuencia_top4": round(freq, 3)
            }

            # Marcar si es parte del core
            if champ_id in core_units:
                champ_entry["es_core"] = True

            cost = champ["coste"]
            if cost <= 2:
                early.append(champ_entry)
            elif cost == 3:
                mid.append(champ_entry)
            else:
                core.append(champ_entry)

        # Ordenar cada grupo por frecuencia descendente
        early.sort(key=lambda x: -x["frecuencia_top4"])
        mid.sort(key=lambda x: -x["frecuencia_top4"])
        core.sort(key=lambda x: -x["frecuencia_top4"])

        # Construir entrada del path
        path_entry = {
            "trait_dominante": dominant_trait,
            "trait_display": trait_display,
            "core_units": core_units,
            "early": early,
            "mid": mid,
            "core": core,
        }

        # Añadir campos de override si existen
        if override:
            path_entry["opener_ideal"] = override.get("opener_ideal")
            path_entry["opener_alternativo"] = override.get("opener_alternativo")
            path_entry["validado_por_humano"] = True
            path_entry["nota_validacion"] = override.get("nota_validacion")
            if has_override:
                path_entry["trait_override"] = True
        else:
            path_entry["opener_ideal"] = None
            path_entry["opener_alternativo"] = None
            path_entry["validado_por_humano"] = False

        comp_paths[comp_key] = path_entry

    # 3. Guardar resultado
    output_path = "comp_paths.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(comp_paths, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado: {output_path}")
    print(f"Total comps procesadas: {len(comp_paths)}")

    # Contar validadas
    validadas = sum(1 for p in comp_paths.values() if p.get("validado_por_humano"))
    print(f"Comps validadas por humano: {validadas}")

    # Mostrar resumen de comps con override
    print(f"\n{'='*50}")
    print("COMPS CON OVERRIDE HUMANO")
    print(f"{'='*50}")

    for comp_key, path in comp_paths.items():
        if path.get("validado_por_humano"):
            override_marker = " [OVERRIDE]" if path.get("trait_override") else ""
            print(f"\n{comp_key}")
            print(f"  Trait: {path['trait_display']}{override_marker}")
            print(f"  Opener ideal: {path.get('opener_ideal')}")
            print(f"  Early: {len(path['early'])} campeones")

if __name__ == "__main__":
    main()
