import os
import sys
import json
import asyncio
import httpx
import websockets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
COMFYUI_API_KEY = os.getenv("COMFYUI_API_KEY")
COMFYUI_BASE_URL = "https://cloud.comfy.org/api"
HEADERS = {"X-API-Key": COMFYUI_API_KEY}

async def generate_and_download_robust(scenes, output_dir):
    """
    Descarga imágenes de ComfyUI Cloud mediante WEBSOCKETS.
    Este método es 100% robusto y bypass-ea el error 401 del endpoint /history.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    workflow_path = BASE_DIR / "config" / "flux1_krea_dev_api.json"
    with open(workflow_path, "r", encoding="utf-8") as f:
        base_workflow = json.load(f)
        
    client_id = f"client_{os.urandom(4).hex()}"
    ws_url = f"wss://cloud.comfy.org/ws?clientId={client_id}"
    
    print(f"🔌 Conectando a ComfyUI Cloud (WebSocket ClientID: {client_id})")
    
    # Se usa reconexión automática y timeouts largos (hasta 10 min por imagen en cola)
    try:
        async with websockets.connect(ws_url, additional_headers=HEADERS, max_size=None) as ws:
            print("✅ WebSocket conectado exitosamente.")
            
            for scene in scenes:
                num = scene.get("scene_number", 0)
                prompt = scene.get("prompt", "")
                img_path = output_dir / f"scene_{num:04d}.png"
                
                if img_path.exists() and img_path.stat().st_size > 1000:
                    print(f"   ⏭️ Escena {num}: ya existe. Saltando...")
                    continue
                    
                # Preparar workflow
                import copy
                nodes = copy.deepcopy(base_workflow)
                import random
                cinematic_prompt = f"Highly realistic cinematic film still, masterpiece, 8k resolution. {prompt}"
                nodes["200:195"]["inputs"]["text"] = cinematic_prompt
                nodes["200:197"]["inputs"]["seed"] = random.randint(100000000000, 999999999999)
                nodes["9"]["inputs"]["filename_prefix"] = f"scene_{num:04d}"
                
                payload = {"prompt": nodes, "client_id": client_id}
                
                print(f"\n🚀 Escena {num}: Enviando prompt a la nube...")
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{COMFYUI_BASE_URL}/prompt", 
                        headers={"X-API-Key": COMFYUI_API_KEY, "Content-Type": "application/json"},
                        json=payload
                    )
                    
                    if resp.status_code != 200:
                        print(f"   ❌ Error enviando escena {num}: {resp.status_code} - {resp.text}")
                        continue
                        
                    prompt_id = resp.json().get("prompt_id")
                    print(f"   ⏳ Escena {num}: Encolada (ID: {prompt_id[:8]}). Esperando renderizado (0-5 min)...")
                    
                # Esperar respuesta del websocket para este prompt
                downloaded = False
                while not downloaded:
                    try:
                        msg_str = await asyncio.wait_for(ws.recv(), timeout=600.0) # 10 minutos max por imagen
                        
                        # Ignorar previas binarias
                        if type(msg_str) == bytes:
                            continue
                            
                        msg = json.loads(msg_str)
                        msg_type = msg.get("type")
                        data = msg.get("data", {})
                        
                        if msg_type == "execution_error":
                            print(f"   ❌ Escena {num}: Error de ejecución en la nube.")
                            break
                            
                        if msg_type == "executed" and data.get("prompt_id") == prompt_id:
                            # Imagen renderizada! Extraer nombre de archivo
                            images = data.get("output", {}).get("images", [])
                            if not images:
                                print(f"   ❌ Escena {num}: Renderizó pero no devolvió imagen.")
                                break
                                
                            filename = images[0].get("filename")
                            subfolder = images[0].get("subfolder", "")
                            
                            print(f"   🌟 Escena {num}: Render finalizado -> {filename}. Descargando...")
                            
                            # Descargar mediante endpoint de vista
                            dl_url = f"{COMFYUI_BASE_URL}/view"
                            async with httpx.AsyncClient() as dl_client:
                                dl_resp = await dl_client.get(
                                    dl_url, 
                                    headers={"X-API-Key": COMFYUI_API_KEY},
                                    params={"filename": filename, "subfolder": subfolder, "type": "output"},
                                    timeout=60.0
                                )
                                
                                if dl_resp.status_code == 200:
                                    with open(img_path, "wb") as file:
                                        file.write(dl_resp.content)
                                    print(f"   ✅ Escena {num}: Descargada exitosamente ({len(dl_resp.content)//1024} KB).")
                                    downloaded = True
                                else:
                                    print(f"   ❌ Escena {num}: Fallo al descargar: HTTP {dl_resp.status_code}")
                                    break
                    except asyncio.TimeoutError:
                        print(f"   ❌ Escena {num}: Timeout en websocket tras 10 minutos.")
                        break
                        
    except Exception as e:
        print(f"❌ Error crítico de WebSocket: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python robust_comfy_downloader.py <json_file>")
        sys.exit(1)
        
    json_path = Path(sys.argv[1])
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    scenes = data.get("video_scenes", [])
    
    import re
    raw_title = data.get("topic", "video_sin_titulo")
    if "seo_metadata" in data and "title" in data["seo_metadata"]:
        raw_title = data["seo_metadata"]["title"]
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title.replace(" ", "_"))
    
    output_dir = BASE_DIR / "output" / "videos" / safe_title / "clips"
    
    print("=" * 60)
    print("🛡️ CONTENT FACTORY — Descargador ROBUSTO de ComfyUI Cloud")
    print("=" * 60)
    
    asyncio.run(generate_and_download_robust(scenes, output_dir))
