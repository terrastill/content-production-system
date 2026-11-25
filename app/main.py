from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

APP_ENV = os.getenv("APP_ENV", "development")
DB_PATH = Path(os.getenv("DATABASE_PATH", "./data/content.sqlite3"))
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "./data/media"))
ALLOWED_WORKSPACE = os.getenv("ANYTHINGLLM_WORKSPACE_SLUG", "doing")
ANYTHINGLLM_BASE = os.getenv("ANYTHINGLLM_BASE_URL", "").rstrip("/")
ANYTHINGLLM_KEY = os.getenv("ANYTHINGLLM_API_KEY", "")
CMS_BASE = os.getenv("CMS_BASE_URL", "").rstrip("/")
CMS_TOKEN = os.getenv("CMS_API_TOKEN", "")
CMS_DRAFT_ENDPOINT = os.getenv("CMS_DRAFT_ENDPOINT", "")
CMS_PUBLISH_ENDPOINT = os.getenv("CMS_PUBLISH_ENDPOINT", "")

app = FastAPI(title="Industrial Content Production", version="0.1.0")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, industry TEXT NOT NULL, audience TEXT NOT NULL,
        keyword_or_topic TEXT NOT NULL, language TEXT NOT NULL, article_type TEXT NOT NULL,
        needs_images INTEGER NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, actor TEXT NOT NULL,
        action TEXT NOT NULL, from_status TEXT, to_status TEXT, detail TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    c.commit()
    return c


def audit(task_id: str, actor: str, action: str, from_status: str | None, to_status: str | None, detail: dict[str, Any]) -> None:
    c = conn()
    c.execute("INSERT INTO audit(task_id,actor,action,from_status,to_status,detail,created_at) VALUES(?,?,?,?,?,?,?)",
              (task_id, actor, action, from_status, to_status, json.dumps(detail), now()))
    c.commit(); c.close()


def get_task(task_id: str) -> dict[str, Any]:
    c = conn(); row = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone(); c.close()
    if not row: raise HTTPException(404, "task not found")
    result = dict(row); result["needs_images"] = bool(result["needs_images"]); result["data"] = json.loads(result["data"]); return result


class Brief(BaseModel):
    industry: str = Field(min_length=1, max_length=200)
    target_audience: str = Field(min_length=1, max_length=500)
    keyword_or_topic: str = Field(min_length=1, max_length=500)
    language: str = Field(min_length=2, max_length=80)
    article_type: str = Field(min_length=2, max_length=100)
    needs_images: bool = True


class Review(BaseModel):
    note: str = Field(default="", max_length=4000)


class Approval(BaseModel):
    note: str = Field(default="", max_length=4000)


def proposals(brief: Brief) -> list[dict[str, str]]:
    base = brief.keyword_or_topic.strip()
    return [{"title": f"How to Choose {base} for Your {brief.industry} Project", "angle": "buyer guide", "intent": "commercial investigation"},
            {"title": f"What Equipment Is Needed for {base}?", "angle": "equipment configuration", "intent": "solution research"},
            {"title": f"How Does {base} Work? Process and Equipment Guide", "angle": "process explanation", "intent": "informational"},
            {"title": f"{base}: Feedstock, Capacity and Site Requirements", "angle": "project planning", "intent": "project research"},
            {"title": f"How to Verify {base} Capacity Claims", "angle": "acceptance and procurement", "intent": "commercial investigation"},
            {"title": f"Batch vs Continuous {base}: How to Compare the Options", "angle": "route comparison", "intent": "solution comparison"},
            {"title": f"How to Prepare Feedstock Before Using {base}", "angle": "preparation", "intent": "technical guidance"},
            {"title": f"What Should Be Included in a {base} Proposal?", "angle": "RFQ checklist", "intent": "procurement"},
            {"title": f"Gas Handling and Environmental Questions for a {base} Project", "angle": "environmental scope", "intent": "technical validation"},
            {"title": f"What to Check Before Choosing a {base} Supplier", "angle": "supplier due diligence", "intent": "commercial investigation"}]


