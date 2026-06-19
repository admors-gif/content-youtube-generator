# Power Music Studio

Estado: 2026-06-17

## Objetivo

Power Music Studio convierte una idea de crecimiento personal en un paquete creativo listo para Suno:

- letra original;
- hook y mantra;
- prompt maestro para Suno;
- prompt alternativo;
- negative prompt;
- portada;
- direccion visual para video;
- metadata de YouTube.
- upload del audio final descargado de Suno.
- produccion de video final en VPS con visuales generativos locales, Ken Burns, thumbnail, cover y metadata.
- Music Director v2 para visuales premium simbolicos, sin Luma y sin Runway.
- multiples tomas/versiones de audio por una misma letra.
- calificador de letra sin costo extra.
- importacion de canciones ya creadas: pegar letra, crear track, subir audio de Suno y renderizar video.
- visuales sincronizados con la letra cada ~5 segundos, usando Comfy/Flux cuando este configurado y fallback local si falla.
- archivo `subtitles.srt` por version renderizada. Si `OPENAI_API_KEY` esta disponible usa Whisper con timestamps de palabra; si falla, cae a sincronizacion estimada por bloques de letra.

La v1 no usa una API de Suno. El usuario copia el paquete a Suno, descarga la cancion y la sube al track en Content Factory. Desde ahi Content Factory ya puede mandar el render completo al VPS/worker para generar `FINAL_MUSIC.mp4`, miniatura y portada sin depender de que la computadora del usuario permanezca prendida.

## Decisiones

- Feature admin-only en v1.
- No consume creditos internos.
- Usa Anthropic por backend.
- Modelo por default: `claude-opus-4-7`.
- No permite subliminal oculto; usa afirmaciones conscientes y sanas.
- No imita artistas reales ni canciones existentes.
- Guarda paquetes en Firestore para reutilizarlos.
- Guarda cada version de audio en Firebase Storage bajo `music/{uid}/{trackId}/audio/`.
- Permite seleccionar una version activa antes de producir el video.
- Permite renderizar una toma especifica sin cambiar la version activa.
- Guarda historial de videos por toma en `musicTracks/{trackId}.renders[]`.
- Renderiza el video en worker/Celery con fallback a background task si la cola no esta disponible.
- No usa Luma por default.
- Renderer v4: Music Director v2 + timeline visual por letra. Divide el audio en beats de ~5 segundos, genera prompts Flux por linea/seccion de la cancion y ensambla con Ken Burns en FFmpeg.
- Si `COMFYUI_API_KEY` esta configurado y `CONTENT_FACTORY_MUSIC_COMFY_ENABLED` no esta desactivado, intenta generar imagenes reales con Flux/Krea via Comfy.
- Si Comfy falla o no esta configurado, usa fallback local limpio sin mostrar prompts tecnicos en pantalla.
- Si `OPENAI_API_KEY` esta configurado y `CONTENT_FACTORY_MUSIC_WHISPER_SUBTITLES_ENABLED` no esta desactivado, transcribe el audio con Whisper, alinea la letra con timestamps reales y usa esas lineas para subtitulos y prompts visuales.
- Si Whisper falla, no se cae el render: el renderer usa `lyric_blocks_estimated`.
- El score de letra es heuristico: no llama otro modelo ni consume API adicional.
- Luma y Runway quedan excluidos por decision de producto para este motor musical.

## Music Director v2

Archivo principal: `scripts/power_music_director.py`.

Objetivo: convertir la letra y la intencion de la cancion en una biblia visual reutilizable antes de pedir imagenes. El director decide un mundo visual, motivos permitidos, objetos prohibidos, reglas de continuidad y un contrato de prompt para que Comfy/Flux genere frames premium sin texto quemado.

Lo que hace hoy:

- Elige uno de estos mundos: `luxury_ascent`, `athletic_power`, `feminine_power`, `inner_child_victory` o `shadow_to_power`.
- Reescribe la direccion visual del paquete con escenas simbolicas y text-free.
- Prohibe letras, logos, pantallas con texto, pseudo-palabras, posters, planchas, objetos domesticos aleatorios y visuales literales por cada frase.
- Guarda `package.musicVideoDirector` y `videoConcept.directorPlan`.
- Agrega `directorVersion`, `musicVideoDirector` y `promptGateSummary` en metadata del render.
- Expone badges `Director v2`, `Sin Luma`, `Sin Runway` en la UI de musica.

