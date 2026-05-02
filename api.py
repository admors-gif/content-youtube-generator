from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
import sys
import json
import logging
from datetime import timedelta, datetime, timezone
from pathlib import Path

FIREBASE_STORAGE_BUCKET = os.environ.get(
    "FIREBASE_STORAGE_BUCKET",
    "content-factory-5cbcb.firebasestorage.app",
)

# ── Observabilidad ────────────────────────────────────────────────────────────
# 1) Sentry: captura errores no-handleados con stack trace.
#    Se activa solo si SENTRY_DSN está en .env, así dev local no envía nada.
SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            traces_sample_rate=0.1,    # 10% de requests trackean performance
            profiles_sample_rate=0.0,   # Profiling desactivado (caro)
            environment=os.environ.get("ENV", "production"),
            release=os.environ.get("GIT_SHA", "unknown"),
            send_default_pii=False,     # No enviar IPs ni headers sensibles
        )
        print(f"Sentry initialized (env={os.environ.get('ENV','production')})", flush=True)
    except Exception as e:
        print(f"Sentry init failed: {e}", flush=True)

# 2) structlog: logs estructurados (JSON en prod, pretty en dev).
#    Reemplaza print() con logger.info(event, **kwargs).
try:
    import structlog
    _is_tty = sys.stderr.isatty()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            (structlog.dev.ConsoleRenderer(colors=True) if _is_tty
             else structlog.processors.JSONRenderer()),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
    log = structlog.get_logger("content-factory")
    log.info("logger_initialized", env=os.environ.get("ENV", "production"))
except Exception as _log_err:
    # Fallback a logging stdlib si structlog no está
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("content-factory")
    log.warning(f"structlog init failed, using stdlib logging: {_log_err}")

# ── Escribir firebase-admin.json desde variable de entorno (si existe) ──
firebase_creds = os.environ.get("FIREBASE_CREDENTIALS", "")
if firebase_creds:
    cred_path = "/app/firebase-admin.json"
    try:
        import base64
        try:
            decoded = base64.b64decode(firebase_creds).decode("utf-8")
            json.loads(decoded)
            firebase_creds = decoded
        except Exception:
            pass  # Ya es JSON raw

        # Normalización defensiva: des-escapar \\n en private_key si viene
        # doble-escapado (problema común con creds pegados desde JSON anidado).
        try:
            data = json.loads(firebase_creds)
            pk = data.get("private_key", "")
            if "\\n" in pk and "BEGIN" in pk:
                data["private_key"] = pk.replace("\\n", "\n")
                firebase_creds = json.dumps(data)
                print("Firebase credentials: private_key un-escaped \\n", flush=True)
        except Exception as norm_err:
            print(f"Firebase credentials: could not normalize: {norm_err}", flush=True)

        with open(cred_path, "w") as f:
            f.write(firebase_creds)
        print(f"Firebase credentials written to {cred_path}", flush=True)
    except Exception as e:
        print(f"Could not write Firebase credentials: {e}", flush=True)

app = FastAPI(title="Content Factory API")

# CORS para que el frontend pueda cargar imágenes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ensure_firebase_initialized():
    """Inicializa firebase_admin con storageBucket si no está activo. Idempotente."""
    import firebase_admin
    from firebase_admin import credentials
    try:
        firebase_admin.get_app()
    except ValueError:
        cred_path = "/app/firebase-admin.json"
        if not os.path.exists(cred_path):
            raise RuntimeError("firebase-admin.json no encontrado")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_STORAGE_BUCKET})


def _upload_video_to_storage(local_path: Path, project_id: str) -> dict | None:
    """
    Sube un .mp4 a Firebase Storage en 'videos/{project_id}/{filename}'.

    Retorna {"gs_path": "gs://bucket/videos/...", "signed_url": "https://..."}
    o None si falla. La signed URL dura 7 días (máximo permitido por v4 signing).
    """
    try:
        _ensure_firebase_initialized()
        from firebase_admin import storage
        # Pasar bucket name explícito: si firebase_admin fue inicializado en otra
        # parte del código sin storageBucket, storage.bucket() sin argumento falla
        bucket = storage.bucket(FIREBASE_STORAGE_BUCKET)
        blob_name = f"videos/{project_id}/{local_path.name}"
        blob = bucket.blob(blob_name)
        size_mb = local_path.stat().st_size / (1024 * 1024)
        print(f"   ☁️ Subiendo a Storage: {blob_name} ({size_mb:.1f} MB)")
        blob.upload_from_filename(str(local_path), content_type="video/mp4")
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(days=7),
            method="GET",
        )
        print(f"   ✅ Storage upload OK ({size_mb:.1f} MB)")
        return {
            "gs_path": f"gs://{bucket.name}/{blob_name}",
            "signed_url": signed_url,
        }
    except Exception as e:
        print(f"   ❌ Storage upload failed: {e}")
        return None


