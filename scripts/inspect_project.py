"""Check what the project data structure looks like in Firebase."""
import firebase_admin
from firebase_admin import credentials, firestore
import json, os

cred_path = "/app/firebase-admin.json"
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()
doc = db.collection("projects").document("3N2sQDJsHxrU4nwazdue").get()
data = doc.to_dict()

# Print keys at top level
print("=== TOP LEVEL KEYS ===")
for k in sorted(data.keys()):
    v = data[k]
    if isinstance(v, str) and len(v) > 100:
        print(f"  {k}: (string, {len(v)} chars)")
    elif isinstance(v, list):
        print(f"  {k}: (list, {len(v)} items)")
    elif isinstance(v, dict):
        print(f"  {k}: (dict, keys: {list(v.keys())})")
    else:
        print(f"  {k}: {v}")

# Check scenes
scenes = data.get("scenes", [])
print(f"\n=== SCENES ({len(scenes)}) ===")
if scenes:
    print(f"  First scene keys: {list(scenes[0].keys()) if isinstance(scenes[0], dict) else type(scenes[0])}")
    print(f"  First scene: {json.dumps(scenes[0], ensure_ascii=False)[:200]}")

# Check script
script = data.get("script", {})
print(f"\n=== SCRIPT ===")
print(f"  Keys: {list(script.keys()) if isinstance(script, dict) else type(script)}")
if isinstance(script, dict):
    plain = script.get("plain", "")
    print(f"  plain length: {len(plain)} chars")
    print(f"  approved: {script.get('approved')}")

# Check video_scenes (old format)
vs = data.get("video_scenes", [])
print(f"\n=== VIDEO_SCENES ({len(vs)}) ===")
if vs:
    print(f"  First: {json.dumps(vs[0], ensure_ascii=False)[:200]}")
