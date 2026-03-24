# TFT Stats Site — Project Context

## What we're building
Un site de stats y guías de TFT (Teamfight Tactics) en español en producción en https://tftguias.gg.
Diferenciador: guías con variantes condicionales y alertas de pivote basadas en datos reales
de partidas Challenger/GM de EUW.

## Stack
- Frontend: Astro (SSG) + Tailwind — en producción en Cloud Run (europe-west1)
- Data pipeline: Python scripts en /scripts/
- Data source: Riot API (match-v1, league-v1) — API key en variable de entorno RIOT_API_KEY
- Storage: JSON estático en src/data/guides/ + archivos de análisis en raíz del proyecto
- CI/CD: cloudbuild.yaml → Cloud Run

## Archivos de datos existentes (en raíz del proyecto)
- `matches_raw.ndjson` — 2745 partidas raw de top 200 Challenger/GM EUW
- `top_players.csv` — 200 jugadores con puuid, leaguePoints, tier
- `comp_summaries.json` — resumen de comps con top4_rate, win_rate, traits, carry items
- `comp_stats.csv` — todas las comps rankeadas por top4_rate
- `trait_stats.csv` — traits rankeados por top4_rate
- `carry_items.csv` — items por carry en top-4

## Estructura de datos de la Riot API (match-v1, Set 16)
Campos disponibles por participante:
- placement, level, last_round, gold_left
- total_damage_to_players, players_eliminated
- traits (name, tier_current, num_units)
- units (character_id, itemNames, tier, rarity)
- SIN augments — no disponibles en Set 16 aún

## Scripts existentes en /scripts/
- `update-meta.py` — pipeline completo de actualización (descarga + análisis + deploy)

## Commands
- `npm run dev` — frontend local
- `npm run build` — build producción
- `gcloud builds submit --config cloudbuild.yaml` — deploy
- `RIOT_API_KEY=xxx python scripts/nombre.py` — ejecutar scripts de datos

## Conventions
- Scripts Python: snake_case, con argparse para flags, logs con print() descriptivos
- Siempre leer RIOT_API_KEY de os.environ, nunca hardcodeada
- Output de análisis en formato JSON o CSV en raíz del proyecto
- Comentarios en inglés, output de consola en español
