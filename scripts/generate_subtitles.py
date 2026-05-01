"""
Content Factory — Generador de Subtítulos Cinematográficos
Whisper API → ASS Subtitles → FFmpeg burn-in

Genera subtítulos estilo YouTube/TikTok premium:
- Montserrat Extra Bold, grande y legible
- 2-3 palabras a la vez con highlight
- Outline negro + sombra para contraste
- Word-by-word timing via Whisper

Costo: ~$0.006/min audio = ~$0.07 por video de 12 min
"""
import os
import json
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ============================================================
# ESTILOS ASS — Configuración visual de subtítulos
# ============================================================
# Colores en formato ASS: &HBBGGRR (hex, invertido)
STYLE_CONFIG = {
    "font_name": "Montserrat",       # Font moderna y legible
    "font_size": 52,                  # Grande para móvil
    "primary_color": "&H00FFFFFF",    # Blanco
    "highlight_color": "&H0000FFFF",  # Amarillo (para palabra activa)
    "outline_color": "&H00000000",    # Negro
    "shadow_color": "&H80000000",     # Negro semitransparente
    "outline_width": 3,              # Borde grueso
    "shadow_depth": 2,               # Sombra sutil
    "margin_v": 60,                  # Margen inferior
    "bold": -1,                      # Bold activado
}

# Fonts fallback si Montserrat no está instalada
FALLBACK_FONTS = ["Arial", "Helvetica", "DejaVu Sans"]

# Cuántas palabras mostrar a la vez
WORDS_PER_GROUP = 3


def transcribe_with_whisper(audio_path: Path) -> dict:
    """
    Transcribe audio usando OpenAI Whisper API con timestamps de palabra.
    
    Returns:
        dict con 'words' lista de {word, start, end}
    """
    try:
        from openai import OpenAI
    except ImportError:
        print("   [!] openai package no instalado")
        return None
    
    if not OPENAI_API_KEY:
        print("   [!] OPENAI_API_KEY no configurada")
        return None
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    print(f"   🎤 Transcribiendo con Whisper: {audio_path.name}")
    
    # Verificar tamaño (Whisper acepta hasta 25MB)
    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    if file_size_mb > 25:
        print(f"   [!] Archivo demasiado grande ({file_size_mb:.1f}MB > 25MB)")
        print(f"   [!] Dividiendo audio...")
        return transcribe_large_audio(client, audio_path)
    
    try:
        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["word"],
                language="es"
            )
        
        # Extraer palabras con timestamps
        words = []
        if hasattr(response, 'words') and response.words:
            for w in response.words:
                words.append({
                    "word": w.word.strip(),
                    "start": w.start,
                    "end": w.end
                })
        
        print(f"   ✅ Whisper: {len(words)} palabras transcritas")
        print(f"   📝 Duración: {words[-1]['end']:.1f}s" if words else "   ⚠️ Sin palabras")
        
        return {"words": words, "text": response.text if hasattr(response, 'text') else ""}
    
    except Exception as e:
        print(f"   [!] Error Whisper: {e}")
        return None


def transcribe_large_audio(client, audio_path: Path) -> dict:
    """
    Para audios > 25MB: divide en segmentos de 10 minutos y concatena.
    """
    import tempfile
    
    # Obtener duración total
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True
    )
    total_duration = float(probe.stdout.strip())
    
    segment_duration = 600  # 10 minutos
    all_words = []
    offset = 0.0
    segment_num = 0
    
    with tempfile.TemporaryDirectory() as tmpdir:
        while offset < total_duration:
            segment_num += 1
            segment_path = Path(tmpdir) / f"segment_{segment_num}.mp3"
            
            # Extraer segmento
            subprocess.run([
                "ffmpeg", "-y", "-i", str(audio_path),
                "-ss", str(offset), "-t", str(segment_duration),
                "-c:a", "libmp3lame", "-b:a", "128k",
                str(segment_path)
            ], capture_output=True)
            
            if not segment_path.exists():
                break
            
            print(f"      Segmento {segment_num}: {offset:.0f}s - {min(offset + segment_duration, total_duration):.0f}s")
            
            with open(segment_path, "rb") as f:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["word"],
                    language="es"
                )
            
            if hasattr(response, 'words') and response.words:
                for w in response.words:
                    all_words.append({
                        "word": w.word.strip(),
                        "start": w.start + offset,
                        "end": w.end + offset
                    })
            
            offset += segment_duration
    
    print(f"   ✅ Whisper (segmentado): {len(all_words)} palabras en {segment_num} segmentos")
    return {"words": all_words, "text": " ".join(w["word"] for w in all_words)}


