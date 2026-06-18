# Content Factory - AI Handoff

Ultima revision local: 2026-05-09

## Para empezar una sesion nueva

Lee estos archivos en este orden:

1. `CODEX_HANDOFF.md` - estado compacto y reglas de trabajo.
2. `MANUAL.md` - fuente de verdad operativa viva.
3. `PRODUCT_ROADMAP.md` - roadmap y prioridades de producto.
4. `web/AGENTS.md` - reglas especificas de Next.js 16 para agentes.
5. `C:\Users\admor\.claude\plans\sprint-2-3-podcaster-frolicking-kazoo.md` - plan activo del rediseño frontend v2, si se trabaja UI.

No leas ni pegues contenido de `.env`, `web/.env.local`, `firebase-admin*.json`, `content-factory-tts-*.json` ni backups de credenciales salvo que el usuario lo pida explicitamente para una tarea de seguridad.

## Estado del repo

- Repo GitHub: `https://github.com/admors-gif/content-youtube-generator`
- Branch local actual: `redesign/v2-editorial-cinematic`
- `git status` al 2026-05-04: limpio, sin cambios locales detectados.
- Frontend: `web/`, Next.js 16.2.4 + React 19.2.4 + Firebase 12.12.1.
- Backend: `api.py` + `scripts/`, FastAPI/Python, deploy por GitHub Actions self-hosted al VPS.

## Producto

Content Factory genera documentales/videos para YouTube:

1. guion con Claude,
2. investigacion con Tavily,
3. imagenes con ComfyUI/Flux,
4. narracion con ElevenLabs,
5. clips con Luma,
6. ensamblado con FFmpeg,
7. subtitulos con Whisper/OpenAI,
8. entrega de video via Firebase Storage signed URLs.

Infra principal:

- Frontend publico: Vercel.
- API publica: `https://api.valtyk.com`.
- VPS Hostinger: contenedor Docker `content-factory`.
- Firebase project: `content-factory-5cbcb`.
- Storage bucket: `content-factory-5cbcb.firebasestorage.app`.

## Estado operativo importante

### Power Music Studio v1

Implementado en la sesion 2026-06-16:

- Backend admin-only:
  - `GET /music/presets`
  - `GET /music/tracks`
  - `POST /music/generate`
- Modulo puro: `scripts/power_music.py` con presets, prompt builder, normalizacion, fallback opcional y hash estable de track.
- Frontend admin-only: `/dashboard/music`, sidebar "Musica" si `NEXT_PUBLIC_CONTENT_FACTORY_MUSIC_STUDIO_ENABLED !== "false"`.
- Firestore: `musicTracks`.
- Prompt maestro documentado: `prompts/agent_power_music.md`.
- Documentacion operativa: `docs/power-music-studio.md`.
- V1 genera letra, prompt Suno, prompt alternativo, negative prompt, portada, direccion visual y metadata YouTube.
- V1 permite subir multiples tomas de audio descargadas de Suno a `musicTracks/{trackId}.audioVersions` y Firebase Storage.
- `musicTracks/{trackId}.audio` conserva la version activa para compatibilidad.
- V1 renderiza video final en VPS/worker desde la version activa de audio y tambien puede renderizar una toma especifica sin cambiar la version activa.
- Firestore conserva `musicTracks/{trackId}.renders[]` como historial por `audioVersionId`, con MP4, miniatura, portada, metadata, estado, progreso, cola y errores.
- V1 incluye `package.lyricScore` heuristico sin costo extra.
- Renderer v2 sincroniza visuales con la letra: divide la duracion real del audio en beats de ~5 segundos, genera prompts Flux por linea/seccion y usa Comfy/Flux si esta configurado.
- Si Comfy falla o no esta configurado, el render sigue con fallback local limpio; ya no muestra prompts tecnicos en el video.
- No consume creditos internos; el usuario copia a Suno manualmente.

Flags:

- Backend: `CONTENT_FACTORY_MUSIC_STUDIO_ENABLED`, `CONTENT_FACTORY_MUSIC_STUDIO_ADMIN_ONLY`, `CONTENT_FACTORY_MUSIC_MODEL`, `CONTENT_FACTORY_MUSIC_ALLOW_FALLBACK`.
- Frontend: `NEXT_PUBLIC_CONTENT_FACTORY_MUSIC_STUDIO_ENABLED`.

Siguiente bloque recomendado:

