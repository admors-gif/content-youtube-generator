"""Diagnóstico exhaustivo - encontrar el método correcto de polling en ComfyUI Cloud"""
import os, json, httpx, asyncio
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("COMFYUI_API_KEY")
BASE = "https://cloud.comfy.org/api"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

print("🔍 Buscando endpoints que funcionen...")

# Enviar un prompt de prueba simple para obtener un prompt_id real
workflow_path = r"C:\Users\admor\Downloads\Content You tube Generator\config\flux1_krea_dev_api.json"
with open(workflow_path, "r", encoding="utf-8") as f:
    nodes = json.load(f)

# Prompt simple
nodes["200:195"]["inputs"]["text"] = "A single red rose on a white background, studio photography"
nodes["200:196"]["inputs"]["width"] = 512
nodes["200:196"]["inputs"]["height"] = 512

with httpx.Client(timeout=30.0, follow_redirects=True) as client:
    # 1. Enviar prompt
    resp = client.post(f"{BASE}/prompt", headers=HEADERS, json={"prompt": nodes})
    print(f"\n✅ POST /prompt: {resp.status_code}")
    prompt_data = resp.json()
    prompt_id = prompt_data.get("prompt_id", "")
    print(f"   prompt_id: {prompt_id}")
    print(f"   Full response: {json.dumps(prompt_data, indent=2)[:500]}")
    
    # 2. Probar TODOS los posibles endpoints de status/history
    import time
    time.sleep(3)  # Dar tiempo a que empiece
    
    endpoints_to_try = [
        f"/prompt/{prompt_id}",
        f"/history/{prompt_id}",
        f"/history",
        f"/queue",
        f"/v1/prompts/{prompt_id}",
        f"/v1/runs/{prompt_id}",
        f"/v1/history/{prompt_id}",
        f"/runs/{prompt_id}",
        f"/runs",
        f"/status/{prompt_id}",
        f"/job/{prompt_id}",
        f"/jobs/{prompt_id}",
        f"/view",
    ]
    
    for ep in endpoints_to_try:
        try:
            r = client.get(f"{BASE}{ep}", headers=HEADERS)
            icon = "✅" if r.status_code == 200 else ("⚠️" if r.status_code < 500 else "❌")
            body_preview = r.text[:150] if r.status_code != 401 else "401 auth"
            print(f"   {icon} GET {ep}: {r.status_code} → {body_preview}")
        except Exception as e:
            print(f"   ❌ GET {ep}: {e}")

    # 3. Probar WebSocket
    print(f"\n🔌 Probando WebSocket...")
    try:
        import websockets
        print("   websockets disponible")
    except ImportError:
        print("   ❌ websockets no instalado, instalando...")
        import subprocess
        subprocess.run(["pip", "install", "websockets"], capture_output=True)
        print("   ✅ websockets instalado")

# 4. Probar websocket connection
import asyncio
async def test_ws():
    try:
        import websockets
        ws_urls = [
            f"wss://cloud.comfy.org/ws?clientId={prompt_id}",
            f"wss://cloud.comfy.org/api/ws?clientId={prompt_id}",
            f"wss://cloud.comfy.org/ws?api_key={API_KEY}",
        ]
        for url in ws_urls:
            try:
                async with websockets.connect(url, additional_headers={"X-API-Key": API_KEY}, close_timeout=5) as ws:
                    print(f"   ✅ WebSocket conectado: {url[:60]}...")
                    # Esperar un mensaje
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=10)
                        print(f"   📨 Mensaje: {str(msg)[:300]}")
                    except asyncio.TimeoutError:
                        print(f"   ⏰ No mensajes en 10s")
                    return
            except Exception as e:
                print(f"   ❌ WS {url[:50]}...: {type(e).__name__}: {e}")
    except ImportError:
        print("   ❌ No se pudo importar websockets")

asyncio.run(test_ws())

# 5. Intentar descargar directamente con el filename pattern
print(f"\n📥 Intentando descarga directa...")
with httpx.Client(timeout=30.0, follow_redirects=True) as client:
    # Probar con el prefijo que configuramos
    view_params = [
        {"filename": f"scene_0001_00001_.png", "type": "output"},
        {"filename": f"scene_0001_.png", "type": "output"},  
        {"filename": f"flux_krea_00001_.png", "type": "output"},
    ]
    for params in view_params:
        try:
            r = client.get(f"{BASE}/view", headers=HEADERS, params=params)
            print(f"   GET /view {params['filename']}: {r.status_code} ({len(r.content)} bytes)")
            if r.status_code == 200 and len(r.content) > 1000:
                print(f"   ✅ ¡ENCONTRADO! {len(r.content)} bytes")
        except Exception as e:
            print(f"   ❌ {e}")
