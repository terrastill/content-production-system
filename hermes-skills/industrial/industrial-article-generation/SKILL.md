---
name: industrial-article-generation
description: Generate cited industrial article drafts with review gates.
version: 1.1.0
author: Yinran, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [industrial, article, seo, geo, vector-retrieval, review]
    related_skills: []
---

# Industrial Article Generation Skill

Create industrial SEO/GEO article packages from a user brief, a configured external vector-retrieval service, and a configured OpenAI-compatible article model. This skill does not connect to AnythingLLM by default, does not contain email, CRM, lead, or outreach capability, and never publishes to a CMS.

## When to Use

- Generate an industrial equipment article, buyer guide, process guide, comparison, diagnostic, project-planning page, or case article.
- Produce a review package containing topics, outline, draft, evidence, image brief, and audit.
- Do not use for uncited enterprise claims, publishing a CMS record, or a request to skip human review.

## Prerequisites

Configure secrets only in the target Hermes profile's secure runtime environment. Do not put tokens in the skill files, prompts, task files, chat, or Git.

```text
VECTOR_STORE_BASE_URL=https://vector.example.com
VECTOR_STORE_RETRIEVAL_PATH=/v1/retrieve
VECTOR_STORE_API_KEY=...
VECTOR_STORE_AUTH_SCHEME=Bearer
VECTOR_STORE_COLLECTION=industrial-knowledge
VECTOR_STORE_TIMEOUT_SECONDS=30

ARTICLE_MODEL_BASE_URL=https://api.openai.com/v1
ARTICLE_MODEL_CHAT_PATH=/chat/completions
ARTICLE_MODEL_API_KEY=...
ARTICLE_MODEL_AUTH_SCHEME=Bearer
ARTICLE_MODEL_NAME=gpt-4.1
ARTICLE_MODEL_TIMEOUT_SECONDS=90
```

The vector service request must accept a JSON object containing `query`, `collection`, `top_k`, and `filters`; adapt names in a local deployment wrapper when the provider differs. Its response must yield source identifiers plus excerpts. The model endpoint must be OpenAI-chat-compatible, or a local wrapper must normalize it to that contract.

## Procedure

1. Collect industry, audience, keyword/topic, language, article type, desired market, and whether images are required. Completion: every field is explicit; otherwise state a bounded assumption.
2. Generate exactly 10 topic proposals, each with title, search intent, reader stage, content angle, and factual-risk note. Do not invent keyword-volume or ranking data.
3. For the selected topic, call the configured vector endpoint with targeted queries. Store query, time, source ID/title, excerpt, conditions, and retrieval status. If it is unavailable or incomplete, return `UNAVAILABLE` or `PARTIAL`; never fabricate sources.
4. Separate evidence into `enterprise_fact`, `generic_industry_fact`, `public_source`, `unknown`, and `conflict`. Enterprise facts without a source remain unknown.
5. Produce the stage-one outline package: H1, TDK, core answer, H2/H3 structure, purpose of each section, comparison dimensions, evidence map, FAQ plan, CTA plan, and unresolved facts. Unless the user explicitly requests one-shot overall review, stop for outline approval.
6. After outline approval, call the article model using the approved outline and evidence map. Preserve distinctions between process, equipment, technical design, application conditions, processing capacity, output, yield, purity, and recovery rate.
7. Audit the draft for evidence coverage, structure, SEO/GEO intent, readability, FAQ incremental value, CTA scope, unsupported numbers, and claims that imply certification, performance, price, delivery, ROI, carbon-credit eligibility, or regulation without verified evidence.
8. Deliver one review package: article HTML/Markdown, TDK, source register, image brief/manifest, audit result, unresolved facts, and `FINAL_PACKAGE_PENDING_APPROVAL`. Do not create a CMS draft or publish.

## Output Contract

```yaml
status: TOPICS_READY | OUTLINE_PENDING_CONFIRMATION | BODY_PENDING_CONFIRMATION | FINAL_PACKAGE_PENDING_APPROVAL | UNAVAILABLE | BLOCKED
sources:
  - source_id: ""
    title: ""
    excerpt: ""
    source_type: enterprise_fact | generic_industry_fact | public_source
    retrieval_query: ""
    retrieved_at: ""
    conditions: ""
limitations: []
```

Every image brief must include `image_type`, `source_scope`, `knowledge_base_basis`, `enterprise_fact_basis`, `review_status`, `alt`, and `caption`. A technical diagram or illustration must never be labeled as an installation photo, client project, certification proof, or measured performance evidence.

## Quality Gates

- Never claim retrieval succeeded without a real response and source identifiers.
- Never present generic knowledge as a company product, configuration, project, or case.
- Require explicit approval before moving from outline to body unless the user explicitly chose one-shot review.
- Require an explicit user authorization such as “可以发布” before any external CMS publishing skill may publish.
- Keep secrets out of all outputs and audit records.

## Pitfalls

- A model response is not a source. Retain retrieval excerpts and identifiers separately.
- A successful HTTP request does not prove a vector response matches the requested collection; validate returned sources.
- If the model or retrieval adapter has no configured endpoint, report it as unavailable rather than falling back silently to unrelated material.

## Verification

Use a test brief with an empty vector configuration. The skill must generate topic proposals but report retrieval as `UNAVAILABLE`, omit enterprise claims, and never report a successful citation or publication.
