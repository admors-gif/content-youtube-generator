"""Encuentra el proyecto más reciente en Firestore y muestra info."""
import sys
sys.path.insert(0, "/app")
from api import _ensure_firebase_initialized
_ensure_firebase_initialized()
from firebase_admin import firestore

db = firestore.client()
# Top 3 más recientes por createdAt
projects = list(
    db.collection("projects")
    .order_by("createdAt", direction=firestore.Query.DESCENDING)
    .limit(3)
    .stream()
)

print(f"Top 3 proyectos más recientes:")
for p in projects:
    d = p.to_dict()
    print()
    print(f"  ID: {p.id}")
    print(f"  Title: {d.get('title','?')}")
    print(f"  Agent: {d.get('agentFile','?')}")
    print(f"  Status: {d.get('status','?')}")
    print(f"  Progress: {d.get('progress',{}).get('percent','?')}% - {d.get('progress',{}).get('stepName','?')}")
    print(f"  Created: {d.get('createdAt','?')}")
