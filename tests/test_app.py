import importlib

from fastapi.testclient import TestClient


def load_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path / "media"))
    monkeypatch.setenv("VECTOR_STORE_BASE_URL", "")
    monkeypatch.setenv("CMS_DRAFT_ENDPOINT", "")
    monkeypatch.setenv("CMS_PUBLISH_ENDPOINT", "")
    monkeypatch.setenv("CMS_VERIFY_ENDPOINT", "")
    import app.main as main
    importlib.reload(main)
    return main, TestClient(main.app)


def brief(article=True):
    return {"industry": "biomass carbonization", "target_audience": "industrial buyers", "keyword_or_topic": "biomass carbonization machine", "language": "English", "article_type": "Buyer guide", "needs_images": True, "title": "Biomass Carbonization Machine Buyer Guide" if article else "", "content_html": "<h1>Biomass Carbonization Machine Buyer Guide</h1><p>Reviewed body.</p>" if article else ""}


def test_creates_ten_topics_and_article_ready(tmp_path, monkeypatch):
    _, client = load_app(tmp_path, monkeypatch)
    response = client.post("/api/tasks", json=brief())
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]["topics"]) == 10
    assert body["status"] == "ARTICLE_READY"


def test_publish_requires_review_draft_and_approval(tmp_path, monkeypatch):
    _, client = load_app(tmp_path, monkeypatch)
    task = client.post("/api/tasks", json=brief()).json()
    task_id = task["id"]
    assert client.post(f"/api/tasks/{task_id}/publish").status_code == 409
    assert client.post(f"/api/tasks/{task_id}/cms-draft").status_code == 409
    assert client.post(f"/api/tasks/{task_id}/review", json={"note": "reviewed"}).status_code == 200
    # No endpoint means CMS draft is unavailable; approval and publish remain blocked.
    draft = client.post(f"/api/tasks/{task_id}/cms-draft")
    assert draft.status_code == 200
    assert draft.json()["status"] == "CMS_DRAFT_UNAVAILABLE"
    assert client.post(f"/api/tasks/{task_id}/approve", json={"note": "approved"}).status_code == 409


def test_audit_is_written_without_secrets(tmp_path, monkeypatch):
    _, client = load_app(tmp_path, monkeypatch)
    task = client.post("/api/tasks", json=brief()).json()
    events = client.get(f"/api/tasks/{task['id']}/audit").json()
    assert len(events) == 1
    assert events[0]["action"] == "create_task"
    assert "password" not in events[0]["detail"].lower()


def test_image_extension_allowlist(tmp_path, monkeypatch):
    _, client = load_app(tmp_path, monkeypatch)
    task = client.post("/api/tasks", json=brief()).json()
    response = client.post(f"/api/tasks/{task['id']}/images", files={"files": ("bad.exe", b"no", "application/octet-stream")})
    assert response.status_code == 400


def test_config_never_returns_secret(tmp_path, monkeypatch):
    _, client = load_app(tmp_path, monkeypatch)
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json()["secrets_are_not_returned"] is True
