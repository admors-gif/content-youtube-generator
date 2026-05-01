"""
═══════════════════════════════════════════════════════════════
  Content Factory — Sync de Proyecto
═══════════════════════════════════════════════════════════════

  Descarga un proyecto completo desde Firestore + VPS
  y lo guarda en carpetas organizadas localmente.

  Uso:
    python sync_project.py                    # Lista proyectos
    python sync_project.py <project_id>       # Descarga un proyecto
    python sync_project.py --all              # Descarga todos

═══════════════════════════════════════════════════════════════
"""
import httpx
import json
import sys
import re
from pathlib import Path

# ============================================================
# CONFIGURACIÓN
# ============================================================
FIREBASE_PROJECT = "content-factory-5cbcb"
FIREBASE_API_KEY = "AIzaSyCJL17JV8Xny4nKI0ag_QcUkw-uadmbZTI"
FIRESTORE_URL = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT}/databases/(default)/documents"
VPS_API_URL = "http://100.99.207.113:8085"
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "videos"


def firestore_to_python(value):
    """Convierte un valor Firestore REST a Python nativo."""
    if "stringValue" in value:
        return value["stringValue"]
    elif "integerValue" in value:
        return int(value["integerValue"])
    elif "doubleValue" in value:
        return float(value["doubleValue"])
    elif "booleanValue" in value:
        return value["booleanValue"]
    elif "timestampValue" in value:
        return value["timestampValue"]
    elif "nullValue" in value:
        return None
    elif "arrayValue" in value:
        return [firestore_to_python(v) for v in value.get("arrayValue", {}).get("values", [])]
    elif "mapValue" in value:
        fields = value.get("mapValue", {}).get("fields", {})
        return {k: firestore_to_python(v) for k, v in fields.items()}
    return value


def parse_firestore_doc(raw):
    """Convierte un documento Firestore completo a dict Python."""
    fields = raw.get("fields", {})
    return {k: firestore_to_python(v) for k, v in fields.items()}


def list_projects():
    """Lista todos los proyectos en Firestore."""
    r = httpx.get(f"{FIRESTORE_URL}/projects?key={FIREBASE_API_KEY}", timeout=15)
    if r.status_code != 200:
        print(f"[!] Error {r.status_code}: {r.text[:200]}")
        return []
    
    docs = r.json().get("documents", [])
    projects = []
    
    print("=" * 60)
    print("   CONTENT FACTORY — Proyectos en Firestore")
    print("=" * 60)
    
    for doc in docs:
        doc_id = doc["name"].split("/")[-1]
        data = parse_firestore_doc(doc)
        projects.append({"id": doc_id, **data})
        
        scenes = data.get("scenes", [])
        status = data.get("status", "?")
        title = data.get("title", "sin titulo")
        agent = data.get("agentId", "?")
        
        print(f"\n   [{status}] {title}")
        print(f"   ID: {doc_id}")
        print(f"   Agente: {agent}")
        print(f"   Escenas: {len(scenes)}")
    
    print(f"\n{'='*60}")
    print(f"   Total: {len(projects)} proyectos")
    print(f"{'='*60}")
    
    return projects


