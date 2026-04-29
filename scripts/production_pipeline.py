"""
Content Factory - Pipeline de Producción Completo
FLUX Krea Dev → Descarga automática → Ken Burns Effect
Procesa TODAS las escenas del guion.
"""
import os, json, time, random, subprocess, copy, re, sys
from pathlib import Path
import httpx
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("COMFYUI_API_KEY")
BASE = "https://cloud.comfy.org/api"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
BASE_DIR = Path(__file__).parent.parent


def generate_image(client, nodes_template, prompt, scene_num):
    """Envía una imagen a FLUX Krea Dev y retorna prompt_id."""
    nodes = copy.deepcopy(nodes_template)
    nodes["200:195"]["inputs"]["text"] = f"Highly realistic cinematic film still, masterpiece, 8k resolution. {prompt}"
    nodes["200:197"]["inputs"]["seed"] = random.randint(100000000000000, 999999999999999)
    nodes["200:196"]["inputs"]["width"] = 1344
    nodes["200:196"]["inputs"]["height"] = 768
    nodes["9"]["inputs"]["filename_prefix"] = f"scene_{scene_num:04d}"
    
    resp = client.post(f"{BASE}/prompt", headers=HEADERS, json={"prompt": nodes})
    if resp.status_code == 200:
        return resp.json()["prompt_id"]
    else:
        print(f"   ❌ HTTP {resp.status_code}: {resp.text[:100]}")
        return None


