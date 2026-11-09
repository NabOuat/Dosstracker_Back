"""Tests pièces jointes (upload/download/delete) et reset mot de passe, avec Supabase simulé."""
import os
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("SUPABASE_URL", "http://x")
os.environ.setdefault("SUPABASE_KEY", "k")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "k")

import uuid
import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.deps import get_current_user
import app.api.v1.endpoints.pieces_jointes as pj
import app.api.v1.endpoints.auth as auth_mod

DOSSIER = str(uuid.uuid4())


def get_password_hash(p):  # hash factice : évite la dépendance à la version locale de bcrypt
    return 'h$' + 'x' * 14 + p[::-1].ljust(12, '_')


def verify_password(p, h):
    return h == get_password_hash(p)


class Res:
    def __init__(self, data):
        self.data = data


class FakeTable:
    def __init__(self, db, name):
        self.db, self.name, self.filters, self.op, self.payload = db, name, {}, "select", None

    def select(self, *_): self.op = "select"; return self
    def insert(self, row): self.op, self.payload = "insert", row; return self
    def update(self, row): self.op, self.payload = "update", row; return self
    def delete(self): self.op = "delete"; return self
    def eq(self, k, v): self.filters[k] = v; return self
    def order(self, *a, **k): return self

    def _match(self):
        return [r for r in self.db[self.name] if all(str(r.get(k)) == str(v) for k, v in self.filters.items())]

    def execute(self):
        if self.op == "insert":
            row = {"id": str(uuid.uuid4()), "created_at": "2026-01-01", **self.payload}
            self.db[self.name].append(row)
            return Res([row])
        if self.op == "update":
            rows = self._match()
            for r in rows:
                r.update(self.payload)
            return Res(rows)
        if self.op == "delete":
            rows = self._match()
            self.db[self.name] = [r for r in self.db[self.name] if r not in rows]
            return Res(rows)
        return Res(self._match())


class FakeBucket:
    def __init__(self, store): self.store = store
    def upload(self, path, data, opts=None): self.store[path] = data
    def remove(self, paths): [self.store.pop(p, None) for p in paths]
    def create_signed_url(self, path, ttl, opts=None):
        if path not in self.store:
            return {}
        return {"signedURL": f"https://sb/signed/{path}?token=t"}


class FakeSupabase:
    def __init__(self):
        self.db = {"dossiers": [{"id": DOSSIER}], "pieces_jointes": [], "users": []}
        self.files = {}
        self.storage = type("S", (), {"from_": lambda _s, b: FakeBucket(self.files)})()

    def table(self, name): return FakeTable(self.db, name)


@pytest.fixture
def sb(monkeypatch):
    fake = FakeSupabase()
    for mod in (pj, auth_mod):
        monkeypatch.setattr(mod, "get_supabase", lambda: fake)
    monkeypatch.setattr(pj, "get_supabase_admin", lambda: fake)
    app.dependency_overrides[get_current_user] = lambda: {"id": str(uuid.uuid4()), "service_id": 2}
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_upload_download_delete(sb, client):
    r = client.post(
        "/api/v1/pieces-jointes/upload",
        data={"dossier_id": DOSSIER},
        files={"file": ("../../etc/titre foncier é.pdf", b"%PDF-1.4 data", "application/pdf")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    path = body["url_stockage"]
    assert path in sb.files and sb.files[path] == b"%PDF-1.4 data"
    assert ".." not in path and " " not in path and path.startswith(DOSSIER + "/")

    d = client.get(f"/api/v1/pieces-jointes/{body['id']}/download")
    assert d.status_code == 200, d.text
    assert d.json()["url"].startswith("https://sb/signed/")

    assert client.delete(f"/api/v1/pieces-jointes/{body['id']}").status_code == 200
    assert path not in sb.files
    assert client.get(f"/api/v1/pieces-jointes/{body['id']}/download").status_code == 404


def test_upload_rejects_bad_extension(sb, client):
    r = client.post("/api/v1/pieces-jointes/upload", data={"dossier_id": DOSSIER},
                    files={"file": ("a.exe", b"x", "application/octet-stream")})
    assert r.status_code == 400


def test_reset_password_flow(sb, client, monkeypatch):
    monkeypatch.setattr(auth_mod, "get_password_hash", get_password_hash)
    sent = []
    monkeypatch.setattr(auth_mod.email_service, "send", lambda *a, **k: sent.append(a) or True)
    sb.db["users"].append({"id": "u1", "username": "agent", "nom_complet": "Agent", "email": "a@afor.ci",
                           "hashed_password": get_password_hash("OldPassword1")})

    # email inconnu : même réponse, aucun mail
    r = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@afor.ci"})
    assert r.status_code == 200 and not sent

    r = client.post("/api/v1/auth/forgot-password", json={"email": "a@afor.ci"})
    assert r.status_code == 200 and len(sent) == 1
    token = sent[0][3].split("/reset-password/")[1]

    assert client.post("/api/v1/auth/validate-reset-token", json={"token": token}).json()["username"] == "agent"
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "court"}).status_code == 422

    ok = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "NewPassword2"})
    assert ok.status_code == 200
    assert verify_password("NewPassword2", sb.db["users"][0]["hashed_password"])

    # usage unique
    assert client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "Another3Pass"}).status_code == 400
    assert client.post("/api/v1/auth/validate-reset-token", json={"token": "garbage"}).status_code == 400
