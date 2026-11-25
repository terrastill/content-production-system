# Industrial Content Production System

## Allowed capabilities

- Industry topic proposals
- AnythingLLM research from the single configured allowlisted workspace
- Industrial article drafts
- Image metadata and upload intake
- Human review gates
- CMS draft creation
- Explicit approval and publish
- Per-task audit trail

## Forbidden capabilities

- Email agents
- SMTP/IMAP/OAuth mailbox connectors
- Mailbox reading or sending
- Lead/prospect/customer lists
- Email templates or outbound campaigns
- Cross-workspace AnythingLLM retrieval
- Automatic publication without approval

## Data boundary

The only enterprise retrieval workspace permitted by the current project policy is `doing` (AnythingLLM `doing碳化网站`) in Hermes group `工作1`. If that mapping cannot be verified, return `UNAVAILABLE` or `AMBIGUOUS` and do not write enterprise facts.