- Analizar audio subido: duracion, waveform y energia aproximada.
- Crear comparador subjetivo de tomas: energia, mezcla, claridad vocal, hook.
- Probar un MP3 real de Suno con `COMFYUI_API_KEY` activo para confirmar costo/tiempo de 30-40 imagenes por cancion.
- Miniatura y publicacion YouTube reutilizando el centro actual.

### Radar editorial v1

Implementado en la sesion 2026-05-09:

- Backend admin-only:
  - `POST /radar/run`
  - `GET /radar/latest`
  - `POST /radar/candidates/{candidate_hash}/save`
  - `POST /radar/candidates/{candidate_hash}/create-project`
  - `GET /library/agents`
  - `POST /library/items/{item_id}/archive`
  - `POST /admin/radar/refresh-nightly`
- Motor puro en `scripts/radar.py`: queries por agente/noticias, scoring, riesgo, dedupe, fallback y parser de ranking LLM.
- Frontend:
  - `/dashboard/radar` para descubrir ideas/noticias, ver fuentes/riesgo/score, guardar y crear proyecto.
  - `/dashboard/library` reemplaza stub por biblioteca real agrupada por agente.
  - Sidebar muestra Radar solo a admins y solo si `NEXT_PUBLIC_CONTENT_FACTORY_RADAR_ENABLED !== "false"`.
- Proyecto desde Radar reutiliza la transaccion de creditos de `/projects/create`; no produce ni publica video.
- `scripts/generate_content.py` acepta `generationOptions.radar_context` para alimentar el guion con fuentes/angulo curado.
- Workflow nocturno: `.github/workflows/radar-nightly.yml`.
- Documentacion: `docs/news-radar-v1.md` y `MANUAL.md`.

Flags:

- Backend: `CONTENT_FACTORY_RADAR_ENABLED`, `CONTENT_FACTORY_RADAR_ADMIN_ONLY`, `CONTENT_FACTORY_ADMIN_TOKEN`.
- Frontend: `NEXT_PUBLIC_CONTENT_FACTORY_RADAR_ENABLED`.

Pruebas agregadas:

- `tests/test_radar.py`

Verificacion pendiente en entorno completo:

- `pytest tests/test_radar.py`
- `cd web && npm run lint`
- `cd web && npm run build`
- `workflow_dispatch` del Radar nocturno cuando los secrets esten confirmados.

### Base de conocimiento Qdrant v1

Implementada en la sesion 2026-05-10:

- Frontend admin-only: `/dashboard/knowledge`, sidebar "Conocimiento" si `NEXT_PUBLIC_CONTENT_FACTORY_KNOWLEDGE_ENABLED !== "false"`.
- Backend admin-only:
  - `GET /knowledge/summary`
  - `POST /knowledge/sync-index`
  - `GET /knowledge/books`
  - `GET /knowledge/books/{bookId}`
  - `GET /knowledge/books/{bookId}/chunks`
  - `POST /knowledge/search`
  - `POST /knowledge/ingest/pdf`
  - `GET /knowledge/ingest/{jobId}`
- Modulo puro: `scripts/knowledge.py` con cliente Qdrant, filtros, scan de indice, chunking, embeddings y upsert.
- Firestore nuevo: `knowledgeBooks`, `knowledgeIngestJobs`, `knowledgeMeta/summary`.
- Celery task: `content_factory.ingest_knowledge_pdf`.
- Infra: `content-api` y `content-worker` conectados a red externa Docker `qdrant_default`; deploy workflow puede propagar `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_KNOWLEDGE_COLLECTION`.
- Coleccion objetivo: `valtyk_knowledge`; no exponer `claude_sessions`.
- Radar 2 aun no consume Knowledge Hub; quedo listo el contrato `/knowledge/search`.

Flags:

- Backend: `CONTENT_FACTORY_KNOWLEDGE_ENABLED`, `CONTENT_FACTORY_KNOWLEDGE_ADMIN_ONLY`.
- Frontend: `NEXT_PUBLIC_CONTENT_FACTORY_KNOWLEDGE_ENABLED`.
- Qdrant: `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_KNOWLEDGE_COLLECTION`.

Pruebas agregadas:

- `tests/test_knowledge.py`

Verificacion local 2026-05-10:

- `uv run python -m py_compile scripts/knowledge.py api.py worker_tasks.py`
- `uv run --with pytest --with requests pytest tests/test_knowledge.py`
- `cd web && npm run lint`
- `cd web && npm run build`

