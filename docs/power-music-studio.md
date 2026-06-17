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
- multiples tomas/versiones de audio por una misma letra.
- calificador de letra sin costo extra.

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
- Renderiza el video en worker/Celery con fallback a background task si la cola no esta disponible.
- No usa Luma por default.
- Renderer v1: imagenes locales premium con PIL + movimiento Ken Burns en FFmpeg.
- El score de letra es heuristico: no llama otro modelo ni consume API adicional.

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
ANTHROPIC_API_KEY=...
```

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

Devuelve un track individual con `package`, `audio` y `render`.
Tambien devuelve `audioVersions` y `activeAudioVersionId`.

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

Encola el render musical completo en el VPS.

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
- `scripts/power_music_video.py`: renderer local de video musical con PIL + FFmpeg.
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
   - `suno_prompt.txt`.
11. La UI muestra progreso, video final, miniatura y enlaces.

## Proximos Bloques

1. Conectar Comfy/Flux como proveedor opcional de escenas reales.
2. Agregar waveform visual reactivo al audio.
3. Integrar publicacion directa a YouTube reutilizando el centro de publicaciones.
4. Agregar ZIP de material musical completo.
5. Calificador LLM opcional para comparar letras con mayor criterio artistico.

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
- seleccionar la version activa;
- pulsar "Producir video musical";
- esperar `video_ready`;
- reproducir `FINAL_MUSIC.mp4` y abrir la miniatura.
- confirmar que no consume credito interno.

## Riesgos

- Suno puede interpretar prompts de forma variable: por eso se genera prompt alternativo y negative prompt.
- Letras demasiado genericas: el formulario pide angulo personal y elementos obligatorios.
- Temas de cuerpo/comida: deben tratarse como autocuidado y fuerza, nunca castigo.
- Copyright: no pedir estilos de artistas reales ni copiar letras.