def generate_ass_subtitles(words: list, output_path: Path, style: dict = None) -> Path:
    """
    Genera archivo ASS con subtítulos estilizados.
    Agrupa palabras de a WORDS_PER_GROUP para legibilidad.
    
    Args:
        words: Lista de {word, start, end} de Whisper
        output_path: Ruta para guardar el .ass
        style: Configuración visual override
    
    Returns:
        Path al archivo .ass generado
    """
    if not words:
        print("   [!] No hay palabras para generar subtítulos")
        return None
    
    s = style or STYLE_CONFIG
    
    # ── Header ASS ──
    ass_header = f"""[Script Info]
Title: Content Factory Subtitles
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{s['font_name']},{s['font_size']},{s['primary_color']},&H000000FF,{s['outline_color']},{s['shadow_color']},{s['bold']},0,0,0,100,100,1,0,1,{s['outline_width']},{s['shadow_depth']},2,40,40,{s['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    # ── Agrupar palabras ──
    groups = []
    for i in range(0, len(words), WORDS_PER_GROUP):
        group = words[i:i + WORDS_PER_GROUP]
        if not group:
            continue
        
        group_text = " ".join(w["word"] for w in group)
        group_start = group[0]["start"]
        group_end = group[-1]["end"]
        
        # Agregar un pequeño padding temporal para transiciones suaves
        # Mínimo 0.3s de display
        if group_end - group_start < 0.3:
            group_end = group_start + 0.3
        
        groups.append({
            "text": group_text,
            "start": group_start,
            "end": group_end,
            "words": group
        })
    
    # ── Generar eventos ASS ──
    events = []
    for g in groups:
        start_ts = format_ass_time(g["start"])
        end_ts = format_ass_time(g["end"])
        
        # Texto limpio con un sutil fade in/out
        fade = "{\\fad(100,100)}"
        text = f"{fade}{g['text']}"
        
        events.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}")
    
    # ── Escribir archivo ──
    ass_content = ass_header + "\n".join(events) + "\n"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)
    
    print(f"   ✅ Subtítulos ASS: {len(groups)} grupos de texto")
    print(f"   📄 Archivo: {output_path.name}")
    
    return output_path


def format_ass_time(seconds: float) -> str:
    """Convierte segundos a formato ASS: H:MM:SS.CC"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def burn_subtitles(video_path: Path, ass_path: Path, output_path: Path = None) -> Path:
    """
    Quema subtítulos ASS en el video usando FFmpeg.
    
    Args:
        video_path: Video original (FINAL_*.mp4)
        ass_path: Archivo de subtítulos .ass
        output_path: Ruta de salida (default: video_subtitulado.mp4)
    
    Returns:
        Path al video con subtítulos
    """
    if output_path is None:
        # Reemplazar FINAL_ con FINAL_SUB_
        stem = video_path.stem
        if stem.startswith("FINAL_"):
            new_stem = stem.replace("FINAL_", "FINAL_SUB_", 1)
        else:
            new_stem = f"SUB_{stem}"
        output_path = video_path.parent / f"{new_stem}.mp4"
    
    print(f"\n   🔥 Quemando subtítulos en video...")
    print(f"   📹 Input: {video_path.name}")
    print(f"   📝 Subs: {ass_path.name}")
    
    # Normalizar path para FFmpeg en Linux/Docker
    ass_str = str(ass_path.absolute()).replace("\\", "/").replace(":", "\\:")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"ass='{ass_str}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    
    if result.returncode == 0 and output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"   ✅ Video con subtítulos: {output_path.name} ({size_mb:.1f}MB)")
        return output_path
    else:
        # Intento alternativo con subtitles filter (SRT compatible)
        print(f"   ⚠️ ASS filter falló, intentando con método alternativo...")
        print(f"   Error: {result.stderr[:200]}")
        
        cmd_alt = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"subtitles='{ass_str}'",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(output_path)
        ]
        
        result = subprocess.run(cmd_alt, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0 and output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"   ✅ Video con subtítulos (alt): {output_path.name} ({size_mb:.1f}MB)")
            return output_path
        else:
            print(f"   ❌ Error burn-in: {result.stderr[:300]}")
            return None