Segun `MANUAL.md`:

- Descarga de video: resuelta con API HTTPS + Firebase Storage signed URLs.
- Subtitulos: fix deployado en `api.py`, pendiente verificacion con un video real.
- Bug pendiente: `factory.py` aun podria no generar subtitulos dentro del flujo principal; investigar raiz.
- Pendientes de seguridad: borrar service account keys huerfanas en GCP y limpiar historial del commit que expuso `hostinger_env.txt`.
- Pendiente operacional: test end-to-end con video corto real.

## Frontend rediseño v2

Hay un plan activo en `C:\Users\admor\.claude\plans\sprint-2-3-podcaster-frolicking-kazoo.md`.

Decisiones confirmadas:

- Branch de trabajo: `redesign/v2-editorial-cinematic`.
- Usar design kit en `design_kit/content-factory-design-system/`.
- Mantener funcionalidad al 100%; cambios visuales por fases.
- Filosofia visual: editorial cinematic, dark-only, accent ember `#E0533D`, sin emojis estructurales.
- Validar visualmente por fase antes de mezclar a `master`.

Al 2026-05-04 el arbol ya muestra muchos archivos del rediseño modificados/creados en `web/app`, `web/components/project`, `web/lib`.

## Reglas de trabajo recomendadas

- Antes de tocar codigo: leer el archivo objetivo y su contexto inmediato.
- Despues de cada cambio: correr la verificacion mas barata disponible (`npm run lint`, build, o test puntual).
- Para frontend: si se arranca dev server, usar `web/` y probar con navegador local.
- Para backend: no producir videos reales sin confirmacion del usuario; cuesta dinero y tarda.
- No commitear secretos ni archivos generados pesados.
- Actualizar `MANUAL.md` cuando se cierre un hito operativo o se cambie infraestructura.
- Actualizar este archivo si cambia el estado actual, branch, bug activo o proximo paso.

## Power Music Studio A-Z 2026-06-17

Estado: implementado como pipeline admin de musica con render en VPS.

Flujo:

1. `/dashboard/music` genera letra, score, prompt Suno, direccion visual y metadata, o importa una letra existente desde "Ya tengo cancion".
2. El usuario crea la cancion en Suno con prompt maestro/alterno y puede subir varias tomas al mismo track.
3. La UI permite seleccionar `activeAudioVersionId`.
4. Boton `Producir toma activa` llama `POST /music/tracks/{trackId}/produce`.
5. Cada fila de audio tambien permite `Renderizar esta toma`, que llama `POST /music/tracks/{trackId}/audio/{versionId}/produce` sin cambiar la version activa.
6. Backend encola `content_factory.produce_music_video` en Celery; si la cola no esta disponible usa background task de API como fallback.
7. Worker descarga el audio elegido desde Firebase Storage, intenta transcribir con Whisper/OpenAI para timestamps reales de palabra, construye `visualBeats` desde la linea activa cada ~5 segundos, intenta Comfy/Flux por beat, rellena faltantes con fallback local, ensambla `FINAL_MUSIC.mp4` con FFmpeg y sube video/thumbnail/cover/metadata/lyrics/sunoPrompt/subtitles a Storage.
8. Firestore `musicTracks/{trackId}.render` guarda estado compatible del render actual/ultimo.
9. Firestore `musicTracks/{trackId}.renders[]` guarda historial por version de audio para comparar v1.1, v1.2, prompt alterno A/B, etc. sin pisar visualmente los MP4s.

Archivos clave:

- `scripts/power_music.py`
- `scripts/power_music_video.py`
- `api.py`
- `worker_tasks.py`
- `web/app/dashboard/music/page.js`
- `docs/power-music-studio.md`

Estados de track:

- `lyrics_ready`
- `audio_uploaded`
- `video_queued`
- `video_rendering`
- `video_ready`
- `render_failed`

Verificacion pasada en desarrollo:

- Import renderer OK.
- Smoke test local con audio sintetico genero `FINAL_MUSIC.mp4`.
- Smoke test posterior valido que el MP4 final respeta la duracion exacta del audio.
- UI soporta boton rapido de copia en Lyrics, score de letra y versiones de audio.
- Smoke test 2026-06-17 valido renderer `power_music_video_v2_lyric_beats` con 3 beats visuales en 12s y fallback local.
- 2026-06-17: agregado `POST /music/import`, UI para importar letras existentes, prompts visuales mas semanticos para Comfy/Flux y archivo `subtitles.srt` por render.
- 2026-06-17: Power Music render intenta `subtitleMode=whisper_word_aligned` con `OPENAI_API_KEY`; si falla, conserva `subtitleMode=lyric_blocks_estimated`.

