# Ecosystem CMS

An executable modular CMS with SQLite migrations, password sessions, server-side authorization, audited runtime controls, content workflow, media, forum, chat, public rendering, responsive admin UI, and scoped API keys.

Read [docs/BLUEPRINT.md](docs/BLUEPRINT.md) for module contracts and [DEPLOYMENT.md](DEPLOYMENT.md) for startup, production configuration, and verification evidence.

The redesigned Ecosystem Studio interface includes a focused editor, visual media selection, community workspaces, and accessible mobile navigation. See [UI implementation and screenshots](docs/UI-IMPLEMENTATION-REPORT.md) for browser evidence and remaining limitations.

**Settings → Appearance** configures the dashboard and public site's visual theme with preview, import/export, contrast checks, and an AI-readable contract. **Settings → Public news** selects a forum category whose approved posts appear as public updates. Read the [guide and enhancement plan](docs/THEMES-AND-PUBLIC-NEWS.md).

The service is not declared production-ready until deployment-specific TLS, persistent storage, secret handling, backup/restore, and browser verification are completed in the target environment.

