# GitHub Actions — Daily Exchange Rates

Cloud automation for BCV official and Binance P2P exchange rates. A scheduled workflow fetches live rates, appends/upserts one row per day in `data/rates.csv`, and commits to this repo. The Budget Intelligence backend pulls that CSV via `GITHUB_RATES_URL`.

## One-time setup checklist

1. **Public repo** — push `budget-analysis-app/` as the repository root (e.g. `budget-intelligence`).
2. **Enable Actions** — repo Settings → Actions → General → allow workflows.
3. **Seed baseline** — run `scripts/seed_rates_csv.py` once locally so `data/rates.csv` contains complete history (not header-only).
4. **Configure backend** — in `backend/.env`:
   ```env
   RATE_SOURCE=github
   GITHUB_RATES_URL=https://raw.githubusercontent.com/YOUR_USER/budget-intelligence/main/cloud-automation/github-actions/data/rates.csv
   ```
5. **Manual test** — trigger **Daily Exchange Rates Update** via Actions → workflow_dispatch.

Workflows live at the **repo root**: `.github/workflows/daily-rates.yml` (not under this folder).

## Schedule

| Workflow | Cron | Local time (VET, UTC-4) |
|----------|------|-------------------------|
| Daily Exchange Rates Update | `0 22 * * *` | ~6:00 PM |
| Monthly Cesta Basica Update | `0 22 1,15 * *` | 1st & 15th, ~6:00 PM |

## Scripts

| Script | Purpose |
|--------|---------|
| `run_daily_rates.py` | Orchestrator: fetch BCV + Binance, carry-forward on partial failure, merge CSV, write `sync_meta.json` |
| `fetch_bcv.py` | Scrape BCV official USD rate |
| `fetch_binance.py` | Binance P2P median-of-top-10 USDT/VES |
| `update_csv.py` | Upsert today's row into `rates.csv` |
| `seed_rates_csv.py` | One-time export from `Historial_TCBinance.xlsx` or SQLite |

### Seed rates.csv locally

```powershell
cd cloud-automation/github-actions/scripts
..\..\..\backend\venv\Scripts\python.exe seed_rates_csv.py
# Or with explicit Excel path:
python seed_rates_csv.py --excel "C:\path\to\Historial_TCBinance.xlsx"
```

Commit the seeded `data/rates.csv` before relying on daily automation.

### Run orchestrator locally

```powershell
pip install requests beautifulsoup4 lxml
python cloud-automation/github-actions/scripts/run_daily_rates.py
```

## Raw URL format

```
https://raw.githubusercontent.com/{owner}/{repo}/{branch}/cloud-automation/github-actions/data/rates.csv
```

Open this URL in a browser to verify the CSV is publicly readable.

## Resilience

- If **BCV** or **Binance** fails, the orchestrator **carries forward** the last known value from `rates.csv` for that field.
- The job fails only when **both** sources fail and no prior row exists to carry forward.
- On workflow failure, fetch artifacts (`bcv_today.json`, `binance_today.json`, `sync_meta.json`) are uploaded for debugging.

## Troubleshooting

| Issue | What to do |
|-------|------------|
| BCV layout changed | Check workflow logs; update selectors in `fetch_bcv.py`; carry-forward keeps data flowing |
| Binance API blocked | Median filter helps; retry workflow_dispatch; check artifact logs |
| Partial-day row (one rate null) | Acceptable on holidays/weekends when BCV does not update |
| Stale badge in app | Confirm workflow ran; verify `GITHUB_RATES_URL` branch/path; use **Sync Now** on Rates tab |
| Need full history reset | Re-run `seed_rates_csv.py`, commit CSV, or re-upload Excel via Upload tab |

## Manual override

Re-upload `Historial_TCBinance.xlsx` via the **Upload tab** in the web app. Local SQLite becomes authoritative until the next cloud sync upserts overlapping dates.

## Files tracked in git

- `data/rates.csv` — cloud source of truth (seeded + daily commits)
- `data/cesta_basica.csv` — monthly cesta updates
- `data/sync_meta.json` — last successful run metadata

Ephemeral (gitignored): `bcv_today.json`, `binance_today.json`