def _build_master_audio(video_dir: Path) -> Path | None:
    """
    Concatena narration_*.mp3 en master_audio.mp3 con validación robusta.

    Estrategia:
      1. Intenta concat demuxer (rápido). Funciona si todos los MP3 tienen mismo formato.
      2. Si falla, intenta filter_complex (re-decodifica todo a un formato común).
      3. Verifica que el archivo final exista y tenga tamaño > 0 antes de retornarlo.

    Retorna Path al master_audio.mp3 si tuvo éxito, None si todo falló.
    Loggea claramente cada paso para que el operador pueda diagnosticar.
    """
    audio_dir = video_dir / "audio"
    if not audio_dir.is_dir():
        print(f"   ⚠️ No existe {audio_dir} — no hay narraciones para concatenar")
        return None

    narrations = sorted(audio_dir.glob("narration_*.mp3"))
    if not narrations:
        print(f"   ⚠️ No se encontraron archivos narration_*.mp3 en {audio_dir}")
        return None

    print(f"   🔗 Concatenando {len(narrations)} narraciones en master_audio.mp3")
    master_audio = video_dir / "master_audio.mp3"
    concat_list = video_dir / "_concat_audio.txt"

    try:
        # Intento 1: concat demuxer (rápido, requiere mismo formato)
        with open(concat_list, "w") as cl:
            for n in narrations:
                cl.write(f"file '{n}'\n")

        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_list), "-c:a", "libmp3lame",
             "-b:a", "192k", str(master_audio)],
            capture_output=True, text=True, timeout=180,
        )

        if result.returncode == 0 and master_audio.exists() and master_audio.stat().st_size > 0:
            print(f"   ✅ Concat demuxer OK ({master_audio.stat().st_size // 1024} KB)")
            return master_audio

        print(f"   ⚠️ Concat demuxer falló (rc={result.returncode}); intentando filter_complex")
        if result.stderr:
            print(f"      stderr: {result.stderr[-300:]}")

        # Intento 2: filter_complex (lento pero robusto, re-decodifica todo)
        inputs = []
        for n in narrations:
            inputs.extend(["-i", str(n)])
        filter_str = "".join(f"[{i}:a]" for i in range(len(narrations))) + f"concat=n={len(narrations)}:v=0:a=1[out]"

        result = subprocess.run(
            ["ffmpeg", "-y", *inputs,
             "-filter_complex", filter_str,
             "-map", "[out]", "-c:a", "libmp3lame",
             "-b:a", "192k", str(master_audio)],
            capture_output=True, text=True, timeout=300,
        )

        if result.returncode == 0 and master_audio.exists() and master_audio.stat().st_size > 0:
            print(f"   ✅ filter_complex OK ({master_audio.stat().st_size // 1024} KB)")
            return master_audio

        print(f"   ❌ filter_complex también falló (rc={result.returncode})")
        if result.stderr:
            print(f"      stderr: {result.stderr[-500:]}")
        return None

    except subprocess.TimeoutExpired:
        print(f"   ❌ Timeout concatenando audio ({len(narrations)} archivos)")
        return None
    except Exception as e:
        print(f"   ❌ Excepción concatenando audio: {e}")
        return None
    finally:
        if concat_list.exists():
            concat_list.unlink()


@app.get("/images/{project}/{filename}")
def serve_image(project: str, filename: str):
    """Sirve imágenes generadas desde el filesystem del VPS."""
    img_path = Path(f"/app/output/videos/{project}/images/{filename}")
    if img_path.exists():
        return FileResponse(img_path, media_type="image/png")
    return {"error": "Image not found"}


