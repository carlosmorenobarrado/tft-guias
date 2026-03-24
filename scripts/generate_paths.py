#!/usr/bin/env python3
"""
generate_paths.py - Genera resumen legible de caminos de early game

Lee comp_paths.json y muestra el camino completo para cada comp.
Muestra información de validación humana y gameplan cuando existen.
"""

import json
import argparse
import sys
import os

# Fix encoding para Windows
sys.stdout.reconfigure(encoding='utf-8')


def load_champions():
    """Carga datos de campeones para info adicional"""
    try:
        with open("champions_set16.json", "r", encoding="utf-8") as f:
            champs = json.load(f)
        return {c["id"]: c for c in champs}
    except:
        return {}


def load_overrides():
    """Carga overrides con gameplan_early"""
    try:
        with open("comp_overrides.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def normalize_comp_key(comp_key):
    """Normaliza el key de la comp para matching con overrides"""
    return comp_key.replace(" | ", "|")


def generate_path_display(comp_key, path_data, champions_db, overrides):
    """Genera el display formateado para una comp"""

    # Header
    core_units = path_data.get("core_units", [])
    core_names = [u.replace("TFT16_", "") for u in core_units]
    header = " + ".join(core_names)

    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"=== {header} ===")
    lines.append(f"{'='*60}")

    # Trait dominante con indicador de override
    trait_display = path_data['trait_display']
    if path_data.get("trait_override"):
        lines.append(f"Trait dominante: {trait_display} [corregido manualmente]")
    else:
        lines.append(f"Trait dominante: {trait_display}")

    # Info de validación
    if path_data.get("validado_por_humano"):
        lines.append(f"VALIDADO: ✓ por jugador Maestro")

        opener_ideal = path_data.get("opener_ideal")
        opener_alt = path_data.get("opener_alternativo")

        lines.append(f"OPENER IDEAL: {opener_ideal}")
        lines.append(f"OPENER ALTERNATIVO: {opener_alt if opener_alt else '—'}")

        nota = path_data.get("nota_validacion")
        if nota:
            lines.append(f"NOTA: {nota}")

    # Gameplan early si existe en overrides
    normalized_key = normalize_comp_key(comp_key)
    override = overrides.get(normalized_key, {})
    gameplan = override.get("gameplan_early")

    if gameplan:
        lines.append(f"\nGAMEPLAN EARLY:")
        descripcion = gameplan.get("descripcion", "")
        # Formatear descripcion en líneas más cortas
        lines.append(f"  {descripcion}")

        campeones_clave = gameplan.get("campeones_clave", [])
        if campeones_clave:
            nombres = [c.replace("TFT16_", "") for c in campeones_clave]
            lines.append(f"  Campeones clave: {' → '.join(nombres)}")

        nivel = gameplan.get("nivel_transicion")
        if nivel:
            lines.append(f"  Nivel de transición: {nivel}")

        trampa = gameplan.get("trampa_a_evitar")
        if trampa:
            lines.append(f"\nTRAMPA A EVITAR:")
            lines.append(f"  ⚠ {trampa}")

    # Early game
    early = path_data.get("early", [])
    lines.append(f"\nEARLY GAME (coste 1-2):")
    if early:
        for champ in early[:5]:  # Top 5
            freq_pct = int(champ["frecuencia_top4"] * 100)
            traits_str = ", ".join(champ["traits"])
            core_marker = " ★" if champ.get("es_core") else ""
            lines.append(f"  → {champ['nombre']} ({champ['coste']}g) | {traits_str} | frecuencia top4: {freq_pct}%{core_marker}")
    else:
        lines.append("  (ningún campeón de coste 1-2 con este trait)")

    # Mid game
    mid = path_data.get("mid", [])
    lines.append(f"\nMID GAME (coste 3):")
    if mid:
        for champ in mid[:5]:  # Top 5
            freq_pct = int(champ["frecuencia_top4"] * 100)
            traits_str = ", ".join(champ["traits"])
            core_marker = " ★" if champ.get("es_core") else ""
            lines.append(f"  → {champ['nombre']} ({champ['coste']}g) | {traits_str} | frecuencia top4: {freq_pct}%{core_marker}")
    else:
        lines.append("  (ningún campeón de coste 3 con este trait)")

    # Core final - mostrar campeones del trait Y los carries principales
    core = path_data.get("core", [])
    lines.append(f"\nCORE FINAL (coste 4-5):")

    # Primero los carries principales del core
    shown_ids = set()
    for unit_id in core_units:
        champ_data = champions_db.get(unit_id)
        if champ_data and champ_data["coste"] >= 4:
            traits_str = ", ".join(champ_data["traits"])
            lines.append(f"  → {champ_data['nombre']} ({champ_data['coste']}g) | {traits_str} | ★★ carry principal")
            shown_ids.add(unit_id)

    # Luego otros campeones del trait que no son core
    for champ in core:
        if champ["character_id"] not in shown_ids:
            freq_pct = int(champ["frecuencia_top4"] * 100)
            traits_str = ", ".join(champ["traits"])
            lines.append(f"  → {champ['nombre']} ({champ['coste']}g) | {traits_str} | frecuencia top4: {freq_pct}%")

    if not core and not any(champions_db.get(u, {}).get("coste", 0) >= 4 for u in core_units):
        lines.append("  (ningún campeón de coste 4-5 con este trait)")

    # Board recomendado nivel 7
    lines.append(f"\nBoard recomendado en nivel 7 (transición):")

    # Construir sugerencia de board
    board_units = []

    # Añadir los mejores early
    for champ in early[:2]:
        board_units.append(champ["nombre"])

    # Añadir los mejores mid
    for champ in mid[:1]:
        board_units.append(champ["nombre"])

    # Añadir cores de coste 4 disponibles en nivel 7
    core_4cost = []
    for unit_id in core_units:
        champ_data = champions_db.get(unit_id)
        if champ_data and champ_data["coste"] == 4:
            core_4cost.append(champ_data["nombre"])

    # También añadir el mejor core del trait de coste 4
    for champ in core:
        if champ["coste"] == 4 and champ["nombre"] not in core_4cost:
            core_4cost.append(champ["nombre"])
            break

    board_units.extend(core_4cost[:2])

    # Completar con flex
    trait_name = path_data["trait_display"]
    slots_used = len(board_units)
    flex_slots = 7 - slots_used

    if board_units:
        board_str = " + ".join(board_units)
        if flex_slots > 0:
            board_str += f" + [{flex_slots} {trait_name} flex]"
        lines.append(f"  {board_str}")
    else:
        lines.append(f"  [Usar unidades {trait_name} disponibles según tienda]")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Genera resumen de caminos early game")
    parser.add_argument("--comp", type=str, help="Mostrar solo una comp específica")
    parser.add_argument("--all", action="store_true", help="Mostrar todas las comps")
    args = parser.parse_args()

    # Cargar datos
    print("Cargando comp_paths.json...")
    with open("comp_paths.json", "r", encoding="utf-8") as f:
        comp_paths = json.load(f)

    champions_db = load_champions()
    overrides = load_overrides()
    print(f"Total comps disponibles: {len(comp_paths)}")
    print(f"Overrides con gameplan: {len([o for o in overrides.values() if o.get('gameplan_early')])}")

    # Comps a mostrar por defecto
    default_comps = [
        "TFT16_Fiddlesticks | TFT16_Kindred | TFT16_Lucian",
        "TFT16_Kindred | TFT16_Shyvana | TFT16_TahmKench",
        "TFT16_Annie | TFT16_AnnieTibbers | TFT16_Sylas"
    ]

    if args.all:
        comps_to_show = list(comp_paths.keys())
    elif args.comp:
        # Buscar comp que contenga el texto
        matching = [k for k in comp_paths.keys() if args.comp.lower() in k.lower()]
        comps_to_show = matching if matching else []
        if not comps_to_show:
            print(f"No se encontró comp con '{args.comp}'")
            return
    else:
        comps_to_show = default_comps

    # Generar output
    for comp_key in comps_to_show:
        if comp_key in comp_paths:
            output = generate_path_display(comp_key, comp_paths[comp_key], champions_db, overrides)
            print(output)
        else:
            print(f"\n⚠ Comp no encontrada: {comp_key}")

    print(f"\n{'='*60}")
    print("FIN DEL REPORTE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
