# Budget Intelligence

Personal finance and macro analysis app for Venezuelan budgets — exchange rates, inflation, purchasing power, scenarios, and narrative insights.

## Stack

- **Frontend:** React 19 + TypeScript + Vite + Tailwind
- **Backend:** FastAPI + SQLite
- **Cloud rates:** GitHub Actions daily fetch (BCV + Binance P2P) → `rates.csv` → local sync

## Local development

### Prerequisites

- Node.js 20+
- Python 3.11+

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env — set RATE_SOURCE=github and GITHUB_RATES_URL after pushing to GitHub
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```powershell
npm install
npm run dev
```

Open http://localhost:5173 (API at http://localhost:8000).

### Quick start (both servers)

```powershell
.\start.ps1
```

## Cloud exchange rates

Daily BCV and Binance rates are fetched by GitHub Actions and committed to:

`cloud-automation/github-actions/data/rates.csv`

The backend pulls this CSV on startup and via **Sync Now** on the Rates tab when configured:

```env
RATE_SOURCE=github
GITHUB_RATES_URL=https://raw.githubusercontent.com/YOUR_USER/budget-intelligence/main/cloud-automation/github-actions/data/rates.csv
```

See [cloud-automation/github-actions/README.md](cloud-automation/github-actions/README.md) for setup, manual workflow runs, and troubleshooting.

Manual fallback: re-upload `Historial_TCBinance.xlsx` via the Upload tab.

## Project layout

```
budget-analysis-app/
├── src/                  # React frontend
├── backend/              # FastAPI API + SQLite
├── cloud-automation/     # GitHub Actions, Google Sheets, Power Automate options
└── start.ps1             # Launch frontend + backend
```