# Catálogo compacto de agentes para el clasificador (id + descripción de 1 línea).
# Mantener sincronizado con web/lib/agents.js — si agregas un agente allá,
# también aquí, en el mismo orden.
_AGENT_CATALOG = """
[agent_horror] Horror Histórico — torturas, plagas, castillos malditos, episodios oscuros documentados
[agent_misterios] Misterios Sin Resolver — desapariciones, casos fríos, anomalías sin explicación
[agent_biografias] Biografías Épicas — vidas legendarias con drama humano, figuras históricas
[agent_ciencia] Ciencia Explicada — universo, física cuántica, biología, asombro cósmico
[agent_finanzas] Catástrofes Financieras — crashes bursátiles, esquemas Ponzi, burbujas, fraudes
[agent_filosofia] Filosofía Estoica — Marco Aurelio, Séneca, sabiduría aplicada al presente
[agent_erotico_historico] Romance Histórico — cortes reales, cortesanas, poder y seducción de época
[agent_historico] Documental Histórico — vida cotidiana en eras antiguas, "un día en la vida de"
[agent_psicologia_oscura] Psicología Oscura — manipulación, narcisistas, psicópatas, cultos, control mental
[agent_civilizaciones] Civilizaciones Perdidas — Mayas, Atlántida, Sumeria, descubrimientos arqueológicos
[agent_true_crime] True Crime — asesinos seriales, crímenes famosos, investigaciones policiacas
[agent_mitologia] Mitología Universal — dioses, mitos, leyendas de culturas del mundo
[agent_conspiraciones] Conspiraciones — MK-Ultra, Area 51, gobiernos secretos, documentos clasificados
[agent_tecnologia] Tecnología del Futuro — IA, neuralink, fusión nuclear, robots, computación cuántica
[agent_guerras] Guerras y Batallas — Stalingrado, batallas decisivas, estrategia militar épica
[agent_espionaje] Espionaje Real — espías reales, KGB, CIA, operaciones encubiertas
[agent_apocalipsis] Apocalipsis y Catástrofes — Pompeya, Chernóbil, desastres naturales históricos
[agent_religiones] Religiones del Mundo — Vaticano, sectas, misticismo, historia de creencias
[agent_metafisica] Metafísica y Consciencia — Jung, DMT, simulación, experiencias cercanas a la muerte
[agent_imperios] Imperios Legendarios — Mongol, Romano, Otomano, auge y caída de potencias
[agent_arte] Arte y Genios Creativos — Van Gogh, Da Vinci, Picasso, vidas atormentadas de artistas
[agent_emprendimiento] Emprendimiento Extremo — Musk, Jobs, fundadores que casi quiebran y resurgen
[agent_negocios] Negocios y Estrategia — guerras corporativas, quiebras famosas, decisiones empresariales
[agent_liderazgo] Liderazgo y Poder — Mandela, Churchill, líderes que cambiaron el mundo
[agent_biblico] Historias Bíblicas — Éxodo, Apocalipsis, arqueología bíblica, relatos sagrados
[agent_viajes] Viajes y Exploraciones — Shackleton, Everest, lugares peligrosos del mundo
[agent_noticias_virales] Noticias Virales — eventos actuales que están en tendencia esta semana
""".strip()


@app.post("/recommend-agent")
async def recommend_agent(request: Request):
    """
    Dado un tema/idea de video del usuario, devuelve los 3 agentes más adecuados
    en orden de mejor a peor match. Cada uno con score (0-100) y razón corta.
    """
    try:
        data = await request.json()
        topic = (data.get("topic") or "").strip()
        if len(topic) < 5:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=400,
                content={"error": "topic too short (min 5 chars)"},
            )

        prompt = (
            f"Tienes este catálogo de agentes especializados (cada uno con un id y descripción):\n"
            f"{_AGENT_CATALOG}\n\n"
            f'El usuario quiere hacer un video documental sobre: "{topic}"\n\n'
            f"Responde EXCLUSIVAMENTE con un JSON array de los 3 mejores agentes, "
            f"ordenados de mejor a peor match. Sin texto adicional, sin markdown, solo el JSON.\n"
            f"Formato exacto:\n"
            f'[\n'
            f'  {{"agent_id": "agent_xxx", "score": 95, "reason": "frase corta en español"}},\n'
            f'  {{"agent_id": "agent_xxx", "score": 80, "reason": "frase corta en español"}},\n'
            f'  {{"agent_id": "agent_xxx", "score": 70, "reason": "frase corta en español"}}\n'
            f"]\n"
            f"Reglas: score 0-100. Reason en español, máximo 12 palabras, explica por qué encaja."
        )

        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()

        # Por si el modelo envuelve en markdown a pesar de la instrucción
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            text = text.rsplit("```", 1)[0].strip()

        recommendations = json.loads(text)
        if not isinstance(recommendations, list) or not recommendations:
            raise ValueError("respuesta sin recomendaciones")

        return {
            "recommendations": recommendations[:3],
            "tokens_used": resp.usage.input_tokens + resp.usage.output_tokens,
        }
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"error": str(e)[:200], "recommendations": []},
        )

