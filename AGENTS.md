# Ecosystem CMS — Codex instructions

Build a real modular CMS, not merely a specification. Required modules: config, auth, content, media, forum, chat, public, admin, api.

For each feature maintain a human behavior contract, an exact implementation contract, server-side permission enforcement, and executable acceptance tests. Maintain registries SETTINGS, FLAGS, ACTIONS, LABELS. All API routes require declared ACTIONS; configuration changes are persisted and audited; editable labels and flags must change actual behavior without deployment. No fixed five-second propagation requirement.

Never fabricate tests, evidence, routes, files, metrics, or functionality. Record status as NOT_STARTED, SPECIFIED, IMPLEMENTED_UNVERIFIED, TESTED_PASS, TESTED_FAIL, BLOCKED, or NOT_APPLICABLE. Report exact test commands and failures. Do not claim production readiness without security and deployment verification.

First import and examine the Control Lab prototype from the conversation ZIP if available; if unavailable, report that limitation and implement a coherent working baseline. The prototype uses spoofable X-Actor and X-Role headers: replace these with real authentication before public deployment. Preserve audit history and version conflict checks. Implement and test each module incrementally. Use sensible technical defaults but document consequential assumptions.

The user expects a browser-accessible preview URL. Do not invent one. Only report a public URL after deployment and HTTP verification. Do not expose secrets or an unauthenticated admin interface.

