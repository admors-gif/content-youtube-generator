# 🎬 Content Factory — Documentación Completa del Proyecto

> Última actualización: 2026-05-01 21:19 CST
> Conversación origen: `50ee2df7-9826-4abc-ae31-47497b7b38c4`

---

## 1. 🎯 ¿Qué es Content Factory?

Una **fábrica automatizada de documentales/videos para YouTube** que genera contenido completo con un solo clic. El usuario selecciona un "agente" temático (True Crime, Historia, Ciencia, etc.), ingresa un tema, y el sistema produce automáticamente:

1. **Guión cinematográfico** (Anthropic Claude)
2. **Imágenes de escenas** (ComfyUI Flux)
3. **Narración por voz** (ElevenLabs TTS)
4. **Clips cinemáticos con movimiento** (Luma AI Dream Machine)
5. **Efectos Ken Burns** en imágenes estáticas (FFmpeg)
6. **Ensamblado final** del video (FFmpeg)
7. **Subtítulos** word-by-word estilo TikTok (OpenAI Whisper + FFmpeg ASS burn-in) ⚠️ *No funciona aún*

---

## 2. 🏗️ Arquitectura del Sistema

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────────────────┐
│   FRONTEND      │     │   VERCEL     │     │   VPS (Hostinger)           │
│   Next.js 16    │────▶│   Hosting    │     │   Docker Container          │
│   React 19      │     │   + API      │     │   Python 3.11 + FastAPI     │
│   Firebase Auth │     │   Routes     │     │   FFmpeg + libass           │
│   Firestore DB  │     └──────────────┘     │                             │
└─────────────────┘                          │   Scripts:                  │
        │                                    │   - generate_content.py     │
        │ Firestore                          │   - comfyui_client.py       │
        ▼ (real-time)                        │   - elevenlabs_tts.py       │
┌─────────────────┐                          │   - luma_video.py           │
│   FIREBASE      │◀────────────────────────▶│   - download_and_kenburns.py│
│   Auth + DB     │     (status updates)     │   - assemble_video.py       │
│   Firestore     │                          │   - generate_subtitles.py   │
└─────────────────┘                          │   - factory.py (orchestr.)  │
                                             └─────────────────────────────┘
                                                        │
                                             ┌──────────┴──────────┐
                                             │   APIs Externas     │
                                             │   - Anthropic Claude│
                                             │   - OpenAI Whisper  │
                                             │   - ElevenLabs      │
                                             │   - ComfyUI (Flux)  │
                                             │   - Luma AI         │
                                             │   - Tavily (research)│
                                             └─────────────────────┘
