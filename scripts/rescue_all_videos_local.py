"""
Sube TODOS los videos producidos (los que existen en local + VPS)
a Firebase Storage y actualiza Firestore con videoUrl + videoStoragePath.

Se corre LOCALMENTE desde la PC del usuario, usando la new service account key.
"""
import json
import sys
from datetime import timedelta
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore, storage

CRED_PATH = "C:/Users/admor/Backups/content-factory-2026-05-01/new-firebase-key/firebase-key-new.json"
BUCKET = "content-factory-5cbcb.firebasestorage.app"

cred = credentials.Certificate(CRED_PATH)
firebase_admin.initialize_app(cred, {"storageBucket": BUCKET})

db = firestore.client()
bucket = storage.bucket()

# Mapeo: project_id -> (folder_name, local_file_path)
RECOVERY = {
    "FpEPrOPeESGB999lhcLH": (
        "El_caso_del_Zodiac_Killer",
        "C:/Users/admor/Downloads/FINAL_cinematico_El_caso_del_Zodiac_Killer.mp4",  # may not exist locally; will try VPS-mounted name
        "FINAL_cinematico_El_caso_del_Zodiac_Killer.mp4",
    ),
    "96oJBHevwDj4wdcR1h4S": (
        "El_estoicismo_aplicado_al_trabajo_moderno",
        "C:/Users/admor/Downloads/FINAL_cinematico_El_estoicismo_aplicado_al_trabajo_moderno.mp4",
        "FINAL_cinematico_El_estoicismo_aplicado_al_trabajo_moderno.mp4",
    ),
    "3N2sQDJsHxrU4nwazdue": (
        "Las_torturas_de_la_Santa_Inquisici_n",
        "C:/Users/admor/Downloads/FINAL_Las_torturas_de_la_Santa_Inquisici_n.mp4",
        "FINAL_Las_torturas_de_la_Santa_Inquisici_n.mp4",
    ),
    "GQ0jBKNgpnLgIMTPqrWB": (
        "Cleopatra__poder__seducci_n_y_tragedia",
        "C:/Users/admor/Downloads/FINAL_cinematico_Cleopatra__poder__seducci_n_y_tragedia.mp4",
        "FINAL_cinematico_Cleopatra__poder__seducci_n_y_tragedia.mp4",
    ),
    "Zpti2GnHN5y4rWF5j05M": (
        "Jim_Jones_y_el_suicidio_masivo_de_Jonestown",
        "C:/Users/admor/Downloads/Content You tube Generator/output/videos/Jim_Jones_y_el_suicidio_masivo_de_Jonestown/FINAL_cinematico_Jim_Jones_y_el_suicidio_masivo_de_Jonestown.mp4",
        "FINAL_cinematico_Jim_Jones_y_el_suicidio_masivo_de_Jonestown.mp4",
    ),
    "2rzBMzRGpKRekZdrTQIy": (
        "Los_Mayas_y_su_misteriosa_desaparici_n",
        "C:/Users/admor/Downloads/FINAL_Los_Mayas_y_su_misteriosa_desaparici_n.mp4",
        "FINAL_Los_Mayas_y_su_misteriosa_desaparici_n.mp4",
    ),
    "p6xl1JpIv9tb5IP9jN74": (
        "Los_mecanismos_de_un_narcisista_peligroso",
        "C:/Users/admor/Downloads/FINAL_cinematico_Los_mecanismos_de_un_narcisista_peligroso.mp4",
        "FINAL_cinematico_Los_mecanismos_de_un_narcisista_peligroso.mp4",
    ),
}

results = []

for project_id, (folder, local_path, blob_filename) in RECOVERY.items():
    print(f"\n=== {folder} ===")
    p = Path(local_path)
    if not p.exists():
        print(f"  Skip: archivo local no encontrado")
        results.append((folder, project_id, "MISSING_LOCAL"))
        continue

    size_mb = p.stat().st_size / 1024 / 1024
    print(f"  Archivo: {p.name} ({size_mb:.1f} MB)")

    blob_name = f"videos/{project_id}/{blob_filename}"
    blob = bucket.blob(blob_name)

    # Skip if already uploaded
    if blob.exists():
        print(f"  Already in Storage, generating fresh signed URL")
    else:
        print(f"  Uploading...")
        blob.upload_from_filename(str(p), content_type="video/mp4")
        print(f"  Upload OK")

    signed_url = blob.generate_signed_url(
        version="v4", expiration=timedelta(days=7), method="GET"
    )

    db.collection("projects").document(project_id).update({
        "videoFolder": folder,
        "videoStoragePath": f"gs://{BUCKET}/{blob_name}",
        "videoUrl": signed_url,
        "videoUrlGeneratedAt": firestore.SERVER_TIMESTAMP,
        "videoSizeMB": round(size_mb, 1),
    })
    print(f"  Firestore updated")
    results.append((folder, project_id, "OK"))

print()
print("=" * 70)
print("RESUMEN FINAL")
print("=" * 70)
for folder, pid, status in results:
    mark = "OK " if status == "OK" else "-- "
    print(f"  [{mark}] {status:<15} {folder}")
