# Ecosystem CMS UI redesign — research and implementation plan

Date: 2026-10-12. Status: SPECIFIED. This document is a proposal, not an implemented redesign.

## Scope and evidence

Review basis: `app/admin.html`, `app/admin.js`, `app/app.css`, `app/registry.py`, and the existing service contracts. Findings below are from source inspection, not a new browser usability study. Prior browser failures do not establish that browser testing is still blocked; retry it during implementation.

Assumptions: retain the Ecosystem identity and green accent, prioritize content authors and administrators, support phone-based use including Termux, keep the Python/SQLite deployment, and avoid requiring a frontend build tool just to run the CMS. These are design recommendations, not new product requirements.

## Research and application

| Reference | Relevant pattern | Application to Ecosystem |
|---|---|---|
| [Directus collection layouts](https://directus.com/docs/guides/content/layouts) | Tables suit structured records; image cards suit visual collections. | Default content and people to rows; default media to thumbnails. |
| [Sanity Structure tool](https://www.sanity.io/docs/studio/structure-introduction) | Browsing and document editing can be organized into purposeful panes. | Separate the content collection from a focused editor with contextual publishing details. |
| [Carbon data-table guidance](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines) | Table toolbars organize search and actions around records. | Use one collection toolbar, clear column hierarchy, and item-specific secondary actions. |
| [W3C WCAG 2.2 additions](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/) | Focus visibility, target size, and accessible authentication matter in operational interfaces. | Test sticky toolbars, mobile controls, keyboard dialogs, and password-manager compatibility. |

The synthesis and visual direction below are original recommendations; these references are pattern research, not themes to copy or dependencies to install.

## Current problems to solve

1. The same `.card`, `.panel`, and `.form-grid` treatment makes most screens look like repeated forms. Use a different layout for each core task while sharing controls and spacing.
2. The overview contains five counts without recent work or a clear next action. Keep truthful counts, add permitted recent records, and provide useful destinations.
3. Content exposes creation, scheduling, editing, previews, and revisions in an expanding card list. Move editing to its own workspace; open auxiliary details intentionally.
4. The control plane renders every label and permission as a large form, including JSON permissions. Use category navigation, compact rows, and a focused edit panel.
5. Raw JSON custom fields and comma-separated media IDs make routine authoring technical. Generate typed fields from the existing content schema and select media visually.
6. Mobile navigation is a horizontally scrolling list of every module. Replace it with an accessible menu and a visible current location.
7. `loadView()` replaces the whole page while loading, and mutations disable controls globally. Preserve stable page structure, draft inputs, focus, and the context of failures.
8. The public renderer and admin share broad CSS selectors. Scope styles to avoid accidentally giving a published article the appearance of an admin form.

## Recommended visual direction: Ecosystem Studio

An editorial workspace with a dark forest navigation rail, warm off-white canvas, white work surfaces, and emerald primary actions. Personality comes from typography, composition, meaningful images, and consistent iconography. Gradients and decorative analytics are unnecessary here.

| Token | Proposed value / rule |
|---|---|
| Canvas | `#F6F7F4` |
| Surface | `#FFFFFF` |
| Navigation | `#102E28` |
| Primary action | `#176B50`, white label |
| Primary text | `#172B25` |
| Secondary text | `#586A61` |
| Border | `#DCE4DE`; stronger border for inputs |
| Focus | `#2563EB`, visible outline with offset |
| Warning / failure text | `#8A4B08` / `#B42318`, paired with an icon and words |
| Typography | System sans-serif initially; 30–32px page titles, 20px section headings, 16px body/input text, 13–14px metadata |
| Spacing | 4, 8, 12, 16, 24, 32, 48px scale |
| Shape | 8px controls, 12px panels; reserve pills for status and filters |
| Elevation | Borders for normal surfaces; subtle shadow for overlays |
| Icons | One locally bundled SVG family, 18–20px; decorative SVGs hidden from assistive technology |
| Motion | Brief opacity/color transitions only; respect reduced-motion preferences |

These colors are candidate tokens. Verify actual text/background combinations before claiming contrast conformance. Keep system fonts and local assets so the local installation has no font-CDN dependency.

## Information architecture

```text
Ecosystem
  Workspace
    Overview
    Content
    Media
  Community
    Forum
    Chat
  Administration
    People & roles
    Settings
    API keys
    Audit history
  View public site
  Account / Sign out
```

Show only authorized destinations. Feature-disabled pages explain the disabled state; include a settings link only for an authorized administrator. Keep module IDs and action keys stable while changing editable display labels.

Desktop: approximately 232px navigation, a compact 64px top bar, and fluid content with 24–32px gutters. Use breadcrumbs for collection → item. Top bar actions are contextual; do not add a nonfunctional notification bell or workspace selector.

Mobile: a 56px top bar, menu dialog, 16px gutters, and full-width work surfaces. Secondary editor details open as a sheet or separate section. The primary save action stays reachable without covering the focused input or virtual keyboard. Menu dialogs restore focus when closed.

## Screen specifications

### Overview

Use a clear page title and a single primary action, “Create content,” where authorized. A compact summary strip leads into recent content and items awaiting moderation; an activity panel shows the latest permitted audit events. Empty states offer the action appropriate to that module. No visitor, revenue, uptime, or trend charts until corresponding measurements exist.

```text
┌──────────────────┬─────────────────────────────────────────────┐
│ ECOSYSTEM        │ Workspace / Overview          View site     │
│                  ├─────────────────────────────────────────────┤
│ Workspace        │ Overview                   [Create content] │
│   Overview       │ Content total · Media total · Pending review│
│   Content        ├───────────────────────────┬─────────────────┤
│   Media          │ Recent content            │ Recent activity │
│ Community        │ Title / status / updated  │ Actor / change  │
│   Forum          │ Open entry                │ Open audit item │
│   Chat           ├───────────────────────────┤                 │
│ Administration   │ Needs review              │                 │
│   …              │ Open moderation queue     │                 │
└──────────────────┴───────────────────────────┴─────────────────┘
```

This is a static proposed layout; it contains no real counts or interactive controls.

### Content collection and editor

Collection: title, creation action, text filter, status/type filters, then rows showing title, type, status, and updated time. On phones, render a compact list with the same information and an explicit Open action.

Editor: title and body take the main column; a 300px contextual column contains status, slug, type, schedule, and media references. Tabs or disclosures contain revisions and an accurately labeled preview. Provide a clear explicit Save action and an unsaved-change indicator; do not imply autosave. Generate text/number/boolean inputs from the existing type schema. Keep advanced schema editing separate from ordinary authoring.

Publishing: keep Save draft distinct from Publish. Open a publish/schedule dialog with the exact entry name, destination, and timing. Scheduling shows the timezone and converts explicitly to the backend timestamp. Display only transitions supported by the current state and permissions. Existing published entries cannot be edited directly; explain the implemented restore/archive workflow rather than implying parallel draft editing exists.

### Media

Image grid with consistent thumbnail frames, filename, dimensions, and alt-text excerpt. Upload opens a dedicated panel; each file displays selection, validation, transmission, and server-result states where observable. Use indeterminate transmission if byte progress is unavailable. The inspector contains references and resize-copy controls. A media-picker dialog returns real media IDs to the editor. Deletion explains why referenced assets cannot be removed.

### Forum

Category navigation, thread rows, and a dedicated thread/detail view. Moderators get Pending / Approved / Rejected filters and a review panel with the complete item context. Approve and Reject have explicit labels and a consequence summary. Keep locking separate from rejection. Do not fetch every thread's replies when merely rendering the thread list.

### Chat

Room list, message timeline, and bottom composer on desktop; room list → room navigation on mobile. Group author/time information without relying on chat-bubble color. Presence is described as recently seen with its expiry behavior. Keep manual refresh explicit until polling or realtime transport is implemented. Sending preserves unsent text on failure; retention and moderation actions live in room settings for authorized users.

### Settings, people, API, and audit

Settings: General, Features, Labels, and Permissions categories. Each setting row shows its human label, current value, scope, and runtime/restart metadata. Editing opens a small panel with validation, reason, and version. Label editing includes key search and a text preview. A checkbox permission matrix replaces raw JSON while preserving the current server policy and recovery safeguards.

People: a table/list with email, role, and active state; account changes open a detail panel. Show role label and stable identifier separately when editing labels.

API keys: compact rows showing name, scopes, expiry, and revoked state. Select scopes using registered actions. Token creation uses a one-time reveal panel; Copy reports clipboard success only after it succeeds, with manual selection as a fallback.

Audit: readable actor/action/target/time rows. Expand an event to see before/after values and its reason. Offer Undo only when supported and explain stale-version failures. Filters must disclose the API's latest-200-record limit until pagination is added.

### Public site and sign-in

Public site: an editorial home with site identity, title links, excerpts, and referenced images where available; readable article pages with approximately 65–75 characters per line. Keep navigation based on real published content. Do not add metadata editing controls unsupported by the backend.

Sign-in: a focused form, restrained Ecosystem branding, visible input labels, password-manager support, and inline authentication errors. Avoid a blank navigation rail for signed-out users.

## Reusable components and feedback

Build: AppShell, PageHeader, CollectionToolbar, DataTable/RecordList, StatSummary, StatusBadge, FormField, InspectorPanel, MediaPicker, ConfirmDialog, InlineNotice, OperationSteps, EmptyState, LoadingState, and AuditDiff. These are proposed component responsibilities, not a required framework migration.

Use solid green for the primary action, neutral outline/text styles for secondary actions, and red only for genuinely destructive choices. Disable duplicate submission for the operation in progress. Preserve entered values on validation, network, authorization, and version failures. Place feedback beside the operation; keep persistent errors available until resolved or dismissed. Use specific success text only after the server confirms the operation.

Operation steps represent observed stages, not fake percentages. A server validation failure remains visibly failed; completion must not be displayed for a request merely sent. Disabled controls need a visible or focus-accessible reason rather than a hover-only title.

All new application-owned copy, navigation labels, hints, error explanations, accessible names, and confirmation text must be registered in LABELS. Dynamic record names are user data. Avoid embedding secrets in notifications, logs, or local storage.

## Backend boundaries

Existing APIs support the first visual iteration: collection lists, versioned saves/transitions, revisions, media selection, settings/labels/permissions, moderation, manual chat refresh, keys, and audit history. UI search/sort may initially operate on loaded records, clearly indicating bounded results.

Before a larger data rollout, add server pagination/filtering and explicit response metadata. Do not label a latest-200 audit search as a search of the entire history. New global search, bulk mutation, autosave, rich text, independent published/draft versions, and realtime chat are separate functional changes and are not part of the initial visual redesign.

A composed overview must respect the permissions of every data source. The current broad dashboard totals should be reviewed so a new card never reveals data through a weaker aggregate permission. Check secondary authorization gates for publishing and permission edits as well as route-level actions.

## Delivery sequence and acceptance gates

| Phase | Deliverable | Evidence required before passing |
|---|---|---|
| 1 | Tokens, scoped CSS, shell, sign-in, shared controls | Browser screenshots at 390px and 1440px; keyboard navigation and label-registry checks |
| 2 | Overview, content collection, focused editor, media picker | Draft → save → preview → publish; schedule timezone; revision conflict; referenced-media behavior |
| 3 | Media library, forum moderation, chat layout | Upload failure/retry; approve/reject/lock; room navigation and failed message preservation |
| 4 | Settings, people, keys, audit, public pages | Forum flag, stable role ID with renamed label, editable Publish label, retention execution, undo and scopes |
| 5 | Responsive/accessibility and regression pass | 320/390/768/1024/1440px layouts, 200% zoom, dialog focus, contrast, reduced motion, permissions and failure tests |

Each phase follows SPECIFIED → IMPLEMENTED_UNVERIFIED → TESTED_PASS or TESTED_FAIL with commands and observed results. Browser inability is BLOCKED with the actual current error. Do not upgrade a whole module to TESTED_PASS solely because its screenshot is attractive.

Acceptance includes: no page-level horizontal overflow except intentional table containers; touch controls target 44px; normal text contrast at least 4.5:1 and applicable large text/UI boundaries at least 3:1; focus stays visible under sticky controls; errors are announced; dialogs support Escape and restore focus; all enabled controls perform their documented action; hidden buttons never substitute for server permission checks. These are test targets, not current compliance claims.

## Status at handoff

Initial planning handoff: research and design plan SPECIFIED; application redesign and its tests were NOT_STARTED. Implementation has since proceeded; see [UI-IMPLEMENTATION-REPORT.md](UI-IMPLEMENTATION-REPORT.md) for current evidence, status, and remaining limits.
