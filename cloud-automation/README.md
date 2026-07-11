# Cloud Rate Automation

Exchange rates need to be updated daily, but your local machine may be sleeping. This folder documents cloud-based automation options — **GitHub Actions is the chosen path** for this project.

## Option A1: GitHub Actions (Active)

**Pros:** Free, fully transparent, no OAuth setup, easy to debug in GitHub UI.

### Setup
1. Push the `budget-analysis-app/` folder to a public GitHub repo (e.g. `budget-intelligence`)
2. Enable Actions on the repo
3. Seed `github-actions/data/rates.csv` with complete history (`scripts/seed_rates_csv.py`)
4. Workflows at repo root (`.github/workflows/`) run daily at 22:00 UTC (~6 PM VET)
5. Configure the web app:
   ```
   RATE_SOURCE=github
   GITHUB_RATES_URL=https://raw.githubusercontent.com/YOUR_USER/budget-intelligence/main/cloud-automation/github-actions/data/rates.csv
   ```

See [github-actions/README.md](github-actions/README.md) for detailed setup, manual runs, and troubleshooting.

---

## Option A2: Google Sheets + Apps Script

**Pros:** Familiar spreadsheet interface, easy to view/edit rates manually.

### Setup
1. Create a Google Sheet
2. Install `google-apps-script/rate_updater.gs`
3. Run `setupTrigger` once
4. Share the sheet publicly (Viewer)
5. Configure the web app with the Sheet ID

See `google-apps-script/README.md` for detailed setup.

---

## Option A3: OneDrive Excel + Power Automate

**Pros:** Integrates with your existing OneDrive workflow.

See `power-automate/README.md` for setup.

---

## Option B: Manual Re-upload (Always Available)

You can always re-upload your `Historial_TCBinance.xlsx` via the **Upload tab** in the web app. The system detects it's a rates file and merges/replaces the rate history.

This is the fallback if cloud automation fails.

---

## Priority Order

The app checks sources in this order:
1. **Cloud source** (GitHub / Google Sheets / OneDrive) — if configured and reachable
2. **Last manual upload** — from SQLite database
3. **Fallback** — uses last known rates (marks data as STALE)
