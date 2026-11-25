---
name: industrial-cms-publishing
description: Create reviewed CMS drafts and publish only after approval.
version: 1.1.0
author: Yinran, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [industrial, cms, draft, approval, publishing, verification]
    related_skills: []
---

# Industrial CMS Publishing Skill

Prepare reviewed industrial article packages for any CMS, create a CMS draft by default, and publish only after explicit approval. It supports API or browser-adapter implementations, but credentials remain in the service account runtime environment and are never requested in chat, put in a Skill, or exported to Git.

## When to Use

- A final article package has passed human content review and needs a CMS draft.
- An approved draft needs a controlled publication and read-back verification.
- Do not use for content generation, password collection, publishing without explicit approval, or publishing a package with unresolved factual or media gaps.

## Prerequisites

```text
CMS_BASE_URL=https://cms.example.com
CMS_LOGIN_URL=https://cms.example.com/admin
CMS_SERVICE_USERNAME=content-service
CMS_SERVICE_PASSWORD=...
CMS_AUTH_MODE=api_token|browser_session|oauth
CMS_API_TOKEN=...
CMS_DRAFT_ENDPOINT=/api/articles
CMS_PUBLISH_ENDPOINT=/api/articles/{id}/publish
CMS_MEDIA_ENDPOINT=/api/media
CMS_VERIFY_ENDPOINT=/api/articles/{id}
CMS_TIMEOUT_SECONDS=45
```

Use a dedicated service account restricted to creating/editing this system's drafts, uploading article media, reading back its records, and—only for the publishing role—publishing approved records. It must not administer users, site settings, templates, plugins, mail, leads, or CRM data.

For a browser adapter, the operator logs in to a locally controlled browser session. Do not request or type a password. Inspect the actual add/edit form and rich-text editor before writing; never assume field names or a visibility value.

## Procedure

1. Validate the handover package: article, SEO fields, source register, image manifest, reviewer result, requested CMS category, and approval status. Completion: no local paths, unresolved media placeholders, or unapproved factual claims remain.
2. Validate every media item against the manifest. Upload one file at a time using a verified endpoint or browser form. Record returned public URL, media ID, HTTP result, hash, ALT, caption, and path type. Stop on the first failed upload.
3. Replace media placeholders only with verified CMS URLs. Generate CMS-ready HTML; preserve the approved body and do not inject credentials, local paths, or unverified images.
4. Before any write, check same-category duplicate title/slug. If a match exists, stop and report its record ID rather than blindly creating another article.
5. Create a CMS record with explicit `draft`/hidden state. Read it back from the CMS and record the draft ID, editor URL, saved title, SEO fields, category, visibility, body length, media count, and canonical or preview URL. `CMS_DRAFT_CREATED` is not publication.
6. Wait for explicit human authorization to publish. “Review passed”, “looks good”, or draft creation is not publication authorization; require a clear publishing instruction such as “可以发布”.
7. Publish once. Read the record back and verify article ID, public state, frontend URL, HTTP status, H1, title, meta description, canonical, one body marker, image URLs, and category/listing visibility when relevant. Any failed verification yields `PUBLISH_FAILED`, not `PUBLISHED`.

## Audit Contract

```yaml
article_task_id: ""
actor: ""
state: CMS_DRAFT_CREATED | PUBLISH_PENDING_APPROVAL | PUBLISHED | PUBLISH_FAILED | BLOCKED
cms_draft_id: ""
cms_draft_url: ""
public_url: ""
approval:
  approved_by: ""
  approved_at: ""
verification:
  backend_readback: pass | fail
  frontend_http_status: 0
  h1: pass | fail
  seo: pass | fail
  media: pass | fail
  listing: pass | fail | not_applicable
```

## Quality Gates

- Default write state is draft/hidden, never public.
- A write is not successful until the CMS record is read back.
- A publish is not successful until the frontend and required backend fields are verified.
- Stop after one failed write; do not retry blindly because duplicate articles are possible.
- Store site credentials only in secure runtime configuration. Never put a password in a form response, browser log, task audit, Git commit, or screenshot.

## Pitfalls

- CMS add and edit forms may use different submit controls.
- Rich-text editors can overwrite hidden textareas; write through the actual editor API, synchronize, then read the field back.
- Public/hidden radio values may be inverted. Calibrate with known records and verify after saving.
- Some CMS templates need a site-relative thumbnail path rather than an absolute URL; validate the rendered frontend, not only the form value.

## Verification

Run a staging smoke test using a `TEST-` title. Verify creation as hidden/draft, readback of all fields, explicit approval transition, and frontend HTTP 200 after publication. Delete or archive the test according to the staging policy.