def wait_and_download(client, prompt_id, img_path, max_wait=300):
    """Poll /jobs/ hasta completar y descargar imagen."""
    for attempt in range(max_wait // 5):
        time.sleep(5)
        try:
            jr = client.get(f"{BASE}/jobs/{prompt_id}", headers=HEADERS)
            if jr.status_code != 200:
                continue
            
            job = jr.json()
            status = job.get("status", "unknown")
            
            if status == "completed":
                outputs = job.get("outputs", {})
                for node_id, node_out in outputs.items():
                    if isinstance(node_out, dict) and "images" in node_out:
                        for img_info in node_out["images"]:
                            fname = img_info.get("filename", "")
                            subfolder = img_info.get("subfolder", "")
                            dl = client.get(
                                f"{BASE}/view", headers=HEADERS,
                                params={"filename": fname, "subfolder": subfolder, "type": "output"}
                            )
                            if dl.status_code == 200 and len(dl.content) > 1000:
                                with open(img_path, "wb") as f:
                                    f.write(dl.content)
                                return True
                return False
                
            elif status in ("failed", "error"):
                return False
            else:
                if attempt % 12 == 11:
                    print(f"   ⏳ aún procesando ({(attempt+1)*5}s)...")
        except Exception as e:
            if attempt % 12 == 11:
                print(f"   ⚠️  {e}")
    return False


def apply_ken_burns(img_path, vid_path, effect, duration=5):
    """Aplica efecto Ken Burns con FFmpeg."""
    fps = 30
    tf = duration * fps
    
    effects_map = {
        "zoom_in": f"zoompan=z='min(zoom+0.0013,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={tf}:s=1920x1080:fps={fps}",
        "zoom_out": f"zoompan=z='if(eq(on,1),1.3,max(zoom-0.002,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={tf}:s=1920x1080:fps={fps}",
        "pan_left": f"zoompan=z='1.15':x='iw-iw/zoom-on*(iw-iw/zoom)/{tf}':y='ih/2-(ih/zoom/2)':d={tf}:s=1920x1080:fps={fps}",
        "pan_right": f"zoompan=z='1.15':x='on*(iw-iw/zoom)/{tf}':y='ih/2-(ih/zoom/2)':d={tf}:s=1920x1080:fps={fps}",
        "pan_up": f"zoompan=z='1.15':x='iw/2-(iw/zoom/2)':y='ih-ih/zoom-on*(ih-ih/zoom)/{tf}':d={tf}:s=1920x1080:fps={fps}",
        "pan_down": f"zoompan=z='1.15':x='iw/2-(iw/zoom/2)':y='on*(ih-ih/zoom)/{tf}':d={tf}:s=1920x1080:fps={fps}",
    }
    
    zoompan = effects_map.get(effect, effects_map["zoom_in"])
    
    cmd = [
        "ffmpeg", "-y", "-i", str(img_path),
        "-vf", zoompan,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-preset", "medium", "-crf", "18", "-t", str(duration),
        str(vid_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.returncode == 0 and vid_path.exists()


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python production_pipeline.py <ruta_al_FULL_json>")
        sys.exit(1)
    
    json_path = Path(sys.argv[1])
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
    
    images_dir = BASE_DIR / "output" / "videos" / safe_title / "images"
    videos_dir = BASE_DIR / "output" / "videos" / safe_title / "kenburns"
    images_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)
    
    # Cargar workflow base
    workflow_path = BASE_DIR / "config" / "flux1_krea_dev_api.json"
    with open(workflow_path, "r", encoding="utf-8") as f:
        base_workflow = json.load(f)
    
    # Ciclo de efectos variados
    effects = ["zoom_in", "pan_right", "zoom_out", "pan_left", "pan_down", "pan_up"]
    
    print("=" * 60)
    print("🏭 CONTENT FACTORY — Producción Completa")
    print("=" * 60)
    print(f"   📖 {raw_title}")
    print(f"   🎬 {len(scenes)} escenas")
    print(f"   📸 {images_dir}")
    print(f"   🎥 {videos_dir}")
    print("=" * 60)
    
    stats = {"generated": 0, "skipped": 0, "failed": 0, "kenburns": 0}
    start_time = time.time()
    
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        for i, scene in enumerate(scenes):
            num = scene["scene_number"]
            prompt = scene["prompt"]
            img_path = images_dir / f"scene_{num:04d}.png"
            vid_path = videos_dir / f"scene_{num:04d}.mp4"
            effect = effects[(num - 1) % len(effects)]
            
            progress = f"[{i+1}/{len(scenes)}]"
            
            # === IMAGEN ===
            if img_path.exists() and img_path.stat().st_size > 5000:
                stats["skipped"] += 1
            else:
                print(f"\n{progress} 🚀 Escena {num}: generando imagen...")
                pid = generate_image(client, base_workflow, prompt, num)
                
                if pid:
                    ok = wait_and_download(client, pid, img_path)
                    if ok:
                        kb = img_path.stat().st_size // 1024
                        stats["generated"] += 1
                        print(f"{progress} ✅ Escena {num}: imagen OK ({kb}KB)")
                    else:
                        stats["failed"] += 1
                        print(f"{progress} ❌ Escena {num}: fallo descarga")
                        continue
                else:
                    stats["failed"] += 1
                    continue
            
            # === KEN BURNS ===
            if vid_path.exists() and vid_path.stat().st_size > 10000:
                pass  # Ya existe
            elif img_path.exists():
                ok = apply_ken_burns(img_path, vid_path, effect)
                if ok:
                    mb = vid_path.stat().st_size / (1024*1024)
                    stats["kenburns"] += 1
                    print(f"{progress} 🎬 Escena {num}: {effect} ({mb:.1f}MB)")
                else:
                    print(f"{progress} ❌ Escena {num}: Ken Burns falló")
            
            # Progreso cada 10 escenas
            if (i + 1) % 10 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed * 60
                eta = (len(scenes) - i - 1) / rate if rate > 0 else 0
                print(f"\n📊 Progreso: {i+1}/{len(scenes)} ({rate:.1f} escenas/min, ETA: {eta:.0f} min)")
    
    elapsed_total = (time.time() - start_time) / 60
    
    print(f"\n{'='*60}")
    print(f"🏆 PRODUCCIÓN FINALIZADA ({elapsed_total:.1f} min)")
    print(f"{'='*60}")
    print(f"   ✅ Generadas: {stats['generated']}")
    print(f"   ⏭️  Existentes: {stats['skipped']}")
    print(f"   ❌ Fallidas: {stats['failed']}")
    print(f"   🎬 Ken Burns: {stats['kenburns']}")
    print(f"   📸 {images_dir}")
    print(f"   🎥 {videos_dir}")
    print(f"{'='*60}")