## Como pedirle contexto a Claude

Si Claude tiene una sesion mas reciente, pedirle esto y pegar la respuesta aqui antes de seguir:

```text
Resume el estado actual del proyecto Content Factory para otro agente.
Incluye: branch actual, cambios no commiteados, ultimo commit relevante,
archivos tocados en la ultima sesion, decisiones tomadas, bugs activos,
proximo paso recomendado, comandos de verificacion que pasaron/fallaron.
No incluyas secretos, tokens, .env ni credenciales.
```

## Proximo paso sugerido

Primero decidir si seguimos:

1. cerrar/verificar el rediseño frontend v2 en `redesign/v2-editorial-cinematic`, o
2. investigar `factory.py` y subtitulos en flujo principal, o
3. hacer limpieza de seguridad de Firebase/GitHub.

Si no hay preferencia, recomiendo terminar y validar el rediseño visual antes de tocar pipeline caro.

## Live podcast test 2026-05-05

Proyecto real de prueba: `g2x8uKGNWY2LPXvXM6NX`
Titulo: `La ciencia detras de la atraccion que nadie te explico`

Objetivo de la prueba:

- Validar que podcast largo no genere 160+ escenas/imagenes.
- Validar preservacion de bloques de dialogo.
- Confirmar que el flujo futuro no se rompa aunque haya una imagen faltante.

Resultado observado hasta ahora:

- Podcast genero `15` escenas para `133` bloques de dialogo y `3538` palabras. Esto valida el fix principal B3/B6 a nivel de conteo.
- Resultado final visto por el usuario: aprox. `22` minutos reales.
- Feedback de calidad del usuario:
  - Guion excepcional, relevante, coherente y con estructura suficientemente buena para publicar.
  - Turnos de podcast buenos; en general se sintio humano.
  - Voces con errores minimos: silencios muy cortos y algunos momentos donde se percibe IA, pero no bloqueantes.
  - Principal debilidad: imagenes. Ya no salieron tetricas/controversiales, pero hubo demasiadas caras y manos mal formadas.
  - Con mejoras visuales, el producto ya podria empezar a generar contenido para YouTube.
- Firestore mostro `15` escenas, pero despues de imagenes solo habia `14/15` `imageUrl`.
- Faltaba especificamente `scene_0006.png` en `/app/output/videos/{safe_title}/images`.
- La UI mostro `99%` durante imagenes/voz, aunque el backend aun estaba en fases intermedias. La barra evita llegar a 100 antes de tiempo, pero todavia no representa bien el progreso end-to-end.
- Imagenes generadas: algunas tienen riesgo de anatomia rota/manos/fingers. Para podcasts conviene evitar manos/rostros detallados cuando no aportan.
- Comfy Cloud si tenia la imagen original de escena 6, pero con filename hash. El proyecto no guardaba `jobId` ni metadata remota por escena, por eso la recuperacion no era directa.

Intervencion manual durante la prueba:

- Primero se creo `scene_0006.png` copiando `scene_0005.png` como fallback no destructivo para evitar que Ken Burns fallara.
- Luego se encontro el job original en Comfy por `preview_output.display_name == scene_0006_00001_.png`.
- Se descargo la imagen original y se reemplazo la copia antes de que Ken Burns procesara escena 6.
- Se dejo backup: `scene_0006.copied_neighbor.bak.png`.
- No se reiniciaron workers y no se gasto una generacion nueva.

Correcciones obligatorias despues de que termine esta prueba:

1. Persistir metadata remota por imagen:
   - Guardar por escena: `scene_number`, `prompt`, `jobId`, `displayName`, `remoteFilename`, `subfolder`, `providerStatus`, `downloadedAt`, `localPath`, `imageUrl`.
   - Esto permite recovery exacto sin buscar a mano en jobs.

2. Validacion dura entre fases:
   - Despues de imagenes, validar que existan todos los `scene_XXXX.png` esperados y que Firestore tenga `imageUrl` para cada escena.
   - Si falta algo, reintentar descarga desde job remoto.
   - Si aun falta, no avanzar a voz/montaje; marcar estado recuperable tipo `image_recovery_required`.