def add_subtitles_to_video(
    video_path: Path,
    audio_path: Path = None,
    output_path: Path = None,
) -> Path:
    """
    Pipeline completo: Audio → Whisper → ASS → Burn-in
    
    Args:
        video_path: Video final (FINAL_*.mp4)
        audio_path: Audio master (si no se proporciona, extrae del video)
        output_path: Ruta de salida personalizada
    
    Returns:
        Path al video subtitulado
    """
    print("\n" + "=" * 60)
    print("   📝 PASO 5: Generando Subtítulos")
    print("=" * 60)
    
    project_dir = video_path.parent
    
    # 1. Obtener audio
    if audio_path is None or not audio_path.exists():
        # Buscar master_audio en el proyecto
        master_audio = project_dir / "master_audio.mp3"
        if not master_audio.exists():
            # Extraer audio del video
            print("   Extrayendo audio del video...")
            master_audio = project_dir / "_temp_audio.mp3"
            subprocess.run([
                "ffmpeg", "-y", "-i", str(video_path),
                "-vn", "-c:a", "libmp3lame", "-b:a", "128k",
                str(master_audio)
            ], capture_output=True, timeout=120)
        audio_path = master_audio
    
    if not audio_path.exists():
        print("   [!] No se encontró audio para transcribir")
        return None
    
    # 2. Transcribir con Whisper
    result = transcribe_with_whisper(audio_path)
    if not result or not result.get("words"):
        print("   [!] Whisper no devolvió palabras")
        return None
    
    # Guardar transcripción para referencia
    transcript_path = project_dir / "transcript.json"
    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"   💾 Transcripción guardada: {transcript_path.name}")
    
    # 3. Generar ASS
    ass_path = project_dir / "subtitles.ass"
    ass_file = generate_ass_subtitles(result["words"], ass_path)
    if not ass_file:
        return None
    
    # 4. Burn-in
    subtitled_video = burn_subtitles(video_path, ass_file, output_path)
    
    # Cleanup
    temp_audio = project_dir / "_temp_audio.mp3"
    if temp_audio.exists():
        temp_audio.unlink()
    
    return subtitled_video


# ============================================================
# EJECUCIÓN STANDALONE
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""
═══════════════════════════════════════════════════════════════
  📝 Content Factory — Generador de Subtítulos
═══════════════════════════════════════════════════════════════

  Uso:
    python generate_subtitles.py <video.mp4> [opciones]

  Opciones:
    --audio <path>    Audio master (si no, extrae del video)
    --output <path>   Video de salida personalizado

  Ejemplo:
    python generate_subtitles.py FINAL_cinematico_video.mp4
    python generate_subtitles.py FINAL_cinematico_video.mp4 --audio master_audio.mp3
        """)
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    if not video_path.exists():
        print(f"[!] Video no encontrado: {video_path}")
        sys.exit(1)
    
    audio_path = None
    output_path = None
    
    if "--audio" in sys.argv:
        idx = sys.argv.index("--audio")
        if idx + 1 < len(sys.argv):
            audio_path = Path(sys.argv[idx + 1])
    
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = Path(sys.argv[idx + 1])
    
    result = add_subtitles_to_video(video_path, audio_path, output_path)
    
    if result:
        print(f"\n🏆 Video subtitulado listo: {result}")
    else:
        print(f"\n❌ Error generando subtítulos")
        sys.exit(1)
