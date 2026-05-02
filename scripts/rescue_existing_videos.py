"""
Sube los 3 videos existentes en disco a Firebase Storage y actualiza Firestore
con los campos videoFolder, videoStoragePath, videoUrl que faltaban.

Mapping project_id -> folder en disco (verificado por título).
"""
import sys
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, "/app")
from api import _ensure_firebase_initialized, _upload_video_to_storage

_ensure_firebase_initialized()
from firebase_admin import firestore

db = firestore.client()

# Mapeo: project_id -> (folder_name, expected_filename)
RECOVERY = {
    "FpEPrOPeESGB999lhcLH": (
        "El_caso_del_Zodiac_Killer",
        "FINAL_cinematico_El_caso_del_Zodiac_Killer.mp4",
    ),
    "96oJBHevwDj4wdcR1h4S": (
        "El_estoicismo_aplicado_al_trabajo_moderno",
        "FINAL_cinematico_El_estoicismo_aplicado_al_trabajo_moderno.mp4",
    ),
    "3N2sQDJsHxrU4nwazdue": (
        "Las_torturas_de_la_Santa_Inquisici_n",
        "FINAL_Las_torturas_de_la_Santa_Inquisici_n.mp4",
    ),
}

results = []
for project_id, (folder, filename) in RECOVERY.items():
    print(f"\n=== Recuperando project {project_id} ===")
    video_path = Path(f"/app/output/videos/{folder}/{filename}")

    if not video_path.exists():
        print(f"  FAIL: archivo no existe en disco: {video_path}")
        results.append((project_id, folder, "MISSING_FILE"))
        continue

    print(f"  Archivo: {video_path.name} ({video_path.stat().st_size / 1024 / 1024:.1f} MB)")

    # Subir a Storage
    upload = _upload_video_to_storage(video_path, project_id)
    if not upload:
        print(f"  FAIL: upload to Storage")
        results.append((project_id, folder, "UPLOAD_FAILED"))
        continue

    # Actualizar Firestore
    has_subs = "FINAL_SUB_" in filename or "_SUB_" in filename
    db.collection("projects").document(project_id).update({
        "videoFolder": folder,
        "videoStoragePath": upload["gs_path"],
        "videoUrl": upload["signed_url"],
        "videoUrlGeneratedAt": firestore.SERVER_TIMESTAMP,
        "hasSubtitles": has_subs,
    })
    print(f"  OK: Firestore updated with videoFolder, videoStoragePath, videoUrl")
    results.append((project_id, folder, "OK"))

print("\n" + "=" * 60)
print("RESUMEN DE RECUPERACIÓN")
print("=" * 60)
for pid, folder, status in results:
    print(f"  [{status}] {folder} ({pid})")