@app.get("/video-url/{project_id}")
def get_video_url(project_id: str):
    """
    Devuelve una URL firmada fresca (7 días) para el video del proyecto.
    El frontend llama a este endpoint para obtener un link de descarga válido.
    """
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore, storage

        db = firestore.client()
        doc = db.collection("projects").document(project_id).get()
        if not doc.exists:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=404, content={"error": "project not found"})
        data = doc.to_dict()

        gs_path = data.get("videoStoragePath", "")
        if gs_path and gs_path.startswith("gs://"):
            blob_name = gs_path.split("/", 3)[3]  # remove gs://bucket/
            bucket = storage.bucket(FIREBASE_STORAGE_BUCKET)
            blob = bucket.blob(blob_name)
            if blob.exists():
                signed_url = blob.generate_signed_url(
                    version="v4", expiration=timedelta(days=7), method="GET",
                )
                return {"url": signed_url, "expiresInDays": 7, "source": "storage"}

        # Fallback: video aún en VPS (proyecto producido antes de la migración)
        video_folder = data.get("videoFolder", "")
        if video_folder:
            return {"url": f"/download/video/{video_folder}", "source": "vps", "note": "video not yet in Storage"}

        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "no video available"})
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


@app.get("/download/all/{project_id}")
def download_all(project_id: str):
    """
    Streamea un ZIP con TODO el material del proyecto organizado en carpetas:
    video/, audio/narrations/, images/, luma_clips/, ken_burns/, composites/,
    + subtitulos.ass + transcripcion.json + guion.txt + proyecto.json.

    Usa zipstream-ng para construir el ZIP on-the-fly (no en memoria),
    crítico cuando hay 88+ archivos por proyecto y video final de 150-200MB.
    """
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        from zipstream import ZipStream

        db = firestore.client()
        doc = db.collection("projects").document(project_id).get()
        if not doc.exists:
            return JSONResponse(status_code=404, content={"error": "project not found"})
        data = doc.to_dict()

        folder = data.get("videoFolder") or ""
        title = data.get("title") or "proyecto"
        if not folder:
            return JSONResponse(status_code=404, content={"error": "project has no videoFolder"})

        video_dir = Path(f"/app/output/videos/{folder}")
        if not video_dir.is_dir():
            return JSONResponse(
                status_code=404,
                content={"error": f"folder {folder} not found on disk"},
            )

        zs = ZipStream(sized=True)

        def add_glob(directory: Path, pattern: str, archive_subdir: str):
            if not directory.is_dir():
                return
            for f in sorted(directory.glob(pattern)):
                if f.is_file():
                    zs.add_path(str(f), arcname=f"{folder}/{archive_subdir}/{f.name}")

        def add_if(file_path: Path, arcname_rel: str):
            if file_path.is_file():
                zs.add_path(str(file_path), arcname=f"{folder}/{arcname_rel}")

        # Videos finales (con y sin subtítulos)
        for mp4 in sorted(video_dir.glob("FINAL_*.mp4")):
            zs.add_path(str(mp4), arcname=f"{folder}/video/{mp4.name}")

        # Audio: master + narraciones individuales
        add_if(video_dir / "master_audio.mp3", "audio/master.mp3")
        add_glob(video_dir / "audio", "narration_*.mp3", "audio/narrations")

        # Imágenes
        add_glob(video_dir / "images", "*.png", "images")
        add_glob(video_dir / "images", "*.jpg", "images")

        # Clips Luma
        add_glob(video_dir / "luma_clips", "*.mp4", "luma_clips")

        # Ken Burns (carpeta puede ser 'kenburns' o 'ken_burns' según versión)
        for kb_name in ["kenburns", "ken_burns"]:
            add_glob(video_dir / kb_name, "*.mp4", "ken_burns")

        # Composites (mezclas intermedias)
        add_glob(video_dir / "composites", "*.mp4", "composites")

        # Otros activos sueltos del root del folder
        add_if(video_dir / "subtitles.ass", "subtitulos.ass")
        add_if(video_dir / "transcript.json", "transcripcion.json")
        add_if(video_dir / "master_visual.mp4", "master_visual.mp4")

        # Guión desde Firestore (no está en disco como .txt)
        script_text = (data.get("script") or {}).get("plain") or ""
        if script_text:
            zs.add(script_text.encode("utf-8"), arcname=f"{folder}/guion.txt")

        # Metadata del proyecto en JSON
        meta = {
            "id": project_id,
            "title": title,
            "agentId": data.get("agentId"),
            "createdAt": str(data.get("createdAt")),
            "completedAt": str(data.get("completedAt")),
            "hasSubtitles": data.get("hasSubtitles"),
            "videoFolder": folder,
            "videoSizeMB": data.get("videoSizeMB"),
            "viralityScore": data.get("viralityScore"),
            "scenesCount": len(data.get("scenes") or []),
            "downloadedAt": datetime.now(timezone.utc).isoformat(),
        }
        zs.add(
            json.dumps(meta, indent=2, default=str).encode("utf-8"),
            arcname=f"{folder}/proyecto.json",
        )

        # Sanitizar nombre del archivo descargado
        safe_filename = "".join(c if (c.isalnum() or c in "_-") else "_" for c in folder)[:100]

        return StreamingResponse(
            iter(zs),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}.zip"',
                "Content-Length": str(len(zs)),
                "Cache-Control": "no-cache",
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:300]})


