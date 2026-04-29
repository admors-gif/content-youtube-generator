"""
Content Factory - Generador de Narración con Google Cloud (Journey Voices)
Genera UN SOLO track de audio a partir del script completo usando Google Cloud TTS.
"""
import os
import sys
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Configurar credenciales de Google
CRED_NAME = "content-factory-tts-494706-0880f6d00a88"
CRED_FILE = BASE_DIR / f"{CRED_NAME}.json"

if not CRED_FILE.exists():
    CRED_FILE = BASE_DIR / CRED_NAME

if not CRED_FILE.exists():
    print(f"❌ No se encontró el archivo de credenciales de Google en {CRED_FILE}")
    sys.exit(1)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CRED_FILE)

from google.cloud import texttospeech

def generate_google_audio(text: str, output_path: Path):
    """Genera audio completo usando Google Cloud TTS dividiendo el texto si es necesario."""
    client = texttospeech.TextToSpeechClient()

    # Configuración de voz (Latinoamericano Masculino - Journey o Neural2)
    # Intentamos primero Journey, si no falla (a veces no está en todas las regiones), 
    # pero Neural2-B es excelente para documentales.
    voice = texttospeech.VoiceSelectionParams(
        language_code="es-US",
        name="es-US-Neural2-A", # Voz femenina profunda, perfecta para historia
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        pitch=-2.0, # Ligeramente grave para voz épica y seductora de documental
        speaking_rate=0.85 # Más lento para generar pausas y expectación
    )

    print("⏳ Enviando guion a Google Cloud TTS (Voz: es-US-Neural2-B)...")
    
    # El límite de Google TTS es de 5000 bytes por request.
    paragraphs = text.split('\n\n')
    temp_files = []
    chunk_text = ""
    chunk_index = 0
    
    for p in paragraphs:
        if len(chunk_text.encode('utf-8')) + len(p.encode('utf-8')) < 4800:
            chunk_text += p + "\n\n"
        else:
            # Generar chunk
            chunk_path = output_path.parent / f"temp_gcp_{chunk_index}.mp3"
            print(f"   -> Generando Parte {chunk_index+1}...")
            
            synthesis_input = texttospeech.SynthesisInput(text=chunk_text.strip())
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            
            with open(chunk_path, "wb") as out:
                out.write(response.audio_content)
                
            temp_files.append(chunk_path)
            chunk_text = p + "\n\n"
            chunk_index += 1
            
    # Último pedazo
    if chunk_text.strip():
        chunk_path = output_path.parent / f"temp_gcp_{chunk_index}.mp3"
        print(f"   -> Generando Parte {chunk_index+1}...")
        synthesis_input = texttospeech.SynthesisInput(text=chunk_text.strip())
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        with open(chunk_path, "wb") as out:
            out.write(response.audio_content)
        temp_files.append(chunk_path)
        
    print("🔗 Uniendo partes de audio de Google...")
    with open(output_path, 'wb') as outfile:
        for tf in temp_files:
            with open(tf, 'rb') as infile:
                outfile.write(infile.read())
            tf.unlink() # Borrar temporal
            
    return True

if __name__ == "__main__":
    import re
    if len(sys.argv) < 2:
        print("Uso: python generate_google_tts.py <ruta_al_FULL_json>")
        sys.exit(1)
        
    json_path = Path(sys.argv[1])
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    script_text = data.get("script_plain", "")
    
    raw_title = data.get("topic", "video_sin_titulo")
    if "seo_metadata" in data and "title" in data["seo_metadata"]:
        raw_title = data["seo_metadata"]["title"]
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title.replace(" ", "_"))
    
    audio_dir = BASE_DIR / "output" / "videos" / safe_title / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = audio_dir / "master_google_narration.mp3"
    
    print("=" * 60)
    print("🎙️ CONTENT FACTORY — Generación con Google Cloud TTS")
    print("=" * 60)
    
    start_time = time.time()
    try:
        success = generate_google_audio(script_text, output_file)
        elapsed = time.time() - start_time
        if success:
            print(f"\n✅ AUDIO GOOGLE GENERADO EXITOSAMENTE ({elapsed:.1f} seg)")
            print(f"   Ruta: {output_file}")
    except Exception as e:
        print(f"\n❌ Error al conectar con Google Cloud: {e}")
        print("Asegúrate de haber 'Habilitado' la API de Cloud Text-to-Speech en la consola de Google.")
    
    print("=" * 60)
