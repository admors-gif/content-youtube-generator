"""Populate imageUrl for all scenes in the completed Inquisition project."""
import firebase_admin
from firebase_admin import credentials, firestore
import os

try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate("/app/firebase-admin.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
PROJECT_ID = "3N2sQDJsHxrU4nwazdue"
VPS_BASE = "http://100.99.207.113:8085"
PROJECT_DIR = "Las_torturas_de_la_Santa_Inquisici_n"

doc_ref = db.collection("projects").document(PROJECT_ID)
project = doc_ref.get().to_dict()
scenes = project.get("scenes", [])

print(f"📸 Updating {len(scenes)} scenes with image URLs...")

for i, scene in enumerate(scenes):
    scene_num = str(i + 1).zfill(4)
    scene["imageUrl"] = f"{VPS_BASE}/images/{PROJECT_DIR}/scene_{scene_num}.png"

doc_ref.update({"scenes": scenes})
print(f"✅ All {len(scenes)} scenes updated with imageUrl!")
