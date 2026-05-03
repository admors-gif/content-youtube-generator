"""
Test de 'química' Mateo+Lucía con conversación real.

Genera 2 mp3s, cada uno con la MISMA conversación pero distinta voz
para Lucía (Will siempre como Mateo):

  test_chemistry_will_lina.mp3      — Will (Mateo) + Lina (Lucía)
  test_chemistry_will_jessica.mp3   — Will (Mateo) + Jessica (Lucía)

Conversación: 6 turnos alternados, ~1 min cada mp3, fragmento natural
del estilo del podcast 'Este no es otro podcast más' sobre manipulación.

Costo total: ~$0.20 USD
"""
import os
import sys
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not API_KEY:
    print("ERROR: falta ELEVENLABS_API_KEY", file=sys.stderr)
    sys.exit(1)

OUT = Path(__file__).parent.parent / "test_v3_audio"
OUT.mkdir(exist_ok=True)
TMP = OUT / "_chemistry_tmp"
TMP.mkdir(exist_ok=True)

WILL = "bIHbv24MWmeRgasZH58o"
LINA = "VmejBeYhbrcTPwDniox7"
JESSICA = "cgSgspJ2msm6clMCkdW9"

# Conversacion natural Mateo+Lucia, 6 turnos, mezcla de tags emocionales
# y diferentes ritmos para evaluar tanto interpretacion de tags como
# resistencia auditiva en conversacion sostenida.
CONVERSATION = [
    {"speaker": "lucia", "text": "Oye, una cosa. [curious] ¿Tú alguna vez terminaste una discusión pensando que habías hecho algo mal, pero sin poder explicar exactamente qué?"},
    {"speaker": "mateo", "text": "[exhales] Sí. Y eso en sí mismo ya es una respuesta."},
    {"speaker": "lucia", "text": "Exacto. Porque resulta que esa sensación tiene nombre, tiene mecanismos, y hay personas que la producen intencionalmente. [laughs softly] Y hoy vamos a hablar de eso."},
    {"speaker": "mateo", "text": "Bienvenidos a Este no es otro podcast más. Soy Mateo, estoy con Lucía, y el tema de hoy es la manipulación. Específicamente, cinco señales de que alguien te está manipulando sin que tú lo estés notando."},
    {"speaker": "lucia", "text": "Y lo importante aquí es que no estamos hablando de villanos de película. [sighs] Estamos hablando de personas comunes, en relaciones cotidianas."},
    {"speaker": "mateo", "text": "La primera señal es lo que en psicología llaman triangulación. Suena técnico, pero es algo muy común. Imagínate que en una discusión, alguien empieza a meter a un tercero que no estaba ahí."},
]


def synth(text: str, voice_id: str, out_path: Path):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": "eleven_v3",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }
    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    r = requests.post(url, json=payload, headers=headers, timeout=60)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    out_path.write_bytes(r.content)
    return True, f"{out_path.name} ({len(r.content) // 1024} KB)"


def make_silence(duration_ms: int, out_path: Path):
    """Genera mp3 de silencio con ffmpeg."""
    duration_s = duration_ms / 1000.0
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anullsrc=channel_layout=mono:sample_rate=44100",
        "-t", str(duration_s),
        "-c:a", "libmp3lame", "-b:a", "128k",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    return result.returncode == 0


def concat_mp3s(input_paths: list, out_path: Path):
    """Concatena una lista de mp3s con ffmpeg concat demuxer."""
    list_file = TMP / "_concat.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in input_paths:
            f.write(f"file '{p.absolute()}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:a", "libmp3lame", "-b:a", "128k",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    return result.returncode == 0


def generate_conversation(test_name: str, mateo_voice: str, lucia_voice: str):
    """Genera una conversación completa con turnos alternados + silencios."""
    print(f"\n=== {test_name} ===")
    block_paths = []
    pause_path = TMP / f"_pause_{test_name}.mp3"

    # Pausa entre turnos: 350ms (un poco más de pausa que entre bloques
    # del mismo speaker, para sentir el cambio natural)
    if not make_silence(350, pause_path):
        print(f"  ERROR: no se pudo generar silencio")
        return False

    for i, turn in enumerate(CONVERSATION, 1):
        voice_id = mateo_voice if turn["speaker"] == "mateo" else lucia_voice
        speaker_label = turn["speaker"].upper()
        chars = len(turn["text"])
        print(f"  [{i}/{len(CONVERSATION)}] {speaker_label:5s} ({chars} chars)")
        block = TMP / f"{test_name}_{i:02d}_{turn['speaker']}.mp3"
        ok, msg = synth(turn["text"], voice_id, block)
        if not ok:
            print(f"        FAIL: {msg}")
            return False
        block_paths.append(block)
        # Agregar pausa entre turnos (excepto despues del ultimo)
        if i < len(CONVERSATION):
            block_paths.append(pause_path)

    final_path = OUT / f"{test_name}.mp3"
    print(f"  Concatenando -> {final_path.name}")
    if not concat_mp3s(block_paths, final_path):
        print("  ERROR concat")
        return False
    size_kb = final_path.stat().st_size // 1024
    print(f"  OK: {final_path.name} ({size_kb} KB)")
    return True


print(f"\nGenerando 2 conversaciones de test en {OUT}/\n")

ok_a = generate_conversation("test_chemistry_will_lina", WILL, LINA)
ok_b = generate_conversation("test_chemistry_will_jessica", WILL, JESSICA)

# Limpieza de tmp
import shutil
try:
    shutil.rmtree(TMP)
except Exception:
    pass

print(f"\n{'='*60}")
print(f"  Resultado: {sum([ok_a, ok_b])}/2 OK")
print(f"  Mp3s en: {OUT}/")
print(f"{'='*60}")
