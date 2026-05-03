"""
Content Factory — Máquina de Narración ElevenLabs
API directa (sin ComfyUI) = más barato, más rápido, más control.

Genera un archivo MP3 de narración completa a partir del guion.
Cada escena se narra por separado para control de timing.

Costo: ~$0.06-0.12 por 1000 caracteres
Ejemplo: guion 52 escenas ≈ 8000 chars = ~$0.48-0.96
"""
import os
import json
import time
import sys
from pathlib import Path
from dotenv import load_dotenv
import httpx

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# ============================================================
# SISTEMA DE 4 VOCES — Content Factory
# ============================================================
#
# 🌑 SALVATORE — Épica, profunda, misteriosa
#    → Misterios, Terror, Psicología Oscura, Biografías,
#      Documentales, Historia, Ciencia
#
# ☀️ LORENZO — Moderna, clara, profesional
#    → Liderazgo, Finanzas, Emprendimiento,
#      Desarrollo Personal
#
# ⚡ DIEGO — Explosiva, impactante, alta energía
#    → Super Motivación, Ventas, Social Media,
#      Redes Sociales, Contenido Viral
#
# 💋 SERAFINA — Sensual, seductora, íntima
#    → Erótico Histórico, Novelas, Romance,
#      Audiobooks Románticos
#
# ============================================================

# Voice IDs de ElevenLabs (Community Library)
VOICE_MAP = {
    # === 4 Voces principales (DOCUMENTALES — usan eleven_multilingual_v2) ===
    "Salvatore": "t3eeeqhBjrUqcrPvDqUn",   # Épica, profunda, misteriosa
    "Lorenzo": "DTGwzA4YLrWB1FAT6Uas",      # Moderna, profesional, clara
    "Diego": "3Y2yr1PdwiaWZ5xxYRed",         # Explosiva, alta energía
    "Serafina": "4tRn1lSkEn13EVTuqb0g",      # Sensual, seductora, íntima
    # === Pre-built (backup) ===
    "Josh": "TxGEqnHWrfWFTfGW9XjX",
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
    # === PODCAST (usan eleven_v3 — soporta audio tags como [exhales] [laughs]) ===
    # Validadas en sesión 2026-05-03: tags interpretados correctamente,
    # ritmo conversacional natural más dinámico que Salvatore/Serafina.
    "Will": "bIHbv24MWmeRgasZH58o",          # Relaxed Optimist — chill conversational
    "Lina": "VmejBeYhbrcTPwDniox7",          # Carefree & Fresh — Colombian podcast voice
}

DEFAULT_VOICE = "Salvatore"

# Mapeo automático: agente → voz óptima
AGENT_VOICE_MAP = {
    # 🌑 Oscuros/Épicos → Salvatore
    "psicologia_oscura": "Salvatore",
    "terror": "Salvatore",
    "misterios": "Salvatore",
    "biografias": "Salvatore",
    "historia": "Salvatore",
    "documentales": "Salvatore",
    "ciencia": "Salvatore",
    # ☀️ Profesionales → Lorenzo
    "finanzas": "Lorenzo",
    "liderazgo": "Lorenzo",
    "emprendimiento": "Lorenzo",
    "desarrollo_personal": "Lorenzo",
    "negocios": "Lorenzo",
    "productividad": "Lorenzo",
    # ⚡ Alta energía → Diego
    "motivacion": "Diego",
    "ventas": "Diego",
    "social_media": "Diego",
    "redes_sociales": "Diego",
    "marketing": "Diego",
    "positivismo": "Diego",
    # 💋 Sensual/Romance → Serafina
    "erotico_historico": "Serafina",
    "erotico": "Serafina",
    "novelas": "Serafina",
    "romance": "Serafina",
    "audiobook_romantico": "Serafina",
}

