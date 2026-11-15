"""Descoberta somente leitura da API Times Connected.

Uso (PowerShell):
  $env:CONNECTED_USER="..."; $env:CONNECTED_PASSWORD="..."
  uv run python scripts/discover.py [typeClass]

Grava respostas sanitizadas em tests/fixtures/. Nunca chama student-history.
"""
import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

BASE = "https://controllercore.timescontroller.com.br/"
FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
SENSITIVE = re.compile(
    r"token|password|email|cpf|phone|telefone|celular|name|nome|^link$|meet_password|meet_hash", re.I
)
JWT = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+")


def sanitize(obj, secrets=()):
    if isinstance(obj, dict):
        return {k: ("<redacted>" if SENSITIVE.search(str(k)) else sanitize(v, secrets))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v, secrets) for v in obj]
    if isinstance(obj, str):
        obj = JWT.sub("<redacted>", obj)
        for s in secrets:
            if s and s in obj:
                obj = obj.replace(s, "<redacted>")
    return obj


def summarize(obj, depth=0, max_depth=4):
    pad = "  " * depth
    if depth > max_depth:
        return pad + "..."
    if isinstance(obj, dict):
        lines = []
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}{k}: {type(v).__name__}")
                lines.append(summarize(v, depth + 1, max_depth))
            else:
                lines.append(f"{pad}{k}: {type(v).__name__}")
        return "\n".join(lines)
    if isinstance(obj, list):
        head = f"{pad}[len={len(obj)}]"
        if obj:
            return head + "\n" + summarize(obj[0], depth + 1, max_depth)
        return head
    return pad + type(obj).__name__


def find_token(obj):
    """Procura recursivamente uma string em chave contendo 'token'."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if "token" in str(k).lower() and isinstance(v, str) and v:
                return v
        for v in obj.values():
            t = find_token(v)
            if t:
                return t
    elif isinstance(obj, list):
        for v in obj:
            t = find_token(v)
            if t:
                return t
    return None


def body_of(resp):
    try:
        return resp.json()
    except ValueError:
        return None


def report(label, resp, secrets, fixture):
    body = body_of(resp)
    print(f"\n=== {label}: HTTP {resp.status_code} ===")
    if body is None:
        print("(corpo nao-JSON)")
        return None
    if resp.is_success:
        print(summarize(body))
        FIXTURES.mkdir(parents=True, exist_ok=True)
        path = FIXTURES / fixture
        path.write_text(json.dumps(sanitize(body, secrets), indent=2, ensure_ascii=False),
                        encoding="utf-8")
        print(f"-> gravado {path.name}")
    else:
        if isinstance(body, dict):
            print("keys:", list(body.keys()))
            msg = body.get("message") or body.get("error")
            if isinstance(msg, str):
                print("message:", msg)
        else:
            print("tipo:", type(body).__name__)
    return body


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return 0
    user = os.environ.get("CONNECTED_USER")
    password = os.environ.get("CONNECTED_PASSWORD")
    if not user or not password:
        print("Defina CONNECTED_USER e CONNECTED_PASSWORD.", file=sys.stderr)
        return 2
    type_class = sys.argv[1] if len(sys.argv) > 1 else "1"
    secrets = [password]

    with httpx.Client(base_url=BASE, timeout=30, headers={"Accept": "application/json"}) as c:
        r = c.post("api/auth/student-login", json={"user": user, "password": password})
        login = report("student-login", r, secrets, "login.json")
        token = find_token(login) if login else None
        student_id = None
        if isinstance(login, dict) and login.get("studentId") is not None:
            student_id = str(login["studentId"])
        print(f"token encontrado: {bool(token)}; student_id encontrado: {student_id is not None}")
        if token:
            secrets.append(token)
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        r = c.get("api/next-classes", headers=headers)
        report("next-classes", r, secrets, "next_classes.json")

        if student_id:
            r = c.get(f"api/student/get-allowed-classes-by-student/{student_id}", headers=headers)
            report("allowed-classes", r, secrets, "allowed_classes.json")

        today = date.today()
        payload = {
            "beginDate": today.isoformat(),
            "endDate": (today + timedelta(days=7)).isoformat(),
            "studentId": student_id,
            "typeClass": type_class,
        }
        r = c.post("api/class-type/day-by-day-new", json=payload, headers=headers)
        report("day-by-day-new", r, secrets, "day_by_day.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
