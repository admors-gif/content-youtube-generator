"""
Content Factory - Generador de Narración (TTS)
Convierte el guion JSON a audio usando OpenAI TTS (Voz Onyx)
"""
import os
import sys
import json
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY no encontrada en .env")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_tts_for_scene(text: str, output_path: Path):
    """Genera audio para una sola escena usando OpenAI TTS."""
    if output_path.exists() and output_path.stat().st_size > 1000:
        return True, "Existente"
        
    try:
        response = client.audio.speech.create(
            model="tts-1",      # tts-1 es más rápido y barato, tts-1-hd es calidad estudio
            voice="onyx",       # Onyx es ideal para documentales profundos
            input=text
        )
        response.stream_to_file(output_path)
        return True, "Generado"
    except Exception as e:
        return False, str(e)


if __name__ == "__main__":
    import re
    
    if len(sys.argv) < 2:
        print("Uso: python generate_audio.py <ruta_al_FULL_json>")
        sys.exit(1)
        
    json_path = Path(sys.argv[1])
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    scenes = data.get("video_scenes", [])
    if not scenes:
        print("❌ No se encontraron escenas en el JSON")
        sys.exit(1)
        
    # Obtener el nombre del proyecto
    raw_title = data.get("topic", "video_sin_titulo")
    if "seo_metadata" in data and "title" in data["seo_metadata"]:
        raw_title = data["seo_metadata"]["title"]
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title.replace(" ", "_"))
    
    # Crear carpeta para los audios
    audio_dir = BASE_DIR / "output" / "videos" / safe_title / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🎙️ CONTENT FACTORY — Generación de Narración (OpenAI TTS)")
    print("=" * 60)
    print(f"   📖 Proyecto: {safe_title}")
    print(f"   🗣️ Voz: Onyx (Documental)")
    print(f"   🎬 Total Escenas: {len(scenes)}")
    print("=" * 60)
    
    stats = {"generados": 0, "existentes": 0, "errores": 0}
    start_time = time.time()
    
    for i, scene in enumerate(scenes):
        num = scene.get("scene_number", i + 1)
        text = scene.get("narration", "")
        
        # Ignorar si no hay narración o es un indicador visual tipo [Pausa]
        if not text or text.strip().startswith("[") and text.strip().endswith("]"):
            print(f"[{num}/{len(scenes)}] ⏭️ Sin narración válida, saltando.")
            continue
            
        audio_path = audio_dir / f"scene_{num:04d}.mp3"
        
        success, msg = generate_tts_for_scene(text, audio_path)
        
        if success and msg == "Generado":
            stats["generados"] += 1
            print(f"[{num}/{len(scenes)}] ✅ Generado: {audio_path.name}")
        elif success and msg == "Existente":
            stats["existentes"] += 1
            print(f"[{num}/{len(scenes)}] ⏭️ Ya existe: {audio_path.name}")
        else:
            stats["errores"] += 1
            print(f"[{num}/{len(scenes)}] ❌ Error: {msg}")
            
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"🏁 AUDIO FINALIZADO ({elapsed:.1f} seg)")
    print(f"   ✅ Generados:  {stats['generados']}")
    print(f"   ⏭️ Existentes: {stats['existentes']}")
    print(f"   ❌ Errores:    {stats['errores']}")
    print(f"   📁 Ruta:       {audio_dir}")
    print(f"{'='*60}")
