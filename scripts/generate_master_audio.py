"""
Content Factory - Generador de Narración Master (TTS)
Genera UN SOLO track de audio a partir del script completo.
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

def generate_master_audio(text: str, output_path: Path):
    """Genera audio completo usando OpenAI TTS."""
    if output_path.exists() and output_path.stat().st_size > 1000:
        print(f"⏭️ El archivo maestro ya existe: {output_path.name}")
        return True
        
    try:
        print("⏳ Enviando guion completo a OpenAI (Voz: Onyx)...")
        # El límite de OpenAI TTS es 4096 caracteres por request.
        # Si el texto es mayor, debemos partirlo.
        if len(text) <= 4096:
            response = client.audio.speech.create(
                model="tts-1",
                voice="onyx",
                input=text
            )
            response.stream_to_file(output_path)
        else:
            print(f"⚠️ El texto es muy largo ({len(text)} chars). Partiendo en fragmentos...")
            # Partir por dobles saltos de línea (párrafos)
            paragraphs = text.split('\n\n')
            temp_files = []
            
            chunk_text = ""
            chunk_index = 0
            
            for p in paragraphs:
                if len(chunk_text) + len(p) < 4000:
                    chunk_text += p + "\n\n"
                else:
                    # Generar chunk
                    chunk_path = output_path.parent / f"temp_{chunk_index}.mp3"
                    print(f"   -> Generando Parte {chunk_index+1}...")
                    res = client.audio.speech.create(model="tts-1", voice="onyx", input=chunk_text.strip())
                    res.stream_to_file(chunk_path)
                    temp_files.append(chunk_path)
                    
                    chunk_text = p + "\n\n"
                    chunk_index += 1
            
            # Generar el último pedazo
            if chunk_text.strip():
                chunk_path = output_path.parent / f"temp_{chunk_index}.mp3"
                print(f"   -> Generando Parte {chunk_index+1}...")
                res = client.audio.speech.create(model="tts-1", voice="onyx", input=chunk_text.strip())
                res.stream_to_file(chunk_path)
                temp_files.append(chunk_path)
                
            # Unir archivos temporalmente con Python (concatenación binaria básica)
            print("🔗 Uniendo partes de audio...")
            with open(output_path, 'wb') as outfile:
                for tf in temp_files:
                    with open(tf, 'rb') as infile:
                        outfile.write(infile.read())
                    tf.unlink() # Borrar temporal
                    
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    import re
    
    if len(sys.argv) < 2:
        print("Uso: python generate_master_audio.py <ruta_al_FULL_json>")
        sys.exit(1)
        
    json_path = Path(sys.argv[1])
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    script_text = data.get("script_plain", "")
    if not script_text:
        print("❌ No se encontró 'script_plain' en el JSON")
        sys.exit(1)
        
    raw_title = data.get("topic", "video_sin_titulo")
    if "seo_metadata" in data and "title" in data["seo_metadata"]:
        raw_title = data["seo_metadata"]["title"]
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title.replace(" ", "_"))
    
    audio_dir = BASE_DIR / "output" / "videos" / safe_title / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = audio_dir / "master_narration.mp3"
    
    print("=" * 60)
    print("🎙️ CONTENT FACTORY — Generación de Narrador Master")
    print("=" * 60)
    
    start_time = time.time()
    success = generate_master_audio(script_text, output_file)
    elapsed = time.time() - start_time
    
    if success:
        print(f"\n✅ AUDIO MAESTRO GENERADO EXITOSAMENTE ({elapsed:.1f} seg)")
        print(f"   Ruta: {output_file}")
    print("=" * 60)
