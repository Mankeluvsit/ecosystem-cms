# Ecosystem CMS blueprint

## Runtime shape

The application is a Python standard-library HTTP service with SQLite persistence. `app/web.py` is the only HTTP boundary. Every API method/path is registered with an action in `app/registry.py`; the boundary authenticates a session or scoped API key, checks the action against the role and key scopes, validates CSRF for cookie mutations, then calls `app/server.py`.

The browser admin client is a same-origin accessible single page interface. `app/admin.js` consumes the same API as other clients. Public pages are server-rendered from published entries and never query drafts.

## Control plane

`SETTINGS`, `FLAGS`, `ACTIONS`, `LABELS`, and role permissions are declared in `app/registry.py`. Runtime values and versions are persisted in `controls`; changes are validated, written transactionally, recorded in `audit`, and can be undone for settings, flags, labels, and permissions while the current version still matches. Labels are looked up by the public and admin interfaces. Flags are enforced by module operations.

## Module contracts

| Module | Persisted records | Main behavior | Registered permissions |
|---|---|---|---|
| config | controls, audit | validated settings, flags, labels, permissions, undo | `config.read`, `config.write`, `audit.read` |
| auth | roles, users, sessions | scrypt passwords, expiring HttpOnly sessions, CSRF, login throttling, last-admin protection | `auth.session`, `auth.users.*`, `auth.permissions.write` |
| content | content_types, entries, revisions, media_references | drafts, review, schedule, publish/archive transitions, optimistic versions, restore | `content.read`, `content.write`, `content.publish` |
| media | media, media_references | validated image upload, normalized PNG storage, resize copies, reference-safe deletion | `media.read`, `media.write` |
| forum | categories, threads, replies | pending moderation, approval/rejection, replies, lock state, version checks | `forum.read`, `forum.write`, `forum.moderate` |
| chat | rooms, messages, presence | room messages, 90-second presence, configurable retention and maintenance pruning | `chat.read`, `chat.write`, `chat.manage` |
| public | published entries and referenced media | public home, slug pages, canonical/meta description, draft isolation | `public.read` |
| admin | browser dashboard and forms | responsive navigation, cards, tables, quick actions, confirmation, feedback | module permissions |
| api | registered routes, API keys, rate buckets | bearer keys with action scopes, revocation, expiry, per-key/user/IP limits | `api.keys.read`, `api.keys.write`, `api.health` |

## Database relationships

`users.role -> roles.id`; sessions and API keys belong to users. Entries belong to content types and authors; revisions and media references belong to entries. Forum threads belong to categories and replies belong to threads. Chat messages and presence belong to rooms and users. Audit records identify actor, category/key, before/after values, versions, reason, and timestamp.

## Failure and acceptance rules

Mutations return explicit error codes such as `UNAUTHENTICATED`, `PERMISSION_DENIED`, `MODULE_DISABLED`, `VERSION_CONFLICT`, `INVALID_VALUE`, `CSRF_REQUIRED`, and `RATE_LIMITED`. Multi-step admin operations show validation, submission, and persisted-result states; a failed server request marks the active stage failed and does not advance it. Destructive controls are disabled or confirmed, and disabled module routes fail server-side.

