from fastapi import FastAPI, BackgroundTasks, Request
import subprocess
import os
import json

app = FastAPI(title="Content Factory API")

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

def run_script(topic, agent_file, project_id):
    print(f"🚀 [API] Starting background job for '{topic}' with '{agent_file}' (Project: {project_id})...")
    try:
        # Ejecutamos el script igual que en consola
        args = ["python", "scripts/generate_content.py", "--agent", agent_file]
        if project_id:
            args.extend(["--project-id", project_id])
        args.append(topic)
        
        process = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True
        )
        print("✅ [API] Script finished.")
        print("--- STDOUT ---")
        print(process.stdout)
        if process.stderr:
            print("--- STDERR ---")
            print(process.stderr)
    except Exception as e:
        print(f"❌ [API] Error running script: {e}")

def run_production(project_id):
    """Ejecuta el pipeline de producción completo con reportes a Firebase."""
    import firebase_admin
    from firebase_admin import credentials, firestore
    from pathlib import Path
    
    print(f"🏭 [PRODUCE] Starting production for project {project_id}...")
    
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
        script_text = project.get("script", {}).get("plain", "")
        
        if not scenes:
            update_progress(0, "Error: No hay escenas visuales", "error")
            return
        
        if not script_text:
            update_progress(0, "Error: No hay guión aprobado", "error")
            return
        
        # Crear JSON temporal para los scripts de producción
        import re
        safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title.replace(" ", "_"))
        
        temp_json = {
            "topic": title,
            "script_plain": script_text,
            "video_scenes": scenes,
            "seo_metadata": project.get("seo_metadata", {"title": title})
        }
        temp_path = f"/app/output/scripts/PRODUCE_{safe_title}.json"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(temp_json, f, ensure_ascii=False, indent=2)
        
        # ═══════════════════════════════════════════
        # PASO 1: Generar Imágenes con FLUX + Ken Burns
        # ═══════════════════════════════════════════
        update_progress(5, f"Generando {len(scenes)} imágenes con FLUX...")
        
        result = subprocess.run(
            ["python", "scripts/production_pipeline.py", temp_path],
            capture_output=True, text=True, timeout=3600  # 1 hora max
        )
        
        if result.returncode != 0:
            update_progress(0, f"Error en generación de imágenes", "error")
            print(f"STDERR: {result.stderr[-500:]}")
            return
        
        update_progress(50, "Imágenes y Ken Burns listos ✅")
        
        # ═══════════════════════════════════════════
        # PASO 2: Generar Audio TTS  
        # ═══════════════════════════════════════════
        update_progress(55, "Generando narración con Google TTS...")
        
        result = subprocess.run(
            ["python", "scripts/generate_google_tts.py", temp_path],
            capture_output=True, text=True, timeout=600  # 10 min max
        )
        
        if result.returncode != 0:
            update_progress(50, f"Error en generación de audio", "error")
            print(f"STDERR: {result.stderr[-500:]}")
            return
        
        update_progress(75, "Audio narrado listo ✅")
        
        # ═══════════════════════════════════════════
        # PASO 3: Ensamblar Video Final
        # ═══════════════════════════════════════════
        update_progress(80, "Ensamblando video final...")
        
        result = subprocess.run(
            ["python", "scripts/assemble_video.py", temp_path],
            capture_output=True, text=True, timeout=600
        )
        
        if result.returncode != 0:
            update_progress(75, f"Error en ensamblaje de video", "error")
            print(f"STDERR: {result.stderr[-500:]}")
            return
        
        # ═══════════════════════════════════════════
        # COMPLETADO
        # ═══════════════════════════════════════════
        final_video_path = f"/app/output/videos/{safe_title}/FINAL_{safe_title}.mp4"
        
        doc_ref.update({
            "status": "completed",
            "progress.percent": 100,
            "progress.stepName": "¡Video finalizado!",
            "videoPath": final_video_path,
        })
        
        print(f"🏆 [PRODUCE] Production complete! Video: {final_video_path}")
        
    except Exception as e:
        update_progress(0, f"Error: {str(e)[:100]}", "error")
        print(f"❌ [PRODUCE] Error: {e}")

