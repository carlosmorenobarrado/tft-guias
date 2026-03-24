#!/usr/bin/env python3
"""
enrich_analysis.py - Enriched analysis of TFT match data

Reads matches_raw.ndjson and comp_summaries.json to generate:
- comp_profiles.json: Full profile of each comp with derived labels
- execution_signals.csv: Top4 vs Bottom4 differences by comp and variable
"""

import json
import csv
from collections import defaultdict
from pathlib import Path
import statistics

# Paths
ROOT = Path(__file__).parent.parent
MATCHES_FILE = ROOT / "matches_raw.ndjson"
COMP_SUMMARIES_FILE = ROOT / "comp_summaries.json"
OUTPUT_PROFILES = ROOT / "comp_profiles.json"
OUTPUT_SIGNALS = ROOT / "execution_signals.csv"


def load_matches():
    """Load all matches from ndjson file"""
    matches = []
    with open(MATCHES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                matches.append(json.loads(line))
    return matches


def load_comp_summaries():
    """Load existing comp summaries to get comp IDs"""
    with open(COMP_SUMMARIES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_participant_units(participant):
    """Extract set of unit character_ids from a participant"""
    return set(u['character_id'] for u in participant.get('units', []))


def identify_comp(participant_units, comp_cores):
    """
    Identify which comp a participant is playing based on core units.
    Returns the comp_id if all core units are present, None otherwise.
    """
    for comp_id, core_units in comp_cores.items():
        if core_units.issubset(participant_units):
            return comp_id
    return None


def safe_mean(values):
    """Calculate mean safely, return 0 if empty"""
    return statistics.mean(values) if values else 0


def safe_stdev(values):
    """Calculate stdev safely, return 0 if less than 2 values"""
    return statistics.stdev(values) if len(values) >= 2 else 0


def calculate_percentile(values, percentile):
    """Calculate percentile of values"""
    if not values:
        return 0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * percentile / 100)
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


def main():
    print("=" * 60)
    print("TFT Enriched Analysis - Perfiles de comps")
    print("=" * 60)

    # Load data
    print("\n[1/5] Cargando datos...")
    matches = load_matches()
    comp_summaries = load_comp_summaries()
    print(f"  - Partidas cargadas: {len(matches)}")
    print(f"  - Comps en comp_summaries: {len(comp_summaries)}")

    # Build comp_cores dict: comp_id -> set of core units
    comp_cores = {}
    for comp_id, data in comp_summaries.items():
        if comp_id and data.get('core_units'):
            comp_cores[comp_id] = set(data['core_units'])
    print(f"  - Comps con core units validos: {len(comp_cores)}")

    # Collect stats per comp
    print("\n[2/5] Recolectando estadisticas por comp...")
    comp_stats = defaultdict(lambda: {
        'top4': defaultdict(list),
        'bottom4': defaultdict(list),
        'all': defaultdict(list)
    })

    total_participants = 0
    matched_participants = 0

    for match in matches:
        participants = match.get('info', {}).get('participants', [])
        for p in participants:
            total_participants += 1
            units = get_participant_units(p)
            comp_id = identify_comp(units, comp_cores)

            if comp_id:
                matched_participants += 1
                placement = p.get('placement', 8)
                is_top4 = placement <= 4

                # Collect all relevant fields
                stats_group = 'top4' if is_top4 else 'bottom4'

                fields = {
                    'last_round': p.get('last_round', 0),
                    'level': p.get('level', 0),
                    'gold_left': p.get('gold_left', 0),
                    'players_eliminated': p.get('players_eliminated', 0),
                    'total_damage_to_players': p.get('total_damage_to_players', 0),
                    'placement': placement
                }

                for field, value in fields.items():
                    comp_stats[comp_id][stats_group][field].append(value)
                    comp_stats[comp_id]['all'][field].append(value)

    print(f"  - Participantes totales: {total_participants}")
    print(f"  - Participantes con comp identificada: {matched_participants}")
    print(f"  - Comps con datos: {len(comp_stats)}")

    # Calculate enriched profiles
    print("\n[3/5] Calculando perfiles enriquecidos...")
    comp_profiles = {}

    for comp_id, stats in comp_stats.items():
        top4 = stats['top4']
        bottom4 = stats['bottom4']
        all_data = stats['all']

        n_games = len(all_data['placement'])
        n_top4 = len(top4['placement'])
        n_bottom4 = len(bottom4['placement'])

        if n_games < 10:  # Skip comps with very few games
            continue

        # Calculate core stats
        avg_last_round_top4 = safe_mean(top4['last_round'])
        avg_last_round_bottom4 = safe_mean(bottom4['last_round'])
        avg_level_top4 = safe_mean(top4['level'])
        avg_level_bottom4 = safe_mean(bottom4['level'])
        avg_gold_left_top4 = safe_mean(top4['gold_left'])
        avg_gold_left_bottom4 = safe_mean(bottom4['gold_left'])
        avg_players_elim_top4 = safe_mean(top4['players_eliminated'])
        avg_players_elim_bottom4 = safe_mean(bottom4['players_eliminated'])
        avg_damage_top4 = safe_mean(top4['total_damage_to_players'])
        avg_damage_bottom4 = safe_mean(bottom4['total_damage_to_players'])

        # Level distribution in top4
        levels_top4 = top4['level']
        pct_nivel_9_top4 = (sum(1 for l in levels_top4 if l >= 9) / len(levels_top4) * 100) if levels_top4 else 0
        pct_nivel_10_top4 = (sum(1 for l in levels_top4 if l >= 10) / len(levels_top4) * 100) if levels_top4 else 0

        # Most frequent level in top4
        if levels_top4:
            level_counts = defaultdict(int)
            for l in levels_top4:
                level_counts[l] += 1
            nivel_optimo = max(level_counts, key=level_counts.get)
        else:
            nivel_optimo = 8

        # Determine derived labels
        # Estilo: based on avg level and last_round
        if avg_level_top4 >= 9 and avg_last_round_top4 >= 32:
            estilo = "late_game"
        elif avg_level_top4 <= 7.5 or pct_nivel_9_top4 < 20:
            estilo = "reroll"
        else:
            estilo = "mid_game"

        # Economia: based on gold_left comparison
        if avg_gold_left_top4 >= 15:
            economia = "eco"
        elif avg_gold_left_top4 <= 5:
            economia = "rolldown"
        else:
            economia = "mixto"

        # Presion: based on players_eliminated and damage
        all_damage = [safe_mean(s['all']['total_damage_to_players']) for s in comp_stats.values() if len(s['all']['total_damage_to_players']) >= 10]
        all_elims = [safe_mean(s['all']['players_eliminated']) for s in comp_stats.values() if len(s['all']['players_eliminated']) >= 10]

        if all_damage and all_elims:
            median_damage = statistics.median(all_damage)
            median_elims = statistics.median(all_elims)

            avg_damage_comp = safe_mean(all_data['total_damage_to_players'])
            avg_elims_comp = safe_mean(all_data['players_eliminated'])

            pressure_score = 0
            if avg_damage_comp > median_damage * 1.2:
                pressure_score += 1
            if avg_elims_comp > median_elims * 1.2:
                pressure_score += 1
            if avg_damage_comp < median_damage * 0.8:
                pressure_score -= 1
            if avg_elims_comp < median_elims * 0.8:
                pressure_score -= 1

            if pressure_score >= 1:
                presion = "alta"
            elif pressure_score <= -1:
                presion = "baja"
            else:
                presion = "media"
        else:
            presion = "media"

        # Ronda de estabilizacion: approximate using last_round of top4
        # Assumption: stabilization is roughly 5-7 rounds before average death
        ronda_estabilizacion = max(1, int(avg_last_round_top4 - 6))

        comp_profiles[comp_id] = {
            "comp_id": comp_id,
            "n_games": n_games,
            "n_top4": n_top4,
            "n_bottom4": n_bottom4,
            "estilo": estilo,
            "economia": economia,
            "presion": presion,
            "nivel_optimo": nivel_optimo,
            "ronda_estabilizacion": ronda_estabilizacion,
            "stats": {
                "avg_last_round_top4": round(avg_last_round_top4, 1),
                "avg_last_round_bottom4": round(avg_last_round_bottom4, 1),
                "min_last_round_top4": min(top4['last_round']) if top4['last_round'] else 0,
                "max_last_round_top4": max(top4['last_round']) if top4['last_round'] else 0,
                "avg_level_top4": round(avg_level_top4, 1),
                "avg_level_bottom4": round(avg_level_bottom4, 1),
                "pct_nivel_9_top4": round(pct_nivel_9_top4, 1),
                "pct_nivel_10_top4": round(pct_nivel_10_top4, 1),
                "avg_gold_left_top4": round(avg_gold_left_top4, 1),
                "avg_gold_left_bottom4": round(avg_gold_left_bottom4, 1),
                "avg_players_elim_top4": round(avg_players_elim_top4, 2),
                "avg_players_elim_bottom4": round(avg_players_elim_bottom4, 2),
                "avg_damage_top4": round(avg_damage_top4, 1),
                "avg_damage_bottom4": round(avg_damage_bottom4, 1)
            }
        }

    print(f"  - Perfiles generados: {len(comp_profiles)}")

    # Calculate execution signals
    print("\n[4/5] Calculando senales de ejecucion (top4 vs bottom4)...")
    execution_signals = []

    variables = [
        ('level', 'Nivel', 'mayor'),
        ('last_round', 'Ronda supervivencia', 'mayor'),
        ('gold_left', 'Oro sobrante', 'variable'),
        ('players_eliminated', 'Eliminaciones', 'variable'),
        ('total_damage_to_players', 'Daño total', 'variable')
    ]

    # Sort by n_games descending for console output
    sorted_comps = sorted(comp_profiles.items(), key=lambda x: x[1]['n_games'], reverse=True)

    for comp_id, profile in sorted_comps:
        stats_data = comp_stats[comp_id]
        top4 = stats_data['top4']
        bottom4 = stats_data['bottom4']

        for var_key, var_name, direction in variables:
            top4_vals = top4[var_key]
            bottom4_vals = bottom4[var_key]

            if not top4_vals or not bottom4_vals:
                continue

            top4_mean = safe_mean(top4_vals)
            bottom4_mean = safe_mean(bottom4_vals)
            diff = top4_mean - bottom4_mean
            diff_pct = (diff / bottom4_mean * 100) if bottom4_mean != 0 else 0

            # Effect size (Cohen's d approximation)
            pooled_std = ((safe_stdev(top4_vals) ** 2 + safe_stdev(bottom4_vals) ** 2) / 2) ** 0.5
            effect_size = diff / pooled_std if pooled_std > 0 else 0

            execution_signals.append({
                'comp_id': comp_id,
                'variable': var_key,
                'variable_name': var_name,
                'top4_mean': round(top4_mean, 2),
                'bottom4_mean': round(bottom4_mean, 2),
                'diff': round(diff, 2),
                'diff_pct': round(diff_pct, 1),
                'effect_size': round(effect_size, 2),
                'n_games': profile['n_games']
            })

    # Analysis 3: Print execution signals for top comps
    print("\n" + "=" * 60)
    print("ANALISIS 3 - Senales de ejecucion correcta vs incorrecta")
    print("=" * 60)

    # Get top 3 comps by n_games with at least 30 games
    top_comps = [(comp_id, profile) for comp_id, profile in sorted_comps if profile['n_games'] >= 30][:3]

    for comp_id, profile in top_comps:
        print(f"\n{'-' * 60}")
        print(f"[COMP] {comp_id}")
        print(f"   Partidas: {profile['n_games']} | Estilo: {profile['estilo']} | Economia: {profile['economia']} | Presion: {profile['presion']}")
        print(f"{'-' * 60}")

        stats = profile['stats']
        signals = [s for s in execution_signals if s['comp_id'] == comp_id]

        # Sort by effect size to show most differentiating factors first
        signals.sort(key=lambda x: abs(x['effect_size']), reverse=True)

        print(f"\n   Factores diferenciadores (ordenados por impacto):\n")

        for s in signals:
            direction = "+" if s['diff'] > 0 else "-"
            impact = "ALTO" if abs(s['effect_size']) > 0.5 else "MEDIO" if abs(s['effect_size']) > 0.3 else "BAJO"

            print(f"   * {s['variable_name']}: top4={s['top4_mean']:.1f} vs bottom4={s['bottom4_mean']:.1f} ({direction}{abs(s['diff']):.1f}) [Impacto: {impact}]")

        print(f"\n   Interpretacion:")

        # Level interpretation
        level_diff = stats['avg_level_top4'] - stats['avg_level_bottom4']
        if level_diff > 0.8:
            print(f"   >> Los top-4 llegan a nivel {stats['avg_level_top4']:.1f} de media, los bottom-4 a {stats['avg_level_bottom4']:.1f}")
            print(f"      El NIVEL es el factor mas diferenciador")

        # Gold interpretation
        gold_top4 = stats['avg_gold_left_top4']
        gold_bottom4 = stats['avg_gold_left_bottom4']
        if gold_top4 < gold_bottom4 - 3:
            print(f"   >> Los top-4 tienen {gold_top4:.1f} oro sobrante, los bottom-4 tienen {gold_bottom4:.1f}")
            print(f"      Los top-4 rollearon mas AGRESIVO")
        elif gold_top4 > gold_bottom4 + 3:
            print(f"   >> Los top-4 tienen {gold_top4:.1f} oro sobrante, los bottom-4 tienen {gold_bottom4:.1f}")
            print(f"      Los top-4 jugaron mas ECO/INTERES")

        # Last round interpretation
        round_diff = stats['avg_last_round_top4'] - stats['avg_last_round_bottom4']
        print(f"   >> Ronda media de supervivencia: top-4 llegan a ronda {stats['avg_last_round_top4']:.0f}, bottom-4 mueren en ronda {stats['avg_last_round_bottom4']:.0f}")

        # Level 9/10 interpretation
        if stats['pct_nivel_9_top4'] > 50:
            print(f"   >> {stats['pct_nivel_9_top4']:.0f}% de los top-4 llegan a nivel 9+, {stats['pct_nivel_10_top4']:.0f}% a nivel 10")

    # Write output files
    print("\n\n[5/5] Escribiendo archivos de salida...")

    # Write comp_profiles.json
    with open(OUTPUT_PROFILES, 'w', encoding='utf-8') as f:
        json.dump(comp_profiles, f, indent=2, ensure_ascii=False)
    print(f"  [OK] {OUTPUT_PROFILES.name} ({len(comp_profiles)} comps)")

    # Write execution_signals.csv
    with open(OUTPUT_SIGNALS, 'w', newline='', encoding='utf-8') as f:
        if execution_signals:
            writer = csv.DictWriter(f, fieldnames=execution_signals[0].keys())
            writer.writeheader()
            writer.writerows(execution_signals)
    print(f"  [OK] {OUTPUT_SIGNALS.name} ({len(execution_signals)} registros)")

    print("\n" + "=" * 60)
    print("[COMPLETADO] Analisis finalizado")
    print("=" * 60)

    # Summary stats
    print(f"\nResumen de perfiles generados:")
    estilos = defaultdict(int)
    economias = defaultdict(int)
    presiones = defaultdict(int)

    for p in comp_profiles.values():
        estilos[p['estilo']] += 1
        economias[p['economia']] += 1
        presiones[p['presion']] += 1

    print(f"  Estilos: {dict(estilos)}")
    print(f"  Economias: {dict(economias)}")
    print(f"  Presiones: {dict(presiones)}")


if __name__ == "__main__":
    main()
