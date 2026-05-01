"""Update project status to completed in Firebase."""
import firebase_admin
from firebase_admin import credentials, firestore
import os

try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate("/app/firebase-admin.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
doc_ref = db.collection("projects").document("3N2sQDJsHxrU4nwazdue")
doc_ref.update({
    "status": "completed",
    "progress.percent": 100,
    "progress.stepName": "¡Documental completado! 🏆",
    "output.videoPath": "/app/output/videos/Las_torturas_de_la_Santa_Inquisici_n/FINAL_Las_torturas_de_la_Santa_Inquisici_n.mp4",
    "output.audioPath": "/app/output/videos/Las_torturas_de_la_Santa_Inquisici_n/audio/master_google_narration.mp3",
})
print("✅ Status updated to completed!")
