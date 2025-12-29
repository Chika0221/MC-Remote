from typing import Any

import json
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

app = FastAPI()

REPO_ROOT = Path(__file__).resolve().parent.parent
IRRP_PATH = REPO_ROOT / "irrp.py"
CODES_PATH = REPO_ROOT / "codes"


def parse_code_input(value: Any) -> list[int]:
    """Parse request `code` into list[int] (microseconds).

    Accepts either:
    - JSON list string: "[9000,4500,560,...]"
    - CSV/space separated string: "9000,4500,560 ..."
    - JSON array: [9000, 4500, 560, ...]
    """
    if value is None:
        raise ValueError("code is required")

    if isinstance(value, list):
        if not value:
            raise ValueError("code must contain at least one value")
        out: list[int] = []
        for item in value:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise ValueError("code items must be numbers")
            ii = int(item)
            if ii <= 0:
                raise ValueError("code items must be positive microseconds")
            out.append(ii)
        return out

    if not isinstance(value, str):
        raise ValueError("code must be a string or a list")

    raw = value.strip()
    if not raw:
        raise ValueError("code must contain at least one value")

    # JSON list form.
    if raw.startswith('['):
        try:
            parsed = json.loads(raw)
        except Exception as e:
            raise ValueError("invalid JSON list") from e
        return parse_code_input(parsed)

    # CSV / whitespace / semicolon separated.
    parts = raw.replace(';', ' ').replace(',', ' ').split()
    if not parts:
        raise ValueError("code must contain at least one value")
    out: list[int] = []
    for p in parts:
        try:
            ii = int(float(p))
        except Exception as e:
            raise ValueError("code items must be numbers") from e
        if ii <= 0:
            raise ValueError("code items must be positive microseconds")
        out.append(ii)
    return out


class IRSendRequest(BaseModel):
    name: str
    code: str

    @field_validator("name")
    @classmethod
    def _name_required(cls, v: str) -> str:
        vv = v.strip()
        if not vv:
            raise ValueError("name is required")
        return vv

    @field_validator("code")
    @classmethod
    def _code_required(cls, v: str) -> str:
        if v is None:
            raise ValueError("code is required")
        vv = v.strip()
        if not vv:
            raise ValueError("code must contain at least one value")
        return vv

# @app.get("/hello")
# async def hello():
#     return {"message": "Hello World"}

# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: Union[str, None] = None):
#     return {"item_id": item_id, "q": q}



# このエンドポイントではjsonで受けて対応する
# {
#   name: "aircon:on"
#   code: "[3388, 1502, 446, 421, 446, 421, 446, 421, 446, 1288, 446, 421, 446, 1288, 446, 421, 446, 421, 446, 1288, 446, 421, 446, 421, 446, 421, 446, 421, 446, 1288, 446, 1288, 446, 421, 446, 1288, 446, 421, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 421, 446, 421, 446, 421, 446, 1288, 446, 421, 446, 421, 446, 1288, 446, 421, 446, 421, 446, 421, 446, 1288, 446, 421, 446, 1288, 446, 1288, 446, 421, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 421, 446, 421, 446, 1288, 446, 1288, 446, 1288, 446, 421, 446, 1288, 446, 421, 446, 1288, 446, 1288, 446, 421, 446, 421, 446, 421, 446, 1288, 446, 421, 446, 10965, 3388, 1502, 446, 421, 446, 421, 446, 421, 446, 1288, 446, 421, 446, 1288, 446, 421, 446, 421, 446, 1288, 446, 421, 446, 421, 446, 421, 446, 421, 446, 1288, 446, 1288, 446, 421, 446, 1288, 446, 421, 446, 1288, 446, 1288, 446, 421, 446, 1288, 446, 1288, 446, 421, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 10965, 3388, 1502, 446, 421, 446, 421, 446, 421, 446, 1288, 446, 421, 446, 1288, 446, 421, 446, 421, 446, 1288, 446, 421, 446, 421, 446, 421, 446, 421, 446, 1288, 446, 1288, 446, 421, 446, 1288, 446, 421, 446, 1288, 446, 1288, 446, 421, 446, 421, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 1288, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446, 421, 446]"
# }
@app.post("/ir/send")
async def send_code(doc: IRSendRequest):
    if not IRRP_PATH.exists():
        raise HTTPException(status_code=500, detail=f"irrp.py not found at {IRRP_PATH}")

    # doc.code is a string in JSON, so parse it server-side.
    try:
        code_list = parse_code_input(doc.code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    code_json = json.dumps(code_list)

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
                code_json,
            ],
            check=True,
        )

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"irrp.py failed: {e}")

    return {"message": "Success", "name": doc.name, "code_len": len(code_list)}

