# Public Reports on GitHub Pages

This project serves the public sports report as a self-contained static artifact on GitHub Pages.
The deployment does **not** depend on `frontend/`, a sibling `reports/` directory, a backend, Google Sheets,
or an external JSON endpoint. Opening the project Pages URL loads the report directly from the built artifact.

## How to deploy

1. Push the repository to GitHub.
2. Go to **Settings → Pages**.
3. Set **Source** to **GitHub Actions** (the workflow `.github/workflows/deploy-frontend.yml` will run and
   upload `reports/dist` as the Pages artifact).
4. The public URL will serve the report directly — no further configuration is needed.

### What the workflow does

The workflow **only** builds and deploys `reports/dist`. It does **not** build or deploy `frontend/`.
The workflow runs on every push to `main` that changes files under `reports/` or the workflow file itself.

| Step | What happens |
|---|---|
| `npm --prefix reports run build` | Vite + TypeScript build; `report.json` is copied from `backend/data/public-report.json` into `dist/` |
| `actions/upload-pages-artifact` | Uploads `reports/dist` as the Pages site root |

**Important:** Do **not** select `frontend/` or `reports/` as a branch folder in the Pages Settings UI.
The deployment method is the GitHub Actions workflow, which uploads the `reports/dist` contents as the site root.
Selecting a folder branch instead of Actions will use the old combined `site/` artifact and is not the intended method.

## Local development

```bash
# Install deps and run Vite dev server
npm --prefix reports install
npm --prefix reports run dev

# Build the report project (produces dist/ with index.html, assets, and report.json)
npm --prefix reports run build
```

The built `reports/dist/` contains:
- `index.html` — the SPA entry point
- `assets/` — bundled CSS and JS
- `report.json` — the canonical public report JSON (embedded at build time from the backend projection)

## Report default — no env var required

The report app defaults to a local `report.json` bundled at `dist/report.json`. No `VITE_PUBLIC_REPORT_URL`
environment variable is required for the report to display. If a remote URL is needed, it can be set via
`VITE_PUBLIC_REPORT_URL` as an optional override, but the local bundled JSON will be used by default.

### Remote override (optional)

Set `VITE_PUBLIC_REPORT_URL` in the repository secrets or workflow variables to point at an external
HTTPS JSON endpoint. The app will fall back to the local `report.json` if the remote fetch fails.
This is **not** required for basic deployment.

## Local JSON source

The `report.json` embedded in `dist/` is a deterministic copy from `backend/data/public-report.json`
(the allowlisted public projection sample). No duplicated or divergent example data is committed; the
backend is the single canonical source, and the copy is generated automatically by the build script.

## Verification

Run the project tests to confirm the deployment configuration:

```bash
npm --prefix reports run test
```

All existing projection validation tests pass. The workflow test (`deployWorkflow.test.ts`) confirms
reports-only deployment and local JSON inclusion.