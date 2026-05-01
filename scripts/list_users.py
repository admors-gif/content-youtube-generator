"""List all users in Firestore with their emails and credits."""
import firebase_admin
from firebase_admin import credentials, firestore

try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate("/app/firebase-admin.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
users = db.collection("users").stream()

print("=" * 70)
print("👥 USUARIOS REGISTRADOS EN CONTENT FACTORY")
print("=" * 70)

for u in users:
    data = u.to_dict()
    uid = u.id
    email = data.get("email", "???")
    name = data.get("displayName", "???")
    plan = data.get("plan", "???")
    credits = data.get("credits", {})
    included = credits.get("included", 0)
    used = credits.get("used", 0)
    extra = credits.get("extra", 0)
    available = max(0, included - used) + extra
    
    # Count projects
    projects = list(db.collection("projects").where("userId", "==", uid).stream())
    
    print(f"\n🔑 UID: {uid}")
    print(f"   📧 Email: {email}")
    print(f"   👤 Nombre: {name}")
    print(f"   💎 Plan: {plan}")
    print(f"   💰 Créditos: {available} disponibles (included={included}, used={used}, extra={extra})")
    print(f"   📁 Proyectos: {len(projects)}")
    for p in projects:
        pd = p.to_dict()
        print(f"      - [{pd.get('status','?')}] {pd.get('title','Sin título')}")

print(f"\n{'='*70}")