# Configuración de voz optimizada por estilo
VOICE_SETTINGS = {
    "Salvatore": {
        "stability": 0.55,
        "similarity_boost": 0.85,
        "style": 0.10,
        "speed": 0.88,
    },
    "Lorenzo": {
        "stability": 0.50,
        "similarity_boost": 0.80,
        "style": 0.15,
        "speed": 0.95,
    },
    "Diego": {
        "stability": 0.45,
        "similarity_boost": 0.80,
        "style": 0.20,
        "speed": 1.0,
    },
    "Serafina": {
        "stability": 0.45,
        "similarity_boost": 0.85,
        "style": 0.15,
        "speed": 0.85,
    },
    # === PODCAST V3 voices ===
    # Para eleven_v3: el parámetro `speed` no aplica (v3 controla ritmo
    # con tags y características de la voz). stability más bajo permite
    # mayor expresividad emocional con tags como [exhales]/[laughs].
    "Will": {
        "stability": 0.45,
        "similarity_boost": 0.75,
        "style": 0.0,
        "speed": 1.0,  # ignorado por v3 pero requerido por la firma
    },
    "Lina": {
        "stability": 0.45,
        "similarity_boost": 0.75,
        "style": 0.0,
        "speed": 1.0,  # ignorado por v3
    },
}


def get_voice_id(voice_name: str) -> str:
    """Obtiene el voice_id de ElevenLabs."""
    return VOICE_MAP.get(voice_name, VOICE_MAP[DEFAULT_VOICE])


def get_voice_for_agent(agent_name: str) -> str:
    """Selecciona automáticamente la voz óptima según el agente."""
    # Normalizar nombre del agente
    normalized = agent_name.lower().replace(" ", "_").replace("-", "_")
    # Buscar match exacto o parcial
    for key, voice in AGENT_VOICE_MAP.items():
        if key in normalized or normalized in key:
            return voice
    return DEFAULT_VOICE


def get_voice_settings(voice_name: str) -> dict:
    """Obtiene la configuración optimizada para cada voz."""
    return VOICE_SETTINGS.get(voice_name, VOICE_SETTINGS["Salvatore"])


def generate_narration(
    text: str,
    output_path: Path,
    voice: str = DEFAULT_VOICE,
    model: str = "eleven_multilingual_v2",
    stability: float = 0.65,
    similarity_boost: float = 0.80,
    speed: float = 0.95,
    style: float = 0.05,
) -> bool:
    """
    Genera un archivo de audio MP3 con ElevenLabs.
    
    Args:
        text: Texto a narrar
        output_path: Ruta del archivo MP3 de salida
        voice: Nombre de la voz (Josh, Adam, etc.)
        model: Modelo TTS
        stability: Estabilidad de voz (0-1)
        similarity_boost: Similitud a la voz original (0-1)
        speed: Velocidad (0.7-1.3)
        style: Estilo expresivo (0-0.2)
    
    Returns:
        True si se generó correctamente
    """
    voice_id = get_voice_id(voice)
    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}"
    
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    
    payload = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": False
        },
        "output_format": "mp3_44100_192"
    }
    
    # Solo eleven_multilingual_v2 soporta speed
    if model == "eleven_multilingual_v2":
        payload["voice_settings"]["speed"] = speed
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                size_kb = len(response.content) / 1024
                return True
            else:
                print(f"   [!] ElevenLabs error {response.status_code}: {response.text[:200]}")
                return False
                
    except Exception as e:
        print(f"   [!] ElevenLabs exception: {e}")
        return False


