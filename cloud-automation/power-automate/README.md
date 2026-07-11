# Power Automate Rate Updater (Option A3)

This option uses Microsoft Power Automate (cloud flows) to update an Excel file on OneDrive daily.

## Prerequisites
- Microsoft 365 / OneDrive account
- Power Automate (free tier: 750 flow runs/month — sufficient for daily)
- Note: The **HTTP action** in Power Automate requires a **Premium license**. If you don't have one, use Option A1 (GitHub Actions) or Option A2 (Google Sheets) instead.

## Setup

### 1. Create the Excel File on OneDrive
1. Upload `Historial_TCBinance.xlsx` to OneDrive (or create a new Excel Online file)
2. Note the file path (e.g., `/Documents/Budget Analysis/rates.xlsx`)
3. In the file, ensure the first sheet has a table named **`Rates`** with columns:
   - `fecha`, `tasa_binance`, `tasa_bcv`, `dif_pct_paralelo`, `dif_pct_oficial`, `log_return_binance`, `log_return_bcv`

### 2. Create the Power Automate Flow
1. Go to [flow.microsoft.com](https://flow.microsoft.com)
2. Create **New flow > Scheduled cloud flow**
3. Set recurrence: **Daily at 10:00 PM UTC**
4. Add the following actions:

**Action 1: HTTP - Fetch Binance Rate**
```
Method: POST
URI: https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search
Headers: Content-Type: application/json
Body: {"asset":"USDT","fiat":"VES","merchantCheck":false,"page":1,"payTypes":[],"rows":10,"tradeType":"BUY"}
```

**Action 2: Parse JSON - Extract Binance Rate**
Parse the response body, extract `data[0].adv.price` as the rate.

**Action 3: HTTP - Fetch BCV Page**
```
Method: GET
URI: https://www.bcv.org.ve/
```

**Action 4: Excel Online (Business) - Add a row**
```
Location: OneDrive for Business
Document Library: OneDrive
File: /path/to/your/rates.xlsx
Table: Rates
Row: {fecha: utcNow(), tasa_binance: [from step 2], tasa_bcv: [from step 3 regex], ...}
```

### 3. Configure the Web App
If OneDrive syncs the file locally:
```
RATE_SOURCE=local_only
# App reads from the synced OneDrive path directly
```

Or use the Upload tab to manually push updates.

## Alternative: Cloudflare Worker Proxy
Since the HTTP action requires Premium, a free alternative is to deploy a small
Cloudflare Worker (free tier: 100k requests/day) that fetches BCV + Binance and
returns JSON. Your Power Automate flow then calls the Cloudflare Worker URL instead.

See the [Cloudflare Workers docs](https://developers.cloudflare.com/workers/) for setup.
