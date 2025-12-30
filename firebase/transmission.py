import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

import json
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
    # IMPORTANT: Updating a document triggers this callback again.
    # Process only newly added docs to avoid re-processing on state updates.
    for change in changes:
        change_type = getattr(change.type, "name", str(change.type))
        if change_type != "ADDED":
            continue

        doc = change.document
        print(f"{doc.id}")

        doc_dict = doc.to_dict()
        name = (doc_dict.get("name") or "").strip()
        if not name:
            doc.reference.update({"state": "error", "error": "name is required"})
            continue

        # Notify clients that IR read is in progress.
        doc.reference.update({"state": "reading"})

        try:
            code_list = get_command(name)
        except Exception as e:
            doc.reference.update({"state": "error", "error": str(e)})
            continue

        db.collection("codes").document().set({
            "name": name,
            "code": json.dumps(code_list),
            "state": False,
        })

        # Optional: briefly mark as done before removal.
        doc.reference.update({"state": "done"})
        time.sleep(3)
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


def get_command(name: str) -> list[int]:
    """Record one IR code for `name` and return it as list[int] microseconds.

    Uses irrp.py record mode and reads the newly-recorded code from stdout.
    """

    # python3 irrp.py -r -g18 -f codes light:on --no-confirm --post 130
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(IRRP_PATH),
                "-r",
                "-g18",
                "-f",
                str(CODES_PATH),
                name,
                "--no-confirm",
                "--post",
                str(130),
                "--export",
                "-",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        raise RuntimeError(f"irrp.py record failed: {stderr or e}") from e

    # irrp.py should print ONLY a JSON dict like {"name": [..]} to stdout when using --export -.
    # Be tolerant anyway: grab the last line that looks like JSON.
    stdout = proc.stdout or ""
    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError("irrp.py returned no exported JSON on stdout")

    json_line = None
    for ln in reversed(lines):
        if (ln.startswith("{") and ln.endswith("}")) or (ln.startswith("[") and ln.endswith("]")):
            json_line = ln
            break
    if json_line is None:
        tail = "\\n".join(lines[-5:])
        raise RuntimeError(f"irrp.py stdout did not contain JSON. tail=\\n{tail}")

    try:
        exported = json.loads(json_line)
    except Exception as e:
        raise RuntimeError(f"failed to parse irrp.py JSON line: {json_line[:200]}") from e

    if not isinstance(exported, dict) or name not in exported:
        raise RuntimeError(f"exported JSON did not include key '{name}'")

    code_list = exported[name]
    if not isinstance(code_list, list) or not code_list:
        raise RuntimeError("recorded code is empty")
    out: list[int] = []
    for item in code_list:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise RuntimeError("recorded code contained non-numeric item")
        out.append(int(item))
    return out


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