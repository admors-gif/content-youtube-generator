"""
Test mini de Eleven v3 — valida 3 cosas críticas:

1. ¿Las voces actuales (Salvatore + Serafina) son compatibles con eleven_v3?
2. ¿Los audio tags [exhales], [laughs softly] se interpretan o se leen literal?
3. ¿La voz suena más dinámica/rápida que con eleven_multilingual_v2?

Genera 3 mp3s en test_v3_audio/ para escuchar:
- 01_mateo_exhales.mp3       — Salvatore con [exhales]
- 02_lucia_laughs.mp3        — Serafina con [laughs softly]
- 03_mateo_natural.mp3       — Salvatore conversación natural sin tags

Costo total estimado: <$0.05 USD
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not API_KEY:
    print("ERROR: falta ELEVENLABS_API_KEY en .env", file=sys.stderr)
    sys.exit(1)

# Voces actuales del podcast (mismas que generate_dual_narration usa)
VOICES = {
    "Salvatore": "t3eeeqhBjrUqcrPvDqUn",  # Mateo: dramático/profundo
    "Serafina":  "4tRn1lSkEn13EVTuqb0g",  # Lucía: cálida/íntima
}

OUT = Path(__file__).parent.parent / "test_v3_audio"
OUT.mkdir(exist_ok=True)


def synthesize(filename: str, voice_id: str, text: str, model: str = "eleven_v3"):
    """Llama a la API de ElevenLabs y guarda el mp3. Retorna (success, error)."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": model,
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
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:300]}"
        out_path = OUT / filename
        out_path.write_bytes(r.content)
        size_kb = len(r.content) / 1024
        return True, f"{filename} ({size_kb:.1f} KB)"
    except Exception as e:
        return False, f"exception: {e}"


TESTS = [
    {
        "filename": "01_mateo_exhales.mp3",
        "voice": "Salvatore",
        "text": "[exhales] A ver, vamos a empezar fuerte. Lo que vas a escuchar te va a hacer pensar dos veces antes de juzgar a las personas que tienes cerca.",
    },
    {
        "filename": "02_lucia_laughs.mp3",
        "voice": "Serafina",
        "text": "[laughs softly] Espera, espera. ¿Me estás diciendo que esto pasa todos los días? No puede ser tan común, Mateo.",
    },
    {
        "filename": "03_mateo_natural.mp3",
        "voice": "Salvatore",
        "text": "La primera señal es lo que en psicología llaman triangulación. Suena técnico, pero es algo muy común. Imagínate que en una discusión, alguien empieza a meter a un tercero que no estaba ahí.",
    },
]

print(f"\nEleven v3 mini test — generando {len(TESTS)} mp3s en {OUT}/\n")

results = []
for i, t in enumerate(TESTS, 1):
    voice_id = VOICES[t["voice"]]
    chars = len(t["text"])
    print(f"[{i}/{len(TESTS)}] {t['filename']} | {t['voice']} | {chars} chars")
    ok, msg = synthesize(t["filename"], voice_id, t["text"])
    status = "OK " if ok else "FAIL"
    print(f"      {status}: {msg}\n")
    results.append((t["filename"], ok, msg))

ok_count = sum(1 for _, ok, _ in results if ok)
print(f"\nResultado: {ok_count}/{len(results)} OK")
for fname, ok, msg in results:
    print(f"  {'OK' if ok else 'FAIL'}  {fname}  {msg if not ok else ''}")
print(f"\nMp3s en: {OUT}/")
