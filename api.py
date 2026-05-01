from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
import json
from pathlib import Path

# ── Escribir firebase-admin.json desde variable de entorno (si existe) ──
firebase_creds = os.environ.get("FIREBASE_CREDENTIALS", "")
if firebase_creds:
    cred_path = "/app/firebase-admin.json"
    try:
        # Intentar decodificar base64 primero
        import base64
        try:
            decoded = base64.b64decode(firebase_creds).decode("utf-8")
            json.loads(decoded)  # Validar que es JSON
            firebase_creds = decoded
        except Exception:
            pass  # Ya es JSON raw
        
        with open(cred_path, "w") as f:
            f.write(firebase_creds)
        print(f"✅ Firebase credentials written to {cred_path}", flush=True)
    except Exception as e:
        print(f"⚠️ Could not write Firebase credentials: {e}", flush=True)

app = FastAPI(title="Content Factory API")

# CORS para que el frontend pueda cargar imágenes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/images/{project}/{filename}")
def serve_image(project: str, filename: str):
    """Sirve imágenes generadas desde el filesystem del VPS."""
    img_path = Path(f"/app/output/videos/{project}/images/{filename}")
    if img_path.exists():
        return FileResponse(img_path, media_type="image/png")
    return {"error": "Image not found"}

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
        return {"error": "Video not found"}
    
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
    
    # Inicializar Firebase si no está activo
    try:
        firebase_admin.get_app()
    except ValueError:
        cred_path = "/app/firebase-admin.json"
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            print("❌ [PRODUCE] firebase-admin.json not found")
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
                    subtitled = add_subtitles_to_video(
                        video_path=regular_videos[0],
                        audio_path=master_audio if master_audio.exists() else None
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
        
        status_msg = "🏆 ¡Video cinemático finalizado!" if not has_subs else "🏆 ¡Video cinemático con subtítulos finalizado!"
        
        doc_ref.update({
            "status": "completed",
            "progress.percent": 100,
            "progress.stepName": status_msg,
            "videoPath": final_path,
            "hasSubtitles": has_subs,
        })
        
        print(f"🏆 [PRODUCE] Cinematic production complete! Subs: {has_subs} | {final_path}")
        
    except Exception as e:
        update_progress(0, f"Error: {str(e)[:100]}", "error")
        print(f"❌ [PRODUCE] Error: {e}")


