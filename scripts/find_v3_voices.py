"""
Lista TODAS las voces "premade" oficiales de ElevenLabs (las que vienen
con tu cuenta — todas v3-compatible, calidad premium, multilingüe).

Después de ejecutar: elige 2-3 masculinas + 2-3 femeninas y genero
samples con el mismo texto del test anterior.
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not API_KEY:
    print("ERROR: falta ELEVENLABS_API_KEY", file=sys.stderr)
    sys.exit(1)


def get_voices():
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {"xi-api-key": API_KEY}
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:200]}"
    return r.json(), None


def print_voice(v, idx):
    name = v.get("name", "?")
    vid = v.get("voice_id", "?")
    category = v.get("category", "?")
    labels = v.get("labels", {}) or {}
    accent = labels.get("accent", "?")
    age = labels.get("age", "?")
    gender = labels.get("gender", "?")
    descriptive = labels.get("descriptive") or labels.get("description") or "?"
    use_case = labels.get("use_case", "?")
    description = (v.get("description") or "")[:140]
    print(f"  [{idx}] {name}  ({gender}, {age}, {accent})")
    print(f"      voice_id: {vid}")
    print(f"      category: {category} | use_case: {use_case} | descriptive: {descriptive}")
    if description and description != "?":
        print(f"      desc: {description}")
    print()


data, err = get_voices()
if err:
    print(f"ERROR: {err}")
    sys.exit(1)

voices = data.get("voices", [])
print(f"\nTotal voces en cuenta: {len(voices)}\n")

# Separar por género
male = []
female = []
other = []
for v in voices:
    labels = v.get("labels", {}) or {}
    g = (labels.get("gender") or "").lower()
    if g == "male":
        male.append(v)
    elif g == "female":
        female.append(v)
    else:
        other.append(v)

# Solo mostrar las premade (oficiales) y las que parecen relevantes
print("="*70)
print(f"  MASCULINAS PREMADE/PREMIUM (para Mateo) — {len(male)} totales")
print("="*70 + "\n")
shown = 0
for v in male:
    cat = (v.get("category") or "").lower()
    if cat in ("premade", "professional"):
        print_voice(v, shown + 1)
        shown += 1
    if shown >= 12:
        break

print("="*70)
print(f"  FEMENINAS PREMADE/PREMIUM (para Lucía) — {len(female)} totales")
print("="*70 + "\n")
shown = 0
for v in female:
    cat = (v.get("category") or "").lower()
    if cat in ("premade", "professional"):
        print_voice(v, shown + 1)
        shown += 1
    if shown >= 12:
        break

if other:
    print("="*70)
    print(f"  SIN GÉNERO ETIQUETADO — {len(other)} totales")
    print("="*70 + "\n")
    for v in other[:5]:
        print_voice(v, "?")

print("\n" + "="*70)
print("  NEXT: dime qué 2-3 voces masculinas + 2-3 femeninas quieres probar")
print("  (por nombre o voice_id) y genero samples con cada una.")
print("="*70)
