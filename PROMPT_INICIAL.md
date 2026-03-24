Antes de escribir ningún código, entra en **plan mode** y proponme el plan completo.

## Contexto del proyecto

Estoy construyendo un site de stats y guías de TFT (Teamfight Tactics) en español.
El diferenciador respecto a MetaTFT es que nuestras guías incluyen:
1. Variantes de la comp según lo que encuentres en partida
2. Alertas de cuándo pivotar a otra comp

Los datos vienen de 2745 partidas de los top 200 jugadores Challenger/GM de EUW,
procesadas con la Riot API. Ya tengo los archivos generados en la raíz del proyecto:
- `comp_summaries.json` — el insumo principal
- `comp_stats.csv`, `trait_stats.csv`, `carry_items.csv`

Lee `CLAUDE.md` para el contexto completo del stack y convenciones.

## Tarea de esta sesión

Scaffoldea el proyecto Astro completo y genera las primeras dos páginas de guía funcionales.

### Paso 1 — Scaffold
Inicializa un proyecto Astro con Tailwind. Estructura de carpetas:
```
src/
  components/      # componentes reutilizables
  layouts/         # Layout base con nav, footer, AdSense placeholder
  pages/
    index.astro    # home con tier list de comps
    comps/
      [slug].astro # página de guía por comp
  data/            # copia de los JSONs procesados
  styles/
public/
```

### Paso 2 — Datos
Lee `comp_summaries.json` y `comp_stats.csv`. Selecciona las dos comps con mayor
muestra estadística confiable (n_games >= 30 Y top4_rate >= 0.85):
- La que más aparece en los datos: `TFT16_Annie | TFT16_AnnieTibbers | TFT16_Sylas` (299 partidas, 90.6% top4)
- La más dominante en win rate: `TFT16_Azir | TFT16_Ryze | TFT16_Sylas` (94 partidas, 93.6% top4, 52.1% win)

Para cada comp genera un archivo JSON de guía en `src/data/guides/` con esta estructura:
```json
{
  "slug": "annie-tibbers-sylas",
  "nombre": "Annie Tibbers Sylas",
  "dificultad": "Media",
  "top4_rate": 0.906,
  "win_rate": 0.358,
  "n_games": 299,
  "descripcion": "...",
  "gameplan": {
    "early": "...",
    "mid": "...",
    "late": "..."
  },
  "carries": [
    { "unidad": "AnnieTibbers", "items_ideales": [], "items_alternativos": [] }
  ],
  "variantes": [
    { "condicion": "Si encuentras X", "ajuste": "Haz Y" }
  ],
  "cuando_pivotar": ["señal 1", "señal 2"],
  "traits_activos": [],
  "avg_level": 9.4
}
```

Infiere el contenido de gameplan, variantes y cuando_pivotar a partir de:
- Los traits activos más frecuentes del `comp_summaries.json`
- El avg_level (9.4 → fast-9, siempre)
- Los items de carry del CSV
- Tu conocimiento de TFT Set 16

### Paso 3 — Componentes y páginas
Construye:

**`CompCard.astro`** — tarjeta de comp para la home con:
- Nombre de la comp
- Badge de dificultad
- Top-4 rate y win rate como métricas visuales
- Icono de tier (S/A/B según top4_rate)
- Link a la página de guía

**`index.astro`** — home con:
- H1: "Guías y stats de TFT Set 16 — Actualizado para el meta de EUW Challenger"
- Meta description optimizada para SEO
- Grid de CompCards ordenadas por top4_rate
- Placeholder para AdSense (div con comentario, no el script real)

**`comps/[slug].astro`** — página de guía con:
- H1 con nombre de la comp
- Sección de stats (top4_rate, win_rate, partidas analizadas)
- Sección "Cómo jugarla" con gameplan por stage (early/mid/late)
- Sección "Items recomendados" por carry
- Sección "Variantes" — el diferenciador principal, layout en cards
- Sección "¿Cuándo pivotar?" — lista de señales en rojo/naranja
- Meta tags SEO por comp

## Restricciones
- Tailwind únicamente, sin CSS custom salvo variables de color en el layout base
- Diseño mobile-first
- Todo el copy en español
- No instales dependencias innecesarias — Astro + Tailwind es suficiente para el MVP

## Output esperado al final de la sesión
- Proyecto Astro funcional con `npm run dev`
- Home con tier list de comps
- Dos páginas de guía completas y navegables
- Sin errores de build

Empieza por el plan en modo lectura, luego ejecuta paso a paso.