def sync_project(project_id):
    """Descarga un proyecto completo: guión + imágenes + video."""
    
    # 1. Obtener datos de Firestore
    print(f"\n{'='*60}")
    print(f"   SYNC — Descargando proyecto")
    print(f"{'='*60}")
    print(f"   ID: {project_id}")
    
    r = httpx.get(f"{FIRESTORE_URL}/projects/{project_id}?key={FIREBASE_API_KEY}", timeout=15)
    if r.status_code != 200:
        print(f"   [!] Error Firestore: {r.status_code}")
        return False
    
    data = parse_firestore_doc(r.json())
    title = data.get("title", "sin_titulo")
    safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title.replace(" ", "_"))
    scenes = data.get("scenes", [])
    script = data.get("script", {})
    seo = data.get("seo", {})
    agent_id = data.get("agentId", "general")
    
    print(f"   Título: {title}")
    print(f"   Agente: {agent_id}")
    print(f"   Escenas: {len(scenes)}")
    
    # 2. Crear estructura de carpetas
    project_dir = OUTPUT_DIR / safe_title
    images_dir = project_dir / "images"
    audio_dir = project_dir / "audio"
    kenburns_dir = project_dir / "kenburns"
    luma_dir = project_dir / "luma_clips"
    scripts_dir = project_dir / "scripts"
    
    for d in [images_dir, audio_dir, kenburns_dir, luma_dir, scripts_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # 3. Guardar guión como FULL JSON (compatible con factory.py)
    full_json = {
        "topic": title,
        "agent": agent_id,
        "agent_name": agent_id,
        "seo_metadata": seo,
        "script_plain": script.get("plain", ""),
        "word_count": script.get("wordCount", 0),
        "estimated_minutes": script.get("estimatedMinutes", 0),
        "video_scenes": [],
        "firestore_id": project_id,
    }
    
    # Convertir escenas al formato que factory.py espera
    # Firestore usa: narration_text, narration_context, prompt, scene_number, timestamp
    for i, scene in enumerate(scenes):
        narration = scene.get("narration_text", scene.get("narration", scene.get("text", "")))
        full_json["video_scenes"].append({
            "scene_number": scene.get("scene_number", i + 1),
            "narration": narration,
            "prompt": scene.get("prompt", scene.get("imagePrompt", "")),
            "narration_context": scene.get("narration_context", ""),
            "timestamp": scene.get("timestamp", ""),
            "motion": scene.get("motion", "low"),
        })
    
    script_path = scripts_dir / f"FULL_{safe_title}.json"
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(full_json, f, ensure_ascii=False, indent=2)
    print(f"\n   [OK] Guión guardado: {script_path.name} ({len(scenes)} escenas)")
    
    # 4. Descargar imágenes del VPS
    print(f"\n   Descargando imágenes del VPS...")
    downloaded = 0
    skipped = 0
    failed = 0
    
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for i in range(1, len(scenes) + 1):
            img_path = images_dir / f"scene_{i:04d}.png"
            
            if img_path.exists() and img_path.stat().st_size > 5000:
                skipped += 1
                continue
            
            try:
                url = f"{VPS_API_URL}/images/{safe_title}/scene_{i:04d}.png"
                r = client.get(url)
                if r.status_code == 200 and len(r.content) > 5000:
                    with open(img_path, "wb") as f:
                        f.write(r.content)
                    downloaded += 1
                    if downloaded % 10 == 0:
                        print(f"   ... {downloaded} imágenes descargadas")
                else:
                    failed += 1
            except Exception as e:
                failed += 1
    
    print(f"   [OK] Imágenes: {downloaded} descargadas, {skipped} existentes, {failed} fallidas")
    
    # 5. Resumen
    total_size_mb = sum(f.stat().st_size for f in images_dir.glob("*.png")) / (1024 * 1024)
    
    print(f"\n{'='*60}")
    print(f"   SYNC COMPLETO")
    print(f"{'='*60}")
    print(f"   📖 Guión: {script_path}")
    print(f"   📸 Imágenes: {len(list(images_dir.glob('*.png')))} ({total_size_mb:.1f}MB)")
    print(f"   📁 Proyecto: {project_dir}")
    print(f"   🤖 Agente: {agent_id} → Voz recomendada: Salvatore")
    print(f"{'='*60}")
    print(f"\n   Para producir:")
    print(f"   python scripts/factory.py \"{script_path}\" --mode cinematico")
    
    return True


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--list":
        list_projects()
    elif sys.argv[1] == "--all":
        projects = list_projects()
        for p in projects:
            sync_project(p["id"])
    else:
        sync_project(sys.argv[1])
