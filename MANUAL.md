# 📘 Content Factory — Manual del Proyecto

> **Documento vivo.** Se actualiza cada vez que pasa algo significativo en el proyecto. Sirve como blueprint reproducible y referencia técnica completa. Si alguien (incluido tú en 6 meses) quiere reproducir el proyecto desde cero, este documento debe tener todo lo necesario.

**Última actualización:** 2026-05-01
**Versión del manual:** 0.1 (en construcción durante la migración a deploy via GitHub Actions)
**Repo:** `https://github.com/admors-gif/content-youtube-generator`
**Tag de rollback:** `pre-migration-2026-05-01` (commit `099a25f`)

---

## Tabla de contenidos

1. [Qué es Content Factory](#1-qué-es-content-factory)
2. [Stack completo](#2-stack-completo)
3. [Arquitectura](#3-arquitectura)
4. [APIs y proveedores externos](#4-apis-y-proveedores-externos)
5. [Variables de entorno](#5-variables-de-entorno)
6. [Estructura de archivos](#6-estructura-de-archivos)
7. [Cómo se construyó (cronología)](#7-cómo-se-construyó-cronología)
8. [Cómo deployar](#8-cómo-deployar)
9. [Cómo reproducir desde cero](#9-cómo-reproducir-desde-cero)
10. [Bugs conocidos](#10-bugs-conocidos)
11. [Backlog técnico (mejoras pendientes)](#11-backlog-técnico-mejoras-pendientes)
12. [Troubleshooting común](#12-troubleshooting-común)
13. [Glosario](#13-glosario)

---

## 1. Qué es Content Factory

**Lenguaje plano:** Una fábrica automatizada de videos largos para YouTube. Tú eliges un "agente" (True Crime, Historia, Ciencia, Estoicismo, etc., 27 disponibles), escribes un tema, y el sistema produce un video documental de 12-15 minutos, completamente listo para subir a YouTube, en aproximadamente 45-60 minutos, con un costo de ~$2.94 USD por video.

**Lo que produce:**
- Guión cinematográfico de ~2,000 palabras (Anthropic Claude)
- 10-12 imágenes de escenas (ComfyUI con Flux)
- Narración por voz humana realista (ElevenLabs)
- 5-8 clips cinemáticos con movimiento (Luma AI Dream Machine)
- Efecto Ken Burns para imágenes estáticas (FFmpeg)
- Subtítulos word-by-word estilo TikTok (OpenAI Whisper + FFmpeg ASS burn-in)
- Video final ensamblado (FFmpeg)
- Score de viralidad con 5 métricas (Hook, Emoción, Ritmo, Retención, CTA)

**Investigación previa:** antes de generar el guión, Tavily hace búsqueda web en tiempo real sobre el tema, así el contenido tiene datos reales, no solo texto que el LLM "imagina".

---

## 2. Stack completo

### Frontend (web/)
- **Framework:** Next.js 16.2.4 con App Router
- **UI:** React 19.2.4
- **Auth + DB:** Firebase 12.12.1 (Google Sign-In + Firestore real-time)
- **Estilos:** CSS custom con design system dark theme + Tailwind CSS 4 (devDep)
- **Build/lint:** ESLint 9, babel-plugin-react-compiler 1.0.0
- **Hosting:** Vercel (Hobby plan, auto-deploy desde branch master)

### Backend (raíz del repo)
- **Runtime:** Python 3.11 (en imagen Docker `python:3.11-slim`)
- **Framework HTTP:** FastAPI + Uvicorn
- **Procesamiento media:** FFmpeg (con libass para subtítulos ASS)
- **Fonts:** Montserrat (instalado en Dockerfile vía `fonts-montserrat`)
- **Cliente Firebase:** firebase-admin
- **Hosting:** Hostinger VPS (Ubuntu 24.04, Docker)

### Infraestructura compartida
- **VPN privada:** Tailscale (acceso seguro al VPS sin exponer puertos públicos)
- **DNS:** Namecheap (dominio `valtyk.com`)
- **Reverse proxy + HTTPS:** nginx-proxy-manager (en el VPS, gestiona Let's Encrypt automáticamente)
- **Almacenamiento de videos finales:** Firebase Storage (planificado, ver Backlog)
- **Workflows:** n8n self-hosted (en el VPS, integrado pero aún no usado activamente)
- **CI/CD:** GitHub Actions (planificado, ver Sección 8)

---

## 3. Arquitectura

```
┌─────────────────┐
│   USUARIO       │
│   (browser)     │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐         ┌──────────────────────┐
│   FRONTEND      │ ◀──────▶│   FIREBASE           │
│   Next.js       │ Auth +  │   - Auth (Google)    │
│   Vercel        │ DB R/W  │   - Firestore        │
│                 │ realtime│   - Storage (video)  │
└────────┬────────┘         └──────────────────────┘
         │ HTTPS POST /produce
         ▼
┌─────────────────────────────────────────────────────┐
│   VPS Hostinger (srv1375702)                        │
│   IP pública: 187.77.30.158                         │
│   IP Tailscale: 100.99.207.113                      │
│                                                     │
│  ┌──────────────────────────┐                       │
│  │  nginx-proxy-manager     │ ← puerto 80/443       │
│  │  (HTTPS Let's Encrypt)   │   api.valtyk.com →    │
│  └────────────┬─────────────┘   redirige a:         │
│               │                                     │
│  ┌────────────▼─────────────┐                       │
│  │  content-factory         │ ← puerto 8000 (interno)│
│  │  Python 3.11 + FastAPI   │                       │
│  │  + FFmpeg + Whisper      │                       │
│  └──────────────────────────┘                       │
│                                                     │
│  Otros contenedores en el mismo VPS:                │
│  - n8n (puerto 5678)                                │
│  - qdrant (vector DB, 6333)                         │
│  - calcom (3005)                                    │
│  - postgres (5432, interna)                         │
│  - redis (6379, interna)                            │
│  - notion-mcp (4000 sólo Tailscale)                 │
│  - openclaw (44549, panel Hostinger)                │
└─────────────────────────────────────────────────────┘
         │
         │ HTTPS calls a APIs externas
         ▼
┌────────────────────────────────────────────────────┐
│   APIs Externas                                    │
│   - Anthropic Claude (guión)                       │
│   - OpenAI Whisper (subtítulos)                    │
│   - ElevenLabs (TTS)                               │
│   - ComfyUI Flux (imágenes)                        │
│   - Luma AI Dream Machine (video clips)            │
│   - Tavily (web research)                          │
│   - ImgBB (hosting temporal de imágenes)           │
└────────────────────────────────────────────────────┘
```

### Flujo de producción de un video (15 pasos)

1. Usuario abre el frontend, hace login con Google.
2. Usuario va a "Nuevo video" → elige agente → escribe tema.
3. Frontend crea documento en Firestore con `status: "draft"`.
4. Timer de 3 min para auto-aprobación, o usuario edita y aprueba el guión.
5. Frontend hace `POST https://api.valtyk.com/produce` con `{projectId}`.
6. Backend lee proyecto de Firestore.
7. **Tavily** investiga el tema → datos web reales.
8. **Anthropic Claude** genera guión cinematográfico (~2,000 palabras).
9. **ComfyUI Flux** genera 10-12 imágenes (una por escena).
10. **ElevenLabs** genera narración por escena (mp3).
11. **Luma AI** genera 5-8 clips cinemáticos (mp4 con movimiento de cámara).
12. **FFmpeg** aplica efecto Ken Burns a las imágenes estáticas.
13. **FFmpeg** ensambla el video final con audio sincronizado.
14. **OpenAI Whisper** transcribe → genera ASS → FFmpeg quema subtítulos word-by-word.
15. Backend sube `.mp4` a Firebase Storage → genera URL firmada → actualiza Firestore con `status: "completed"`, `videoUrl`, `videoFolder`.

Frontend escucha el cambio (real-time Firestore) y muestra el botón de descarga apuntando a la URL firmada de Firebase Storage.

---

## 4. APIs y proveedores externos

| Proveedor | Uso | Costo aprox/video | Endpoint |
|---|---|---|---|
| **Anthropic Claude** | Guión + prompts visuales | $1.16 | `api.anthropic.com` |
| **OpenAI** | Whisper (subtítulos) | $0.07 | `api.openai.com` |
| **Luma AI** | Clips cinemáticos | $1.78 | `api.lumalabs.ai` |
| **ElevenLabs** | Narración TTS | ~11,965 créditos (~$0.30) | `api.elevenlabs.io` |
| **ComfyUI Flux** | Imágenes generadas | ~210 créditos (~$0.20) | (servicio API privado) |
| **Tavily** | Búsqueda web | ~1 crédito (~$0.001) | `api.tavily.com` |
| **ImgBB** | Hosting temporal de imágenes | Gratis | `api.imgbb.com` |
| **TOTAL** | | **~$2.94 USD/video** | |

### Cuello de botella económico
**Luma AI** es la más cara. Si quisieras bajar costo a ~$1.50/video:
- Reducir clips Luma de 8 a 4
- Compensar con más imágenes Ken Burns
- O migrar parcialmente a Runway / Pika con fallback

---

## 5. Variables de entorno

### Backend (`.env` en VPS, montado en el contenedor)

```env
OPENAI_API_KEY=sk-proj-...        # Whisper para subtítulos
OPENAI_MODEL=gpt-5.5              # No usado directamente
ANTHROPIC_API_KEY=sk-ant-api03-... # Generación de guiones
ELEVENLABS_API_KEY=sk_...          # Narración TTS
COMFYUI_API_KEY=comfyui-...        # Generación de imágenes
LUMA_API_KEY=luma-...              # Clips cinemáticos
IMGBB_API_KEY=...                  # Hosting temporal de imágenes
TAVILY_API_KEY=tvly-dev-...        # Investigación web
FIREBASE_CREDENTIALS=ewog...       # Service account JSON (base64 o raw)
```

### Frontend (`web/.env.local`)

```env
NEXT_PUBLIC_FIREBASE_API_KEY=AIza...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=content-factory-5cbcb.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=content-factory-5cbcb
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=content-factory-5cbcb.firebasestorage.app
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=903561262290
NEXT_PUBLIC_FIREBASE_APP_ID=1:903561262290:web:...
NEXT_PUBLIC_N8N_WEBHOOK_URL=https://n8n.valtyk.com/webhook/content-factory-trigger
NEXT_PUBLIC_VPS_API_URL=https://api.valtyk.com   # ← migrado a HTTPS via NPM
```

### GitHub repo secrets (para Actions)
Configurados en `Settings → Secrets and variables → Actions`:
- `VPS_SSH_KEY` — llave privada SSH del usuario `deploy` del VPS
- `VPS_HOST` — `187.77.30.158`
- `VPS_USER` — `deploy` (no root, por seguridad)

---

## 6. Estructura de archivos

```
C:\Users\admor\Downloads\Content You tube Generator\
├── api.py                        # FastAPI server (corre en VPS)
├── Dockerfile                    # Definición de la imagen Docker
├── docker-compose.yml            # Orquestación del contenedor
├── requirements.txt              # Deps Python del backend
├── .env                          # ⚠️ Credenciales locales (gitignored)
├── .gitignore
├── MANUAL.md                     # ESTE DOCUMENTO
├── README.md
│
├── scripts/                      # Pipeline de producción
│   ├── factory.py                # Orquestador principal
│   ├── generate_content.py       # Guión + Tavily research
│   ├── comfyui_client.py         # Cliente ComfyUI (imágenes)
│   ├── elevenlabs_tts.py         # Narración TTS
│   ├── luma_video.py             # Clips cinemáticos
│   ├── download_and_kenburns.py  # Ken Burns en imágenes
│   ├── assemble_video.py         # Ensamblaje FFmpeg
│   ├── generate_subtitles.py     # Whisper + ASS + burn-in
│   └── generate_master_audio.py  # Concatenar narraciones
│
├── web/                          # Frontend Next.js (deployado en Vercel)
│   ├── package.json
│   ├── .env.local                # ⚠️ Config Firebase + VPS URL (gitignored)
│   ├── app/
│   │   ├── page.js               # Landing
│   │   ├── login/                # Firebase Auth
│   │   ├── dashboard/
│   │   │   ├── page.js           # Lista de proyectos
│   │   │   ├── new/page.js       # Crear video
│   │   │   └── project/[id]/page.js  # Página principal del proyecto
│   │   └── api/
│   │       └── download/
│   │           ├── video/[project]/route.js
│   │           └── images/[project]/route.js
│   ├── lib/
│   │   ├── agents.js             # 27 agentes con sus prompts
│   │   └── firebase.js           # Config Firebase client
│   ├── components/
│   └── context/
│
├── prompts/                      # Prompts del sistema (legacy)
├── config/
└── output/                       # Videos generados localmente (vacío en práctica)
```

---

## 7. Cómo se construyó (cronología)

> Esta sección crece con cada hito significativo del proyecto.

### Fase 1 — Génesis (abril 2026)
- Idea inicial: generador de videos para YouTube con IA, automatizado end-to-end.
- Construido con asistente IA **Antigravity** (editor con MCP de Hostinger).
- Antigravity integró 6 APIs, escribió el pipeline Python, el frontend Next.js, deployó la primera versión al VPS.

### Fase 2 — Iteración de features (abril-mayo 2026)
- Agregado: 27 agentes temáticos (True Crime, Historia, Estoicismo, etc.).
- Agregado: Tavily para web research previo al guión.
- Agregado: scoring de viralidad con 5 métricas.
- Agregado: timer de auto-aprobación de 3 min para guión.
- Agregado: subtítulos word-by-word con Whisper + ASS.
- Agregado: efecto Ken Burns para imágenes estáticas.
- Producido exitosamente: video "El estoicismo aplicado al trabajo moderno" (167MB, 22:17 del 30/abr).
- Producido exitosamente: video "El caso del Zodiac Killer" (171MB, 1:52am del 1/may).

### Fase 3 — Bugs visibles (mayo 2026)
- Bug 1: descarga de video desde frontend no funciona (mixed content + Vercel no alcanza VPS).
- Bug 2: subtítulos no se generan (Whisper nunca corre, $0 consumo OpenAI).

### Fase 4 — Migración de arquitectura (en curso, 2026-05-01)
- Detectado: contenedor `v7` en estado `Created` por conflicto de puerto 80 con nginx-proxy-manager.
- Detectado: deploy via Antigravity → MCP Hostinger desincroniza el repo de git de la realidad del VPS.
- Decisión: migrar deploy a `git push` → GitHub Actions → SSH al VPS.
- Decisión: enrutar API por nginx-proxy-manager con HTTPS Let's Encrypt en `api.valtyk.com`.
- Decisión: migrar entrega de videos a Firebase Storage para descargas confiables sin VPS.
- Respaldo completo creado: `C:\Users\admor\Backups\content-factory-2026-05-01\`.

---

## 8. Cómo deployar

### Frontend → Vercel (automático)
Cualquier push a `master` en GitHub dispara auto-deploy de Vercel del directorio `web/`.

```bash
cd "C:/Users/admor/Downloads/Content You tube Generator"
git add web/
git commit -m "feat: cambio en frontend"
git push origin master
# Vercel detecta el push y deploya en ~2 minutos
```

### Backend → VPS (futuro: GitHub Actions)
Una vez configurado GitHub Actions (Paso 9 de la migración), funcionará así:

```bash
git add api.py scripts/ Dockerfile docker-compose.yml
git commit -m "fix: ajuste backend"
git push origin master
# GitHub Actions detecta el push, construye imagen, hace SSH al VPS,
# pull + docker compose up -d, verifica health endpoint, hace rollback si falla.
```

Mientras tanto (deploy manual via SSH):

```bash
# Subir cambios al VPS
scp -r api.py scripts/ Dockerfile docker-compose.yml root@100.99.207.113:/docker/content-factory/

# SSH y rebuild
ssh root@100.99.207.113 "cd /docker/content-factory && docker compose up -d --build"
```

---

## 9. Cómo reproducir desde cero

> Si tuvieras que reconstruir todo el proyecto desde cero en una máquina nueva, estos son los pasos.

> 🚧 Esta sección se completará al final de la migración con todos los pasos verificados.

Pasos generales:

1. **Cuentas externas**: crear cuentas en Anthropic, OpenAI, Luma, ElevenLabs, ComfyUI, Tavily, ImgBB, Firebase, Vercel, Hostinger, Namecheap, Tailscale.
2. **Domain**: comprar dominio en Namecheap.
3. **VPS**: contratar Hostinger VPS Ubuntu 24.04 con Docker.
4. **Firebase project**: crear proyecto, habilitar Google Sign-In, Firestore, Storage.
5. **Local tools**: instalar Node, Git, GitHub CLI, Firebase CLI, Tailscale.
6. **Repo**: `git clone` el repo.
7. **Env vars**: configurar `.env` (backend) y `web/.env.local` (frontend).
8. **VPS setup**: Tailscale, nginx-proxy-manager, Docker, deploy de containers.
9. **DNS**: apuntar `api.tudominio.com` (A record) al VPS.
10. **Vercel**: conectar repo, configurar env vars de frontend, primer deploy.
11. **GitHub Actions**: configurar secrets, primer deploy automático.
12. **Test end-to-end**: producir un video corto.

---

## 10. Bugs conocidos

> Lista de bugs activos. Se actualizan conforme se resuelven.

### 🔴 Bug 1 — Descarga de video falla
**Estado:** En proceso de fix (Pasos 5, 6, 8 de migración actual)
**Causa raíz:** Frontend HTTPS intenta llamar a backend HTTP, browser bloquea por mixed content. Adicionalmente, Vercel no puede alcanzar VPS si está detrás de Tailscale.
**Fix planeado:** API expuesta por `https://api.valtyk.com` (NPM + Let's Encrypt) + entrega final del video por URL firmada de Firebase Storage.

### 🔴 Bug 2 — Subtítulos no se generan
**Estado:** Fix aplicado en `api.py:457-482` (fallback) pero no probado en producción.
**Causa raíz:** El paso original en `factory.py` falla silenciosamente. El fallback en `api.py` concatena las narraciones individuales en `master_audio.mp3` antes de Whisper, pero no valida que el concat haya tenido éxito.
**Fix planeado:** Endurecer validación en Paso 7 — verificar `result.returncode == 0` y `master_audio.exists()` y `size > 0` antes de llamar a Whisper.

### 🟡 Bug 3 — `factory.py` no genera subtítulos en el flujo principal
**Estado:** Pendiente investigación.
**Por qué:** El fix en `api.py` es un fallback. El problema raíz está en `factory.py` y no se ha investigado.

---

## 11. Backlog técnico (mejoras pendientes)

> Observaciones del code review del 2026-05-01. Cada item es una mejora que el sistema necesita para llegar a calidad de producción seria. Ordenado por prioridad recomendada.

### Prioridad alta — Estabilidad y operación

#### 11.1 Sistema de cola persistente (queue + workers)
**Por qué:** Hoy un video tarda 45-60 min como request HTTP síncrona. Si el contenedor reinicia, pierdes el video y los $1.50 USD ya gastados.
**Solución:** Migrar a Celery/Bull/Temporal. El video se vuelve un job persistente, recuperable, reintentable. Workers separados procesan jobs.
**Esfuerzo:** ~2 días.

#### 11.2 Observabilidad (errores + métricas + logs)
**Por qué:** Cuando subtítulos fallaron silenciosamente, no nos enteramos hasta que el video ya estaba "terminado" sin subs. Solo descubrimos el bug del puerto 80 mirando logs manualmente vía SSH.
**Solución:**
- **Sentry** para errores con stack trace (free tier hasta 5K eventos/mes)
- **Métricas básicas**: tiempo y éxito de cada paso del pipeline, costo real por video
- **Logs estructurados** a Logtail / BetterStack / Datadog (free tiers disponibles)
**Esfuerzo:** ~1 día.

#### 11.3 Tests automatizados
**Por qué:** Pipeline con 6 APIs y 15 pasos. Cualquier cambio fuerza producir un video real (45 min, $3) para verificar.
**Solución:**
- Unit tests de funciones puras (parsers, builders de prompts)
- Integration test mockeando las 6 APIs (rápido, deterministico)
- Smoke test semanal de pipeline real con video corto (~5 min, ~$0.50)
**Esfuerzo:** ~3 días.

### Prioridad media — Producto y costos

#### 11.4 Migrar Whisper a modelo más nuevo
**Por qué:** Hoy se usa `whisper-1` (modelo de 2023). OpenAI lanzó `gpt-4o-mini-transcribe` y `gpt-4o-transcribe` con mucho mejor precisión multilingüe y manejo de ruido. Costo similar.
**Solución:** Cambio de 1 línea en `scripts/generate_subtitles.py:79` — `model="whisper-1"` → `model="gpt-4o-mini-transcribe"`.
**Esfuerzo:** 5 min + verificación con un video.

#### 11.5 Aprobación humana después de imágenes
**Por qué:** ComfyUI a veces genera imágenes con anatomía rota, texto basura, elementos irrelevantes. Hoy entran directo a Luma (~$1.78) sin que tú las veas.
**Solución:** Checkpoint en el frontend después del paso 9 del pipeline → "aprueba o regenera estas imágenes" → continuar a Luma.
**Esfuerzo:** ~1 día.

#### 11.6 Cambiar auto-aprobación de guión
**Por qué:** Si te paras del computador, el sistema produce un video de $2.94 sin que lo hayas leído.
**Solución:** Aprobación explícita siempre (un click), o timer de 30 min con notificación push (no 3 min).
**Esfuerzo:** ~2 horas.

#### 11.7 Moderación de contenido
**Por qué:** True Crime + IA puede generar contenido sensible (violencia gráfica, especulación sobre víctimas reales) que viola políticas de YouTube. Sin check, eventual desmonetización o problemas legales.
**Solución:** Llamar a OpenAI Moderation API (gratis) sobre el guión antes de producir. Bloquear o flagear si triggers sensitive_content.
**Esfuerzo:** ~3 horas.

### Prioridad baja — Escalabilidad y robustez

#### 11.8 Fallbacks para APIs críticas
**Por qué:** Hoy si Luma cae, el pipeline se detiene. Igual con ComfyUI.
**Solución:** Adaptadores con fallback automático:
- Video: Luma → Runway → Pika
- Imágenes: ComfyUI → Replicate → fal.ai
**Esfuerzo:** ~2 días.

#### 11.9 Multi-tenancy
**Por qué:** Hoy diseñado como app personal. Para venderlo como SaaS necesita aislamiento entre tenants, billing, terms of service.
**Solución:** Refactor mayor — agregar `tenantId` a todos los datos, billing con Stripe, queue por tenant, cuotas.
**Esfuerzo:** ~2 semanas.

#### 11.10 Eliminar tab "Audio TTS" del frontend
**Por qué:** Obsoleta, no se usa en pipeline actual.
**Esfuerzo:** 15 min.

---

## 12. Troubleshooting común

> Esta sección se completa con problemas reales que aparezcan durante operación.

### "El contenedor no arranca tras un deploy"
1. Ver estado: `ssh root@100.99.207.113 "docker ps -a --filter name=content-factory"`
2. Ver logs: `ssh root@100.99.207.113 "docker logs content-factory --tail 50"`
3. Si dice "Bind for ... port is already allocated": revisar `docker-compose.yml`, no debe mapear puerto 80 (lo usa nginx-proxy-manager) ni 443 ni puertos de otros contenedores (5678 n8n, 6333 qdrant, 3005 calcom).

### "El API responde pero los videos no se producen"
1. Ver logs en vivo: `ssh root@100.99.207.113 "docker logs content-factory -f"`
2. Verificar saldo de APIs: Anthropic, OpenAI, Luma, ElevenLabs (cuello de botella usual: Luma).
3. Verificar Firestore: que los proyectos se creen con `status: "draft"`.

### "El frontend no descarga el video"
1. Verificar `NEXT_PUBLIC_VPS_API_URL` en Vercel apunte a `https://api.valtyk.com` (no IP).
2. Verificar que `api.valtyk.com` resuelva: `nslookup api.valtyk.com`.
3. Verificar que NPM tenga el proxy host configurado y SSL activo.
4. Verificar Firebase Storage rules permiten lectura de URLs firmadas.

---

## 13. Glosario

| Término | Significado |
|---|---|
| **Agente** | Personaje temático (True Crime, Historia...) con prompts especializados que define el tono del video. |
| **Antigravity** | Editor IDE con IA integrada (similar a Cursor) que se usó para construir el proyecto inicialmente. |
| **CNAME** | Tipo de registro DNS — apunta un nombre a otro nombre. Ej: `cname.vercel.com`. |
| **A record** | Tipo de registro DNS — apunta un nombre a una IP. Ej: `187.77.30.158`. |
| **Docker container** | Proceso aislado corriendo una imagen Docker. |
| **Docker image** | "Snapshot" empaquetado de un sistema con todo su código y dependencias. |
| **FFmpeg** | Herramienta de línea de comandos para procesar audio y video. |
| **Firestore** | Base de datos NoSQL en tiempo real de Firebase. |
| **GitHub Actions** | Sistema de automatización gratuito de GitHub para correr scripts en respuesta a eventos del repo. |
| **Ken Burns effect** | Pan + zoom lento sobre una imagen estática para darle dinamismo. |
| **Let's Encrypt** | Autoridad certificadora gratuita que emite certificados SSL/TLS. |
| **MCP** | Model Context Protocol — estándar para que IAs accedan a herramientas externas. |
| **nginx-proxy-manager (NPM)** | Reverse proxy con UI web que enruta dominios a contenedores y gestiona Let's Encrypt. |
| **SCP** | Secure Copy — copiar archivos vía SSH. |
| **SSH** | Secure Shell — protocolo para acceso remoto seguro a servidores. |
| **SSH key** | Par de llaves (privada + pública) para autenticación sin contraseña. |
| **Tailscale** | VPN privada para conectar tus dispositivos en una red segura. |
| **Vercel** | Plataforma de hosting para frontend, especializada en Next.js. |
| **VPS** | Virtual Private Server — servidor virtual contratado a un proveedor (Hostinger en este caso). |
| **Whisper** | Modelo de OpenAI para transcripción de audio a texto. |

---

*Manual creado y mantenido durante la sesión de migración del 2026-05-01.*
