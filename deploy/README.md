# Deployment and security runbook

## Development

```bash
cp .env.example .env
# Keep CMS endpoints empty for safe local development.
docker compose -f deploy/docker-compose.dev.yml up --build
```

Use mock/external adapters and local SQLite. Do not mount production media or databases.

## Test

```bash
docker compose -f deploy/docker-compose.test.yml run --rm test
```

Test the state machine, denial of publish before approval, workspace allowlist, audit trail and image file validation.

## Production

1. Create a dedicated server account and private checkout.
2. Inject `.env` values through Docker secrets, systemd credentials, Vault, 1Password Secrets Automation or the hosting provider secret manager.
3. Set `ANYTHINGLLM_WORKSPACE_SLUG=doing` and verify that the endpoint maps to `doing碳化网站` before enabling research.
4. Create a dedicated CMS service account with minimum permissions. Do not reuse a human admin token.
5. Put the service behind HTTPS/reverse proxy and restrict the bind address to the internal network or VPN.
6. Use a persistent encrypted volume for SQLite and media. Back up the database separately; do not put it in Git.
7. Enable log rotation and redact request bodies, Authorization headers, source documents and image contents from logs.
8. Run `docker compose -f deploy/docker-compose.prod.yml up -d --build`.
9. Verify `/docs`, create a test task, inspect its audit trail, create a CMS draft, and confirm publish remains rejected until approval.

## Secrets and excluded data

Never commit `.env`, API tokens, CMS credentials, logs, SQLite files, AnythingLLM exports, source documents or generated images. Rotate service credentials if they appear in shell history or logs.

## Per-article audit

`GET /api/tasks/{task_id}/audit` returns actor, action, source and destination status, timestamp and result detail for every transition. Keep the audit database on the server; export only redacted records for review.