async def research(task: dict[str, Any]) -> dict[str, Any]:
    # Strictly scoped adapter. No other workspace can be queried.
    if not ANYTHINGLLM_BASE:
        return {"status": "UNAVAILABLE", "workspace": ALLOWED_WORKSPACE, "facts": [], "message": "AnythingLLM endpoint is not configured."}
    headers = {"Authorization": f"Bearer {ANYTHINGLLM_KEY}"} if ANYTHINGLLM_KEY else {}
    payload = {"message": f"Research verified enterprise facts for: {task['keyword_or_topic']}", "mode": "chat", "workspace": ALLOWED_WORKSPACE}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{ANYTHINGLLM_BASE}/api/v1/workspace/{ALLOWED_WORKSPACE}/chat", json=payload, headers=headers)
            r.raise_for_status()
            return {"status": "VERIFIED", "workspace": ALLOWED_WORKSPACE, "facts": r.json()}
    except Exception as exc:
        return {"status": "UNAVAILABLE", "workspace": ALLOWED_WORKSPACE, "facts": [], "message": str(exc)}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html><html><head><meta charset='utf-8'><title>Industrial Content</title><style>body{font:16px system-ui;max-width:760px;margin:40px auto;padding:0 20px}input,textarea,select,button{display:block;width:100%;margin:8px 0 16px;padding:10px;box-sizing:border-box}button{cursor:pointer}.note{background:#f4f4f4;padding:12px}</style></head><body><h1>Industrial Content Production</h1><p class='note'>Workflow: topics → research → draft → human review → CMS draft → approval → publish.</p><form id='f'><label>Industry<input name='industry' required></label><label>Target readers<textarea name='target_audience' required></textarea></label><label>Keyword / topic<input name='keyword_or_topic' required></label><label>Language<input name='language' value='English' required></label><label>Article type<select name='article_type'><option>Buyer guide</option><option>Process guide</option><option>Equipment comparison</option><option>Project planning</option></select></label><label><input type='checkbox' name='needs_images' checked> Need images</label><button>Create task</button></form><pre id='out'></pre><script>f.onsubmit=async e=>{e.preventDefault();let x=Object.fromEntries(new FormData(f));x.needs_images=!!f.needs_images.checked;x=await fetch('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(x)});out.textContent=JSON.stringify(await x.json(),null,2)}</script></body></html>"""


@app.post("/api/tasks")
def create_task(brief: Brief, request: Request):
    task_id = str(uuid.uuid4()); t = now(); data = {"brief": brief.model_dump(), "topics": proposals(brief), "research": None, "draft": None, "images": [], "cms": None}
    c = conn(); c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?)", (task_id, brief.industry, brief.target_audience, brief.keyword_or_topic, brief.language, brief.article_type, int(brief.needs_images), "TOPICS_READY", json.dumps(data), t, t)); c.commit(); c.close()
    audit(task_id, "user", "create_task", None, "TOPICS_READY", {"topics_count": 10}); return get_task(task_id)


@app.get("/api/tasks/{task_id}")
def task(task_id: str): return get_task(task_id)


@app.post("/api/tasks/{task_id}/research")
async def run_research(task_id: str):
    t = get_task(task_id); result = await research(t); old = t["status"]; t["data"]["research"] = result
    t["status"] = "RESEARCHED" if result["status"] == "VERIFIED" else "RESEARCH_UNAVAILABLE"; c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "system", "research", old, t["status"], result); return get_task(task_id)


@app.post("/api/tasks/{task_id}/draft")
def create_draft(task_id: str):
    t = get_task(task_id); old = t["status"]; research_status = (t["data"].get("research") or {}).get("status")
    if research_status != "VERIFIED": raise HTTPException(409, "verified AnythingLLM research is required before drafting")
    title = t["data"]["topics"][0]["title"]; t["data"]["draft"] = {"title": title, "body": "Draft generation adapter is ready; connect the approved LLM provider to generate the full article.", "sources": t["data"]["research"].get("facts", [])}; t["status"] = "DRAFT_READY"
    c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "system", "draft", old, t["status"], {"sources_status": research_status}); return get_task(task_id)