@app.get("/download/video/{project}")
def download_video(project: str):
    """Descarga el video final ensamblado."""
    video_dir = Path(f"/app/output/videos/{project}")
    # Buscar el archivo FINAL_*.mp4
    finals = list(video_dir.glob("FINAL_*.mp4"))
    video_file = finals[0] if finals else None
    if not video_file:
        # Buscar cualquier .mp4 que no sea de kenburns
        all_mp4 = [f for f in video_dir.glob("*.mp4") if "kenburns" not in str(f)]
        video_file = all_mp4[0] if all_mp4 else None
    if not video_file:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": f"Video not found in {video_dir}"})
    
    file_size = video_file.stat().st_size
    safe_name = video_file.name.encode('ascii', 'ignore').decode('ascii') or "video.mp4"
    return FileResponse(
        video_file,
        media_type="video/mp4",
        filename=safe_name,
        headers={
            "Content-Length": str(file_size),
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
        }
    )

@app.get("/download/images/{project}")
def download_images_zip(project: str):
    """Descarga todas las imágenes del proyecto como ZIP."""
    import zipfile
    images_dir = Path(f"/app/output/videos/{project}/images")
    if not images_dir.exists():
        return {"error": "Images not found"}
    
    zip_path = Path(f"/tmp/{project}_images.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for img in sorted(images_dir.glob("scene_*.png")):
            zf.write(img, img.name)
    
    file_size = zip_path.stat().st_size
    safe_name = f"{project}_imagenes.zip".encode('ascii', 'ignore').decode('ascii')
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=safe_name,
        headers={
            "Content-Length": str(file_size),
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Cache-Control": "no-cache",
        }
    )

@app.get("/")
def health_check():
    return {"status": "online", "service": "Content Factory API"}


