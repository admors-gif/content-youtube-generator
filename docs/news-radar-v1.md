# Radar Global De Ideas Y Noticias Virales v1

Ultima actualizacion: 2026-05-09

## Objetivo

El Radar es una capa editorial previa a la creacion de proyectos. Sirve para:

- encontrar noticias virales actuales para `agent_noticias_virales`;
- generar ideas nuevas para cualquier agente;
- guardar ideas en una biblioteca editorial por agente;
- crear proyectos desde una idea curada sin producir ni publicar automaticamente.

La v1 es admin-only, cacheada y apagable por feature flag. Explorar ideas no cobra creditos; solo se cobra 1 credito cuando se crea un proyecto real.

## Alcance

Incluido en v1:

- `POST /radar/run`
- `GET /radar/latest`
- `POST /radar/candidates/{candidate_hash}/save`
- `POST /radar/candidates/{candidate_hash}/create-project`
- `GET /library/agents`
- `POST /library/items/{item_id}/archive`
- `POST /admin/radar/refresh-nightly`
- pantalla `/dashboard/radar`
- pantalla `/dashboard/library`
- workflow `.github/workflows/radar-nightly.yml`

Fuera de v1:

- autoproduccion de video;
- autopublicacion;
- creacion masiva de proyectos;
- scraping directo de redes sociales;
- cambios invasivos al modelo `projects`.

## Seguridad Y Flags

Backend:

```env
CONTENT_FACTORY_RADAR_ENABLED=true
CONTENT_FACTORY_RADAR_ADMIN_ONLY=true
CONTENT_FACTORY_ADMIN_TOKEN=...
```

Frontend:

```env
NEXT_PUBLIC_CONTENT_FACTORY_RADAR_ENABLED=true
```

Todos los endpoints del Radar usan `_require_admin()`. El refresh nocturno tambien acepta `x-admin-token` para GitHub Actions.

## Modelo De Datos

### `radarRuns`

Guarda el ultimo resultado cacheado por combinacion de:

- `scope`
- `agentId`
- `market`
- `language`
- `category`
- `window`

Campos principales:

- `runId`
- `cacheKey`
- `mode`: `manual` o `nightly`
- `scope`: `global`, `agent`, `news`
- `status`: `ok`, `empty`, `error`
- `items`
- `itemsCount`
- `generatedAt`
- `expiresAt`
- `errors`

### `topicLibrary`

Guarda ideas y su estado editorial por usuario/agente.

Campos principales:

- `userId`
- `agentId`
- `agentName`
- `agentFile`
- `title`
- `angle`
- `summary`
- `sources`
- `scores`
- `editorialScore`
- `risk`
- `status`: `suggested`, `saved`, `project_created`, `produced`, `archived`
- `candidateHash`
- `candidate`
- `projectId`

Las ideas nocturnas se guardan bajo `userId="admin"` para que el admin las vea como biblioteca compartida.

## Motor Editorial

Archivo: `scripts/radar.py`

Funciones principales:

- `build_news_queries()`
- `build_agent_queries()`
- `tavily_results_to_candidates()`
- `shape_candidate()`
- `score_candidate()`
- `dedupe_candidates()`
- `parse_ranking_response()`
- `apply_llm_ranking()`

Score universal:

- Potencial de audiencia: 25
- Encaje con agente: 20
- Arco narrativo: 20
- Frescura/tendencia: 15
- Facilidad de produccion: 10
- Riesgo bajo: 10

Noticias ponderan mas actualidad y fuentes. Wellness penaliza promesas medicas. El podcast `Esto no es amor` favorece apego, limites, ruptura, contacto cero y metaforas emocionales.

## Cache Y Costos

- TTL: 60 minutos.
- `limit` manual maximo: 12.
- `limit` por agente maximo: 5.
- refresh nocturno: maximo 2 queries Tavily por agente y 5 candidatos por agente.
- LLM ranking global queda apagado por default salvo `CONTENT_FACTORY_RADAR_LLM_GLOBAL=true`.

Si Tavily no esta disponible, el motor devuelve ideas fallback por agente para mantener la UI util sin romper.

## Creacion De Proyecto

`POST /radar/candidates/{candidate_hash}/create-project`:

1. resuelve el candidato desde biblioteca o ultimo cache;
2. bloquea riesgo alto salvo revision explicita futura;
3. reconstruye payload compatible con `_validate_project_payload()`;
4. llama la misma logica transaccional de creditos que `/projects/create`;
5. crea proyecto en `draft`;
6. guarda `generationOptions.radar_context`;
7. marca `topicLibrary.status = project_created`.

No llama `/produce`, no sube a YouTube/TikTok y no dispara publicaciones.

## UI

### `/dashboard/radar`

Vista admin para descubrir ideas.

Incluye:

- filtros por scope, agente, categoria, ventana, formato y busqueda;
- cards con titulo, angulo, resumen, score, riesgo, formato y fuentes;
- panel de detalle con fuentes, score y advertencias;
- acciones guardar y crear proyecto.

Los candidatos de riesgo alto no muestran creacion primaria.

### `/dashboard/library`

Biblioteca por agente.

Incluye:

- ideas sugeridas/guardadas;
- proyectos creados;
- material completado;
- huecos editoriales;
- acciones crear proyecto, abrir proyecto y archivar idea.

La biblioteca no borra ni modifica proyectos existentes; solo organiza encima.

## Refresh Nocturno

Workflow: `.github/workflows/radar-nightly.yml`

Schedule actual:

```text
35 8 * * *
```

Llama:

```text
POST https://api.valtyk.com/admin/radar/refresh-nightly
```

Headers:

```text
x-admin-token: CONTENT_FACTORY_ADMIN_TOKEN
content-type: application/json
```

El workflow tambien puede ejecutarse manualmente con `workflow_dispatch`.

## Riesgos Y Mitigaciones

- Costo excesivo: cache, caps, admin-only, refresh limitado.
- Ideas duplicadas: `candidateHash` y `canonical_title_key`.
- Noticias falsas: fuentes visibles, riesgo medio/alto con fuente unica, fact-check posterior.
- Proyectos duplicados: idempotencia por `candidateHash + userId`.
- Riesgo reputacional: etiquetas de riesgo y bloqueo de riesgo alto.
- Fallo nocturno: conserva ultimo cache valido y registra `nightly-last-error`.
- Secrets en logs: workflow usa secrets de GitHub y no imprime valores.

## Pruebas

Unitarias:

```bash
pytest tests/test_radar.py
```

Frontend:

```bash
cd web
npm run lint
npm run build
```

Operacion:

1. ejecutar `/radar/run` con `force=false`;
2. guardar una idea;
3. crear un proyecto desde una idea de bajo/medio riesgo;
4. confirmar que se cobra solo al crear proyecto;
5. confirmar que el proyecto queda en flujo normal;
6. ejecutar workflow nocturno en `workflow_dispatch`;
7. revisar que no se dispare produccion ni publicacion.
