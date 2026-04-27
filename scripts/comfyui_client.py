"""
Content Factory - Máquina 4: ComfyUI Cloud Client
Genera clips de video a partir de prompts cinematográficos.
Usa la API de ComfyUI Cloud con el modelo LTX Video.
"""
import os
import json
import time
import io
import sys
import httpx
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()

# ============================================================
# CONFIGURACIÓN
# ============================================================
BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "config" / "settings.json"
CLIPS_DIR = BASE_DIR / "output" / "clips"
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

COMFYUI_API_KEY = os.getenv("COMFYUI_API_KEY")
COMFYUI_BASE_URL = "https://cloud.comfy.org/api"

# Modelo de video configurado
VIDEO_MODEL = config["models"]["video_generation"]  # "ltx-video-2.3"
CLIP_DURATION = config.get("clip_duration_seconds", 5)  # 5

# Headers de autenticación
HEADERS = {
    "X-API-Key": COMFYUI_API_KEY,
    "Content-Type": "application/json"
}


def build_text_to_video_workflow(prompt: str, scene_number: int) -> dict:
    """
    Carga el workflow JSON exportado de ComfyUI Cloud para Wan 2.2 14B Premium,
    inyecta el prompt, semilla y duración forzada.
    """
    workflow_path = BASE_DIR / "config" / "video_wan2_2_14B_t2v_api.json"
    
    with open(workflow_path, "r", encoding="utf-8") as f:
        nodes = json.load(f)
        
    # 1. Inyectar el prompt en el nodo CLIPTextEncode (Positive Prompt: 128:89)
    if "128:89" in nodes and "inputs" in nodes["128:89"]:
        cinematic_prompt = f"Masterpiece, cinematic lighting, ultra-detailed, highly realistic, 8k resolution. {prompt}"
        nodes["128:89"]["inputs"]["text"] = cinematic_prompt
        
    # 2. Inyectar la semilla aleatoria en el KSamplerAdvanced (128:81)
    if "128:81" in nodes and "inputs" in nodes["128:81"]:
        import random
        nodes["128:81"]["inputs"]["noise_seed"] = random.randint(100000000000000, 999999999999999)
        
    # 3. Nombrar el archivo de salida en SaveVideo (80)
    if "80" in nodes and "inputs" in nodes["80"]:
        nodes["80"]["inputs"]["filename_prefix"] = f"scene_{scene_number:04d}"
        
    # 4. Forzar la duración a 81 frames (5 segundos a 16fps) en EmptyHunyuanLatentVideo (128:74)
    if "128:74" in nodes and "inputs" in nodes["128:74"]:
        nodes["128:74"]["inputs"]["length"] = 81
        
    return {"prompt": nodes}



def submit_workflow(prompt: str, scene_number: int) -> str:
    """
    Envía un workflow a ComfyUI Cloud.
    Returns: prompt_id para monitorear el progreso.
    """
    workflow = build_text_to_video_workflow(prompt, scene_number)
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{COMFYUI_BASE_URL}/prompt",
                headers=HEADERS,
                json=workflow
            )
            
            if response.status_code == 200:
                data = response.json()
                prompt_id = data.get("prompt_id", "")
                return prompt_id
            else:
                print(f"   ❌ Error HTTP {response.status_code}: {response.text[:200]}")
                return None
                
    except Exception as e:
        print(f"   ❌ Error enviando workflow: {e}")
        return None


