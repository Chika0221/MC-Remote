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

def on_send_snapshot(col_snapshot, changes, read_time):
    print("わ")
    for doc in col_snapshot:
        print(f"{doc.id}")

        doc_dict = doc.to_dict()

        send_command(doc_dict["name"], doc_dict["code"])
        doc.reference.update({"state": False})

def on_get_snapshot(col_snapshot, changes, read_time):
    print("あ")
    for doc in col_snapshot:
        print(f"{doc.id}")

        doc_dict = doc.to_dict()

        get_command()

        db.collection("codes").document().set({
            "name": doc_dict["name"],
            "code": "[wawawa]",
            "state": False,
        })
        doc.reference.delete()

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


def get_command():
    pass


# col_query = db.collection('codes').where('state', '==', True)
send_query = db.collection("codes").where(filter=FieldFilter("state", "==", True))
send_query_watch = send_query.on_snapshot(on_send_snapshot)

get_query = db.collection("unregisteredCodes")
get_query_watch = get_query.on_snapshot(on_get_snapshot)


try:
    while True:
        # send_sensor_data(25.5, 60) # データ送信
        time.sleep(60)
except KeyboardInterrupt:
    print("終了します")