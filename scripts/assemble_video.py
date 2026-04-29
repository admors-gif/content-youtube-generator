"""
Content Factory - Ensamblador Final de Video
Une todos los clips Ken Burns y les sobrepone la pista de audio maestra.
"""
import os
import sys
import json
import time
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def run_ffmpeg(cmd, desc):
    """Ejecuta un comando FFmpeg y maneja la salida."""
    print(f"\n⏳ Ejecutando: {desc}")
    try:
        # Usamos creationflags=subprocess.CREATE_NO_WINDOW si estuviera disponible, pero shell=True funciona bien
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
        print("Uso: python assemble_video.py <ruta_al_FULL_json>")
        sys.exit(1)
        
    json_path = Path(sys.argv[1])
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    raw_title = data.get("topic", "video_sin_titulo")
    if "seo_metadata" in data and "title" in data["seo_metadata"]:
        raw_title = data["seo_metadata"]["title"]
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title.replace(" ", "_"))
    
    project_dir = BASE_DIR / "output" / "videos" / safe_title
    kenburns_dir = project_dir / "kenburns"
    audio_file = project_dir / "audio" / "master_google_narration.mp3"
    
    if not kenburns_dir.exists() or not audio_file.exists():
        print("❌ Faltan archivos. Asegúrate de tener los videos generados y el audio maestro.")
        sys.exit(1)
        
    print("=" * 60)
    print("🎬 CONTENT FACTORY — Ensamblaje Final de Video")
    print("=" * 60)
    
    start_time = time.time()
    
    # 1. Crear lista de videos para concatenar
    list_file = project_dir / "concat_list.txt"
    video_files = sorted([f for f in kenburns_dir.glob("*.mp4")])
    
    if not video_files:
        print("❌ No se encontraron videos mp4 en la carpeta kenburns.")
        sys.exit(1)
        
    with open(list_file, "w", encoding="utf-8") as f:
        for vf in video_files:
            # FFmpeg requiere rutas absolutas escapadas o relativas correctas
            # Usamos forward slashes para evitar problemas en Windows con ffmpeg
            safe_path = str(vf.absolute()).replace("\\", "/")
            f.write(f"file '{safe_path}'\n")
            
    print(f"📋 Lista de concatenación creada con {len(video_files)} clips.")
    
    # 2. Concatenar los videos (Copia directa, ultra rápido, sin perder calidad)
    master_visuals = project_dir / "master_visuals.mp4"
    if master_visuals.exists():
        master_visuals.unlink()
        
    concat_cmd = [
        "ffmpeg", "-y", 
        "-f", "concat", 
        "-safe", "0", 
        "-i", str(list_file), 
        "-c", "copy", 
        str(master_visuals)
    ]
    
    if not run_ffmpeg(concat_cmd, "Uniendo clips de video"):
        sys.exit(1)
        
    # 3. Mezclar Visuales + Audio
    final_video = project_dir / f"FINAL_{safe_title}.mp4"
    if final_video.exists():
        final_video.unlink()
        
    # Mezclamos video y audio. 
    # -c:v copy mantiene el video sin recompresión
    # -c:a aac recompresa el audio a formato estándar de video
    mix_cmd = [
        "ffmpeg", "-y",
        "-i", str(master_visuals),
        "-i", str(audio_file),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        str(final_video)
    ]
    
    if not run_ffmpeg(mix_cmd, "Sincronizando Voz y Video"):
        sys.exit(1)
        
    # Limpieza
    if list_file.exists():
        list_file.unlink()
        
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"🏆 DOCUMENTAL FINALIZADO ({elapsed:.1f} seg)")
    print(f"   🎥 Archivo Final: {final_video}")
    print(f"{'='*60}")