Contratos preparados:

- LangGraph: el plan guarda nodos listos (`creative_brief`, `scene_planner`, `prompt_gate`, `image_generation`, `vision_critic`, `renderer`, `analytics`) para convertir el flujo en grafo stateful si el motor musical crece.
- Inngest: el plan deja eventos sugeridos para retries y jobs largos sin bloquear UI.
- n8n: recomendado solo para automatizaciones externas como avisos, archivado o checklist de publicacion.
- OpenAI Vision QA: disponible via `CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_ENABLED`, pero apagado por default para evitar costo extra. Si se prende, revisa hasta `CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_MAX_FRAMES` frames y guarda `visionQa` en metadata.
- Remotion: marcado como ready si despues queremos plantillas animadas reutilizables; el render actual sigue en FFmpeg porque ya es estable.
- Qdrant/PostHog/Langfuse: se guardan campos listos en metadata para memoria visual, medicion y trazabilidad futura.

## Variables

Backend:

```env
CONTENT_FACTORY_MUSIC_STUDIO_ENABLED=true
CONTENT_FACTORY_MUSIC_STUDIO_ADMIN_ONLY=true
CONTENT_FACTORY_MUSIC_MODEL=claude-opus-4-7
CONTENT_FACTORY_MUSIC_MAX_TOKENS=5200
CONTENT_FACTORY_MUSIC_ALLOW_FALLBACK=false
MUSIC_MAX_AUDIO_BYTES=167772160
MUSIC_RENDER_DIR=/app/output/music_renders
CONTENT_FACTORY_MUSIC_COMFY_ENABLED=true
CONTENT_FACTORY_MUSIC_VISUAL_INTERVAL_SECONDS=5
CONTENT_FACTORY_MUSIC_MAX_VISUAL_BEATS=120
CONTENT_FACTORY_MUSIC_MAX_COMFY_IMAGES=120
CONTENT_FACTORY_MUSIC_WHISPER_SUBTITLES_ENABLED=true
CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_ENABLED=false
CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_MODEL=gpt-4o-mini
CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_MAX_FRAMES=8
ANTHROPIC_API_KEY=...
COMFYUI_API_KEY=...
OPENAI_API_KEY=...
```

Notas de costo visual:

- Una cancion de 3 minutos con intervalo de 5 segundos genera aprox. 36 imagenes.
- `CONTENT_FACTORY_MUSIC_MAX_COMFY_IMAGES` limita cuantas imagenes se mandan a Comfy por render.
- Los beats que excedan el limite o fallen entran con fallback local.
- Para apagar Comfy sin romper el render: `CONTENT_FACTORY_MUSIC_COMFY_ENABLED=false`.

Frontend:

```env
NEXT_PUBLIC_CONTENT_FACTORY_MUSIC_STUDIO_ENABLED=true
```

## Endpoints

### `GET /music/presets`

Devuelve intenciones, estilos, usos recomendados y modelo activo.

### `GET /music/tracks`

Lista paquetes recientes del usuario/admin desde `musicTracks`.

### `GET /music/tracks/{trackId}`

Devuelve un track individual con `package`, `audio`, `render`, `renders`, `audioVersions` y `activeAudioVersionId`.

- `render` conserva el ultimo render/estado principal por compatibilidad.
- `renders[]` contiene el historial por `audioVersionId`, para conservar MP4, miniatura y metadata de cada toma.

### `POST /music/generate`

Genera y guarda un paquete musical.

Payload principal:

```json
{
  "intention": "disciplina",
  "style": "latin_trap_anthem",
  "theme": "Hoy no negocio conmigo",
  "targetUse": "entrenar fuerza",
  "energy": "alta, elegante, feroz pero limpia",
  "vocalPerspective": "primera persona",
  "personalAngle": "Cancion para entrenar y volver a mi vision.",
  "mustInclude": "hook repetible, promesa conmigo mismo",
  "mustAvoid": "imitacion de artistas reales"
}
```

### `POST /music/import`

Crea un track desde una cancion existente. No llama Anthropic y no consume creditos internos. Sirve cuando el usuario ya tiene letra de Suno u otra fuente y solo quiere producir el video.