3. `factory.py --images-only` / API:
   - Hoy el proceso puede terminar con `failed > 0` y aun asi avanzar porque el return code no falla.
   - Cambiar contrato para que errores de imagen sean visibles a la API.
   - API debe parsear/validar resultado, no confiar solo en exit code.

4. Progreso real end-to-end:
   - Evitar que el 100% de `script_ready` contamine produccion.
   - Pesos recomendados: investigacion 5%, guion 15%, imagenes 30%, voz 20%, movimiento/montaje 20%, entrega 10%.
   - Mientras falte cualquier fase, capar progreso global a 99%.
   - Mostrar subtareas reales: imagenes `n/total`, voz `n/total`, movimiento `n/total`, entrega final.

5. Prompts visuales para podcast:
   - Para podcasts usar prompts de bajo riesgo anatomico: objetos, ambientes, siluetas, espaldas, manos fuera de cuadro, planos macro abstractos.
   - Evitar frases que inviten manos/dedos/rostros muy cercanos salvo que sea necesario.
   - Mantener estilo premium/editorial, pero con guardrails negativos de anatomia.

6. Ocultar proveedores/modelos en UI final:
   - Revisar textos visibles para que nunca digan nombres de proveedores/modelos internos.
   - Mantener lenguaje tipo "Investigacion", "Guion", "Visuales", "Voz", "Montaje", "Entrega final".
   - Logs internos pueden conservar detalle tecnico, pero no UI del cliente.

7. Sincronizacion UI/Firestore:
   - La UI debe reflejar exacto `imageUrl` por escena y actualizar al recuperarse una imagen.
   - Si backend recupera una imagen, Firestore debe actualizar una sola escena sin pisar otras.

8. Observabilidad:
   - Enviar a Sentry warning/evento no secreto cuando falte una escena o cuando se use recovery.
   - Tags utiles: `project_id`, `scene_number`, `phase`, `recoverable=true`.

Implementado antes de la siguiente prueba:

- `scripts/factory.py`
  - Guarda `image_jobs.json` con metadata remota por escena: job id, display/filename remoto, outputs y path local.
  - Intenta recuperar descargas faltantes desde outputs remotos ya generados, sin crear jobs nuevos.
  - Valida que todos los `scene_XXXX.png` esperados existan antes de voz.
  - `--images-only` sale con error si quedan imagenes faltantes/invalidas.
  - Ken Burns y ensamblaje final fallan si faltan visuales, en vez de continuar con menos escenas.
  - Prompt base de podcast ahora favorece objetos/abstraccion y aleja caras/manos/dedos.

- `api.py`
  - Sincroniza Firestore contra disco al terminar imagenes para evitar UI `14/15` cuando el monitor pierde una escena.
  - Cuenta solo archivos exactos `scene_0001.png`; backups como `scene_0006.copied_neighbor.bak.png` ya no cuentan como imagen real.
  - Si falta una imagen, limpia `imageUrl`, marca escena `missing_image` y detiene la produccion como error recuperable antes de gastar voz/montaje.
  - Guarda `productionStartedAt`, `productionCompletedAt` y `productionDurationSeconds` para medir duracion real.

- `scripts/generate_content.py` y `prompts/video_prompt_generator_podcast.md`
  - Templates de podcast actualizados para evitar manos, dedos, rostros frontales y retratos.
  - El set visual se inclina a objetos, estudios vacios, abstraccion y siluetas anonimas.

- `scripts/elevenlabs_tts.py`
  - Se mantiene baseline validado `baseline_2026_05_05` sin cambiar el sonido actual.
  - Se agrego perfil opcional `PODCAST_TTS_PROFILE=natural_v2` para A/B test futuro; rollback inmediato dejando o volviendo a baseline.

- `web/app/dashboard/project/[id]/page.js`
  - La barra de progreso ya puede bajar si cambia de `script_ready` a produccion real; evita quedarse pegada en 99%.

Verificacion local:

- `py_compile` paso en `api.py`, `factory.py`, `generate_content.py`, `elevenlabs_tts.py`.
- `npm run lint` paso en `web/`.
- `npm run build` paso con red habilitada para `next/font`.
- Tests nuevos agregados:
  - `tests/test_podcast_visual_pipeline.py`
  - `tests/test_factory_visual_validation.py`
  - No se ejecutaron localmente porque el runtime embebido no tiene `pytest` ni dependencias runtime (`openai`, etc.); quedan para entorno del repo/VPS.