```

---

## 3. 📁 Estructura de Archivos

### 3.1 Repositorio Local
```
C:\Users\admor\Downloads\Content You tube Generator\
├── api.py                          # FastAPI server (531 líneas) — corre en VPS
├── Dockerfile                      # Python 3.11-slim + FFmpeg + libass + Montserrat
├── docker-compose.yaml             # Config Docker local (no se usa directo)
├── requirements.txt                # Dependencias Python del backend
├── .env                            # Variables de entorno LOCAL
├── .env.txt                        # Backup de env vars
├── firebase-admin.json             # Credenciales Firebase service account
├── hostinger_env.txt               # Referencia de env vars del VPS
│
├── scripts/                        # Pipeline de producción (corre en VPS)
│   ├── factory.py                  # Orquestador principal (28K)
│   ├── generate_content.py         # Generación de guión + Tavily research (34K)
│   ├── comfyui_client.py           # Cliente ComfyUI para generar imágenes (12K)
│   ├── elevenlabs_tts.py           # Narración con ElevenLabs (12K)
│   ├── luma_video.py               # Clips cinemáticos con Luma AI (12K)
│   ├── download_and_kenburns.py    # Ken Burns effect en imágenes (11K)
│   ├── assemble_video.py           # Ensamblaje FFmpeg del video (7K)
│   ├── generate_subtitles.py       # Whisper → ASS → burn-in (15K)
│   ├── generate_master_audio.py    # Concatenar audios de narración
│   ├── ffmpeg_assembler.py         # Assembler alternativo
│   └── [varios scripts de test/debug]
│
├── web/                            # Frontend Next.js (deployado en Vercel)
│   ├── package.json                # Next.js 16.2.4, React 19.2.4, Firebase 12.12.1
│   ├── .env.local                  # Firebase config + VPS URL
│   ├── app/
│   │   ├── page.js                 # Landing page
│   │   ├── layout.js               # Root layout con metadata
│   │   ├── globals.css             # Design system completo (dark theme)
│   │   ├── login/                  # Firebase Auth (Google login)
│   │   ├── dashboard/
│   │   │   ├── page.js             # Lista de proyectos del usuario
│   │   │   ├── layout.js           # Sidebar layout
│   │   │   ├── new/page.js         # Crear nuevo video (selector de agentes)
│   │   │   └── project/[id]/page.js # ⭐ Página principal del proyecto (540 líneas)
│   │   └── api/
│   │       └── download/
│   │           ├── video/[project]/route.js  # Proxy descarga video (ahora directo)
│   │           └── images/[project]/route.js # Proxy descarga imágenes ZIP
│   ├── lib/
│   │   ├── agents.js               # 27 agentes temáticos con prompts
│   │   └── firebase.js             # Config Firebase client
│   ├── components/                 # Componentes reutilizables
│   └── context/                    # React contexts (auth)
│
├── prompts/                        # Prompts del sistema (legacy)
├── config/                         # Configuraciones adicionales
└── output/                         # Videos generados localmente (si aplica)
```

### 3.2 Repositorio GitHub
```
URL: https://github.com/admors-gif/content-youtube-generator
Branch: master
Total commits: 50
Último commit: 099a25f "fix: download buttons go directly to VPS via Tailscale"
```

### 3.3 VPS (Hostinger)
```
ID VM:           1375702
Hostname:        srv1375702.hstgr.cloud
IP Pública:      187.77.30.158 (puerto 8085 BLOQUEADO por firewall)
IP Tailscale:    100.99.207.113 (DEBE estar activo para que funcione)
OS:              Ubuntu 24.04 with Docker
Plan:            KVM 2 (2 CPU, 8GB RAM, 100GB disco)
Container:       content-factory-v7 (último deploy)
Puerto interno:  8000 (FastAPI/Uvicorn)
Puerto externo:  8085 (mapeado) + 80 (mapeado, último intento)

Volumen persistente: /opt/content-factory/output → /app/output
  └── /app/output/videos/{safe_title}/
      ├── images/           # Imágenes generadas por ComfyUI
      ├── audio/            # narration_001.mp3, narration_002.mp3...
      ├── kenburns/         # Videos con efecto Ken Burns
      ├── luma/             # Clips cinemáticos de Luma AI
      ├── FINAL_*.mp4       # Video ensamblado sin subtítulos
      └── FINAL_SUB_*.mp4   # Video con subtítulos (si Whisper funciona)
```

### 3.4 Vercel (Frontend)
```
URL:         https://content-youtube-generator.vercel.app
Proyecto:    content-youtube-generator
Team:        tomas-flores-projects-90a126f3
Auto-deploy: Sí, desde branch master

Variables de Entorno en Vercel:
  NEXT_PUBLIC_FIREBASE_API_KEY
  NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
  NEXT_PUBLIC_FIREBASE_PROJECT_ID
  NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET
  NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID
  NEXT_PUBLIC_FIREBASE_APP_ID
  NEXT_PUBLIC_N8N_WEBHOOK_URL
  NEXT_PUBLIC_VPS_API_URL  → http://100.99.207.113:8085 (Tailscale)
