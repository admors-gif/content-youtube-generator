"""
Genera 6 samples con voces v3-compatible candidatas para reemplazar
Salvatore + Serafina del podcast.

Mateo (masculino) — 3 candidatos:
  - Charlie    (energetic young australian)
  - Will       (relaxed optimist conversational)
  - Liam       (energetic social media)

Lucía (femenino) — 3 candidatos:
  - Marcela    (Colombian podcast specialist)
  - Lina       (Carefree Colombian conversational)
  - Jessica    (Playful, bright, warm American)

Usa el mismo texto del test anterior (con tags emocionales para
también validar que cada voz interpreta tags bien).

Costo total estimado: ~$0.10 USD
"""
import os
import sys
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

CANDIDATES_MATEO = [
    {"name": "charlie", "voice_id": "IKne3meq5aSn9XLyUdCD"},
    {"name": "will",    "voice_id": "bIHbv24MWmeRgasZH58o"},
    {"name": "liam",    "voice_id": "TX3LPaxmHKxFdv7VOQHJ"},
]

CANDIDATES_LUCIA = [
    {"name": "marcela", "voice_id": "86V9x9hrQds83qf7zaGn"},
    {"name": "lina",    "voice_id": "VmejBeYhbrcTPwDniox7"},
    {"name": "jessica", "voice_id": "cgSgspJ2msm6clMCkdW9"},
]

TEXT_MATEO = (
    "[exhales] A ver, vamos a empezar fuerte. Lo que vas a escuchar te va a hacer "
    "pensar dos veces antes de juzgar a las personas que tienes cerca."
)
TEXT_LUCIA = (
    "[laughs softly] Espera, espera. ¿Me estás diciendo que esto pasa todos los días? "
    "No puede ser tan común, Mateo."
)


def synthesize(filename: str, voice_id: str, text: str):
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
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        out = OUT / filename
        out.write_bytes(r.content)
        return True, f"{filename} ({len(r.content) // 1024} KB)"
    except Exception as e:
        return False, f"exception: {e}"


print(f"\nGenerando 6 samples de voces candidatas en {OUT}/\n")

results = []

print("=== MATEO (masculino) ===")
for i, c in enumerate(CANDIDATES_MATEO, 1):
    fname = f"v_mateo_{i}_{c['name']}.mp3"
    print(f"  [{i}/3] {c['name']:10s} -> {fname}")
    ok, msg = synthesize(fname, c["voice_id"], TEXT_MATEO)
    print(f"        {'OK ' if ok else 'FAIL'}: {msg}\n")
    results.append((fname, ok))

print("=== LUCÍA (femenino) ===")
for i, c in enumerate(CANDIDATES_LUCIA, 1):
    fname = f"v_lucia_{i}_{c['name']}.mp3"
    print(f"  [{i}/3] {c['name']:10s} -> {fname}")
    ok, msg = synthesize(fname, c["voice_id"], TEXT_LUCIA)
    print(f"        {'OK ' if ok else 'FAIL'}: {msg}\n")
    results.append((fname, ok))

ok_count = sum(1 for _, ok in results if ok)
print(f"\nResultado: {ok_count}/{len(results)} OK")
print(f"Mp3s en: {OUT}/")
