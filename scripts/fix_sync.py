"""
Content Factory - Sincronizador Maestro (Time Scale)
Ajusta la duración total del video para que calce milimétricamente con el audio sin re-renderizar.
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def get_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", str(file_path)
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    return float(result.stdout.strip())

def run_ffmpeg(cmd, desc):
    print(f"\n⏳ Ejecutando: {desc}")
    try:
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if process.returncode != 0:
            print(f"❌ Error en FFmpeg ({desc}):")
            print(process.stderr)
            return False
        print(f"✅ Completado: {desc}")
        return True
    except Exception as e:
        print(f"❌ Excepción ejecutando FFmpeg: {e}")
        return False

if __name__ == "__main__":
    import re
    if len(sys.argv) < 2:
        print("Uso: python fix_sync.py <ruta_al_FULL_json>")
        sys.exit(1)
        
    json_path = Path(sys.argv[1])
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    raw_title = data.get("topic", "video_sin_titulo")
    if "seo_metadata" in data and "title" in data["seo_metadata"]:
        raw_title = data["seo_metadata"]["title"]
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title.replace(" ", "_"))
    
    project_dir = BASE_DIR / "output" / "videos" / safe_title
    master_visuals = project_dir / "master_visuals.mp4"
    audio_file = project_dir / "audio" / "master_google_narration.mp3"
    
    if not master_visuals.exists() or not audio_file.exists():
        print("❌ Faltan archivos maestros.")
        sys.exit(1)
        
    print("=" * 60)
    print("🛠️ CONTENT FACTORY — Corrección de Sincronía (Time-Stretch)")
    print("=" * 60)
    
    video_dur = get_duration(master_visuals)
    audio_dur = get_duration(audio_file)
    
    # Calculamos el factor de estiramiento
    scale_factor = audio_dur / video_dur
    
    print(f"   ⏱️ Duración Audio: {audio_dur:.2f} s")
    print(f"   ⏱️ Duración Video Original: {video_dur:.2f} s")
    print(f"   📐 Factor de Ajuste: {scale_factor:.4f}x")
    
    final_synced = project_dir / f"FINAL_SYNCED_{safe_title}.mp4"
    if final_synced.exists():
        final_synced.unlink()
        
    # Usamos -itsscale para alterar el framerate sin recompresión, es instantáneo.
    sync_cmd = [
        "ffmpeg", "-y",
        "-itsscale", str(scale_factor), "-i", str(master_visuals),
        "-i", str(audio_file),
        "-c", "copy",
        str(final_synced)
    ]
    
    start_time = time.time()
    if run_ffmpeg(sync_cmd, "Aplicando Time-Scale y Muxing Audio..."):
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"🎯 SINCRONIZACIÓN PERFECTA LOGRADA ({elapsed:.1f} seg)")
        print(f"   🎥 Nuevo Archivo: {final_synced}")
        print(f"{'='*60}")
