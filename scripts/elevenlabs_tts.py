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
    # === 4 Voces principales ===
    "Salvatore": "t3eeeqhBjrUqcrPvDqUn",   # Épica, profunda, misteriosa
    "Lorenzo": "DTGwzA4YLrWB1FAT6Uas",      # Moderna, profesional, clara
    "Diego": "3Y2yr1PdwiaWZ5xxYRed",         # Explosiva, alta energía
    "Serafina": "4tRn1lSkEn13EVTuqb0g",      # Sensual, seductora, íntima
    # === Pre-built (backup) ===
    "Josh": "TxGEqnHWrfWFTfGW9XjX",
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
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

