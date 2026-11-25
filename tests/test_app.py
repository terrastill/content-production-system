import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("ANYTHINGLLM_BASE_URL", "")
    monkeypatch.setenv("CMS_DRAFT_ENDPOINT", "")
    monkeypatch.setenv("CMS_PUBLISH_ENDPOINT", "")
    import importlib
    import app.main as main
    importlib.reload(main)
    return main, TestClient(main.app)


def brief():
    return {"industry":"biomass carbonization", "target_audience":"industrial buyers", "keyword_or_topic":"biomass carbonization machine", "language":"English", "article_type":"Buyer guide", "needs_images":True}


def test_creates_ten_topics(tmp_path, monkeypatch):
    _, client = load_app(tmp_path, monkeypatch)
    r = client.post("/api/tasks", json=brief())
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]["topics"]) == 10
    assert body["status"] == "TOPICS_READY"


def test_publish_requires_approval_and_cms_draft(tmp_path, monkeypatch):
    _, client = load_app(tmp_path, monkeypatch)
    task = client.post("/api/tasks", json=brief()).json()
    task_id = task["id"]
    assert client.post(f"/api/tasks/{task_id}/publish").status_code == 409
    assert client.post(f"/api/tasks/{task_id}/research").status_code == 200
    assert client.post(f"/api/tasks/{task_id}/draft").status_code == 409
    # No CMS endpoint means draft creation stays unavailable and approval remains blocked.
    reviewed = client.post(f"/api/tasks/{task_id}/review", json={"note":"reviewed"})
    assert reviewed.status_code == 409
    assert client.post(f"/api/tasks/{task_id}/cms-draft").status_code == 409


def test_audit_is_written(tmp_path, monkeypatch):
    _, client = load_app(tmp_path, monkeypatch)
    task = client.post("/api/tasks", json=brief()).json()
    audit = client.get(f"/api/tasks/{task['id']}/audit").json()
    assert len(audit) == 1
    assert audit[0]["action"] == "create_task"


def test_image_extension_allowlist(tmp_path, monkeypatch):
    _, client = load_app(tmp_path, monkeypatch)
    task = client.post("/api/tasks", json=brief()).json()
    r = client.post(f"/api/tasks/{task['id']}/images", files={"files": ("bad.exe", b"no", "application/octet-stream")})
    assert r.status_code == 400
