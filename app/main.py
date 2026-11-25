from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

APP_ENV = os.getenv("APP_ENV", "development")
DB_PATH = Path(os.getenv("DATABASE_PATH", "./data/content.sqlite3"))
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "./data/media"))
VECTOR_BASE = os.getenv("VECTOR_STORE_BASE_URL", "").rstrip("/")
MODEL_BASE = os.getenv("ARTICLE_MODEL_BASE_URL", "").rstrip("/")
CMS_BASE = os.getenv("CMS_BASE_URL", "").rstrip("/")
CMS_LOGIN_URL = os.getenv("CMS_LOGIN_URL", "")
CMS_DRAFT_ENDPOINT = os.getenv("CMS_DRAFT_ENDPOINT", "")
CMS_PUBLISH_ENDPOINT = os.getenv("CMS_PUBLISH_ENDPOINT", "")
CMS_VERIFY_ENDPOINT = os.getenv("CMS_VERIFY_ENDPOINT", "")
CMS_TOKEN = os.getenv("CMS_API_TOKEN", "")

app = FastAPI(title="Industrial Content Production", version="0.2.0")


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


def audit(task_id: str, actor: str, action: str, old: str | None, new: str | None, detail: dict[str, Any]) -> None:
    c = conn()
    safe = {k: v for k, v in detail.items() if k.lower() not in {"password", "token", "api_key", "authorization"}}
    c.execute("INSERT INTO audit(task_id,actor,action,from_status,to_status,detail,created_at) VALUES(?,?,?,?,?,?,?)",
              (task_id, actor, action, old, new, json.dumps(safe), now()))
    c.commit(); c.close()


def get_task(task_id: str) -> dict[str, Any]:
    c = conn(); row = c.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone(); c.close()
    if not row:
        raise HTTPException(404, "task not found")
    result = dict(row)
    result["needs_images"] = bool(result["needs_images"])
    result["data"] = json.loads(result["data"])
    return result


class Brief(BaseModel):
    industry: str = Field(min_length=1, max_length=200)
    target_audience: str = Field(default="industrial buyers", max_length=500)
    keyword_or_topic: str = Field(min_length=1, max_length=500)
    language: str = Field(default="English", min_length=2, max_length=80)
    article_type: str = Field(default="Buyer guide", min_length=2, max_length=100)
    needs_images: bool = True
    title: str = Field(default="", max_length=300)
    content_html: str = Field(default="", max_length=300000)
    meta_title: str = Field(default="", max_length=300)
    meta_description: str = Field(default="", max_length=1000)
    category_id: str = Field(default="", max_length=100)
    cms_login_url: str = Field(default="", max_length=1000)


class Review(BaseModel):
    note: str = Field(default="", max_length=4000)


class Approval(BaseModel):
    note: str = Field(default="", max_length=4000)


def proposals(brief: Brief) -> list[dict[str, str]]:
    base = brief.keyword_or_topic.strip()
    return [
        {"title": f"How to Choose {base} for Your {brief.industry} Project", "angle": "buyer guide", "intent": "commercial investigation"},
        {"title": f"What Equipment Is Needed for {base}?", "angle": "equipment configuration", "intent": "solution research"},
        {"title": f"How Does {base} Work? Process and Equipment Guide", "angle": "process explanation", "intent": "informational"},
        {"title": f"{base}: Feedstock, Capacity and Site Requirements", "angle": "project planning", "intent": "project research"},
        {"title": f"How to Verify {base} Capacity Claims", "angle": "acceptance and procurement", "intent": "commercial investigation"},
        {"title": f"Batch vs Continuous {base}: How to Compare the Options", "angle": "route comparison", "intent": "solution comparison"},
        {"title": f"How to Prepare Feedstock Before Using {base}", "angle": "preparation", "intent": "technical guidance"},
        {"title": f"What Should Be Included in a {base} Proposal?", "angle": "RFQ checklist", "intent": "procurement"},
        {"title": f"Gas Handling and Environmental Questions for a {base} Project", "angle": "environmental scope", "intent": "technical validation"},
        {"title": f"What to Check Before Choosing a {base} Supplier", "angle": "supplier due diligence", "intent": "commercial investigation"},
    ]


def safe_cms_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {CMS_TOKEN}"} if CMS_TOKEN else {}


def endpoint(template: str, cms_id: str = "") -> str:
    return template.replace("{id}", cms_id) if template else ""


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "environment": APP_ENV}


