"""
Content Factory — Máquina de Video Cinemático Luma AI
API directa (sin ComfyUI) = sin overhead de GPU.

Toma imágenes FLUX ya generadas → las convierte en clips de video
con movimiento cinematográfico real usando Luma ray-flash-2.

Costo: ~$0.04-0.08 por clip de 5s (depende del plan)
Ejemplo: 52 escenas = ~$2.08-4.16
"""
import os
import json
import time
import sys
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
LUMA_API_KEY = os.getenv("LUMA_API_KEY")
LUMA_BASE_URL = "https://api.lumalabs.ai/dream-machine/v1"

# Donde servir imágenes temporalmente para que Luma las descargue
# Opción 1: Si tienes un servidor público (VPS), servir desde ahí
# Opción 2: Subir a un bucket temporal (S3, GCS, etc.)
# Opción 3: Usar imgbb o similar como hosting temporal gratuito
TEMP_IMAGE_HOST = os.getenv("TEMP_IMAGE_HOST", "")  # ej: "https://tu-vps.com/temp"


def upload_image_to_temp(image_path: Path) -> str:
    """
    Sube una imagen a un hosting temporal para que Luma pueda accederla.
    Luma requiere URL pública para la imagen de input.
    
    Usa imgbb.com (gratis, 32MB max, no requiere cuenta).
    """
    IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")
    
    if IMGBB_API_KEY:
        # Opción A: imgbb (gratis, 32MB max)
        try:
            import base64
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.imgbb.com/1/upload",
                    data={
                        "key": IMGBB_API_KEY,
                        "image": image_data,
                        "expiration": 3600  # 1 hora, suficiente para Luma
                    }
                )
                
                if response.status_code == 200:
                    url = response.json()["data"]["url"]
                    return url
        except Exception as e:
            print(f"   [!] imgbb upload failed: {e}")
    
    if TEMP_IMAGE_HOST:
        # Opción B: tu propio servidor
        filename = image_path.name
        return f"{TEMP_IMAGE_HOST}/{filename}"
    
    # Opción C: Usar el file:// protocol local (solo para testing)
    print("   [!] No hay hosting de imagenes configurado")
    print("   [!] Configura IMGBB_API_KEY o TEMP_IMAGE_HOST en .env")
    return None


def create_generation(
    image_url: str,
    prompt: str = "Subtle cinematic motion, atmospheric lighting, slow dramatic camera drift",
    model: str = "ray-flash-2",
    aspect_ratio: str = "16:9",
) -> str:
    """
    Crea una generación de video en Luma AI.
    
    Args:
        image_url: URL pública de la imagen de input
        prompt: Prompt de movimiento cinematográfico
        model: Modelo Luma (ray-flash-2 = rápido y barato)
        aspect_ratio: Aspect ratio del video
    
    Returns:
        generation_id si se creó correctamente, None si falló
    """
    headers = {
        "Authorization": f"Bearer {LUMA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "prompt": prompt,
        "model": model,
        "aspect_ratio": aspect_ratio,
        "keyframes": {
            "frame0": {
                "type": "image",
                "url": image_url
            }
        }
    }
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{LUMA_BASE_URL}/generations",
                headers=headers,
                json=payload
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                gen_id = data.get("id", "")
                state = data.get("state", "unknown")
                print(f"      Creada: {gen_id[:12]}... (estado: {state})")
                return gen_id
            else:
                print(f"   [!] Luma error {response.status_code}: {response.text[:200]}")
                return None
                
    except Exception as e:
        print(f"   [!] Luma exception: {e}")
        return None


