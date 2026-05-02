# 🗺️ Product Roadmap — Content Factory

> Ruta de evolución de "pipeline funcional" a "producto que sostiene tu plan estratégico de 3 canales con 100+ videos/mes, eventualmente vendible como SaaS".
>
> **Origen:** sesión 2026-05-02 tras validar producción end-to-end de "La vida de Michael Jackson" ($5.76 USD, video con subtítulos burned-in, subido a Firebase Storage, descargable via signed URL).
>
> **Ver también:** `MANUAL.md` (estado actual, infraestructura), memoria `project_content_factory_next_session.md` (contexto previo).

---

## Principios de ejecución

1. Cada fase termina con algo USABLE en producción.
2. Cada feature: build → test E2E → commit/push → auto-deploy via runner self-hosted → verify.
3. `MANUAL.md` se actualiza con cada sprint terminado.
4. Decision gate después de cada fase: continuar o ajustar.
5. Cero technical debt. No se empieza una nueva fase sin cerrar la anterior.

---

## Phase 0 — Quick Wins + Foundation (Semana 1-2, ~25h)

**Goal:** wins visibles que generan momentum + base para producir en paralelo.

### Sprint 0.1 — UX wins (3-4 días)
- **Video player** en página de proyecto: HTML5 player consumiendo signed URL desde `/video-url/{id}`. Lazy load, thumbnail preview.
- **Recomendador de agente**: al crear nuevo proyecto, prompt rápido a Claude Haiku con el tema → sugiere los 3 mejores agentes con razonamiento corto.
- **ZIP organizado** con todo el material del proyecto: estructura `video/`, `audio/narrations/`, `images/`, `luma_clips/`, `thumbnails/`, `script.txt`, `prompts.json`, `metadata.json`. Streaming server-side, no en memoria.

### Sprint 0.2 — Observabilidad básica (2 días)
- **Sentry** integrado para errores en backend (free tier 5K events/mes). Stack traces capturados con context (project_id, agent, step).
- **Logging estructurado** (JSON) en lugar de print(). Library: `structlog`.
- **Endpoint `/metrics`** que expone: jobs en queue, tiempo promedio por step, costo acumulado del día.

### Sprint 0.3 — Cola persistente con workers paralelos (5-7 días)
- **Celery** + Redis (Redis ya está en VPS como `calcom-redis`).
- Workers en docker-compose escalables (3 workers iniciales, configurable).
- Cada paso del pipeline (script → images → audio → luma → assembly → subtitles → upload) es task celery con retry.
- Frontend muestra progreso real-time consultando estado de jobs.
- Si un worker muere mid-job, otro retoma desde el último checkpoint.

**Decision gate Phase 0:** ¿el sistema procesa 3 videos simultáneos sin pelearse por recursos?

---

## Phase 1 — Calidad antes de escalar (Semana 3, ~10h)

**Goal:** evitar que escalar a 100 videos/mes destruya tu marca.

### Sprint 1.1 — Gate de moderación (2 días)
- Tras generar guión, llamada a OpenAI Moderation API (gratis).
- Score por categoría (violence, sexual, self-harm, hate).
- Si supera umbrales, marca proyecto como `requires_review` en Firestore.
- Frontend muestra warning con scores y razones.
- Producción solo continúa con aprobación humana explícita.

### Sprint 1.2 — Fact-checking layer (3 días)
- Tras generar guión, segundo pase de Claude que extrae claims numéricos/factuales.
- Cada claim se valida contra investigación de Tavily realizada al inicio.
- UI muestra cada claim con: source confidence (alta/media/baja), sugerencia de fuente, opción de editar.
- Si <60% de claims tienen `confidence=alta`, marca como `needs_fact_check`.

**Decision gate Phase 1:** ¿tienes confianza para publicar 4 videos/semana sin riesgo de que te quemen por errores?

---

## Phase 2 — Nuevos formatos (Semana 4-5, ~25h)

**Goal:** desbloquear los formatos que el plan estratégico de canales exige.

### Sprint 2.1 — Pipeline de Shorts (4-5 días)
- Tras producir long-form, identifica los 3 momentos de mayor "intensity score" (heuristics: pico de hook score, palabras de impacto, transiciones cinematográficas).
- Para cada momento: extrae 60s de audio + visuales correspondientes.
- Re-render como vertical 9:16 con captions más grandes y dinámicos.
- Hook visual en los primeros 3s (zoom-in controlado, no glitch obvio).
- Auto-genera 3 variantes de Short por video largo, costo marginal ~$0.30 c/u.

### Sprint 2.2 — Pipeline de thumbnails (3-4 días)
- Template programático por canal (font, paleta, layout fijo).
- Genera 3 variantes con Flux (oil painting style + composición Cinzel) + composición programática con Pillow.
- Output: 3 PNGs 1280x720 listos para subir.

### Sprint 2.3 — Podcaster agent v1 (5-6 días)
- Nuevo agente `agent_podcaster_*` con prompt que genera dialogue (`Anfitrión: ...` / `Invitado: ...`).
- 2 voces ElevenLabs distintas (configurables por agente).
- Pipeline TTS multi-voz con timing (gaps de 0.3-0.5s entre intervenciones).
- Music bed loop opcional (catalog interno).
- Visualización: video con waveform animado o avatares estáticos.
- Outputs: mp3 (audio puro para Spotify) + mp4 (con visual para YouTube).

**Decision gate Phase 2:** ¿generas long-form + 3 shorts + 3 thumbnails + opción podcast en la misma sesión?

---

## Phase 3 — Distribución (Semana 6-7, ~15h)

**Goal:** automatizar el último paso manual: subir a YouTube.