def generate_scene_narrations(
    scenes: list,
    output_dir: Path,
    voice: str = DEFAULT_VOICE,
    skip_existing: bool = True
) -> dict:
    """
    Genera narración individual por escena.
    
    Args:
        scenes: Lista de dicts con scene_number y narration
        output_dir: Directorio donde guardar los MP3
        voice: Voz a usar
        skip_existing: Si True, no regenera archivos existentes
    
    Returns:
        dict con estadísticas
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    stats = {"generated": 0, "skipped": 0, "failed": 0, "chars_total": 0}
    
    print("=" * 60)
    print(f"   ElevenLabs TTS — Narracion por Escena")
    print("=" * 60)
    print(f"   Voz: {voice}")
    print(f"   Escenas: {len(scenes)}")
    print(f"   Destino: {output_dir}")
    print("=" * 60)
    
    for i, scene in enumerate(scenes):
        num = scene.get("scene_number", i + 1)
        narration = scene.get("narration", "")
        
        if not narration:
            print(f"   [{i+1}/{len(scenes)}] Escena {num}: sin narracion, saltando")
            continue
        
        audio_path = output_dir / f"narration_{num:04d}.mp3"
        
        if skip_existing and audio_path.exists() and audio_path.stat().st_size > 1000:
            stats["skipped"] += 1
            continue
        
        stats["chars_total"] += len(narration)
        
        ok = generate_narration(narration, audio_path, voice=voice)
        
        if ok:
            size_kb = audio_path.stat().st_size / 1024
            stats["generated"] += 1
            print(f"   [{i+1}/{len(scenes)}] Escena {num}: OK ({size_kb:.0f}KB, {len(narration)} chars)")
        else:
            stats["failed"] += 1
            print(f"   [{i+1}/{len(scenes)}] Escena {num}: FALLO")
        
        # Rate limiting: ElevenLabs permite ~3 req/sec
        time.sleep(0.5)
    
    # Costo estimado
    cost_low = stats["chars_total"] / 1000 * 0.06
    cost_high = stats["chars_total"] / 1000 * 0.12
    
    print(f"\n{'='*60}")
    print(f"   RESUMEN")
    print(f"{'='*60}")
    print(f"   Generadas: {stats['generated']}")
    print(f"   Existentes: {stats['skipped']}")
    print(f"   Fallidas: {stats['failed']}")
    print(f"   Total caracteres: {stats['chars_total']:,}")
    print(f"   Costo estimado: ${cost_low:.2f} - ${cost_high:.2f}")
    print(f"{'='*60}")
    
    return stats


def generate_full_narration(
    scenes: list,
    output_path: Path,
    voice: str = DEFAULT_VOICE,
    pause_between: str = "... "
) -> bool:
    """
    Genera UNA sola narración completa concatenando todas las escenas.
    Más eficiente que por escena si no necesitas timing individual.
    
    Args:
        scenes: Lista de escenas con narration
        output_path: Ruta del MP3 completo
        voice: Voz a usar
        pause_between: Texto insertado entre escenas para pausas naturales
    
    Returns:
        True si se generó correctamente
    """
    # Concatenar todas las narraciones
    full_text = pause_between.join(
        scene.get("narration", "") 
        for scene in scenes 
        if scene.get("narration")
    )
    
    if not full_text:
        print("   [!] No hay narraciones en el guion")
        return False
    
    char_count = len(full_text)
    cost_low = char_count / 1000 * 0.06
    cost_high = char_count / 1000 * 0.12
    
    print(f"   Generando narracion completa...")
    print(f"   Caracteres: {char_count:,}")
    print(f"   Costo estimado: ${cost_low:.2f} - ${cost_high:.2f}")
    
    return generate_narration(full_text, output_path, voice=voice)


# ============================================================
# PODCAST: Dual narration (2 voces alternando por bloque de diálogo)
# ============================================================
import subprocess as _subprocess


def _generate_silence_mp3(duration_ms: int, output_path: Path) -> bool:
    """Genera un MP3 de silencio de duración exacta usando FFmpeg.
    Útil como pausa entre turnos de speaker en un podcast (la respiración
    real entre quien habla es lo que más distingue diálogo humano de TTS)."""
    duration_s = duration_ms / 1000.0
    try:
        result = _subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"anullsrc=r=44100:cl=mono",
                "-t", f"{duration_s:.3f}",
                "-c:a", "libmp3lame", "-b:a", "192k",
                str(output_path),
            ],
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0
    except Exception as e:
        print(f"   [!] silencio FFmpeg falló: {e}")
        return False


def _concat_mp3s(input_paths: list, output_path: Path) -> bool:
    """Concatena varios MP3 en uno solo con FFmpeg concat demuxer.
    Re-encodea para evitar artifacts de concat directo si los formatos
    difieren ligeramente."""
    if not input_paths:
        return False
    list_path = output_path.parent / f"_concat_{output_path.stem}.txt"
    try:
        with open(list_path, "w", encoding="utf-8") as f:
            for p in input_paths:
                f.write(f"file '{p.as_posix()}'\n")
        result = _subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(list_path),
                "-c:a", "libmp3lame", "-b:a", "192k",
                str(output_path),
            ],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            print(f"   [!] concat falló: {result.stderr[-200:]}")
            return False
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception as e:
        print(f"   [!] concat exception: {e}")
        return False
    finally:
        if list_path.exists():
            try:
                list_path.unlink()
            except Exception:
                pass


def generate_dual_narration(
    scenes: list,
    output_dir: Path,
    voice_a: str = "Will",
    voice_b: str = "Lina",
    pause_between_blocks_ms: int = 280,
    skip_existing: bool = True,
    model: str = "eleven_v3",
) -> dict:
    """
    Genera narración dual para podcast: 2 voces alternando por bloque de diálogo.

    Para cada escena con `dialogue_blocks`:
      1. Genera 1 MP3 por bloque: narration_{scene:04d}_{block:03d}_{speaker}.mp3
      2. Genera silencios de pause_between_blocks_ms entre bloques
      3. Concatena en narration_{scene:04d}.mp3 (reusable por factory.py
         exactamente igual que generate_scene_narrations)

    Reintento 3x con backoff lineal por bloque. Si un bloque falla 3 veces,
    se inserta silencio sintético para no abortar el episodio entero.

    Si voice_a == voice_b → fallback a generate_scene_narrations (warning).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    blocks_dir = output_dir / "blocks"
    blocks_dir.mkdir(parents=True, exist_ok=True)

    if voice_a == voice_b:
        print(f"⚠️  voice_a == voice_b ({voice_a}) — degradando a single-voice narration")
        return generate_scene_narrations(scenes, output_dir, voice=voice_a, skip_existing=skip_existing)

    print("=" * 60)
    print(f"   ElevenLabs DUAL TTS — Podcast 2 voces")
    print("=" * 60)
    print(f"   Host A: {voice_a}")
    print(f"   Host B: {voice_b}")
    print(f"   Escenas: {len(scenes)}")
    print(f"   Pausa entre bloques: {pause_between_blocks_ms}ms")
    print("=" * 60)

    settings_a = get_voice_settings(voice_a)
    settings_b = get_voice_settings(voice_b)

    # Silencio pre-generado (lo reusamos en todas las escenas)
    silence_path = blocks_dir / f"_silence_{pause_between_blocks_ms}ms.mp3"
    if not silence_path.exists():
        if not _generate_silence_mp3(pause_between_blocks_ms, silence_path):
            print(f"⚠️  No pude generar silencio. Las pausas serán omitidas.")
            silence_path = None

    stats = {
        "generated_blocks": 0,
        "skipped_blocks": 0,
        "failed_blocks": 0,
        "scenes_assembled": 0,
        "scenes_failed": 0,
        "chars_total": 0,
    }

    for i, scene in enumerate(scenes):
        scene_num = scene.get("scene_number", i + 1)
        scene_audio_path = output_dir / f"narration_{scene_num:04d}.mp3"

        if skip_existing and scene_audio_path.exists() and scene_audio_path.stat().st_size > 0:
            print(f"   [{i+1}/{len(scenes)}] Escena {scene_num}: ya existe, saltando")
            stats["scenes_assembled"] += 1
            continue

        dialogue_blocks = scene.get("dialogue_blocks", [])
        if not dialogue_blocks:
            # Fallback: si no hay dialogue_blocks pero sí narration plain,
            # tratamos como single-voice (Host A por default)
            narration = scene.get("narration", "")
            if narration:
                print(f"   [{i+1}/{len(scenes)}] Escena {scene_num}: sin dialogue_blocks, single-voice fallback")
                opts = {"stability": settings_a.get("stability", 0.55),
                        "similarity_boost": settings_a.get("similarity_boost", 0.85),
                        "speed": settings_a.get("speed", 0.92),
                        "style": settings_a.get("style", 0.10)}
                if generate_narration(narration, scene_audio_path, voice=voice_a, model=model, **opts):
                    stats["scenes_assembled"] += 1
                    stats["chars_total"] += len(narration)
                else:
                    stats["scenes_failed"] += 1
            continue

        block_paths = []
        any_block_failed = False

        for j, block in enumerate(dialogue_blocks):
            speaker_code = (block.get("speaker") or "?").upper()
            text = (block.get("text") or "").strip()
            if not text:
                continue

            voice_to_use = voice_a if speaker_code == "A" else voice_b
            speaker_settings = settings_a if speaker_code == "A" else settings_b
            speaker_label = "A" if speaker_code == "A" else "B"

            block_path = blocks_dir / f"narration_{scene_num:04d}_{j+1:03d}_{speaker_label}.mp3"

            if skip_existing and block_path.exists() and block_path.stat().st_size > 0:
                stats["skipped_blocks"] += 1
                block_paths.append(block_path)
                # Insertar silencio entre bloques (excepto antes del primero)
                if j < len(dialogue_blocks) - 1 and silence_path and silence_path.exists():
                    block_paths.append(silence_path)
                continue

            # Reintento 3x con backoff lineal
            success = False
            for attempt in range(3):
                ok = generate_narration(
                    text, block_path,
                    voice=voice_to_use, model=model,
                    stability=speaker_settings.get("stability", 0.55),
                    similarity_boost=speaker_settings.get("similarity_boost", 0.85),
                    speed=speaker_settings.get("speed", 0.92),
                    style=speaker_settings.get("style", 0.10),
                )
                if ok:
                    success = True
                    break
                wait_s = 0.1 + attempt * 0.5
                print(f"   ⚠️  bloque {j+1} escena {scene_num} falló (intento {attempt+1}), reintentando en {wait_s}s")
                time.sleep(wait_s)

            if success:
                stats["generated_blocks"] += 1
                stats["chars_total"] += len(text)
                block_paths.append(block_path)
            else:
                stats["failed_blocks"] += 1
                any_block_failed = True
                # Silencio sintético del largo aproximado (chars/15 segundos)
                synth_ms = max(500, int(len(text) / 15 * 1000))
                synth_path = blocks_dir / f"narration_{scene_num:04d}_{j+1:03d}_FAIL_silence.mp3"
                if _generate_silence_mp3(synth_ms, synth_path):
                    block_paths.append(synth_path)
                print(f"   ❌ Bloque {j+1}/{len(dialogue_blocks)} de escena {scene_num} falló — silencio sintético {synth_ms}ms")

            # Insertar silencio entre bloques (excepto antes del primero)
            if j < len(dialogue_blocks) - 1 and silence_path and silence_path.exists():
                block_paths.append(silence_path)

            time.sleep(0.4)  # rate limit ElevenLabs

        # Concatenar bloques en el archivo de escena
        if block_paths:
            if _concat_mp3s(block_paths, scene_audio_path):
                stats["scenes_assembled"] += 1
                marker = "⚠️" if any_block_failed else "✅"
                print(f"   {marker} [{i+1}/{len(scenes)}] Escena {scene_num} ensamblada ({len(block_paths)} segmentos)")
            else:
                stats["scenes_failed"] += 1
                print(f"   ❌ [{i+1}/{len(scenes)}] Escena {scene_num} concat falló")
        else:
            stats["scenes_failed"] += 1
            print(f"   ❌ [{i+1}/{len(scenes)}] Escena {scene_num} sin audio")

    print("=" * 60)
    print(f"   PODCAST DUAL NARRATION — Estadísticas")
    print(f"   Bloques generados: {stats['generated_blocks']}")
    print(f"   Bloques saltados (existentes): {stats['skipped_blocks']}")
    print(f"   Bloques fallidos: {stats['failed_blocks']}")
    print(f"   Escenas ensambladas: {stats['scenes_assembled']}/{len(scenes)}")
    print(f"   Caracteres totales: {stats['chars_total']:,}")
    cost_low = (stats["chars_total"] / 1000) * 0.06
    cost_high = (stats["chars_total"] / 1000) * 0.12
    print(f"   Costo estimado ElevenLabs: ${cost_low:.2f} - ${cost_high:.2f}")
    print("=" * 60)

    return stats


