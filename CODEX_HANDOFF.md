# Content Factory - AI Handoff

Ultima revision local: 2026-05-05

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
