"""Audit: cross-reference Firestore projects vs files on disk vs Storage."""
import os
import sys

sys.path.insert(0, "/app")
from api import _ensure_firebase_initialized

_ensure_firebase_initialized()
from firebase_admin import firestore, storage

db = firestore.client()
bucket = storage.bucket()

projects = list(db.collection("projects").stream())
print(f"Total proyectos en Firestore: {len(projects)}")
print()
print(f"{'Status':<11} | Disk | Stor | Folder")
print("-" * 110)

stats = {"completed": 0, "on_disk": 0, "in_storage": 0, "lost": 0}
lost = []

for p in sorted(projects, key=lambda x: x.to_dict().get("title", "")):
    d = p.to_dict()
    title = (d.get("title", "?") or "?")[:60]
    status = d.get("status", "?")
    folder = d.get("videoFolder", "")
    has_storage_path = bool(d.get("videoStoragePath", ""))
    on_disk = os.path.isdir(f"/app/output/videos/{folder}") if folder else False

    in_storage = False
    if folder:
        try:
            blobs = list(bucket.list_blobs(prefix=f"videos/{p.id}/", max_results=1))
            in_storage = len(blobs) > 0
        except Exception:
            pass

    disk_mark = " OK " if on_disk else " -- "
    stor_mark = " OK " if (has_storage_path or in_storage) else " -- "

    print(f"{status:<11} | {disk_mark}| {stor_mark}| {folder[:50]:<50} | {title}")

    if status == "completed":
        stats["completed"] += 1
        if on_disk:
            stats["on_disk"] += 1
        if has_storage_path or in_storage:
            stats["in_storage"] += 1
        if not on_disk and not (has_storage_path or in_storage):
            stats["lost"] += 1
            lost.append({"id": p.id, "title": title, "folder": folder})

print()
print("=" * 60)
print(f"Total proyectos completados: {stats['completed']}")
print(f"  - Con archivo en disco VPS: {stats['on_disk']}")
print(f"  - Con archivo en Storage:    {stats['in_storage']}")
print(f"  - PERDIDOS (sin archivo):    {stats['lost']}")

if lost:
    print()
    print("Proyectos PERDIDOS (marcados completed pero sin archivo en ningún lado):")
    for item in lost:
        print(f"  - {item['title'][:60]}")
        print(f"      project_id: {item['id']}")
        print(f"      folder esperado: {item['folder']}")