@app.post("/api/tasks/{task_id}/images")
async def upload_images(task_id: str, files: list[UploadFile] = File(...)):
    t = get_task(task_id); folder = MEDIA_ROOT / task_id; folder.mkdir(parents=True, exist_ok=True); saved = []
    for upload in files:
        name = Path(upload.filename or "image").name
        if Path(name).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}: raise HTTPException(400, "unsupported image type")
        target = folder / name; target.write_bytes(await upload.read()); saved.append({"filename": name, "path": str(target)})
    t["data"]["images"].extend(saved); old = t["status"]; t["status"] = "IMAGES_READY"; c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "user", "upload_images", old, t["status"], {"count": len(saved)}); return get_task(task_id)


@app.post("/api/tasks/{task_id}/review")
def review(task_id: str, review: Review):
    t = get_task(task_id); old = t["status"]
    if old not in {"DRAFT_READY", "IMAGES_READY"}: raise HTTPException(409, "draft and image review inputs are required")
    t["status"] = "REVIEWED"; t["data"]["review"] = review.model_dump(); c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "reviewer", "review", old, t["status"], review.model_dump()); return get_task(task_id)


@app.post("/api/tasks/{task_id}/cms-draft")
async def cms_draft(task_id: str):
    t = get_task(task_id)
    if t["status"] != "REVIEWED": raise HTTPException(409, "human review is required")
    if not CMS_DRAFT_ENDPOINT: result = {"status": "UNAVAILABLE", "message": "CMS draft endpoint is not configured"}
    else:
        headers = {"Authorization": f"Bearer {CMS_TOKEN}"}; payload = {"title": t["data"]["draft"]["title"], "body": t["data"]["draft"]["body"], "status": "draft"}
        try:
            async with httpx.AsyncClient(timeout=30) as client: r = await client.post(CMS_DRAFT_ENDPOINT, json=payload, headers=headers); r.raise_for_status(); result = {"status": "CREATED", "response": r.json()}
        except Exception as exc: result = {"status": "FAILED", "message": str(exc)}
    old = t["status"]; t["data"]["cms"] = result; t["status"] = "CMS_DRAFT" if result["status"] == "CREATED" else "CMS_DRAFT_UNAVAILABLE"; c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "system", "cms_draft", old, t["status"], result); return get_task(task_id)


@app.post("/api/tasks/{task_id}/approve")
def approve(task_id: str, approval: Approval):
    t = get_task(task_id)
    if t["status"] != "CMS_DRAFT": raise HTTPException(409, "a CMS draft must exist before approval")
    old = t["status"]; t["status"] = "APPROVED"; t["data"]["approval"] = approval.model_dump(); c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "approver", "approve", old, t["status"], approval.model_dump()); return get_task(task_id)


@app.post("/api/tasks/{task_id}/publish")
async def publish(task_id: str):
    t = get_task(task_id)
    if t["status"] != "APPROVED": raise HTTPException(409, "explicit approval is required")
    if not CMS_PUBLISH_ENDPOINT: raise HTTPException(503, "CMS publish endpoint is not configured")
    headers = {"Authorization": f"Bearer {CMS_TOKEN}"}; result: dict[str, Any]
    try:
        async with httpx.AsyncClient(timeout=30) as client: r = await client.post(CMS_PUBLISH_ENDPOINT, json={"draft": t["data"]["cms"]}, headers=headers); r.raise_for_status(); result = {"status": "PUBLISHED", "response": r.json()}
    except Exception as exc: result = {"status": "FAILED", "message": str(exc)}
    if result["status"] != "PUBLISHED": raise HTTPException(502, result["message"])
    old = t["status"]; t["status"] = "PUBLISHED"; t["data"]["publish"] = result; c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "publisher", "publish", old, t["status"], result); return get_task(task_id)


@app.get("/api/tasks/{task_id}/audit")
def task_audit(task_id: str):
    get_task(task_id); c = conn(); rows = c.execute("SELECT * FROM audit WHERE task_id=? ORDER BY id", (task_id,)).fetchall(); c.close(); return [dict(r) for r in rows]