```

### 3.5 Firebase
```
Proyecto:    content-factory-5cbcb
Auth:        Google Sign-In
Base datos:  Firestore
Colección:   users/{uid}/projects/{projectId}
```

---

## 4. 🔌 APIs y Proveedores

| Proveedor | Uso | Balance (post-prueba) | Costo/video |
|-----------|-----|----------------------|-------------|
| **Anthropic Claude** | Guión + prompts visuales | $14.27 | ~$1.16 |
| **OpenAI (Whisper)** | Subtítulos (word-level) | $14.95 | ~$0.07 (NO corrió) |
| **Luma AI** | Clips cinemáticos (Dream Machine) | $20.83 | ~$1.78 |
| **ElevenLabs** | Narración TTS | 236,106 créditos | ~11,965 cr |
| **ComfyUI (Flux)** | Generación de imágenes | 4,842 créditos | ~210 cr |
| **Tavily** | Investigación web en tiempo real | ~999 créditos | ~1 cr |
| **ImgBB** | Hosting temporal de imágenes | Gratis | $0 |
| **TOTAL** | | | **~$2.94 USD/video** |

### Videos restantes hasta recargar:
- Luma AI: **~11 videos** 🔴 (cuello de botella)
- Anthropic: ~12 videos
- ElevenLabs: ~19 videos
- ComfyUI: ~23 videos

---

## 5. 🛠️ Dependencias y Herramientas

### Backend (VPS Docker Container)
- **Python 3.11** (slim)
- **FFmpeg** con libass (para subtítulos ASS)
- **Fonts Montserrat** (para subtítulos premium)
- Paquetes Python: openai, anthropic, httpx, aiohttp, pydub, fastapi, uvicorn, firebase-admin, lumaai, tavily-python, requests, google-genai, google-cloud-texttospeech

### Frontend
- **Node.js** (requerido para Next.js)
- **Next.js 16.2.4** (App Router)
- **React 19.2.4**
- **Firebase 12.12.1** (Auth + Firestore)
- **Tailwind CSS 4** (dev dependency)
- CSS custom design system (dark theme premium)

### Herramientas de Desarrollo (Local)
- **PowerShell 5.1** (Windows)
- **Git** → GitHub
- **npm** (para correr frontend local: `cd web && npm run dev`)
- **Antigravity** (este asistente AI)

### Infraestructura
- **Vercel** → Hosting frontend (Hobby plan, auto-deploy desde GitHub)
- **Hostinger VPS** → Backend API + pipeline de producción
- **Tailscale** → VPN para conectar tu PC al VPS (⚠️ necesita estar activo)
- **Docker** → Containerización del backend
- **Firebase** → Auth + Firestore database
- **n8n** → Workflow automation (URL: https://n8n.valtyk.com, webhook integrado pero no usado activamente aún)

---

## 6. 📜 Log de Cambios (Historial Completo)

### Commits recientes (del más nuevo al más viejo):
```
099a25f fix: download buttons go directly to VPS via Tailscale (no Vercel proxy)
0aa33dd fix: update fallback VPS IP to 187.77.30.158 in download routes
4f6a5db fix: download uses videoFolder from Firebase + subtitle audio concat fallback
c1c4502 fix: React hooks order - move useEffect/useCallback before conditional returns
eab52d7 feat: Tavily web research engine - scripts now include real-time web data
d634c07 fix: dynamic landing page - agent count and grid now from SYSTEM_AGENTS
1f7b2b8 feat: auto-approve timer (3min) + virality score panel with 5 metrics
78810b1 fix: explicit subtitle generation fallback + HTTPS download proxy
67a966c fix: HTTPS download proxy - solve mixed content blocking
ffa9373 fix: persistent volume + smart retry that skips existing assets
05a4529 feat: add /retry and /reset-status API endpoints
0db2b03 fix: increase FFmpeg timeouts from 600s to 1800s
9cd4111 fix: use env_file for Hostinger env injection
2849ec6 fix: inject env vars and firebase creds via environment
e93d13b feat: add all 27 agents to frontend catalog
0357725 fix: use content-factory-v5 container name
ecdd9f7 fix: move cache bust to top of Dockerfile
117a68c security: remove all tracked credentials
```

---

## 7. 🐛 Bugs Activos (BLOQUEADORES)

### Bug 1: ❌ Descarga de Video No Funciona
**Síntoma:** Al hacer clic en "Descargar Video", no descarga nada o muestra `{"error":"Download failed"}`

**Causa raíz:** El VPS solo es accesible vía **Tailscale** (IP `100.99.207.113:8085`). La IP pública (`187.77.30.158:8085`) tiene el puerto bloqueado por firewall del VPS. Ni Vercel ni el browser pueden llegar al VPS.

**Estado actual:**
- Se intentó proxy vía Vercel → falla porque Vercel no está en la red Tailscale
- Se intentó acceso directo vía Tailscale IP → falla con `ERR_CONNECTION_REFUSED`
- Se intentó abrir puerto 80 → pendiente de verificar

**Diagnóstico pendiente:**
1. ¿Tailscale está activo en el VPS? (verificar con `tailscale status` via SSH)
2. ¿La IP de Tailscale cambió? (verificar en panel de Tailscale)
3. ¿El firewall del VPS permite puerto 80? (el 8085 está bloqueado)

**Posibles soluciones (en orden de prioridad):**
1. **Activar Tailscale en el VPS** y verificar la IP correcta
2. **Abrir puerto 8085** en el firewall de Hostinger (panel → Firewall → agregar regla)
3. **Usar Cloudflare Tunnel** como alternativa a Tailscale
4. **Subir videos a Firebase Storage** después de producir (solución definitiva)

### Bug 2: ⚠️ Subtítulos No Se Generan
**Síntoma:** OpenAI muestra $0.00 de consumo = Whisper nunca se ejecutó

**Causa raíz (probable):**
- El archivo `master_audio.mp3` no existía como archivo único en la carpeta del video
- Los audios están como `narration_001.mp3`, `narration_002.mp3`, etc. en `/audio/`
- El código de subtítulos busca `master_audio.mp3` en la raíz

**Fix aplicado (pendiente de prueba):**
- Se agregó lógica en `api.py` (líneas 457-482) para concatenar narraciones individuales en `master_audio.mp3` antes de llamar a Whisper
- Requiere producir un nuevo video para verificar

---

## 8. 📋 Backlog de Features (Próximo Sprint)

### Prioridad Alta
1. **🔧 Fix descarga de video** — Resolver acceso al VPS (Tailscale/firewall/Storage)
2. **🔧 Fix subtítulos** — Verificar que el fix de concat audio funciona

### Prioridad Media
3. **🧠 Feedback Loop de Viralidad** — Guardar scores en Firestore para que el agente aprenda de sus propios resultados y ajuste prompts automáticamente
4. **🗑️ Eliminar tab "Audio TTS"** — Obsoleta, no se usa en el pipeline actual

### Prioridad Baja
5. **🔔 Notificaciones in-page** — Reemplazar `alert()` por notificaciones UI (evita problemas con bloqueadores de popups)
6. **☁️ Firebase Storage** — Subir videos completados a Storage para descarga confiable (elimina dependencia de Tailscale)
7. **📊 Dashboard de costos** — Panel con consumo de APIs en tiempo real

---

## 9. 🔑 Flujo de Producción (Pipeline Paso a Paso)

```
1. Usuario selecciona agente + escribe tema
2. Frontend crea doc en Firestore (status: "draft")
3. Timer de 3 min (auto-aprobación) o usuario edita y aprueba guión
4. Frontend envía POST al VPS: /produce {projectId}
5. VPS lee proyecto de Firestore
6. 🔍 Tavily investiga el tema (web research)
7. 📝 Anthropic genera guión cinematográfico (~2000 palabras)
8. 🎨 ComfyUI genera ~10-12 imágenes (Flux model)
9. 🎙️ ElevenLabs genera narración por escena
10. 🎬 Luma AI genera clips cinemáticos (~5 clips)
11. 🖼️ FFmpeg aplica Ken Burns a imágenes estáticas
12. 🎞️ FFmpeg ensambla video final con audio
13. 📝 Whisper transcribe → ASS subtítulos → burn-in (⚠️ no funciona aún)
14. 🏆 VPS actualiza Firestore: status="completed", videoPath, videoFolder
15. Frontend muestra botón de descarga
```

**Tiempo estimado de producción:** ~45-60 minutos por video

---

## 10. 🔐 Variables de Entorno Críticas

### VPS (.env en Docker)
```env
OPENAI_API_KEY=sk-proj-...        # Para Whisper (subtítulos)
OPENAI_MODEL=gpt-5.5              # Modelo OpenAI (no usado directo)
ANTHROPIC_API_KEY=sk-ant-api03-...# Para generar guiones
ELEVENLABS_API_KEY=sk_cd1d...     # Para narración TTS
COMFYUI_API_KEY=comfyui-23c0...   # Para generar imágenes
LUMA_API_KEY=luma-d71950...       # Para clips cinemáticos
IMGBB_API_KEY=5a9bbea...          # Para hosting temporal imágenes
TAVILY_API_KEY=tvly-dev-3gG...    # Para investigación web
FIREBASE_CREDENTIALS=ewog...      # Base64 del service account JSON
```

### Frontend (.env.local)
```env
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSyCJL17...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=content-factory-5cbcb.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=content-factory-5cbcb
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=content-factory-5cbcb.firebasestorage.app
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=903561262290
NEXT_PUBLIC_FIREBASE_APP_ID=1:903561262290:web:35dd8d54c3bbd26529690b
NEXT_PUBLIC_N8N_WEBHOOK_URL=https://n8n.valtyk.com/webhook/content-factory-trigger
NEXT_PUBLIC_VPS_API_URL=http://100.99.207.113:8085  # ⚠️ Tailscale IP
```

---

## 11. 🔧 Comandos Útiles

### Desarrollo Local (Frontend)
```powershell
cd "C:\Users\admor\Downloads\Content You tube Generator\web"
npm run dev
# Abre http://localhost:3000
```

### Git
```powershell
cd "C:\Users\admor\Downloads\Content You tube Generator"
git add -A
git commit -m "mensaje"
git push origin master
# Vercel auto-deploy en ~2 min
```

### Deploy VPS (via Hostinger MCP)
```
# Se usa la herramienta mcp_hostinger_VPS_createNewProjectV1
# VM ID: 1375702
# Project name: content-factory
# Cambiar CACHE_BUST para forzar rebuild
```

### Ver Logs VPS
```
# Herramienta: mcp_hostinger_VPS_getProjectLogsV1
# VM ID: 1375702, Project: content-factory
```

---

## 12. 🎥 Prueba Completada: "El caso del Zodiac Killer"

**Video producido exitosamente el 1 de mayo 2026**
- Agente: True Crime
- Guión: 1,979 palabras, 13.2 minutos estimados
- Imágenes: 12 escenas generadas
- Score de Viralidad: 62/100
  - Hook: 55 (bajo) ⚠️
  - Emoción: 48 (bajo) ⚠️
  - Ritmo: 70
  - Retención: 68
  - CTA: 65
- Producción tomó aprox. 45-50 minutos
- Video generado pero **NO se puede descargar** (bug activo)
- **Sin subtítulos** (Whisper no corrió)

---

## 13. ⚡ Para Retomar Mañana

### Paso 1: Resolver acceso al VPS
1. Verificar si Tailscale está activo en el VPS (SSH al VPS vía Hostinger panel)
2. Si Tailscale no está activo, activarlo y obtener la IP actualizada
3. Alternativa: abrir puerto 8085 en firewall de Hostinger

### Paso 2: Probar descarga
1. Actualizar `NEXT_PUBLIC_VPS_API_URL` en Vercel con la IP correcta
2. Hacer Ctrl+Shift+R en la página del proyecto
3. Clic en "Descargar Video"

### Paso 3: Producir nuevo video para verificar subtítulos
1. Crear un video corto (tema simple)
2. Verificar que Whisper se ejecuta ($0+ en OpenAI = éxito)
3. Confirmar que `master_audio.mp3` se crea por concatenación

### Paso 4: Features pendientes
1. Eliminar tab "Audio TTS"
2. Diseñar sistema de feedback loop de viralidad
3. Implementar subida a Firebase Storage (elimina dependencia de Tailscale)
