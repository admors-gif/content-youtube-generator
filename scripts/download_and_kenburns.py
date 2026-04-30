"""
Content Factory - Descarga imágenes de ComfyUI Cloud + Aplica Ken Burns
Genera clips de video de 5 segundos a partir de imágenes estáticas.
"""
import os
import sys
import json
import random
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
COMFYUI_API_KEY = os.getenv("COMFYUI_API_KEY")
COMFYUI_BASE_URL = "https://cloud.comfy.org/api"
HEADERS = {
    "X-API-Key": COMFYUI_API_KEY,
    "Content-Type": "application/json"
}

# ============================================================
# PASO 1: Generar imágenes con FLUX y descargarlas
# ============================================================
def generate_and_download_images(scenes: list, output_dir: Path) -> list:
    """
    Genera imágenes con FLUX Krea Dev y las descarga una por una.
    """
    import httpx
    
    output_dir.mkdir(parents=True, exist_ok=True)
    workflow_path = BASE_DIR / "config" / "flux1_krea_dev_api.json"
    
    with open(workflow_path, "r", encoding="utf-8") as f:
        base_workflow = json.load(f)
    
    downloaded = []
    
    for scene in scenes:
        num = scene.get("scene_number", 0)
        prompt = scene.get("prompt", "")
        img_path = output_dir / f"scene_{num:04d}.png"
        
        # Si ya existe, saltar
        if img_path.exists() and img_path.stat().st_size > 1000:
            print(f"   ⏭️  Escena {num}: ya existe ({img_path.stat().st_size // 1024}KB)")
            downloaded.append(img_path)
            continue
        
        # Clonar workflow e inyectar datos
        import copy
        nodes = copy.deepcopy(base_workflow)
        
        cinematic_prompt = f"Highly realistic cinematic film still, masterpiece, 8k resolution. {prompt}"
        nodes["200:195"]["inputs"]["text"] = cinematic_prompt
        nodes["200:197"]["inputs"]["seed"] = random.randint(100000000000000, 999999999999999)
        nodes["200:196"]["inputs"]["width"] = 1344
        nodes["200:196"]["inputs"]["height"] = 768
        nodes["9"]["inputs"]["filename_prefix"] = f"scene_{num:04d}"
        
        payload = {"prompt": nodes}
        
        print(f"   🚀 Escena {num}: enviando a FLUX Krea Dev...")
        
        try:
            with httpx.Client(timeout=60.0) as client:
                # Enviar
                resp = client.post(
                    f"{COMFYUI_BASE_URL}/prompt",
                    headers=HEADERS,
                    json=payload
                )
                
                if resp.status_code != 200:
                    print(f"   ❌ Escena {num}: Error HTTP {resp.status_code} - {resp.text[:150]}")
                    continue
                    
                prompt_id = resp.json().get("prompt_id", "")
                print(f"   ⏳ Escena {num}: encolada ({prompt_id[:8]}...), esperando...")
                
                # Polling hasta que termine
                import time
                for attempt in range(60):  # Max 5 min
                    time.sleep(5)
                    
                    hist = client.get(
                        f"{COMFYUI_BASE_URL}/history/{prompt_id}",
                        headers=HEADERS
                    )
                    
                    if hist.status_code != 200:
                        continue
                    
                    data = hist.json()
                    if prompt_id not in data:
                        continue
                    
                    entry = data[prompt_id]
                    status_info = entry.get("status", {})
                    
                    if status_info.get("status_str") == "error":
                        print(f"   ❌ Escena {num}: error en generación")
                        break
                    
                    if not status_info.get("completed", False):
                        if attempt % 6 == 5:
                            print(f"   ⏳ Escena {num}: aún procesando ({(attempt+1)*5}s)...")
                        continue
                    
                    # Completado! Descargar imagen
                    outputs = entry.get("outputs", {})
                    for node_id, node_out in outputs.items():
                        if "images" in node_out:
                            for img_info in node_out["images"]:
                                filename = img_info.get("filename", "")
                                subfolder = img_info.get("subfolder", "")
                                
                                dl = client.get(
                                    f"{COMFYUI_BASE_URL}/view",
                                    headers=HEADERS,
                                    params={
                                        "filename": filename,
                                        "subfolder": subfolder,
                                        "type": "output"
                                    }
                                )
                                
                                if dl.status_code == 200:
                                    with open(img_path, "wb") as f:
                                        f.write(dl.content)
                                    size_kb = img_path.stat().st_size // 1024
                                    print(f"   ✅ Escena {num}: descargada ({size_kb}KB)")
                                    downloaded.append(img_path)
                                else:
                                    print(f"   ❌ Escena {num}: error descargando ({dl.status_code})")
                    break
                else:
                    print(f"   ❌ Escena {num}: timeout (5 min)")
                    
        except Exception as e:
            print(f"   ❌ Escena {num}: {e}")
    
    return downloaded