Payload principal:

```json
{
  "title": "Hoy no negocio conmigo",
  "subtitle": "Disciplina para entrenar sin excusas",
  "intention": "disciplina",
  "style": "latin_trap_anthem",
  "energy": "alta, elegante, cinematica",
  "visualIdentity": "guerrero moderno al amanecer, gimnasio industrial, oro y azul profundo",
  "lyrics": "[Intro]\nHoy no negocio conmigo..."
}
```

Respuesta:

```json
{
  "ok": true,
  "trackId": "music_...",
  "track": {},
  "package": {},
  "generationMode": "external_song_import",
  "creditCharged": false
}
```

### `POST /music/tracks/{trackId}/audio`

Sube una version de audio descargada de Suno al track. Cada upload se guarda como una toma nueva y queda seleccionada como activa.

Form fields opcionales:

- `label`: nombre visible, por ejemplo `Prompt maestro A`, `Prompt alterno B`.
- `promptKind`: `original`, `alternate`, `retry` o `manual`.

Formatos v1:

- `.mp3`
- `.wav`
- `.m4a`
- `.aac`

Respuesta:

```json
{
  "ok": true,
  "track": {
    "trackId": "...",
    "status": "audio_uploaded",
    "activeAudioVersionId": "take_...",
    "audioVersions": [],
    "audio": {
      "versionId": "take_...",
      "label": "Prompt maestro A",
      "promptKind": "original",
      "fileName": "...",
      "contentType": "audio/mpeg",
      "sizeBytes": 123,
      "storagePath": "gs://...",
      "url": "https://..."
    }
  }
}
```

### `POST /music/tracks/{trackId}/audio/{versionId}/activate`

Selecciona una toma de audio como version activa. Si el render anterior era de otra toma, queda marcado como pendiente para evitar confundir MP4 viejo con audio nuevo.

### `POST /music/tracks/{trackId}/produce`

Encola el render musical completo en el VPS usando la version activa.

Precondicion:

- el track debe tener una version activa de audio.

Respuesta:

```json
{
  "ok": true,
  "status": "queued",
  "dispatch": {
    "queue": "celery",
    "taskId": "..."
  },
  "track": {
    "status": "video_queued",
    "render": {
      "status": "queued",
      "progress": 2,
      "audioVersionId": "take_..."
    }
  }
}
```

### `POST /music/tracks/{trackId}/audio/{versionId}/produce`

Encola el render musical completo para una toma especifica, sin cambiar `activeAudioVersionId`.

Uso recomendado:

- subir `Prompt maestro A`, `Prompt maestro B`, `Prompt alterno A`, etc.;
- pulsar `Renderizar esta toma` en cada version;
- revisar la seccion `Videos generados por version`;
- abrir el MP4/miniatura de cada toma sin pisar visualmente las demas.

Solo se permite un render activo por track para evitar colisiones de worker y gasto duplicado.

Respuesta:

```json
{
  "ok": true,
  "trackId": "...",
  "package": {},
  "saved": true,
  "model": "claude-opus-4-7",
  "generationMode": "llm",
  "creditCharged": false
}
```

## Firestore

Coleccion: `musicTracks`

Campos principales:

- `userId`
- `email`
- `status`
- `package`
- `input`
- `model`
- `generationMode`
- `createdAt`
- `updatedAt`
- `audio`
- `audioVersions`
- `activeAudioVersionId`
- `render`
- `renders`

`render` es el estado compatible del render actual/ultimo.

`renders[]` guarda un registro por toma:

- `audioVersionId`
- `audioLabel`
- `status`
- `progress`
- `stepName`
- `video`
- `thumbnail`
- `cover`
- `metadata`
- `lyrics`
- `sunoPrompt`
- `subtitles`
- `durationSeconds`
- `visualBeatCount`
- `subtitleMode`
- `subtitleCount`
- `visualProvider`
- `queue`
- `taskId`
- `error`
- `queuedAt`
- `startedAt`
- `completedAt`
- `updatedAt`

`package.lyricScore` contiene:

- `total`
- `dimensions.melodia`
- `dimensions.lirica`
- `dimensions.ritmo`
- `dimensions.viralidad`
- `dimensions.musica`
- `dimensions.coherencia`
- `dimensions.impacto`
- `dimensions.poder`
- `strengths`
- `risks`
- `suggestions`

