# Deployment and verification

## Local startup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export CMS_DB="$PWD/var/cms.sqlite3"
mkdir -p var
python -m app.manage migrate
python -m app.manage bootstrap --email admin@example.com
python -m app.web
```

The bootstrap command prompts for a password of at least 12 characters. The server refuses to start until an active administrator exists.

## Production requirements

Use a persistent absolute `CMS_DB` path, set `CMS_ENV=production`, and set `CMS_ORIGIN` to an HTTPS origin without a trailing slash. Put the process behind TLS termination and a reverse proxy that forwards only the application port. Keep the database outside the release directory and back it up with `python -m app.manage backup /secure/backup/cms.sqlite3`.

Health check: `GET /api/health`.

## Fly.io deployment

Create the app and persistent volume once, then configure the GitHub repository secret `FLY_API_TOKEN`. Set `CMS_ORIGIN` to the final HTTPS hostname. For the first boot, set `CMS_BOOTSTRAP_EMAIL` and `CMS_BOOTSTRAP_PASSWORD` as temporary Fly secrets; the service creates the administrator only when no active administrator exists. Remove the bootstrap password immediately after the first successful health check.

```bash
fly auth login
fly apps create ecosystem-cms
fly volumes create ecosystem_cms_data --region ord --size 1
fly secrets set CMS_ORIGIN=https://ecosystem-cms.fly.dev CMS_BOOTSTRAP_EMAIL=admin@example.com CMS_BOOTSTRAP_PASSWORD='use-a-unique-12-character-secret'
fly deploy
fly secrets unset CMS_BOOTSTRAP_PASSWORD
curl -fsS https://ecosystem-cms.fly.dev/api/health
```

The included workflow repeats tests and deploys on pushes to `main`. Do not store the bootstrap password or API token in the repository.

The local managed build environment uses an injected proxy certificate. To reproduce the image there, pass it as a BuildKit secret; the certificate is never copied into an image layer:

```bash
docker build --secret id=proxy_ca,src="$CODEX_PROXY_CERT" -t ecosystem-cms:local .
```

## Evidence collected

- Baseline controls: 5/5 unit tests pass.
- Current checks: `python -m unittest discover -s tests -v`, `python -m compileall -q app`, and `node --check app/admin.js` pass.
- HTTP startup check: migration, bootstrap, health `200`, public bootstrap `200`, unauthenticated dashboard `401`, and password login `200`.
- Acceptance check: disabling forum returned `403 MODULE_DISABLED`; role and Publish labels changed through runtime controls; chat retention accepted `30`; audit endpoint returned `200`; draft entry was absent from public listing and slug lookup returned `404`.

Browser screenshot/accessibility automation remains environment-dependent; the implementation includes semantic controls, keyboard focus styles, status text, responsive CSS, and reduced-motion handling, but no browser run is claimed until a browser executable is available.

