# Public Reports on GitHub Pages

This project serves public sports reports as self-contained static artifacts on GitHub Pages.
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
| `npm --prefix reports run build` | Vite + TypeScript build; the complete `reports/public/` catalog is copied into `dist/` by Vite |
| `actions/upload-pages-artifact` | Uploads `reports/dist` as the Pages site root |

**Important:** Do **not** select `frontend/` or `reports/` as a branch folder in the Pages Settings UI.
The deployment method is the GitHub Actions workflow, which uploads the `reports/dist` contents as the site root.
Selecting a folder branch instead of Actions will use the old combined `site/` artifact and is not the intended method.

## Local development

```bash
# Install deps and run Vite dev server
npm --prefix reports install
npm --prefix reports run dev

# Build the report project (produces dist/ with index.html, assets, report.json, reports.json, and per-match JSON)
npm --prefix reports run build
```

The built `reports/dist/` contains:
- `index.html` — the SPA entry point
- `assets/` — bundled CSS and JS
- `report.json` — fallback public report JSON
- `reports.json` — public match catalog
- `report_<public-key>.json` — one privacy-safe static artifact per catalog entry

## Report catalog — no env var required

The app loads local `reports.json` first and fetches the selected public-key report. If the catalog is unavailable,
it falls back to local `report.json`. No backend or environment variable is required at runtime.

## Local JSON source

The complete `reports/public/` directory is committed to the repository and copied by Vite at build time.
No backend, Docker volume, or untracked local file is required at runtime. Each artifact is a safe public
projection validated by the projection tests. See [the export workflow](match-report-workflow.md) for generation.

## Verification

Run the project tests to confirm the deployment configuration:

```bash
npm --prefix reports run test
```

All existing projection validation tests pass. The workflow test (`deployWorkflow.test.ts`) confirms
reports-only deployment and local JSON inclusion.
