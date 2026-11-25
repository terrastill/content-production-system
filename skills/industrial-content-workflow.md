# Industrial Content Workflow

```text
TOPICS_READY
  → RESEARCHED
  → DRAFT_READY
  → IMAGES_READY (when images are requested)
  → REVIEWED
  → CMS_DRAFT
  → APPROVED
  → PUBLISHED
```

External calls are fail-closed:

- No AnythingLLM endpoint: `RESEARCH_UNAVAILABLE`.
- No verified research: article drafting is rejected.
- No CMS draft endpoint: `CMS_DRAFT_UNAVAILABLE`.
- No explicit approval: publish is rejected.

The browser form is intentionally small: industry, readers, topic/keyword, language, article type and image requirement.
