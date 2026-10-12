# Ecosystem Studio implementation and evidence

## What changed

The original repeated panels have been replaced with a forest navigation shell, a clear top bar, grouped module navigation, a permission-aware overview, collection tables, a dedicated content editor, typed schema inputs, image selection, a thumbnail library, focused inspectors, thread detail/moderation, room navigation, and categorized configuration controls. Scope and permission selection use checkboxes; tokens have a one-time reveal with clipboard fallback. Audit events expand to a readable diff and supported undo.

Mobile navigation is a native modal with Escape/focus restoration. Record tables render as labeled lists on narrow screens. Feedback is in the page flow so it cannot cover a save control. Request failures keep the editor or composer input and mark the operation failed/blocked. The UI uses system fonts and local SVGs; no frontend compilation or third-party runtime CDN is required in Termux.

Public pages have their own editorial layout and scoped styles. Only published entries and their referenced images are rendered. New interface text is registered in LABELS; startup inserts new keys without overwriting existing edited values.

Two supporting server corrections were needed: dashboard counts now honor the underlying module permissions and retention cutoff; `/api/forum/moderation` uses `forum.moderate` to retrieve pending threads and replies without fetching every conversation. Chat send responses include their actual persisted timestamp.

## Evidence and status

| Area | Status | Evidence |
|---|---|---|
| Existing control regression | TESTED_PASS | Five baseline tests in `tests/test_control.py` |
| HTTP module/security integration | TESTED_PASS | Five integration cases in `tests/test_integration.py`; all ten tests pass together |
| Redesign workflows | TESTED_PASS | `scripts/verify_ui.py`: login, typed fields, references, publishing, scheduling, uploads, moderation, chat, users, scopes, labels/flags, and audit undo |
| Failure feedback | TESTED_PASS | Injected 409 save conflict and 403 message failure preserve input and expose failed/blocked steps |
| Responsive screens | TESTED_PASS | Nine module screens plus editor checked at 320, 390, 768, 1024, and 1440 CSS pixels with no page overflow; mobile scope picker also fits |
| Accessibility automation | TESTED_PASS | 21 axe-core A/AA-tagged scans with zero reported violations; recorded results in `evidence/ui/accessibility.json` |
| Dialog keyboard behavior | TESTED_PASS | Menu and upload-inspector Escape/focus restoration exercised in Chromium |
| Zoom and reduced motion | TESTED_PASS | Overview at 200% CSS zoom and reduced-motion media emulation |
| Syntax | TESTED_PASS | Python compilation and `node --check app/admin.js` |
| CI workflow execution | TESTED_FAIL | First run [38324155309](https://github.com/Mankeluvsit/ecosystem-cms/actions/runs/38324155309) passed server/syntax tests but detected a 2px overview overflow at 768px; grid sizing corrected, rerun pending |
| Manual screen-reader assessment | NOT_STARTED | Automated results do not establish full WCAG conformance |
| Native Android/Termux browser test | NOT_STARTED | Tested in desktop Chromium with mobile viewport sizes |
| Public deployment | BLOCKED | No hosting provider credential is configured; this source update does not create a deployment |

Screenshots and browser results use an isolated synthetic database. The names, counts, images, and activity are persisted test fixtures, not production telemetry. No production accounts are accessed. No credentials or API tokens appear in the screenshots.

## Reproduce

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
node --check app/admin.js
python -m playwright install chromium
curl -fsSL https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.3/axe.min.js -o /tmp/ecosystem-axe.min.js
CMS_AXE_PATH=/tmp/ecosystem-axe.min.js python scripts/verify_ui.py
```

`CMS_BROWSER` optionally selects a compatible test Chromium executable. Without `CMS_AXE_PATH`, functional/browser checks still execute, and the result records zero accessibility scans; that run must not be cited as accessibility evidence. Screenshot evidence is regenerated in `evidence/ui`.

## Practical limits

Content and people filters operate on loaded records. Audit filters cover the latest 200 events; chat shows the latest 100 retained messages and uses explicit refresh. Autosave, rich text, realtime chat, and bulk publishing are outside this iteration. Published entries retain the existing restore/archive workflow instead of promising separate simultaneous draft and published versions.

The plan's remaining scalability work is server pagination and broader search. Cross-browser, native mobile, and manual assistive-technology verification remain outstanding. The complete CMS is not declared production-ready by this UI report.