Estados v1:

- `lyrics_ready`
- `audio_uploaded`
- `video_queued`
- `video_rendering`
- `video_ready`
- `render_failed`

Estados futuros:

- `published`
- `archived`

## Archivos Principales

- `scripts/power_music.py`: presets, prompt builder, normalizacion y fallback.
- `scripts/power_music_video.py`: renderer de video musical; crea un visualizer simbolico premium desde el arco emocional, intenta Comfy/Flux y arma MP4 con FFmpeg.
- `api.py`: endpoints `/music/*`.
- `worker_tasks.py`: task Celery `content_factory.produce_music_video`.
- `web/app/dashboard/music/page.js`: UI admin.
- `web/components/Sidebar.js`: acceso en dashboard.
- `prompts/agent_power_music.md`: prompt maestro documentado.

## Flujo Actual

1. Admin abre `/dashboard/music`.
2. Llena intencion, estilo, tema, energia y notas.
3. Pulsa "Generar paquete premium".
4. Copia letra y prompt a Suno.
5. Genera la cancion en Suno con prompt maestro y/o alternativo.
6. Descarga las versiones buenas.
7. Sube cada audio al mismo track en `/dashboard/music`.
8. Escucha y selecciona la version activa.
9. Pulsa "Producir video musical".
10. El VPS/worker genera:
   - `FINAL_MUSIC.mp4`;
   - `thumbnail.jpg`;
   - `cover.jpg`;
   - `metadata.json`;
   - `lyrics.txt`;
   - `suno_prompt.txt`;
   - `subtitles.srt`.
11. La UI muestra progreso, video final, miniatura, proveedor visual (`Flux/Comfy` o fallback local), numero de beats y enlaces.

Flujo alterno con cancion existente:

1. Admin abre `/dashboard/music`.
2. En "Ya tengo cancion", pega titulo, letra completa, estilo e identidad visual.
3. Pulsa "Crear track para video".
4. Sube el audio final descargado de Suno como toma.
5. Renderiza la toma activa o una toma especifica.
6. El renderer intenta alinear la letra con Whisper/OpenAI. Si hay timestamps confiables, exporta `subtitles.srt`; el video final no quema letras encima por defecto.
7. Los prompts visuales usan un mundo simbolico premium por bloques emocionales, no ilustraciones literales linea por linea. Las imagenes generadas deben ser text-free; portada y miniatura agregan texto exacto desde backend.

## Proximos Bloques

1. Agregar waveform visual reactivo al audio.
2. Integrar publicacion directa a YouTube reutilizando el centro de publicaciones.
3. Agregar ZIP de material musical completo.
4. Calificador LLM opcional para comparar letras con mayor criterio artistico.
5. Mejorar alineacion a nivel palabra/LRC si Suno exporta letras cronometradas en el futuro.

## Handoff Para Otro Equipo

Para continuar:

```powershell
git pull origin master
```

Validar:

```powershell
python -m py_compile api.py worker_tasks.py scripts\power_music.py scripts\power_music_video.py
cd web
npm run lint
npm run build
```

Probar en produccion:

- abrir `/dashboard/music`;
- generar paquete;
- copiar prompt a Suno;
- confirmar que aparece en tracks recientes;
- subir un `.mp3` o `.wav` descargado de Suno;
- subir varias tomas si Suno devuelve mas de una version;
- reproducir audios desde la UI;
- confirmar que el render muestre `Whisper` si se genero con timestamps reales o `SRT estimado` si uso fallback;
- seleccionar la version activa;
- pulsar "Producir video musical";
- esperar `video_ready`;
- reproducir `FINAL_MUSIC.mp4` y confirmar que cambian los visuales por beats de letra.
- abrir metadata y revisar `visualBeatCount`, `visualProvider`, `generatedFrames`, `fallbackFrames` y `visualBeats`.
- confirmar que no consume credito interno.

## Riesgos

- Suno puede interpretar prompts de forma variable: por eso se genera prompt alternativo y negative prompt.
- Letras demasiado genericas: el formulario pide angulo personal y elementos obligatorios.
- Temas de cuerpo/comida: deben tratarse como autocuidado y fuerza, nunca castigo.
- Copyright: no pedir estilos de artistas reales ni copiar letras.