# ============================================================
# EJECUCIÓN STANDALONE
# ============================================================
if __name__ == "__main__":
    import re
    
    if not ELEVENLABS_API_KEY:
        print("[!] ELEVENLABS_API_KEY no configurada en .env")
        print("    Obtener en: https://elevenlabs.io/app/settings/api-keys")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Uso: python elevenlabs_tts.py <ruta_al_FULL_json> [opciones]")
        print("")
        print("Opciones:")
        print("  --voice NAME   Voz específica (Salvatore, Lorenzo, Diego)")
        print("  --agent NAME   Auto-seleccionar voz por agente")
        print("  --full         Generar 1 MP3 completo (no por escena)")
        print("  --test         Solo generar escena 1 como prueba")
        print("")
        print("Voces disponibles:")
        print("  Salvatore  — Épica, profunda (misterio, terror, biografías)")
        print("  Lorenzo    — Moderna, energética (finanzas, liderazgo)")
        print("  Diego      — Impactante, dinámica (backup energético)")
        sys.exit(1)
    
    json_path = Path(sys.argv[1])
    voice = None
    full_mode = "--full" in sys.argv
    test_mode = "--test" in sys.argv
    
    if "--voice" in sys.argv:
        idx = sys.argv.index("--voice")
        if idx + 1 < len(sys.argv):
            voice = sys.argv[idx + 1]
    
    if "--agent" in sys.argv:
        idx = sys.argv.index("--agent")
        if idx + 1 < len(sys.argv):
            voice = get_voice_for_agent(sys.argv[idx + 1])
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    scenes = data.get("video_scenes", [])
    if not scenes:
        print("[!] No se encontraron escenas")
        sys.exit(1)
    
    # Auto-detectar voz desde el agente del JSON si no se especificó
    if not voice:
        agent = data.get("agent", data.get("agent_name", ""))
        if agent:
            voice = get_voice_for_agent(agent)
            print(f"   Auto-detected: agente '{agent}' -> voz '{voice}'")
        else:
            voice = DEFAULT_VOICE
    
    # Directorio del proyecto
    raw_title = data.get("topic", "video_sin_titulo")
    if "seo_metadata" in data and "title" in data["seo_metadata"]:
        raw_title = data["seo_metadata"]["title"]
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_title.replace(" ", "_"))
    
    audio_dir = BASE_DIR / "output" / "videos" / safe_title / "audio"
    
    if test_mode:
        # Solo primera escena
        scenes = scenes[:1]
        print(f"\n   MODO TEST — Solo escena 1")
    
    if full_mode:
        output_path = audio_dir / "full_narration.mp3"
        generate_full_narration(scenes, output_path, voice=voice)
    else:
        generate_scene_narrations(scenes, audio_dir, voice=voice)

