# Musica con OpenAI — 18 de octubre de 2026

## Flujo actual

1. Crear el paquete de letra y prompt con el compositor existente (Anthropic), o importar una letra propia.
2. Copiar la letra y el prompt en Suno, generar la cancion manualmente y subir su audio a la app.
3. Preparar un storyboard con personajes, vestuario, lugares y acciones vinculados a la letra. El compositor lo entrega para los paquetes nuevos; las canciones importadas o antiguas sin storyboard usan un planificador de texto OpenAI antes de generar imagenes.
4. Generar escenas y miniatura con OpenAI Images. FFmpeg monta el audio, las imagenes, movimientos de camara y transiciones. Sigue siendo un montaje de imagenes; no produce movimiento real de los personajes.
5. Si la transcripcion esta activada, OpenAI alinea el audio. Los subtitulos requieren suficiente confianza; un fallo de alineacion no impide montar el video.

Suno sigue sin integracion directa. Musica usa el perfil `openai_only`, fijado en la API y transportado en cada trabajo de Celery. Este perfil impide Comfy, ElevenLabs y Deepgram, incluso si existen sus claves o configuraciones antiguas. Los Shorts conservan el audio musical y no llaman a ElevenLabs para la firma de voz. Otros modulos de Content Factory conservan su configuracion.

Las llamadas a OpenAI y al compositor usan saldo de sus respectivas APIs. "Sin creditos internos" no significa generacion gratuita. Esta revision se verifico sin llamadas pagadas ni prueba de disponibilidad de modelos en la cuenta.

## Por que aparecian pesas

Se mezclaba el contexto de escucha (por ejemplo, entrenar) con la narrativa. Algunos prompts incluian pesas, estadios o entrenamiento como ejemplos universales. Palabras metaforicas como "me levanto", "fuerza" o "el peso del pasado" activaban recetas deportivas. Ademas, las escenas del compositor se sustituian por plantillas y la cache podia conservar una imagen aunque cambiara su prompt.

Ahora el director v6 conserva el storyboard estructurado y separa el contexto de escucha. Las indicaciones humanas tienen prioridad sobre los bancos genericos. Cada receta conserva los personajes, relaciones, vestuario, lugar y accion del relato. El deporte requiere evidencia explicita; las exclusiones como "sin boxeo" no seleccionan ese deporte.

La revision visual evalua relevancia narrativa ademas de anatomia y texto accidental. Una imagen atractiva pero ajena al relato puede rechazarse. La reparacion usa OpenAI; un rechazo persistente pasa a una imagen procedural local, sin reciclar la miniatura rechazada. Los avisos y `degradedOutput` hacen visible ese resultado.

Las imagenes tienen firma de prompt, modelos, calidad, tamano y version del director. Las imagenes antiguas sin firma no se reutilizan como si fueran del relato nuevo.

## Modelos y configuracion

| Trabajo | Valor predeterminado | Observacion |
| --- | --- | --- |
| Componer letra y paquete Suno | `claude-opus-4-7` | Se conserva la configuracion existente. |
| Planificar historias importadas/antiguas | `gpt-6-luna` | Una llamada de texto con salida estructurada, configurable por `CONTENT_FACTORY_MUSIC_STORY_MODEL`. No reescribe la letra. |
| Generar escenas y miniatura | `gpt-image-2.5-flare` | Configurable; puede intentar `gpt-image-2`, `gpt-image-1.5` y `gpt-image-1` como respaldo, todos de OpenAI. |

El planificador reutiliza storyboards validos del compositor o humanos. Sus planes propios llevan firma de entrada para invalidarlos cuando cambia la letra o direccion. Un fallo se registra como direccion provisional, no como guion semantico completado.

Variables publicas de Musica:

- `CONTENT_FACTORY_MUSIC_PRODUCTION_PROFILE=openai_only`.
- `CONTENT_FACTORY_MUSIC_OPENAI_IMAGES_ENABLED=true`.
- `CONTENT_FACTORY_MUSIC_OPENAI_IMAGE_MODEL=gpt-image-2.5-flare` y `CONTENT_FACTORY_MUSIC_THUMBNAIL_MODEL=gpt-image-2.5-flare`.
- `CONTENT_FACTORY_MUSIC_STORY_PLANNING_ENABLED=true` y `CONTENT_FACTORY_MUSIC_STORY_MODEL=gpt-6-luna`.
- `CONTENT_FACTORY_MUSIC_TRANSCRIPTION_ENABLED` controla alineacion; `CONTENT_FACTORY_MUSIC_PREMIUM_THUMBNAIL_ENABLED` y `CONTENT_FACTORY_MUSIC_OPENAI_VISION_QA_ENABLED` controlan miniatura y QA.

No se configura ninguna clave dentro del repositorio. Se necesita `OPENAI_API_KEY` en el entorno normal del backend. Tener clave no demuestra saldo ni acceso a cada modelo. Los fallos, modelos efectivos y respaldos quedan registrados en los metadatos. No hay una estimacion fija fiable por imagen de GPT Image 2.5: el costo depende del consumo y la configuracion.

## Evaluacion y siguientes mejoras

La base es util: Suno manual evita depender de una integracion adicional, FFmpeg permite continuar sin un servidor de Comfy y OpenAI cubre imagenes, alineacion y revision. El mayor problema era perder la intencion narrativa entre etapas; cambiar solamente el modelo no lo resolvia.

La continuidad por instrucciones mejora la coherencia, pero no garantiza el mismo rostro entre imagenes independientes. La siguiente mejora de mayor valor es revisar 3-6 imagenes clave antes de producir toda la cancion, aprobar una referencia de personajes y generar/editar los demas planos a partir de ella. Tambien conviene poder regenerar una escena aislada y fijar un limite de gasto. Esas funciones de aprobacion visual, referencias y presupuesto todavia no estan implementadas en este cambio.

No recomiendo agregar ahora mas orquestadores o plataformas de video. Conviene medir primero relacion con la letra, continuidad, porcentaje de rechazos, tiempo y costo por video. El `lyricScore` actual es una heuristica textual: no escucha la cancion ni mide su calidad musical. Figma/Canva, LangGraph y otras herramientas marcadas "ready" en los contratos no constituyen integraciones ejecutadas por este motor.

## Verificacion y operacion

Las 91 pruebas y 12 subpruebas de Musica usan proveedores, cola y Firebase simulados. Cubren propagacion del perfil, mensajes antiguos de Celery, prompts, deportes metaforicos/explicitos/negados, conservacion del storyboard, cache, QA y respaldos. Dos pruebas adicionales verifican la cache del service worker. Se verifican lint y build del frontend; lint conserva dos avisos previos sobre etiquetas `img`. Un smoke local produjo un MP4 H.264/AAC de 4 segundos a 1920x1080 con cero intentos de red. Falta una prueba artistica con una cancion real y saldo de la cuenta para evaluar el resultado generado.

Para trabajar desde casa: `cd web` y `npm run dev:remote -- --hostname 127.0.0.1 --port 3001`; abrir `http://localhost:3001/dashboard/music`. El backend se ejecuta en el VPS. La interfaz exige que el servidor anuncie el perfil nuevo antes de lanzar renders. Los videos ya terminados no se regeneran automaticamente con estos cambios.

Fuentes oficiales consultadas el 18 de octubre de 2026: [GPT Image 2.5 Flare](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare), [generacion de imagenes](https://developers.openai.com/api/docs/guides/image-generation), [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [salida estructurada](https://developers.openai.com/api/docs/guides/structured-outputs) y [precios](https://developers.openai.com/api/docs/pricing#image-generation).