@app.get("/metrics")
def metrics():
    """
    Snapshot operacional del sistema. Pensado para chequeo rápido del operador
    (curl o dashboard interno futuro), no expuesto al usuario final.

    Devuelve:
      - jobs.active: proyectos en producción ahora mismo
      - jobs.completed_24h: producciones exitosas últimas 24h
      - jobs.errored_24h: producciones con error últimas 24h
      - sizes.total_storage_mb: suma de videoSizeMB de todos los completados
      - api_uptime_seconds: cuánto lleva corriendo este worker
    """
    try:
        _ensure_firebase_initialized()
        from firebase_admin import firestore
        db = firestore.client()

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)

        # Solo agregamos métricas baratas (sin scan completo de la colección).
        # En producción a escala, esto debe migrar a contadores agregados o cache.
        all_projects = list(db.collection("projects").stream())

        active = 0
        completed_24h = 0
        errored_24h = 0
        total_size_mb = 0.0

        for p in all_projects:
            d = p.to_dict() or {}
            status = d.get("status", "")
            if status == "producing":
                active += 1
            size = d.get("videoSizeMB")
            if isinstance(size, (int, float)):
                total_size_mb += size
            completed_at = d.get("completedAt")
            if completed_at and hasattr(completed_at, "timestamp"):
                if datetime.fromtimestamp(completed_at.timestamp(), tz=timezone.utc) >= cutoff:
                    if status == "completed":
                        completed_24h += 1
                    elif status == "error":
                        errored_24h += 1

        uptime = (datetime.now(timezone.utc) - _STARTED_AT).total_seconds()

        return {
            "jobs": {
                "active": active,
                "completed_24h": completed_24h,
                "errored_24h": errored_24h,
                "total_known": len(all_projects),
            },
            "storage": {
                "total_video_mb": round(total_size_mb, 1),
            },
            "api": {
                "uptime_seconds": int(uptime),
                "uptime_human": _humanize_seconds(uptime),
                "started_at": _STARTED_AT.isoformat(),
            },
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


_STARTED_AT = datetime.now(timezone.utc)


def _humanize_seconds(s: float) -> str:
    s = int(s)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    h = s // 3600
    return f"{h}h {(s % 3600) // 60}m"

@app.post("/generate")
async def trigger_generation(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    topic = data.get("topic")
    agent_file = data.get("agentFile", "agent_erotico_historico.md")
    project_id = data.get("projectId")
    
    if not topic:
        return {"status": "error", "message": "Missing 'topic' in request body"}

    # Ejecutar en segundo plano para no dejar colgada la petición HTTP a n8n
    background_tasks.add_task(run_script, topic, agent_file, project_id)
    
    return {
        "status": "accepted", 
        "message": f"Generation started for '{topic}' with agent '{agent_file}' (Project: {project_id})"
    }

@app.post("/produce")
async def trigger_production(request: Request, background_tasks: BackgroundTasks):
    """Dispara el pipeline de producción: Imágenes → Audio → Video Final."""
    data = await request.json()
    project_id = data.get("projectId")
    
    if not project_id:
        return {"status": "error", "message": "Missing 'projectId'"}
    
    background_tasks.add_task(run_production, project_id)
    
    return {
        "status": "accepted",
        "message": f"Production pipeline started for project {project_id}"
    }

@app.post("/retry")
async def retry_production(request: Request, background_tasks: BackgroundTasks):
    """Resetea estado de un proyecto con error y re-lanza producción."""
    data = await request.json()
    project_id = data.get("projectId")
    
    if not project_id:
        return {"status": "error", "message": "Missing 'projectId'"}
    
    # Resetear estado en Firebase
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        try:
            firebase_admin.get_app()
        except ValueError:
            cred_path = "/app/firebase-admin.json"
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        doc_ref = db.collection("projects").document(project_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return {"status": "error", "message": "Project not found"}
        
        # Resetear a estado "produced" para re-lanzar
        doc_ref.update({
            "status": "producing",
            "progress.percent": 5,
            "progress.stepName": "Retrying production...",
        })
        
        background_tasks.add_task(run_production, project_id)
        
        return {
            "status": "accepted",
            "message": f"Retry started for project {project_id}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/reset-status")
async def reset_project_status(request: Request):
    """Resetea el estado de un proyecto para permitir re-producción desde la UI."""
    data = await request.json()
    project_id = data.get("projectId")
    new_status = data.get("status", "produced")
    
    if not project_id:
        return {"status": "error", "message": "Missing 'projectId'"}
    
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        try:
            firebase_admin.get_app()
        except ValueError:
            cred_path = "/app/firebase-admin.json"
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
        
        db = firestore.client()
        doc_ref = db.collection("projects").document(project_id)
        doc_ref.update({
            "status": new_status,
            "progress.percent": 0,
            "progress.stepName": "",
        })
        
        return {"status": "ok", "message": f"Project reset to '{new_status}'"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def run_script(topic, agent_file, project_id):
    print(f"🚀 [API] Starting background job for '{topic}' with '{agent_file}' (Project: {project_id})...", flush=True)
    try:
        # Import directo — sin subprocess, para que los errores aparezcan en logs
        import sys
        sys.path.insert(0, "/app")
        from scripts.generate_content import run_full_pipeline
        result = run_full_pipeline(topic, agent_file, project_id)
        if result:
            print(f"✅ [API] Pipeline completed successfully for '{topic}'", flush=True)
        else:
            print(f"⚠️ [API] Pipeline returned None for '{topic}' — check Firebase for error status", flush=True)
    except Exception as e:
        import traceback
        print(f"❌ [API] Error running script: {e}", flush=True)
        traceback.print_exc()
        # Reportar error a Firebase
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore
            try:
                firebase_admin.get_app()
            except ValueError:
                cred_path = "/app/firebase-admin.json"
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
            db = firestore.client()
            db.collection("projects").document(project_id).update({
                "status": "error",
                "progress.stepName": f"Error: {str(e)[:150]}",
                "progress.percent": 0,
            })
        except Exception as fb_err:
            print(f"❌ [API] Also failed to report error to Firebase: {fb_err}", flush=True)

def run_production(project_id):
    """Ejecuta el pipeline cinemático: FLUX → ElevenLabs → Luma → Ken Burns → Ensamblaje."""
    import firebase_admin
    from firebase_admin import credentials, firestore
    from pathlib import Path
    import threading
    import time
    
    print(f"🏭 [PRODUCE] Starting CINEMATIC production for project {project_id}...")
    
    # Inicializar Firebase con storageBucket (necesario para upload del video final)
    try:
        _ensure_firebase_initialized()
    except Exception as init_err:
        print(f"❌ [PRODUCE] firebase init failed: {init_err}")
        return

    db = firestore.client()
    doc_ref = db.collection("projects").document(project_id)
    
    def update_progress(percent, step_name, status="producing"):
        doc_ref.update({
            "status": status,
            "progress.percent": percent,
            "progress.stepName": step_name,
        })
        print(f"   [{percent}%] {step_name}")
    
    try:
        # Leer datos del proyecto desde Firebase
        project = doc_ref.get().to_dict()
        if not project:
            print("❌ [PRODUCE] Project not found in Firebase")
            return
        
        title = project.get("title", "video_sin_titulo")
        scenes = project.get("scenes", [])
        agent_id = project.get("agentId", "")
        
        if not scenes:
            update_progress(0, "Error: No hay escenas visuales", "error")
            return
        
        # Crear JSON compatible con factory.py
        import re
        safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title.replace(" ", "_"))
        
        # Mapear scenes de Firestore al formato factory.py
        factory_scenes = []
        for s in scenes:
            factory_scenes.append({
                "scene_number": s.get("scene_number", s.get("sceneNumber", 0)),
                "prompt": s.get("prompt", ""),
                "narration": s.get("narration_text", s.get("narration", "")),
            })
        
        temp_json = {
            "topic": title,
            "agent": agent_id,
            "video_scenes": factory_scenes,
            "seo_metadata": project.get("seo_metadata", {"title": title})
        }
        temp_path = f"/app/output/scripts/PRODUCE_{safe_title}.json"
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(temp_json, f, ensure_ascii=False, indent=2)
        
        # ═══════════════════════════════════════════
        # Directorios del proyecto
        # ═══════════════════════════════════════════
        images_dir = Path(f"/app/output/videos/{safe_title}/images")
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # ═══════════════════════════════════════════
        # PASO 1: Generar Imágenes con FLUX (5% → 40%)
        # ═══════════════════════════════════════════
        
        # Detectar imágenes existentes para evitar regenerar
        existing_images = sorted(images_dir.glob("scene_*.png"))
        existing_count = len([f for f in existing_images if f.stat().st_size > 1000])
        
        if existing_count >= len(scenes):
            print(f"   ✅ {existing_count}/{len(scenes)} imágenes ya existen — saltando FLUX")
            update_progress(40, f"✅ {existing_count} imágenes ya existentes (reutilizadas)")
        else:
            update_progress(5, f"Generando {len(scenes)} imágenes con FLUX... ({existing_count} existentes)")
            
            # Monitorear progreso de imágenes
            stop_monitoring = threading.Event()
            
            def monitor_images():
                vps_base = os.environ.get("VPS_PUBLIC_URL", "http://100.99.207.113:8085")
                reported = set()
                while not stop_monitoring.is_set():
                    time.sleep(8)
                    existing = sorted(images_dir.glob("scene_*.png"))
                    for img in existing:
                        if img.name not in reported and img.stat().st_size > 1000:
                            reported.add(img.name)
                            try:
                                num = int(img.stem.split("_")[1])
                                image_url = f"{vps_base}/images/{safe_title}/{img.name}"
                                updated_scenes = doc_ref.get().to_dict().get("scenes", [])
                                for s in updated_scenes:
                                    sn = s.get("scene_number", s.get("sceneNumber", 0))
                                    if sn == num:
                                        s["imageUrl"] = image_url
                                        break
                                doc_ref.update({"scenes": updated_scenes})
                                pct = 5 + int((len(reported) / len(scenes)) * 35)
                                update_progress(pct, f"🎨 Imagen {len(reported)}/{len(scenes)} generada")
                            except Exception as e:
                                print(f"   ⚠️ Monitor error: {e}")
            
            monitor_thread = threading.Thread(target=monitor_images, daemon=True)
            monitor_thread.start()
            
            # factory.py con --images-only
            result = subprocess.run(
                ["python", "scripts/factory.py", temp_path, "--mode", "cinematico", "--images-only"],
                capture_output=True, text=True, timeout=3600
            )
            
            stop_monitoring.set()
            monitor_thread.join(timeout=5)
            
            if result.returncode != 0:
                update_progress(0, f"Error generando imágenes", "error")
                print(f"STDERR: {result.stderr[-500:]}")
                return
            
            update_progress(40, "✅ Imágenes FLUX listas")
        
        # ═══════════════════════════════════════════
        # PASO 2-4: Narración + Luma + Ken Burns + Ensamblaje (40% → 100%)
        # ═══════════════════════════════════════════
        update_progress(45, "🎙️ Generando narración con ElevenLabs...")
        
        # Ejecutar factory.py completo (skip-images ya que las tenemos)
        # Monitorear progreso por pasos
        def monitor_factory():
            """Monitorea los archivos generados para actualizar progreso."""
            audio_dir = Path(f"/app/output/videos/{safe_title}/audio")
            kb_dir = Path(f"/app/output/videos/{safe_title}/kenburns")
            luma_dir = Path(f"/app/output/videos/{safe_title}/luma_clips")
            
            while not stop_monitoring.is_set():
                time.sleep(5)
                try:
                    # Audio progress (45% → 65%)
                    audio_count = len(list(audio_dir.glob("narration_*.mp3"))) if audio_dir.exists() else 0
                    if audio_count > 0 and audio_count < len(scenes):
                        pct = 45 + int((audio_count / len(scenes)) * 20)
                        update_progress(pct, f"🎙️ Narración {audio_count}/{len(scenes)}")
                    elif audio_count >= len(scenes):
                        # Ken Burns progress (65% → 85%)
                        kb_count = len(list(kb_dir.glob("scene_*.mp4"))) if kb_dir.exists() else 0
                        if kb_count > 0 and kb_count < len(scenes):
                            pct = 65 + int((kb_count / len(scenes)) * 15)
                            update_progress(pct, f"🎬 Ken Burns {kb_count}/{len(scenes)}")
                        elif kb_count >= len(scenes):
                            # Luma progress (80% → 90%)
                            luma_count = len(list(luma_dir.glob("luma_*.mp4"))) if luma_dir.exists() else 0
                            if luma_count > 0:
                                update_progress(85, f"🎥 Luma clips: {luma_count}")
                except:
                    pass
        
        stop_monitoring = threading.Event()
        factory_monitor = threading.Thread(target=monitor_factory, daemon=True)
        factory_monitor.start()
        
        result = subprocess.run(
            ["python", "scripts/factory.py", temp_path, 
             "--mode", "cinematico", "--luma-scenes", "8", "--skip-images"],
            capture_output=True, text=True, timeout=3600
        )
        
        stop_monitoring.set()
        factory_monitor.join(timeout=5)
        
        if result.returncode != 0:
            update_progress(40, f"Error en pipeline cinemático", "error")
            print(f"STDERR: {result.stderr[-500:]}")
            return
        
        # ═══════════════════════════════════════════
        # PASO EXTRA: Subtítulos explícitos (fallback)
        # ═══════════════════════════════════════════
        video_dir = Path(f"/app/output/videos/{safe_title}")
        sub_videos = list(video_dir.glob("FINAL_SUB_*.mp4"))
        
        if not sub_videos:
            # factory.py no generó subtítulos — intentar directamente
            update_progress(92, "📝 Generando subtítulos...")
            regular_videos = list(video_dir.glob("FINAL_*.mp4"))
            regular_videos = [v for v in regular_videos if "FINAL_SUB_" not in v.name]
            
            if regular_videos:
                try:
                    sys.path.insert(0, "/app/scripts")
                    from generate_subtitles import add_subtitles_to_video

                    master_audio = video_dir / "master_audio.mp3"
                    if not master_audio.exists():
                        master_audio = _build_master_audio(video_dir)

                    if master_audio is None or not master_audio.exists() or master_audio.stat().st_size == 0:
                        print("   ⚠️ Sin audio maestro válido — saltando subtítulos")
                    else:
                        print(f"   🎤 Audio maestro listo ({master_audio.stat().st_size // 1024} KB) → Whisper")
                        subtitled = add_subtitles_to_video(
                            video_path=regular_videos[0],
                            audio_path=master_audio,
                        )
                        if subtitled:
                            sub_videos = [subtitled]
                            print(f"   ✅ Subtítulos generados: {subtitled.name}")
                        else:
                            print("   ⚠️ Subtítulos fallaron — continuando sin subs")
                except Exception as sub_err:
                    print(f"   ⚠️ Error subtítulos: {sub_err}")
        
        # ═══════════════════════════════════════════
        # COMPLETADO
        # ═══════════════════════════════════════════
        # Refrescar listas después del paso de subtítulos
        sub_videos = list(video_dir.glob("FINAL_SUB_*.mp4"))
        regular_videos = list(video_dir.glob("FINAL_*.mp4"))
        regular_videos = [v for v in regular_videos if "FINAL_SUB_" not in v.name]
        
        if sub_videos:
            final_path = str(sub_videos[0])
            has_subs = True
        elif regular_videos:
            final_path = str(regular_videos[0])
            has_subs = False
        else:
            final_path = ""
            has_subs = False
        
        # Subir video final a Firebase Storage para entrega via CDN (sin pegar al VPS)
        storage_info = None
        if final_path:
            update_progress(96, "☁️ Subiendo a Storage...")
            storage_info = _upload_video_to_storage(Path(final_path), project_id)

        status_msg = "🏆 ¡Video cinemático finalizado!" if not has_subs else "🏆 ¡Video cinemático con subtítulos finalizado!"

        update_payload = {
            "status": "completed",
            "progress.percent": 100,
            "progress.stepName": status_msg,
            "videoPath": final_path,
            "videoFolder": safe_title,
            "hasSubtitles": has_subs,
        }
        if storage_info:
            update_payload["videoStoragePath"] = storage_info["gs_path"]
            update_payload["videoUrl"] = storage_info["signed_url"]
            update_payload["videoUrlExpiresAt"] = firestore.SERVER_TIMESTAMP

        doc_ref.update(update_payload)

        print(f"🏆 [PRODUCE] Cinematic production complete! Subs: {has_subs} | Storage: {bool(storage_info)} | {final_path}")
        
    except Exception as e:
        update_progress(0, f"Error: {str(e)[:100]}", "error")
        print(f"❌ [PRODUCE] Error: {e}")