### Sprint 3.1 — YouTube Data API integration (4-5 días)
- Setup OAuth 2.0 con cuentas de Google.
- Upload de video con metadata (título, descripción, tags, categoría, idioma).
- Auto-marcado de "altered or synthetic content".
- Upload de thumbnail.
- Programación según calendario configurado por canal.

### Sprint 3.2 — Multi-channel routing (2 días)
- Cada canal tiene su propia config: Firebase project (o subcollection), OAuth token, calendario, branding (template thumbnails, voces preferidas).
- Al crear proyecto: dropdown "Canal destino".
- Tags y branding se aplican según canal seleccionado.

**Decision gate Phase 3:** ¿pasa "idea → publicado programado en YouTube" sin tocar YouTube Studio?

---

## Phase 4 — Optimización de costos (Semana 8-9, ~20h)

**Goal:** bajar el costo por video conforme escala el volumen.

### Sprint 4.1 — Galería con embeddings + reuso semántico (5 días)
- Generar embedding CLIP de cada imagen y clip Luma producido.
- Indexar en qdrant (ya está en VPS) con metadatos (proyecto, agente, escena, prompt original, fecha).
- Pipeline check: antes de generar nueva imagen, busca top-3 en gallery con score >0.85.
- UI: muestra candidatos al usuario, opción "reuse vs generate new".
- Restricción: solo reuso cross-canal o con >6 meses entre videos del mismo canal.
- Ahorro proyectado: -20% costo por video tras 50+ videos producidos.

### Sprint 4.2 — Pipeline de traducción (4-5 días)
- Traduce guión con Claude (manteniendo timing aproximado).
- Re-genera narration en idioma destino (ElevenLabs admite 30+ idiomas).
- Re-genera subs Whisper en idioma destino.
- Reusa imágenes y Luma clips (visualmente neutros).
- Crea video destino con costo marginal ~$1.50 (vs $5.76 video original).
- Soporte inicial: ES → EN, PT, FR, DE.

**Decision gate Phase 4:** ¿costo promedio por video bajó al menos 20% comparado contra Phase 2?

---

## Phase 5 — Inteligencia y aprendizaje (Semana 10-12, ~30h)

**Goal:** que el sistema mejore solo con cada video producido.

### Sprint 5.1 — A/B testing de hooks y thumbnails (3-4 días)
- Genera 2 variantes del hook + 2 thumbnails al producir.
- Sube como YouTube split test (feature nativo de Studio).
- Después de 7 días, identifica ganador automáticamente.
- Guarda data en Firestore: variante ganadora + métricas + razón hipotetizada.

### Sprint 5.2 — Analytics dashboard + feedback loop a prompts (8-10 días)
- Pull diario de YouTube Analytics API: CTR, retention curve, AVD, sub conversion por video.
- Dashboard cruza prediction (virality score interno) vs reality (YouTube data).
- Identifica patterns: "videos con cliffhanger en min 11 retienen 8% más", "thumbnails con texto rojo en lugar de blanco tienen +12% CTR".
- Auto-ajuste de pesos del virality scoring engine.
- Auto-ajuste de prompts de agentes según patterns identificados.
- Reporte semanal en email/dashboard: "esta semana aprendiste X, ajustamos Y".

**Decision gate Phase 5:** ¿el sistema te dice 1-3 ajustes específicos que mejoren tu próxima cosecha de videos?

---

## Phase 6 — SaaS multi-tenant (Futuro)

**Cuándo abrir:** cuando tu canal #1 tenga 5K+ subs Y al menos 3 personas te hayan pedido el servicio.

- Aislamiento por tenant (Firebase project compartido con security rules estrictas, o project por tenant).
- Stripe billing (subscripción + usage-based híbrido).
- Onboarding flow para nuevos usuarios.
- Quota management por plan.
- Soporte con Cal.com (ya tienes en VPS).

---

## 📊 Resumen total

| Aspecto | Plan total |
|---|---|
| Duración | 10-12 semanas de trabajo enfocado |
| Inversión de tiempo | 200-240 horas |
| Costo adicional infra | ~$15/mes (Sentry tier opcional) |
| Costo de testing | ~$50-100 total (videos durante development) |
| Resultado | Producto produce 100+ videos/mes en 4 formatos, upload auto a YouTube, mejora con feedback |

---

## ❌ Ideas descartadas y por qué

| Idea | Razón |
|---|---|
| Llegar a 50 agentes | 10 excepcionales > 50 mediocres. Más mantenimiento, peor calidad |
| Catálogo estático 500 ideas | Se queda viejo. Mejor Tavily + Trends en vivo |
| Editor de video en la app | Overkill. Reeditar = DaVinci externo |
| Voces clonadas | Diferenciador menor + problema legal |

---

## ⚠️ Riesgos a monitorear

1. **Sprint que se infla.** Si lleva >2x del estimado: parar, reevaluar approach.
2. **Cambio de estrategia de canales.** Los pipelines siguen sirviendo igual.
3. **ElevenLabs queda corto** al escalar (~22 videos largos en plan actual). Para 26+ → upgrade Pro $99/mo = 500K credits.
4. **YouTube cambia política de AI.** Mantener "altered/synthetic" siempre declarado.

---

## 🎬 Punto de entrada recomendado

**Phase 0 / Sprint 0.1 — Video player.** Ganarás momentum con un win visible en 1 día.

Después: Sprint 0.1 (recomendador + ZIP), 0.2 (Sentry), 0.3 (cola).

Cuando termine Phase 0 (semana 2), ya tienes la base para producir en paralelo y observar lo que pasa. De ahí, las siguientes fases construyen sobre esa base.
