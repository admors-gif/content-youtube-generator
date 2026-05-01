"""Quick utility to list all projects in Firebase."""
import firebase_admin
from firebase_admin import credentials, firestore
import os

cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/app/firebase-admin.json")
if not os.path.exists(cred_path):
    cred_path = "firebase-admin.json"

try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()
for d in db.collection("projects").stream():
    data = d.to_dict()
    print(f"{d.id} | {data.get('title','')[:60]} | {data.get('status','')}")