def poll_generation(generation_id: str, timeout_min: int = 10) -> dict:
    """
    Espera a que una generación de Luma termine.
    
    Returns:
        dict con video URL si completó, None si falló
    """
    headers = {
        "Authorization": f"Bearer {LUMA_API_KEY}",
        "Accept": "application/json"
    }
    
    start = time.time()
    timeout_sec = timeout_min * 60
    
    while (time.time() - start) < timeout_sec:
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{LUMA_BASE_URL}/generations/{generation_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    state = data.get("state", "unknown")
                    
                    if state == "completed":
                        video_url = data.get("assets", {}).get("video", "")
                        return {"video_url": video_url, "data": data}
                    
                    elif state == "failed":
                        reason = data.get("failure_reason", "unknown")
                        print(f"   [!] Luma generation failed: {reason}")
                        return None
                    
                    # Still processing (queued, dreaming, etc.)
                    elapsed = int(time.time() - start)
                    if elapsed % 30 < 5:  # Log cada ~30s
                        print(f"      ... procesando ({state}, {elapsed}s)")
                        
        except Exception as e:
            pass
        
        time.sleep(5)
    
    print(f"   [!] Timeout despues de {timeout_min} min")
    return None


def download_video(video_url: str, output_path: Path) -> bool:
    """Descarga el video generado por Luma."""
    try:
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            response = client.get(video_url)
            
            if response.status_code == 200:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True
            else:
                print(f"   [!] Download error {response.status_code}")
                return False
                
    except Exception as e:
        print(f"   [!] Download exception: {e}")
        return False


def generate_cinematic_clips(
    scenes: list,
    images_dir: Path,
    output_dir: Path,
    skip_existing: bool = True,
    motion_prompts: list = None
) -> dict:
    """
    Convierte imágenes FLUX en clips de video cinematográficos con Luma.
    
    Args:
        scenes: Lista de escenas con scene_number y prompt
        images_dir: Directorio con imágenes FLUX generadas
        output_dir: Directorio para guardar clips de video
        skip_existing: Si True, no regenera clips existentes
        motion_prompts: Lista de prompts de movimiento variados
    
    Returns:
        dict con estadísticas
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Prompts de movimiento cinematográfico variados
    if not motion_prompts:
        motion_prompts = [
            "Slow subtle push in, gentle atmospheric haze movement, physically realistic motion, no morphing or distortion",
            "Smooth lateral dolly right, volumetric light shifts, natural human movement only",
            "Slow pull back revealing scene, dust particles floating, physically grounded camera motion",
            "Gentle tilt up with subtle depth of field shift, realistic lighting transition",
            "Slow orbit left, cinematic lighting flicker, no warping or impossible physics",
            "Static shot with subtle atmospheric movement, smoke wisps, minimal subject motion",
            "Very slow push in, dramatic shadow play, stable and grounded composition",
            "Gentle crane down, atmospheric fog drift, photorealistic motion only",
        ]
    
    stats = {"generated": 0, "skipped": 0, "failed": 0, "no_image": 0}
    
    print("=" * 60)
    print(f"   Luma AI — Clips Cinematicos")
    print("=" * 60)
    print(f"   Modelo: ray-flash-2")
    print(f"   Escenas: {len(scenes)}")
    print(f"   Imagenes: {images_dir}")
    print(f"   Destino: {output_dir}")
    print("=" * 60)
    
    for i, scene in enumerate(scenes):
        num = scene.get("scene_number", i + 1)
        
        img_path = images_dir / f"scene_{num:04d}.png"
        vid_path = output_dir / f"luma_{num:04d}.mp4"
        
        # Skip si ya existe
        if skip_existing and vid_path.exists() and vid_path.stat().st_size > 10000:
            stats["skipped"] += 1
            continue
        
        # Verificar que la imagen existe
        if not img_path.exists():
            stats["no_image"] += 1
            print(f"   [{i+1}/{len(scenes)}] Escena {num}: sin imagen, saltando")
            continue
        
        print(f"\n   [{i+1}/{len(scenes)}] Escena {num}: generando clip...")
        
        # 1. Subir imagen
        image_url = upload_image_to_temp(img_path)
        if not image_url:
            stats["failed"] += 1
            continue
        
        # 2. Crear generación en Luma
        motion = motion_prompts[(num - 1) % len(motion_prompts)]
        scene_context = scene.get("prompt", "")[:100]
        full_prompt = f"{motion}. Scene context: {scene_context}"
        
        gen_id = create_generation(
            image_url=image_url,
            prompt=full_prompt,
            model="ray-flash-2"
        )
        
        if not gen_id:
            stats["failed"] += 1
            continue
        
        # 3. Esperar y descargar
        result = poll_generation(gen_id, timeout_min=10)
        
        if result and result.get("video_url"):
            ok = download_video(result["video_url"], vid_path)
            if ok:
                size_mb = vid_path.stat().st_size / (1024 * 1024)
                stats["generated"] += 1
                print(f"   [{i+1}/{len(scenes)}] Escena {num}: OK ({size_mb:.1f}MB)")
            else:
                stats["failed"] += 1
        else:
            stats["failed"] += 1
        
        # Rate limiting
        time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"   RESUMEN")
    print(f"{'='*60}")
    print(f"   Generados: {stats['generated']}")
    print(f"   Existentes: {stats['skipped']}")
    print(f"   Sin imagen: {stats['no_image']}")
    print(f"   Fallidos: {stats['failed']}")
    print(f"{'='*60}")
    
    return stats


# ============================================================
# EJECUCIÓN STANDALONE
# ============================================================
if __name__ == "__main__":
    import re
    
    if not LUMA_API_KEY:
        print("[!] LUMA_API_KEY no configurada en .env")
        print("    Obtener en: https://lumalabs.ai/dream-machine/api/keys")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Uso: python luma_video.py <ruta_al_FULL_json> [--test]")
        print("")
        print("Opciones:")
        print("  --test    Solo generar escena 1 como prueba de costos")
        sys.exit(1)
    
    json_path = Path(sys.argv[1])
    test_mode = "--test" in sys.argv
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    scenes = data.get("video_scenes", [])
    if not scenes:
        print("[!] No se encontraron escenas")
        sys.exit(1)
    
    # Directorio del proyecto
    raw_title = data.get("topic", "video_sin_titulo")
    if "seo_metadata" in data and "title" in data["seo_metadata"]:
        raw_title = data["seo_metadata"]["title"]
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title.replace(" ", "_"))
    
    images_dir = BASE_DIR / "output" / "videos" / safe_title / "images"
    luma_dir = BASE_DIR / "output" / "videos" / safe_title / "luma_clips"
    
    if test_mode:
        scenes = scenes[:1]
        print(f"\n   MODO TEST — Solo escena 1 (para medir costo)")
    
    if not images_dir.exists():
        print(f"[!] No se encontro directorio de imagenes: {images_dir}")
        print(f"    Primero ejecuta: python production_pipeline.py <json> --images-only")
        sys.exit(1)
    
    generate_cinematic_clips(scenes, images_dir, luma_dir)