def check_status(prompt_id: str) -> dict:
    """
    Verifica el estado de un workflow en ejecución.
    Returns: dict con status y outputs si están listos.
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{COMFYUI_BASE_URL}/history/{prompt_id}",
                headers=HEADERS
            )
            
            if response.status_code == 200:
                data = response.json()
                if prompt_id in data:
                    return data[prompt_id]
            return None
            
    except Exception as e:
        print(f"   ⚠️  Error checking status: {e}")
        return None


def download_clip(prompt_id: str, scene_number: int, output_dir: Path) -> str:
    """
    Descarga el clip generado desde ComfyUI Cloud.
    Returns: ruta al archivo descargado.
    """
    status = check_status(prompt_id)
    
    if not status or "outputs" not in status:
        return None
    
    outputs = status["outputs"]
    
    for node_id, node_output in outputs.items():
        if "videos" in node_output:
            for video in node_output["videos"]:
                filename = video.get("filename", "")
                subfolder = video.get("subfolder", "")
                
                try:
                    with httpx.Client(timeout=120.0) as client:
                        response = client.get(
                            f"{COMFYUI_BASE_URL}/view",
                            headers=HEADERS,
                            params={
                                "filename": filename,
                                "subfolder": subfolder,
                                "type": "output"
                            }
                        )
                        
                        if response.status_code == 200:
                            output_path = output_dir / f"scene_{scene_number:04d}.mp4"
                            with open(output_path, "wb") as f:
                                f.write(response.content)
                            return str(output_path)
                            
                except Exception as e:
                    print(f"   ❌ Error descargando: {e}")
    
    return None


def wait_for_completion(prompt_id: str, timeout_minutes: int = 10) -> dict:
    """
    Espera a que un workflow termine, con polling.
    """
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    poll_interval = 5  # segundos
    
    while (time.time() - start_time) < timeout_seconds:
        status = check_status(prompt_id)
        
        if status:
            status_info = status.get("status", {})
            completed = status_info.get("completed", False)
            
            if completed:
                return status
            
            # Check for errors
            if status_info.get("status_str") == "error":
                return {"error": True, "details": status}
        
        time.sleep(poll_interval)
    
    return {"error": True, "details": "timeout"}


def generate_batch(scenes: list, output_dir: Path, batch_size: int = 5, 
                   start_from: int = 0) -> list:
    """
    Genera clips en batch desde ComfyUI Cloud.
    Procesa en lotes para no saturar la API.
    
    Args:
        scenes: lista de dicts con scene_number y prompt
        output_dir: ruta donde se guardarán los videos de este proyecto
        batch_size: cuántos clips enviar simultáneamente
        start_from: escena desde la que empezar (para reanudar)
    
    Returns:
        lista de rutas a clips generados
    """
    # Crear la carpeta específica para este proyecto
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🎬 COMFYUI CLOUD — Generación de Video en Batch")
    print("=" * 60)
    print(f"   Carpeta Destino: {output_dir.name}")
    print(f"   Total escenas: {len(scenes)}")
    print(f"   Batch size: {batch_size}")
    print(f"   Empezando desde: escena {start_from}")
    print("=" * 60)
    
    if not COMFYUI_API_KEY:
        print("❌ ERROR: COMFYUI_API_KEY no configurada en .env")
        return []
    
    generated = []
    failed = []
    
    # Filtrar escenas ya generadas
    remaining = [s for s in scenes if s.get("scene_number", 0) >= start_from]
    
    for batch_start in range(0, len(remaining), batch_size):
        batch = remaining[batch_start:batch_start + batch_size]
        batch_num = (batch_start // batch_size) + 1
        total_batches = (len(remaining) + batch_size - 1) // batch_size
        
        print(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} escenas)")
        
        # Enviar batch
        pending = {}
        for scene in batch:
            num = scene.get("scene_number", batch_start)
            prompt = scene.get("prompt", "")
            
            # Verificar si ya existe
            clip_path = output_dir / f"scene_{num:04d}.mp4"
            if clip_path.exists():
                print(f"   ⏭️  Escena {num}: ya existe, saltando")
                generated.append(str(clip_path))
                continue
            
            prompt_id = submit_workflow(prompt, num)
            if prompt_id:
                pending[prompt_id] = num
                print(f"   ✅ Escena {num}: enviada ({prompt_id[:8]}...)")
            else:
                failed.append(num)
                print(f"   ❌ Escena {num}: falló al enviar")
        
        # No esperar ni descargar porque la API de la nube requiere descarga manual por ahora
        print("   ⏭️  Trabajos enviados. Por favor, revisa el dashboard de ComfyUI Cloud.")
        
        # Progreso
        progress = (batch_start + len(batch)) / len(remaining) * 100
        print(f"   📊 Progreso: {progress:.0f}%")
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE GENERACIÓN")
    print("=" * 60)
    print(f"   ✅ Enviados: {len(pending)} clips")
    print(f"   ❌ Fallidos: {len(failed)} clips")
    if failed:
        print(f"   🔄 Escenas fallidas: {failed}")
    print(f"   💾 Directorio: {output_dir}")
    print("=" * 60)
    
    # Guardar log
    log = {
        "timestamp": datetime.now().isoformat(),
        "total_scenes": len(scenes),
        "generated": len(generated),
        "failed": len(failed),
        "failed_scenes": failed,
        "generated_paths": generated
    }
    log_path = output_dir / "generation_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    
    return generated


# ============================================================
# EJECUCIÓN STANDALONE
# ============================================================
if __name__ == "__main__":
    import sys
    import re
    
    if len(sys.argv) < 2:
        print("Uso: python comfyui_client.py <ruta_al_FULL_json>")
        print("Ejemplo: python comfyui_client.py output/primer_guion_generado.json")
        sys.exit(1)
    
    json_path = Path(sys.argv[1])
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    scenes = data.get("video_scenes", [])
    
    if not scenes:
        print("❌ No se encontraron escenas de video en el JSON")
        sys.exit(1)
        
    # Obtener título y limpiar caracteres raros para la carpeta
    raw_title = data.get("topic", "video_sin_titulo")
    if "seo_metadata" in data and "title" in data["seo_metadata"]:
        raw_title = data["seo_metadata"]["title"]
        
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title.replace(" ", "_"))
    output_dir = BASE_DIR / "output" / "videos" / safe_title / "clips"
    
    print(f"📂 Cargando {len(scenes)} escenas desde {json_path}")
    print(f"📁 Directorio de proyecto: {output_dir}")
    
    # LÍMITE DE PRUEBA: Generar los clips 4, 5 y 6 para el modelo premium
    generate_batch(scenes[3:6], output_dir=output_dir, batch_size=3)

