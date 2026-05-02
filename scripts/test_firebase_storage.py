"""Quick connectivity check for Firebase Storage from inside the container."""
import json
from pathlib import Path

cred_path = Path("/app/firebase-admin.json")
if not cred_path.exists():
    print("ERROR: firebase-admin.json not found")
    raise SystemExit(1)

with open(cred_path) as f:
    creds = json.load(f)

print(f"  project_id: {creds.get('project_id')}")
print(f"  client_email: {creds.get('client_email')}")
print(f"  type: {creds.get('type')}")

import firebase_admin
from firebase_admin import credentials, storage

if not firebase_admin._apps:
    cred = credentials.Certificate(str(cred_path))
    firebase_admin.initialize_app(
        cred,
        {"storageBucket": "content-factory-5cbcb.firebasestorage.app"},
    )

bucket = storage.bucket()
print(f"  bucket: {bucket.name}")
print(f"  exists: {bucket.exists()}")

test_blob = bucket.blob("_test/connectivity_check.txt")
test_blob.upload_from_string("connectivity test", content_type="text/plain")
print(f"  upload test: OK")

test_url = test_blob.generate_signed_url(version="v4", expiration=300, method="GET")
print(f"  signed URL generated (300s expiration, length {len(test_url)})")

test_blob.delete()
print(f"  cleanup: OK")
print()
print("FIREBASE STORAGE: READY")
