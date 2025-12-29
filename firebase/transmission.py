import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

cred = credentials.Certificate("mc-system-1a380-firebase-adminsdk-fbsvc-16af4e4f10.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

def on_snapshot(col_snapshot, changes, read_time):
    pass