@app.get("/api/config")
def config_status() -> dict[str, Any]:
    return {
        "vector_store": {"configured": bool(VECTOR_BASE)},
        "article_model": {"configured": bool(MODEL_BASE)},
        "cms": {"configured": bool(CMS_BASE or CMS_DRAFT_ENDPOINT), "login_url": CMS_LOGIN_URL, "password_configured": bool(CMS_TOKEN or os.getenv("CMS_SERVICE_PASSWORD"))},
        "secrets_are_not_returned": True,
    }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>工业文章一键发布</title><style>
:root{color-scheme:dark}body{font:15px system-ui,-apple-system,sans-serif;max-width:1040px;margin:0 auto;padding:28px;background:#10141b;color:#e8edf5}h1{margin:0 0 8px}.sub{color:#9da9b8}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{background:#18212c;border:1px solid #2b3948;border-radius:12px;padding:18px;margin:16px 0}label{display:block;color:#b9c5d2;margin:10px 0 5px}input,textarea,select,button{font:inherit;border-radius:7px;border:1px solid #425262;padding:10px;box-sizing:border-box;width:100%;background:#0f1720;color:#eef4fb}textarea{min-height:120px;resize:vertical}.html{min-height:260px}button{background:#2374d8;border:0;cursor:pointer;font-weight:600;margin-top:10px}button.secondary{background:#344454}button.danger{background:#a94343}.row{display:flex;gap:10px}.row>*{flex:1}.status{padding:12px;border-radius:8px;background:#0d1722;white-space:pre-wrap;word-break:break-word}.warn{color:#ffcf70}.ok{color:#71e0a0}.small{font-size:13px;color:#9da9b8}a{color:#7db8ff}.hidden{display:none}@media(max-width:720px){.grid{grid-template-columns:1fr}}
</style></head><body><h1>工业文章一键发布</h1><p class='sub'>文章 → 人工审核 → CMS 草稿 → 批准并发布。密码只在服务器运行环境中配置，不在此页面保存或显示。</p>
<div class='card'><h2>1. 文章与 CMS 配置</h2><div class='grid'><div><label>行业 *</label><input id='industry' placeholder='例如 biomass carbonization'><label>目标读者</label><input id='audience' value='industrial buyers'><label>关键词/主题 *</label><input id='topic' placeholder='例如 biomass carbonization machine'><label>语言</label><input id='language' value='English'><label>文章类型</label><select id='type'><option>Buyer guide</option><option>Process guide</option><option>Equipment comparison</option><option>Project planning</option></select></div><div><label>CMS 后台登录网址</label><input id='login' placeholder='https://.../admin'><label>CMS 栏目 ID</label><input id='category' placeholder='例如 53'><label>文章标题 *</label><input id='title' placeholder='已审核的文章标题'><label>Meta Title</label><input id='metaTitle'><label>Meta Description</label><textarea id='metaDescription'></textarea></div></div><label>文章 HTML（已审核正文） *</label><textarea id='html' class='html' placeholder='<h1>...</h1><p>...</p>'></textarea><label><input id='needsImages' type='checkbox' checked style='width:auto'> 需要图片</label><div class='row'><button id='create'>创建任务</button><button id='draft' class='secondary' disabled>创建 CMS 草稿</button><button id='approve' class='secondary' disabled>批准发布</button><button id='publish' class='danger' disabled>一键发布</button></div></div>
<div class='grid'><div class='card'><h2>2. 图片</h2><input id='images' type='file' multiple accept='.png,.jpg,.jpeg,.webp,.svg'><button id='upload' class='secondary' disabled>上传图片到任务</button><p class='small'>正式 CMS 媒体上传仍需配置 CMS_MEDIA_ENDPOINT；本地图片会留在任务媒体目录。</p></div><div class='card'><h2>3. 状态与审计</h2><div id='status' class='status'>尚未创建任务</div><button id='review' class='secondary' disabled>标记人工审核通过</button><button id='audit' class='secondary' disabled>刷新审计记录</button></div></div><div class='card'><h2>安全提示</h2><p class='small'>CMS 草稿创建、批准和正式发布是三个独立动作。没有人工审核和批准，发布按钮不会生效。未配置真实 CMS 接口时，系统只会明确显示 UNAVAILABLE，不会伪造成功。</p></div><script>
let taskId='';const $=id=>document.getElementById(id);const show=x=>{$('status').textContent=JSON.stringify(x,null,2)};async function api(path,opt={}){let r=await fetch(path,opt);let x=await r.json();if(!r.ok)throw new Error((x.detail||x.message||r.status));return x}function brief(){return {industry:$('industry').value,target_audience:$('audience').value,keyword_or_topic:$('topic').value,language:$('language').value,article_type:$('type').value,needs_images:$('needsImages').checked,title:$('title').value,content_html:$('html').value,meta_title:$('metaTitle').value,meta_description:$('metaDescription').value,category_id:$('category').value,cms_login_url:$('login').value}}function enable(){['draft','review','audit','upload'].forEach(x=>$(x).disabled=false)}$('create').onclick=async()=>{try{let x=await api('/api/tasks',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(brief())});taskId=x.id;enable();show(x)}catch(e){show({error:e.message})}};$('review').onclick=async()=>{try{show(await api(`/api/tasks/${taskId}/review`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({note:'人工审核通过，允许创建 CMS 草稿'})}));$('draft').disabled=false}catch(e){show({error:e.message})}};$('draft').onclick=async()=>{try{let x=await api(`/api/tasks/${taskId}/cms-draft`,{method:'POST'});show(x);if(x.status==='CMS_DRAFT'){$('approve').disabled=false}}catch(e){show({error:e.message})}};$('approve').onclick=async()=>{try{show(await api(`/api/tasks/${taskId}/approve`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({note:'明确批准正式发布'})}));$('publish').disabled=false}catch(e){show({error:e.message})}};$('publish').onclick=async()=>{if(!confirm('确认正式发布？此操作会写入 CMS。'))return;try{show(await api(`/api/tasks/${taskId}/publish`,{method:'POST'}))}catch(e){show({error:e.message})}};$('audit').onclick=async()=>{try{show(await api(`/api/tasks/${taskId}/audit`))}catch(e){show({error:e.message})}};$('upload').onclick=async()=>{try{let f=new FormData();for(let x of $('images').files)f.append('files',x);show(await api(`/api/tasks/${taskId}/images`,{method:'POST',body:f}))}catch(e){show({error:e.message})}};
</script></body></html>"""


@app.post("/api/tasks")
def create_task(brief: Brief):
    task_id, t = str(uuid.uuid4()), now()
    article = {"title": brief.title.strip(), "body": brief.content_html, "meta_title": brief.meta_title, "meta_description": brief.meta_description, "category_id": brief.category_id, "cms_login_url": brief.cms_login_url}
    status = "ARTICLE_READY" if article["title"] and article["body"].strip() else "TOPICS_READY"
    data = {"brief": brief.model_dump(), "topics": proposals(brief), "research": None, "article": article, "images": [], "cms": None, "review": None, "approval": None, "publish": None}
    c = conn(); c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?)", (task_id, brief.industry, brief.target_audience, brief.keyword_or_topic, brief.language, brief.article_type, int(brief.needs_images), status, json.dumps(data), t, t)); c.commit(); c.close()
    audit(task_id, "user", "create_task", None, status, {"topics_count": 10, "article_supplied": bool(article["body"])})
    return get_task(task_id)


@app.get("/api/tasks/{task_id}")
def task(task_id: str):
    return get_task(task_id)


@app.post("/api/tasks/{task_id}/research")
async def run_research(task_id: str):
    t = get_task(task_id); old = t["status"]
    result = {"status": "UNAVAILABLE", "message": "External vector-store adapter is not configured."}
    t["data"]["research"] = result; t["status"] = "RESEARCH_UNAVAILABLE"
    c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "system", "research", old, t["status"], result)
    return get_task(task_id)


@app.post("/api/tasks/{task_id}/draft")
def create_article_draft(task_id: str):
    t = get_task(task_id)
    if not t["data"].get("article", {}).get("body"):
        raise HTTPException(409, "an approved article HTML body is required")
    if t["status"] not in {"ARTICLE_READY", "REVIEWED"}:
        raise HTTPException(409, "article must be ready or human-reviewed")
    t["data"]["article"]["title"] = t["data"]["article"]["title"] or t["data"]["topics"][0]["title"]
    old = t["status"]; t["status"] = "DRAFT_READY"
    c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "system", "local_draft", old, t["status"], {"body_length": len(t["data"]["article"]["body"])})
    return get_task(task_id)


@app.post("/api/tasks/{task_id}/images")
async def upload_images(task_id: str, files: list[UploadFile] = File(...)):
    t = get_task(task_id); folder = MEDIA_ROOT / task_id; folder.mkdir(parents=True, exist_ok=True); saved = []
    for upload in files:
        name = Path(upload.filename or "image").name
        if Path(name).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
            raise HTTPException(400, "unsupported image type")
        target = folder / name; target.write_bytes(await upload.read()); saved.append({"filename": name, "path": str(target)})
    t["data"]["images"].extend(saved); old = t["status"]; t["status"] = "IMAGES_READY"
    c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "user", "upload_images", old, t["status"], {"count": len(saved)})
    return get_task(task_id)


@app.post("/api/tasks/{task_id}/review")
def review(task_id: str, review: Review):
    t = get_task(task_id)
    if not t["data"].get("article", {}).get("body"):
        raise HTTPException(409, "article HTML is required before review")
    if t["status"] not in {"ARTICLE_READY", "DRAFT_READY", "IMAGES_READY"}:
        raise HTTPException(409, "article is not ready for review")
    old = t["status"]; t["status"] = "REVIEWED"; t["data"]["review"] = review.model_dump()
    c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "reviewer", "review", old, t["status"], review.model_dump())
    return get_task(task_id)


async def cms_write(t: dict[str, Any]) -> dict[str, Any]:
    if not CMS_DRAFT_ENDPOINT:
        return {"status": "UNAVAILABLE", "message": "CMS draft endpoint is not configured", "login_url": t["data"]["article"].get("cms_login_url") or CMS_LOGIN_URL}
    article = t["data"]["article"]
    payload = {"title": article["title"], "body": article["body"], "status": "draft", "category_id": article.get("category_id", ""), "meta_title": article.get("meta_title", ""), "meta_description": article.get("meta_description", "")}
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(CMS_DRAFT_ENDPOINT, json=payload, headers=safe_cms_headers()); r.raise_for_status(); result = r.json()
        return {"status": "CREATED", "response": result, "cms_id": str(result.get("id", result.get("article_id", ""))), "draft_url": result.get("url", result.get("edit_url", ""))}
    except Exception as exc:
        return {"status": "FAILED", "message": str(exc)}


@app.post("/api/tasks/{task_id}/cms-draft")
async def cms_draft(task_id: str):
    t = get_task(task_id)
    if t["status"] != "REVIEWED":
        raise HTTPException(409, "human review is required before CMS draft")
    result = await cms_write(t); old = t["status"]; t["data"]["cms"] = result
    t["status"] = "CMS_DRAFT" if result["status"] == "CREATED" else "CMS_DRAFT_UNAVAILABLE"
    c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "system", "cms_draft", old, t["status"], result)
    return get_task(task_id)


@app.post("/api/tasks/{task_id}/approve")
def approve(task_id: str, approval: Approval):
    t = get_task(task_id)
    if t["status"] != "CMS_DRAFT":
        raise HTTPException(409, "a CMS draft must exist before approval")
    old = t["status"]; t["status"] = "APPROVED"; t["data"]["approval"] = {**approval.model_dump(), "approved_at": now()}
    c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "approver", "approve", old, t["status"], approval.model_dump())
    return get_task(task_id)


@app.post("/api/tasks/{task_id}/publish")
async def publish(task_id: str):
    t = get_task(task_id)
    if t["status"] != "APPROVED":
        raise HTTPException(409, "explicit approval and a CMS draft are required")
    cms = t["data"].get("cms") or {}; cms_id = str(cms.get("cms_id", ""))
    if not CMS_PUBLISH_ENDPOINT or not cms_id:
        raise HTTPException(503, "CMS publish endpoint or CMS draft id is not configured")
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            r = await client.post(endpoint(CMS_PUBLISH_ENDPOINT, cms_id), json={"id": cms_id, "status": "publish"}, headers=safe_cms_headers()); r.raise_for_status(); response = r.json()
            verify = None
            if CMS_VERIFY_ENDPOINT:
                vr = await client.get(endpoint(CMS_VERIFY_ENDPOINT, cms_id), headers=safe_cms_headers()); vr.raise_for_status(); verify = vr.json()
        result = {"status": "PUBLISHED", "cms_id": cms_id, "response": response, "verification": verify}
    except Exception as exc:
        result = {"status": "PUBLISH_FAILED", "message": str(exc)}
        old = t["status"]; t["status"] = "PUBLISH_FAILED"; t["data"]["publish"] = result
        c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "publisher", "publish", old, t["status"], result)
        raise HTTPException(502, result["message"])
    old = t["status"]; t["status"] = "PUBLISHED"; t["data"]["publish"] = result
    c = conn(); c.execute("UPDATE tasks SET status=?,data=?,updated_at=? WHERE id=?", (t["status"], json.dumps(t["data"]), now(), task_id)); c.commit(); c.close(); audit(task_id, "publisher", "publish", old, t["status"], {"cms_id": cms_id, "verified": verify is not None})
    return get_task(task_id)


@app.get("/api/tasks/{task_id}/audit")
def task_audit(task_id: str):
    get_task(task_id); c = conn(); rows = c.execute("SELECT * FROM audit WHERE task_id=? ORDER BY id", (task_id,)).fetchall(); c.close(); return [dict(r) for r in rows]
