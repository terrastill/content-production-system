# Industrial Content Production System

A colleague-facing web console for preparing and publishing industrial articles. It contains no email agents, mailbox connectors, lead data, or outbound messaging.

## Web workflow

1. Enter industry, topic, article HTML, SEO fields, CMS login URL, and category ID.
2. Create a task and optionally upload article images.
3. Mark the package as human-reviewed.
4. Create a CMS draft. The service sends `status=draft` explicitly.
5. Approve the CMS draft.
6. Click **一键发布** only after the final approval. The service publishes once and reads the CMS record back when `CMS_VERIFY_ENDPOINT` is configured.

The web console is at `/`; API docs are at `/docs`; health is at `/health`. Passwords are never entered into the page or stored in the task audit log. Put CMS credentials in the server environment or secret manager.

## Run locally

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8080`.

Without a real CMS draft endpoint, the application deliberately returns `UNAVAILABLE`; it does not pretend to create or publish an article. Without `CMS_PUBLISH_ENDPOINT`, the publish action is disabled by the server gate.

## External adapters

The article-generation Skill and web service reserve `VECTOR_STORE_BASE_URL`, `VECTOR_STORE_RETRIEVAL_PATH`, `ARTICLE_MODEL_BASE_URL`, and `ARTICLE_MODEL_CHAT_PATH`. AnythingLLM is not a default dependency.

CMS variables:

```text
CMS_BASE_URL
CMS_LOGIN_URL
CMS_SERVICE_USERNAME
CMS_SERVICE_PASSWORD
CMS_API_TOKEN
CMS_DRAFT_ENDPOINT
CMS_PUBLISH_ENDPOINT
CMS_MEDIA_ENDPOINT
CMS_VERIFY_ENDPOINT
```

Use a dedicated CMS service account with draft/create/read/media permissions. Give publishing permission only to the role that performs the explicit approval step.

## Deployment

- Development: `docker compose -f deploy/docker-compose.dev.yml up --build`
- Test: `docker compose -f deploy/docker-compose.test.yml up --build`
- Production: `docker compose -f deploy/docker-compose.prod.yml up --build`

Keep the bind address private until authentication, HTTPS, and role-based access are configured. The default compose file binds only to localhost.

## Portable Hermes Skills

The GitHub-installable Skills are under `hermes-skills/`. Install on another Hermes machine with:

```bash
python3 scripts/validate_hermes_skills.py
python3 scripts/install_hermes_skills.py
```

## Scope and audit

Every task has an audit timeline. CMS state transitions are separate: `REVIEWED → CMS_DRAFT → APPROVED → PUBLISHED`. A review does not authorize publication. `.env`, tokens, databases, logs, media, and generated content are ignored by Git.
