# API contract

The system exposes a small colleague-facing form at `/` and JSON endpoints:

- `POST /api/tasks` — create brief and return 10 topic proposals.
- `GET /api/tasks/{id}` — return brief, topics, research, draft, images, CMS link and status.
- `POST /api/tasks/{id}/research` — query the configured `doing` workspace only.
- `POST /api/tasks/{id}/draft` — create an article draft after verified research.
- `POST /api/tasks/{id}/images` — upload approved image files.
- `POST /api/tasks/{id}/review` — record human review.
- `POST /api/tasks/{id}/cms-draft` — create CMS draft; never publishes.
- `POST /api/tasks/{id}/approve` — explicit human approval.
- `POST /api/tasks/{id}/publish` — publish only an approved CMS draft.
- `GET /api/tasks/{id}/audit` — task audit record.

External adapters return explicit `UNAVAILABLE` or `FAILED` states; no placeholder source, CMS URL or publication claim is fabricated.