# ============================================================
# PASO 2: Ken Burns Effect con FFmpeg
# ============================================================
def apply_ken_burns(img_path: Path, output_path: Path, duration: int = 5, 
                    effect: str = "auto") -> bool:
    """
    Aplica efecto Ken Burns (zoom + pan lento) a una imagen estática.
    Genera un clip de video de 5 segundos a 30fps.
    
    Effects:
        - zoom_in: zoom lento hacia el centro
        - zoom_out: empieza con zoom y se aleja
        - pan_left: paneo suave de derecha a izquierda
        - pan_right: paneo suave de izquierda a derecha
        - auto: selecciona aleatoriamente
    """
    if effect == "auto":
        effect = random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right"])
    
    fps = 30
    total_frames = duration * fps  # 150 frames
    
    # Todas las variaciones producen video 1920x1080 (YouTube Full HD)
    if effect == "zoom_in":
        # Zoom suave: rampa lineal de 100% a 120% (sin temblor)
        zoompan = (
            f"zoompan=z='1+0.2*on/{total_frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s=1920x1080:fps={fps}"
        )
    elif effect == "zoom_out":
        # Zoom out suave: rampa lineal de 130% a 100%
        zoompan = (
            f"zoompan=z='1.3-0.3*on/{total_frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={total_frames}:s=1920x1080:fps={fps}"
        )
    elif effect == "pan_left":
        # Paneo de derecha a izquierda
        zoompan = (
            f"zoompan=z='1.15':x='iw-iw/zoom-on*(iw-iw/zoom)/{total_frames}'"
            f":y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
        )
    elif effect == "pan_right":
        # Paneo de izquierda a derecha
        zoompan = (
            f"zoompan=z='1.15':x='on*(iw-iw/zoom)/{total_frames}'"
            f":y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
        )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(img_path),
        "-vf", zoompan,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "18",
        "-t", str(duration),
        str(output_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0 and output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"   🎬 {output_path.name}: {effect} ({size_mb:.1f}MB)")
            return True
        else:
            print(f"   ❌ FFmpeg error: {result.stderr[-200:]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ FFmpeg timeout")
        return False


def process_scenes_kenburns(images_dir: Path, videos_dir: Path) -> list:
    """
    Procesa todas las imágenes de una carpeta y genera clips con Ken Burns.
    """
    videos_dir.mkdir(parents=True, exist_ok=True)
    
    images = sorted(images_dir.glob("scene_*.png"))
    
    if not images:
        print("❌ No se encontraron imágenes scene_XXXX.png")
        return []
    
    print(f"\n🎬 Aplicando Ken Burns a {len(images)} imágenes...")
    print("=" * 60)
    
    # Secuencia de efectos cinematográficos variados
    effects_cycle = ["zoom_in", "pan_right", "zoom_out", "pan_left"]
    
    generated = []
    for i, img in enumerate(images):
        effect = effects_cycle[i % len(effects_cycle)]
        out_path = videos_dir / img.name.replace(".png", ".mp4")
        
        if out_path.exists() and out_path.stat().st_size > 10000:
            print(f"   ⏭️  {out_path.name}: ya existe")
            generated.append(out_path)
            continue
        
        success = apply_ken_burns(img, out_path, duration=5, effect=effect)
        if success:
            generated.append(out_path)
    
    print(f"\n✅ {len(generated)}/{len(images)} clips generados")
    return generated


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    import re
    
    if len(sys.argv) < 2:
        print("Uso: python download_and_kenburns.py <ruta_al_FULL_json> [--skip-download]")
        sys.exit(1)
    
    json_path = Path(sys.argv[1])
    skip_download = "--skip-download" in sys.argv
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    scenes = data.get("video_scenes", [])
    if not scenes:
        print("❌ No se encontraron escenas")
        sys.exit(1)
    
    # Directorio del proyecto
    raw_title = data.get("topic", "video_sin_titulo")
    if "seo_metadata" in data and "title" in data["seo_metadata"]:
        raw_title = data["seo_metadata"]["title"]
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title.replace(" ", "_"))
    
    images_dir = BASE_DIR / "output" / "videos" / safe_title / "clips"
    videos_dir = BASE_DIR / "output" / "videos" / safe_title / "kenburns"
    
    print("=" * 60)
    print("🏭 CONTENT FACTORY — Pipeline Híbrido FLUX + Ken Burns")
    print("=" * 60)
    
    # PROCESAR TODAS LAS ESCENAS
    test_scenes = scenes
    print(f"📦 Procesando todas las escenas: {len(test_scenes)}")
    
    # PASO 1: Generar y descargar imágenes
    if not skip_download:
        print(f"\n📸 PASO 1: Generando imágenes con FLUX Krea Dev...")
        downloaded = generate_and_download_images(test_scenes, images_dir)
        print(f"   Total descargadas: {len(downloaded)}")
    else:
        print("\n⏭️  PASO 1: Saltando descarga (--skip-download)")
    
    # PASO 2: Ken Burns
    print(f"\n🎥 PASO 2: Aplicando Ken Burns Effect...")
    clips = process_scenes_kenburns(images_dir, videos_dir)
    
    print(f"\n{'=' * 60}")
    print(f"🏆 PIPELINE COMPLETO")
    print(f"   📸 Imágenes: {images_dir}")
    print(f"   🎬 Videos:   {videos_dir}")
    print(f"{'=' * 60}")
