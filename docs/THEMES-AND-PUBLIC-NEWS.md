# Appearance, readable controls, and public news

## Use the features

**Settings → Appearance** offers Forest, Ocean, and Ink presets, custom colors, dashboard/public fonts, spacing, corners, and public card/list layout. Preview affects your current page only. **Save appearance** persists the complete validated theme and records it in History. Refresh other open pages to load it. Discard restores the saved appearance; resetting prepares a default preview that still needs saving. Import/export uses the same validated JSON format.

**Settings → Public news** selects a forum category and the number of latest updates to show. You can create a category here with moderation permission. Selecting a category requires confirmation: every approved top-level post in that category becomes public, including existing approved posts. Pending/rejected posts, replies, user emails, and other categories remain outside the feed. Zero disables news. Disabling the forum hides the feed and its item pages.

Start an announcement in that category through Forum, then approve it. It appears on the homepage, `/news`, and `/news/<thread-id>`. Rejecting it removes it on the next request. News reads the forum directly; no copied entries can drift out of sync. The listing shows the configured latest 1–30 posts; approved item pages remain directly accessible.

The stray `null` came from passing absent elements to native DOM `append()`, which rendered them as text beneath forms and beside messages without moderation controls. These calls now omit missing nodes. History also explains absent values, labels actions clearly, and searches displayed descriptions. Existing custom wording is preserved.

## AI-readable visual theme contract

`GET /api/theme/contract` requires `config.read` and returns the active theme/version, defaults, presets, supported local fonts, schema, semantic tokens, and editing rules. Design notes guide an AI/developer; saving does not run an AI model. Notes are excluded from public bootstrap and CSS.

| Field | Contract |
|---|---|
| schema_version | Integer 1 |
| preset | forest, ocean, ink, custom |
| colors | Exact keys: accent, canvas, surface, text, muted, sidebar, sidebar_text, border, input_border; #RRGGBB only |
| admin_font / public_font | system, humanist, serif; local families with fallbacks |
| density | comfortable, compact; 44px touch targets preserved |
| radius | Integer 0–20px |
| public_layout | cards, list |
| design_notes | Plain text, at most 2,000 characters |

Unknown keys, external fonts, CSS fragments, HTML, and scripts are rejected as theme configuration. Light work surfaces preserve the fixed semantic notice/badge colors. Important text/link pairs require 4.5:1 contrast; input outlines require 3:1. Full interface testing is still necessary.

Save through `POST /api/change`, action `config.write`, with category `settings`, key `appearance.theme`, the complete value, reason, and expected_version. Conflicts return 409; changes are audited and undoable. `POST /api/theme/preview` also requires `config.write`, accepts `{theme: <complete theme>}`, and returns validated tokens without saving. Cookie mutations require CSRF validation. `/assets/theme.css` serves only compiled validated tokens under the existing same-origin CSP. No frontend build or runtime CDN is required.

## News contracts and migrations

| Route | Registered action | Behavior |
|---|---|---|
| GET /api/publication/options | config.read, plus forum.read check | Categories and approved counts for configuration |
| POST /api/news/settings | config.write | Atomic category/limit save with reason and both expected versions |
| GET /api/public/news | public.read | Latest approved posts in selected category |
| GET /api/public/news/item?id=N | public.read | Approved selected-category item; other items unavailable |

`public.news_category` defaults to zero and otherwise must reference an existing category. `public.news_limit` defaults to six and accepts 1–30. Both runtime settings have validation, audit, and undo. A failed atomic save rolls back both values and audit events.

Migration `002_forum_publication.sql` adds nullable `threads.published_at` and a feed index. New approvals record their actual timestamp. Historical approval times are not invented: old approved posts show their real posting date with a Posted label; new approval dates use Published. Forum text is HTML-escaped in public pages.

The tracked `003_readable_labels` data migration upgrades only untouched values matching old defaults, audits those changes, and preserves user-edited labels.

## Evidence

Local status: TESTED_PASS for 13 unit/HTTP tests, browser workflows at five widths, and 24 axe-core A/AA scans. `evidence/ui/results.json` and `accessibility.json` record observations; screenshots use isolated synthetic data. New checks cover preview/save/reset, import/export, contrast rejection, public fonts/layout, news selection/approval, readable audit values, and missing-node regressions for administrators and editors.

GitHub CI is TESTED_PASS: [run 38328736003](https://github.com/Mankeluvsit/ecosystem-cms/actions/runs/38328736003) passed the complete suite for source commit `828f254b8887318fbaf7016b7b08d437bc624827`. Native Android, additional browser engines, and manual screen-reader checks remain NOT_STARTED. Public hosting remains BLOCKED by missing provider credentials. This is not a declaration of full production readiness.

## Enhancement plan

These are SPECIFIED proposals, not implemented controls.

| Priority | Feature | Acceptance requirement |
|---|---|---|
| Next | News archive and pagination | Stable chronological pages; no private/pending records in results or totals |
| Next | RSS/Atom subscriptions | Approved selected-category posts only; rejection/disablement reflected; safely encoded output |
| Next | Dedicated announcement composer | Starts in configured category; approval, permissions, and public consequences remain enforced |
| Next | Visual content-type builder | Avoid JSON for ordinary setup; schema changes preserve records through an explicit migration strategy |
| Later | Scheduled/pinned announcements | Persisted state, authorization, worker evidence and honest feedback |
| Later | Saved theme library | Versioned drafts, comparisons, audited activation and rollback |
| Later | Accessible dark presets | Every form, focus state, notice, badge, and image background verified |
| Later | Logo and public hero controls | Explicit public media references, alternative text, audited settings |
| Later | Draft autosave/recovery | Visible save state, conflicts, offline recovery and duplicate prevention |
| Later | Guided Termux setup/start | Safe storage/account handling, secure prompts, health verification |

Dark mode, rich text, autosave, a theme marketplace, and AI-generated designs are not claimed by the implemented theme editor.
