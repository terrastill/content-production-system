# Industrial Content Production System

An isolated colleague-facing system for industrial content only. It deliberately contains no email agents, mailbox connectors, lead data, or email sending capability.

## Workflow

`industry brief → topic proposals → AnythingLLM research → article draft → image intake → human review → CMS draft → explicit approval → publish`

The default CMS action is always **draft**. Publishing requires a separate approval action and an authenticated CMS service account with the smallest available permissions.

## Quick start

```bash
cp .env.example .env
# Set only the secrets and endpoints needed in your environment.
docker compose up --build
```

Open `http://localhost:8080`. The API docs are at `/docs`.

Without external credentials, the app still runs in safe demo mode: it creates topic proposals and records `UNAVAILABLE` for external research/CMS actions. It never invents sources or claims publication.

## Environments

- Development: `docker compose -f deploy/docker-compose.dev.yml up --build`; use local SQLite and mock adapters.
- Test: `docker compose -f deploy/docker-compose.test.yml up --build`; run `pytest` and integration checks with mock adapters.
- Production: use `deploy/docker-compose.prod.yml` behind a reverse proxy, mount persistent data outside the image, inject secrets through the server secret manager, and use a dedicated CMS service account.

## Scope boundary

The application includes only industrial content production. It must not receive or store email credentials, mailboxes, lead lists, customer prospect data, or email-send permissions. `.env`, tokens, local databases, audit logs and generated images are ignored by Git.

## Approval model

1. Create a task.
2. Generate topics.
3. Run research only against the configured allowlisted AnythingLLM workspace.
4. Generate a draft and attach images.
5. A colleague reviews and marks the task `REVIEWED`.
6. The system creates a CMS draft (`CMS_DRAFT`).
7. An authorized reviewer approves (`APPROVED`).
8. Only then may the CMS publish action run (`PUBLISHED`).

Every transition is appended to the audit log with actor, timestamp, inputs and result. The API rejects publish requests unless the task is `APPROVED` and a CMS draft exists.

## Repository hygiene

Never commit `.env`, secrets, tokens, databases, logs, source knowledge-base exports, or generated images. Use the server's secret manager or environment variables.
