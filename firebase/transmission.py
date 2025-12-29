import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

import time
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IRRP_PATH = REPO_ROOT / "irrp.py"
CODES_PATH = REPO_ROOT / "codes"


cred = credentials.Certificate("/home/chika/Projects/mc_beam/firebase/mc-system-1a380-firebase-adminsdk-fbsvc-16af4e4f10.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

def on_snapshot(col_snapshot, changes, read_time):
    for doc in col_snapshot:
        print(f"{doc.id}")

        doc_dict = doc.to_dict()

        send_command(doc_dict["name"], doc_dict["code"])
        doc.reference.update({"state": False})

def send_command(name: str, code: str) -> bool:
    try:
        subprocess.run(
            [
                sys.executable,
                str(IRRP_PATH),
                "-p",
                "-g17",
                "-f",
                str(CODES_PATH),
                "--code",
                code,
            ],
            check=True,
        )
    
        return True
    except subprocess.CalledProcessError as e:
        return False



# col_query = db.collection('codes').where('state', '==', True)
col_query = db.collection('codes').where(filter=FieldFilter("state", "==", True))
query_watch = col_query.on_snapshot(on_snapshot)

try:
    while True:
        # send_sensor_data(25.5, 60) # データ送信
        time.sleep(60)
except KeyboardInterrupt:
    print("終了します")