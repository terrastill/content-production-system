# Portable Hermes industrial-content Skills

This directory contains two portable Hermes Skills extracted from the existing industrial article-generation and CMS-publishing workflows.

- `industrial-article-generation`: topic generation, server-vector retrieval contract, OpenAI-compatible article-model contract, writing, image brief, and factual/SEO/GEO review.
- `industrial-cms-publishing`: media checks, CMS draft creation, explicit approval gate, publication, and backend/frontend verification.

It deliberately excludes email, mailbox connections, customer leads, CRM, outreach, local knowledge bases, credentials, browser cookies, generated articles, images, and logs.

## Install on a second computer

```bash
git clone <YOUR_PRIVATE_GITHUB_REPOSITORY_URL> content-production-system
cd content-production-system
python3 scripts/install_hermes_skills.py
```

For a named profile, point the installer at that profile home:

```bash
python3 scripts/install_hermes_skills.py --home "$HOME/.hermes/profiles/<profile-name>"
```

It refuses to overwrite existing skills. Use `--force` only after reviewing the destination. Start a new Hermes session after installation so the catalog refreshes.

## Configure runtime services

Copy `hermes-skills/.env.example` into the secure runtime environment of the target Hermes profile, then set values there. Never commit the copied file.

The article-generation Skill defaults to an external vector-service adapter. It does not call AnythingLLM and has no hardcoded workspace. The vector service must return source IDs/titles and excerpts; no response means the Skill reports `UNAVAILABLE` rather than inventing citations.

The model adapter accepts ChatGPT/OpenAI-compatible endpoints by setting `ARTICLE_MODEL_BASE_URL`, `ARTICLE_MODEL_CHAT_PATH`, `ARTICLE_MODEL_API_KEY`, and `ARTICLE_MODEL_NAME`.

The CMS Skill exposes `CMS_LOGIN_URL` as a non-secret administrator navigation address. Passwords and tokens remain runtime-only; a browser adapter uses an operator's pre-authenticated local browser session instead of receiving credentials in chat.

## Mandatory gates

```text
Brief → 10 topics → retrieval → outline → human approval → article/audit
→ human final review → CMS draft → explicit “可以发布” → publication → read-back verification
```

CMS writes default to draft/hidden. An audit or review pass is not publication authority.

## Validate the package

```bash
python3 scripts/validate_hermes_skills.py
python3 scripts/install_hermes_skills.py --home /tmp/hermes-skill-smoke
```

The validator checks frontmatter, required sections, lack of absolute machine paths, and obvious credential patterns. It does not test a real vector model or CMS: those need staging endpoints and non-production test content.
