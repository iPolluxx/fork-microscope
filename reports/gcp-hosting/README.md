# Google Cloud Run deployment — 2026-09-10

Live dashboard: **https://fork-microscope-wzyjs4vwsq-uc.a.run.app**

Alternate Cloud Run URL: https://fork-microscope-879716207624.us-central1.run.app

- Project: `mightdoit`; region: `us-central1`.
- Service: `fork-microscope`; ready revision: `fork-microscope-00002-sm5`.
- Deployment: public HTTPS static dashboard, 100% traffic to the ready revision.
- Runtime: 1 CPU, 256 MiB, request-based billing, 0 minimum / 2 maximum instances, concurrency 80, 30-second timeout.
- Dedicated runtime identity: `fork-dashboard-web`; no project roles granted.
- Image registry: dedicated private Artifact Registry repository `fork-dashboard`. This image contains static assets and nginx, not the private GPU worker image.

## Verified

Every published asset matched the reviewed local SHA-256 manifest. Workspace, Configure, Explore and Compare opened without Google login, without JavaScript errors, and at desktop and 390px mobile widths. The public site correctly starts with no worker connected. New visitors see connection instructions instead of unreachable-worker errors or a perpetually loading set list. The connection dialog shows its actual HTTPS origin. Requests for worker APIs, Git configuration, environment files and local run paths return 404.

Records: `deployment.json`, `browser-checks.json`, `desktop.png`, `mobile.png`. The browser check is reproducible with Playwright and `DASHBOARD_URL` using `browser-qa.cjs`.

No model or GPU was started. No personal prompts/results, upstream Goodfire Python/data, provider credentials or worker tokens were uploaded. The Git repository and previous GPU image remain private. This is website hosting, not a release of the worker source or a hosted GPU service.

## Using it

Click **Connect worker** and enter the URL/token of your own Fork Microscope worker. Allow the exact URL you visit as a dashboard origin on that worker. For the primary URL:

```bash
# First set FORK_WORKER_TOKEN to a fresh private random token on your worker.
.venv/bin/fork-microscope serve --port 8767 \
  --allow-origin https://fork-microscope-wzyjs4vwsq-uc.a.run.app
```

Use HTTPS for a remote worker, or an SSH tunnel to localhost. Hosted-to-local access depends on browser permissions; the local worker's own dashboard remains the fallback. The public site cannot access an unconfigured laptop automatically. Connecting a worker does not start sampling.

Deployment/update and rollback instructions are in [the Cloud Run guide](../../deploy/cloud-run/README.md). Source edits are deployed manually with `GCLOUD_BIN=/path/to/gcloud scripts/deploy_cloud_dashboard.sh PROJECT_ID us-central1`; they do not become public merely by editing the repository.

Cloud Run's free tier is not a guaranteed zero bill; registry storage and traffic can incur charges. The instance maximum is a scaling setting, not a hard dollar cap. Other pre-existing GCP services were left unchanged.
