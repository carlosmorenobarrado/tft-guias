#!/usr/bin/env python3
"""
fetch_champions.py - Descarga campeones del Set 16 desde CommunityDragon

Extrae todos los campeones del Set 16 con sus stats, traits y habilidades.
Usa CommunityDragon porque tiene datos más completos que Data Dragon oficial.

Output: champions_set16.json
"""

import json
import requests
from collections import Counter

def main():
    # 1. Verificar versión de Data Dragon (para referencia)
    print("Verificando versión actual de Data Dragon...")
    versions_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    versions = requests.get(versions_url).json()
    latest = versions[0]
    print(f"Versión Data Dragon: {latest}")

    # 2. Descargar de CommunityDragon (datos más completos)
    print(f"\nDescargando datos de CommunityDragon...")
    cdragon_url = "https://raw.communitydragon.org/latest/cdragon/tft/en_us.json"
    response = requests.get(cdragon_url)

    if response.status_code != 200:
        print(f"Error descargando datos: {response.status_code}")
        return

    data = response.json()
    set16 = data.get("sets", {}).get("16", {})

    if not set16:
        print("Error: No se encontró el Set 16")
        return

    # También descargar versión es_ES para nombres en español
    print("Descargando nombres en español...")
    cdragon_es_url = "https://raw.communitydragon.org/latest/cdragon/tft/es_es.json"
    try:
        data_es = requests.get(cdragon_es_url).json()
        set16_es = data_es.get("sets", {}).get("16", {})
        champs_es = {c["apiName"]: c["name"] for c in set16_es.get("champions", []) if c.get("apiName")}
        traits_es_data = set16_es.get("traits", [])
        traits_es = {t["apiName"]: t["name"] for t in traits_es_data if t.get("apiName")}
    except:
        champs_es = {}
        traits_es = {}

    # 3. Extraer traits disponibles (para mapeo)
    traits_data = set16.get("traits", [])
    trait_name_map = {}  # "Yordle" -> "TFT16_Yordle"
    for trait in traits_data:
        api_name = trait.get("apiName", "")
        display_name = trait.get("name", "")
        if api_name and display_name:
            # El trait en los datos usa nombre sin prefijo
            trait_name_map[display_name] = api_name

    # 4. Procesar campeones
    raw_champions = set16.get("champions", [])
    champions = []
    all_traits = []

    for champ in raw_champions:
        api_name = champ.get("apiName", "")

        # Solo campeones del Set 16 con traits (excluir items/props)
        if not api_name.startswith("TFT16_"):
            continue

        traits_list = champ.get("traits", [])
        if not traits_list:
            continue

        cost = champ.get("cost", 1)
        if cost > 5:  # Excluir items especiales
            continue

        # Mapear traits a IDs completos (TFT16_)
        traits_raw = []
        traits_display = []
        for trait_name in traits_list:
            # Buscar el apiName del trait
            trait_api = trait_name_map.get(trait_name, f"TFT16_{trait_name}")
            traits_raw.append(trait_api)
            traits_display.append(trait_name)
            all_traits.append(trait_name)

        # Extraer stats
        stats_raw = champ.get("stats", {})
        stats = {
            "hp": stats_raw.get("hp", 0),
            "damage": stats_raw.get("damage", 0),
            "armor": stats_raw.get("armor", 0),
            "mr": stats_raw.get("magicResist", 0),
            "attack_speed": stats_raw.get("attackSpeed", 0)
        }

        # Extraer habilidad
        ability_data = champ.get("ability", {})
        habilidad = {
            "nombre": ability_data.get("name", ""),
            "descripcion": ability_data.get("desc", "")
        }

        # Nombre en español si está disponible
        nombre = champs_es.get(api_name, champ.get("name", api_name.replace("TFT16_", "")))

        # Construir objeto campeón
        champion = {
            "id": api_name,
            "nombre": nombre,
            "coste": cost,
            "traits": traits_display,
            "traits_raw": traits_raw,
            "habilidad": habilidad,
            "stats": stats
        }

        champions.append(champion)

    # Ordenar por coste y luego por nombre
    champions.sort(key=lambda x: (x["coste"], x["nombre"]))

    # 5. Guardar JSON
    output_path = "champions_set16.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(champions, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado: {output_path}")

    # 6. Mostrar estadísticas
    print(f"\n{'='*50}")
    print(f"RESUMEN DE CAMPEONES SET 16")
    print(f"{'='*50}")
    print(f"\nTotal campeones encontrados: {len(champions)}")

    # Conteo de traits
    trait_counts = Counter(all_traits)
    print(f"\n--- TRAITS ÚNICOS ({len(trait_counts)}) ---")
    for trait, count in sorted(trait_counts.items(), key=lambda x: -x[1]):
        print(f"  {trait}: {count} campeones")

    # Campeones por coste
    print(f"\n--- CAMPEONES POR COSTE ---")
    cost_groups = {}
    for champ in champions:
        cost = champ["coste"]
        if cost not in cost_groups:
            cost_groups[cost] = []
        cost_groups[cost].append(champ["nombre"])

    for cost in sorted(cost_groups.keys()):
        print(f"  Coste {cost}: {len(cost_groups[cost])} campeones")

    # Top 5 más caros
    print(f"\n--- 5 CAMPEONES MÁS CAROS ---")
    expensive = sorted(champions, key=lambda x: -x["coste"])[:5]
    for champ in expensive:
        print(f"  {champ['nombre']} ({champ['coste']}g) - {', '.join(champ['traits'])}")

    # Top 5 más baratos
    print(f"\n--- 5 CAMPEONES MÁS BARATOS ---")
    cheap = sorted(champions, key=lambda x: x["coste"])[:5]
    for champ in cheap:
        print(f"  {champ['nombre']} ({champ['coste']}g) - {', '.join(champ['traits'])}")

if __name__ == "__main__":
    main()
