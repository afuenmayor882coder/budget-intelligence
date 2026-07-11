# Google Apps Script Rate Updater (Option A2)

## Setup Instructions

### 1. Create the Google Sheet
1. Go to [sheets.google.com](https://sheets.google.com) and create a new spreadsheet
2. Name it **`Historial_TCBinance_Cloud`**

### 2. Install the Script
1. Click **Extensions > Apps Script**
2. Delete the default `myFunction()` code
3. Paste the entire contents of `rate_updater.gs`
4. Click **Save** (disk icon or Ctrl+S)

### 3. Set Up the Daily Trigger
1. In the Apps Script editor, select the function **`setupTrigger`** from the dropdown
2. Click **Run** (▶ play button)
3. Accept the permissions Google asks for (it needs to run as you)
4. The script will now run every day at ~10 PM UTC (6 PM VET)

### 4. Make the Sheet Readable by the App
1. Click **Share** in the Google Sheet
2. Under "General access", select **Anyone with the link** → **Viewer**
3. Copy the Sheet ID from the URL:
   - URL format: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
   - Copy the long alphanumeric string between `/d/` and `/edit`

### 5. Configure the Web App
1. Open `backend/.env` (create it if it doesn't exist, based on `.env.example`)
2. Set:
   ```
   RATE_SOURCE=google_sheets
   GOOGLE_SHEET_ID=your_sheet_id_here
   ```
3. Restart the backend

### How It Works
- Every day at ~6 PM VET, the script:
  1. Fetches the BCV official rate from bcv.org.ve
  2. Fetches the Binance P2P median rate via Binance's API
  3. Appends a new row with today's rates, diffs, and log returns
- The web app reads from this sheet on startup and hourly while open
- You can also manually trigger it by running `runNow()` in Apps Script

### Troubleshooting
- If BCV rate is missing: BCV sometimes changes their website layout. Open `rate_updater.gs` and update the regex patterns in `fetchBCVRate()`
- Check execution logs: Apps Script **Executions** tab shows all runs with logs
- The sheet auto-populates headers on first append

### Manual Override
At any time, you can re-upload your `Historial_TCBinance.xlsx` via the Upload tab in the web app. This will override the cloud rates with your file's data.
