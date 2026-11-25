# CMS Publishing Skill

1. Use a dedicated CMS service account, not a personal account.
2. Scope it to the minimum API permissions: create draft, read draft, upload media if required, and publish only through the approved service endpoint.
3. The application always creates `status=draft` first.
4. A human reviewer must call the approval endpoint before publish is available.
5. On publish, read back the CMS response and record the returned article ID and URL in the audit log.
6. Never retry a failed write blindly; investigate the audit result first.
