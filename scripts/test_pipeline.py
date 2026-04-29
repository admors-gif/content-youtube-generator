"""Prueba rápida: poll /jobs/ endpoint + descarga + Ken Burns"""
import os, json, time, random, subprocess, copy
from pathlib import Path
import httpx
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("COMFYUI_API_KEY")
BASE = "https://cloud.comfy.org/api"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
BASE_DIR = Path(__file__).parent.parent

# Cargar workflow base
workflow_path = BASE_DIR / "config" / "flux1_krea_dev_api.json"
with open(workflow_path, "r", encoding="utf-8") as f:
    base_workflow = json.load(f)

# Cargar escenas
json_path = BASE_DIR / "output" / "scripts" / "FULL_la_vida_cotidiana_en_una_casa_de_samurai_en_edo,_j_20260426_223022.json"
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

scenes = data["video_scenes"][:3]  # Solo 3 de prueba
images_dir = BASE_DIR / "output" / "videos" / "samurai_test" / "images"
videos_dir = BASE_DIR / "output" / "videos" / "samurai_test" / "kenburns"
images_dir.mkdir(parents=True, exist_ok=True)
videos_dir.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("🏭 PIPELINE COMPLETO: FLUX → Descarga → Ken Burns")
print("=" * 60)

with httpx.Client(timeout=120.0, follow_redirects=True) as client:
    for scene in scenes:
        num = scene["scene_number"]
        prompt = scene["prompt"]
        img_path = images_dir / f"scene_{num:04d}.png"
        vid_path = videos_dir / f"scene_{num:04d}.mp4"
        
        # Skip si ya existe
        if img_path.exists() and img_path.stat().st_size > 5000:
            print(f"\n⏭️  Escena {num}: imagen ya existe")
        else:
            # === PASO 1: Enviar a FLUX ===
            nodes = copy.deepcopy(base_workflow)
            nodes["200:195"]["inputs"]["text"] = f"Highly realistic cinematic film still, masterpiece, 8k resolution. {prompt}"
            nodes["200:197"]["inputs"]["seed"] = random.randint(100000000000000, 999999999999999)
            nodes["200:196"]["inputs"]["width"] = 1344
            nodes["200:196"]["inputs"]["height"] = 768
            nodes["9"]["inputs"]["filename_prefix"] = f"scene_{num:04d}"
            
            print(f"\n🚀 Escena {num}: enviando...")
            resp = client.post(f"{BASE}/prompt", headers=HEADERS, json={"prompt": nodes})
            
            if resp.status_code != 200:
                print(f"   ❌ Error: {resp.status_code} {resp.text[:100]}")
                continue
            
            prompt_id = resp.json()["prompt_id"]
            print(f"   📋 Job ID: {prompt_id[:12]}...")
            
            # === PASO 2: Poll /jobs/ hasta completar ===
            for attempt in range(120):  # max 10 min
                time.sleep(5)
                
                try:
                    jr = client.get(f"{BASE}/jobs/{prompt_id}", headers=HEADERS)
                    if jr.status_code != 200:
                        continue
                    
                    job = jr.json()
                    status = job.get("status", "unknown")
                    
                    if status == "completed":
                        print(f"   ✅ Completado!")
                        
                        # Extraer info de output
                        outputs = job.get("outputs", {})
                        print(f"   📦 Outputs keys: {list(outputs.keys())}")
                        print(f"   📦 Full job keys: {list(job.keys())}")
                        
                        # Buscar el filename en los outputs
                        downloaded = False
                        
                        # Intentar extraer de outputs
                        for node_id, node_out in outputs.items():
                            if isinstance(node_out, dict) and "images" in node_out:
                                for img_info in node_out["images"]:
                                    fname = img_info.get("filename", "")
                                    subfolder = img_info.get("subfolder", "")
                                    print(f"   📥 Descargando: {fname}")
                                    
                                    dl = client.get(
                                        f"{BASE}/view",
                                        headers=HEADERS,
                                        params={"filename": fname, "subfolder": subfolder, "type": "output"}
                                    )
                                    
                                    if dl.status_code == 200 and len(dl.content) > 1000:
                                        with open(img_path, "wb") as f:
                                            f.write(dl.content)
                                        print(f"   ✅ Guardado: {img_path.name} ({len(dl.content)//1024}KB)")
                                        downloaded = True
                                        break
                            if downloaded:
                                break
                        
                        if not downloaded:
                            # Imprimir estructura completa para debug
                            print(f"   ⚠️  No encontré images en outputs. Estructura:")
                            print(f"   {json.dumps(job, indent=2)[:800]}")
                        break
                        
                    elif status == "failed" or status == "error":
                        print(f"   ❌ Falló: {job.get('error', 'unknown')}")
                        break
                    else:
                        if attempt % 6 == 5:
                            print(f"   ⏳ {status}... ({(attempt+1)*5}s)")
                            
                except Exception as e:
                    print(f"   ⚠️  Poll error: {e}")
            else:
                print(f"   ❌ Timeout (10 min)")
                continue
        
        # === PASO 3: Ken Burns ===
        if img_path.exists() and img_path.stat().st_size > 5000:
            if vid_path.exists() and vid_path.stat().st_size > 10000:
                print(f"   ⏭️  Ken Burns: ya existe")
                continue
            
            effects = ["zoom_in", "pan_right", "zoom_out", "pan_left"]
            effect = effects[(num - 1) % len(effects)]
            fps = 30
            total_frames = 5 * fps
            
            if effect == "zoom_in":
                zoompan = f"zoompan=z='min(zoom+0.0013,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
            elif effect == "zoom_out":
                zoompan = f"zoompan=z='if(eq(on,1),1.3,max(zoom-0.002,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
            elif effect == "pan_left":
                zoompan = f"zoompan=z='1.15':x='iw-iw/zoom-on*(iw-iw/zoom)/{total_frames}':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
            elif effect == "pan_right":
                zoompan = f"zoompan=z='1.15':x='on*(iw-iw/zoom)/{total_frames}':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
            
            cmd = [
                "ffmpeg", "-y", "-i", str(img_path),
                "-vf", zoompan,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "medium", "-crf", "18", "-t", "5",
                str(vid_path)
            ]
            
            print(f"   🎬 Ken Burns ({effect})...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and vid_path.exists():
                mb = vid_path.stat().st_size / (1024*1024)
                print(f"   ✅ Video: {vid_path.name} ({mb:.1f}MB)")
            else:
                print(f"   ❌ FFmpeg error: {result.stderr[-200:]}")

print(f"\n{'='*60}")
print(f"🏆 RESULTADO FINAL")
print(f"   📸 Imágenes: {images_dir}")
print(f"   🎬 Videos:   {videos_dir}")

imgs = list(images_dir.glob("*.png"))
vids = list(videos_dir.glob("*.mp4"))
print(f"   Total imágenes: {len(imgs)}")
print(f"   Total videos:   {len(vids)}")
print(f"{'='*60}")
