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
    
    # 1. Obtener lista de videos para ensamblar
    video_files = sorted([f for f in kenburns_dir.glob("*.mp4")])
    
    if not video_files:
        print("❌ No se encontraron videos mp4 en la carpeta kenburns.")
        sys.exit(1)
    
    print(f"📋 {len(video_files)} clips encontrados.")
    
    # 2. Ensamblar con crossfade (dissolve) entre escenas
    master_visuals = project_dir / "master_visuals.mp4"
    if master_visuals.exists():
        master_visuals.unlink()
    
    CROSSFADE_DURATION = 0.5  # segundos de transición entre escenas
    
    if len(video_files) <= 1:
        # Solo 1 clip, copiar directo
        import shutil
        shutil.copy2(str(video_files[0]), str(master_visuals))
    elif len(video_files) <= 80:
        # Usar xfade para transiciones suaves
        # Obtener duración de cada clip
        durations = []
        for vf in video_files:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(vf)],
                capture_output=True, text=True
            )
            try:
                durations.append(float(probe.stdout.strip()))
            except:
                durations.append(5.0)  # fallback
        
        # Construir filtro xfade encadenado
        n = len(video_files)
        inputs = []
        for vf in video_files:
            safe_path = str(vf.absolute()).replace("\\", "/")
            inputs.extend(["-i", safe_path])
        
        # Calcular offsets acumulativos para cada transición
        filter_parts = []
        offsets = []
        cumulative = 0
        for i in range(n - 1):
            cumulative += durations[i] - CROSSFADE_DURATION
            offsets.append(cumulative)
        
        # Construir cadena de xfade
        if n == 2:
            filter_str = f"[0:v][1:v]xfade=transition=fade:duration={CROSSFADE_DURATION}:offset={offsets[0]},format=yuv420p[v]"
        else:
            # Primer par
            filter_str = f"[0:v][1:v]xfade=transition=fade:duration={CROSSFADE_DURATION}:offset={offsets[0]}[v1];\n"
            # Pares intermedios
            for i in range(2, n - 1):
                prev = f"v{i-1}"
                curr = f"v{i}"
                filter_str += f"[{prev}][{i}:v]xfade=transition=fade:duration={CROSSFADE_DURATION}:offset={offsets[i-1]}[{curr}];\n"
            # Último par
            last_prev = f"v{n-2}"
            filter_str += f"[{last_prev}][{n-1}:v]xfade=transition=fade:duration={CROSSFADE_DURATION}:offset={offsets[n-2]},format=yuv420p[v]"
        
        xfade_cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_str,
            "-map", "[v]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            str(master_visuals)
        ]
        
        print(f"🎞️ Aplicando dissolve ({CROSSFADE_DURATION}s) entre {n} clips...")
        if not run_ffmpeg(xfade_cmd, f"Crossfade dissolve ({n} clips)"):
            # Fallback: concat simple sin crossfade
            print("⚠️ Crossfade falló, usando concat directo...")
            list_file = project_dir / "concat_list.txt"
            with open(list_file, "w", encoding="utf-8") as f:
                for vf in video_files:
                    safe_path = str(vf.absolute()).replace("\\", "/")
                    f.write(f"file '{safe_path}'\n")
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(list_file), "-c", "copy", str(master_visuals)
            ]
            if not run_ffmpeg(concat_cmd, "Concat directo (fallback)"):
                sys.exit(1)
            list_file.unlink()
    else:
        # Demasiados clips para xfade (limitación FFmpeg), usar concat
        list_file = project_dir / "concat_list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for vf in video_files:
                safe_path = str(vf.absolute()).replace("\\", "/")
                f.write(f"file '{safe_path}'\n")
        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", str(master_visuals)
        ]
        if not run_ffmpeg(concat_cmd, "Uniendo clips de video"):
            sys.exit(1)
        list_file.unlink()
        
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
        
    # Limpieza (concat_list ya se borra dentro de cada rama)
        
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"🏆 DOCUMENTAL FINALIZADO ({elapsed:.1f} seg)")
    print(f"   🎥 Archivo Final: {final_video}")
    print(f"{'='*60}")
