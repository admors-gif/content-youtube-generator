"""
Content Factory - Máquina 5: Ensamblador Híbrido (FFmpeg)
Une los clips de video generados por ComfyUI y aplica efecto Ken Burns (Zoom) 
a las imágenes estáticas para crear un video continuo.
"""
import os
import json
import subprocess
import sys
from pathlib import Path

# ============================================================
# CONFIGURACIÓN
# ============================================================
BASE_DIR = Path(__file__).parent.parent

def run_ffmpeg(command: list):
    """Ejecuta un comando de FFmpeg de forma segura."""
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en FFmpeg: {e.stderr.decode('utf-8', errors='ignore')}")
        sys.exit(1)

def assemble_hybrid_video(json_path: Path):
    """
    Lee el guion JSON y busca los clips de video (o imágenes) correspondientes.
    Si encuentra un .mp4, lo usa. Si encuentra un .png/.jpg, le aplica Zoom (Ken Burns).
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    scenes = data.get("video_scenes", [])
    if not scenes:
        print("❌ No se encontraron escenas en el JSON.")
        return
        
    import re
    raw_title = data.get("topic", "video_sin_titulo")
    if "seo_metadata" in data and "title" in data["seo_metadata"]:
        raw_title = data["seo_metadata"]["title"]
        
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title.replace(" ", "_"))
    project_dir = BASE_DIR / "output" / "videos" / safe_title
    clips_dir = project_dir / "clips"
    final_output = project_dir / f"{safe_title}_FINAL.mp4"
    
    print(f"🎬 Iniciando Ensamblador Híbrido para: {safe_title}")
    
    # Archivo temporal para la lista de FFmpeg
    list_file_path = project_dir / "concat_list.txt"
    
    valid_clips_count = 0
    with open(list_file_path, "w", encoding="utf-8") as list_file:
        for scene in scenes:
            num = scene.get("scene_number")
            video_path = clips_dir / f"scene_{num:04d}.mp4"
            image_path_jpg = clips_dir / f"scene_{num:04d}.jpg"
            image_path_png = clips_dir / f"scene_{num:04d}.png"
            
            clip_to_add = None
            
            # 1. Priorizar Video
            if video_path.exists():
                clip_to_add = video_path
                print(f"   🎥 Escena {num}: Video detectado.")
            
            # 2. Truco Híbrido: Si hay imagen, animarla con Ken Burns (Zoom in)
            elif image_path_jpg.exists() or image_path_png.exists():
                img_path = image_path_jpg if image_path_jpg.exists() else image_path_png
                print(f"   🖼️ Escena {num}: Imagen detectada. Generando video con efecto Zoom (Ken Burns)...")
                
                animated_video_path = clips_dir / f"scene_{num:04d}_animated.mp4"
                
                if not animated_video_path.exists():
                    # Comando FFmpeg para efecto Ken Burns (Zoom in suave de 5 segundos)
                    # Escala de 1 a 1.15 a lo largo de 5 segundos a 24 fps
                    ffmpeg_cmd = [
                        "ffmpeg", "-y", "-loop", "1", "-i", str(img_path),
                        "-vf", "zoompan=z='min(zoom+0.0015,1.15)':d=120:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',framerate=24",
                        "-c:v", "libx264", "-t", "5", "-pix_fmt", "yuv420p",
                        str(animated_video_path)
                    ]
                    run_ffmpeg(ffmpeg_cmd)
                
                clip_to_add = animated_video_path
            else:
                print(f"   ⚠️  Escena {num}: No se encontró ni video ni imagen. Saltando...")
            
            if clip_to_add:
                # Escribir en la lista de concatenación formato FFmpeg
                # Nota: FFmpeg requiere rutas absolutas escapadas o relativas correctas
                # Usaremos rutas limpias cambiando \ por / para evitar problemas
                clean_path = str(clip_to_add.absolute()).replace('\\', '/')
                list_file.write(f"file '{clean_path}'\n")
                valid_clips_count += 1
                
    if valid_clips_count == 0:
        print("❌ No hay clips válidos para unir. Abortando.")
        return

    print(f"\n🔄 Uniendo {valid_clips_count} clips en un solo archivo...")
    
    # Unir todos los clips (Concatenación sin recodificar si son iguales)
    # Al mezclar Wan 2.2 y zoompan, lo ideal sería asegurarse que ambos tienen misma resolución.
    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file_path),
        "-c", "copy",
        str(final_output)
    ]
    
    run_ffmpeg(concat_cmd)
    
    print(f"✅ ¡Video final ensamblado con éxito!")
    print(f"📁 Ruta: {final_output}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ffmpeg_assembler.py <ruta_al_FULL_json>")
        sys.exit(1)
        
    json_target = Path(sys.argv[1])
    assemble_hybrid_video(json_target)
