/**
 * Google Apps Script: Daily Exchange Rate Updater
 * Attaches to a Google Sheet named "Historial_TCBinance_Cloud"
 * Set a time-driven trigger: daily at 6:00 PM VET (22:00 UTC)
 *
 * SETUP:
 * 1. Create a new Google Sheet
 * 2. Open Extensions > Apps Script
 * 3. Paste this script
 * 4. Click "Run" > "setupTrigger" once to install the daily trigger
 * 5. Grant permissions when prompted
 * 6. Share the sheet publicly (Viewer access) for the web app to read
 */

var SHEET_NAME = "Rates";
var BCV_URL = "https://www.bcv.org.ve/";
var BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search";

function setupTrigger() {
  // Delete existing triggers
  var triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(function(t) { ScriptApp.deleteTrigger(t); });

  // Create daily trigger at 10 PM UTC (approximately 6 PM VET)
  ScriptApp.newTrigger("fetchAndAppendRates")
    .timeBased()
    .atHour(22)
    .everyDays(1)
    .create();
  
  Logger.log("Daily trigger set for 22:00 UTC");
}

function fetchBCVRate() {
  try {
    var response = UrlFetchApp.fetch(BCV_URL, {
      muteHttpExceptions: true,
      headers: { "User-Agent": "Mozilla/5.0 (compatible; BudgetBot/1.0)" }
    });
    var html = response.getContentText();
    
    // Try to extract rate from BCV page
    var patterns = [
      /id="dolar"[^>]*>.*?<strong[^>]*>([\d,\.]+)/s,
      /1\s*USD\s*=\s*([\d,\.]+)\s*(?:Bs|VES)/i,
      /<strong[^>]*>([\d]{3,5}[\.,][\d]{2,6})</
    ];
    
    for (var i = 0; i < patterns.length; i++) {
      var match = html.match(patterns[i]);
      if (match) {
        var rate = parseFloat(match[1].replace(",", "."));
        if (rate > 1 && rate < 100000) {
          return rate;
        }
      }
    }
  } catch(e) {
    Logger.log("BCV fetch error: " + e.toString());
  }
  return null;
}

function fetchBinanceRate() {
  try {
    var payload = JSON.stringify({
      asset: "USDT",
      fiat: "VES",
      merchantCheck: false,
      page: 1,
      payTypes: [],
      rows: 20,
      tradeType: "BUY"
    });
    
    var response = UrlFetchApp.fetch(BINANCE_P2P_URL, {
      method: "post",
      contentType: "application/json",
      payload: payload,
      muteHttpExceptions: true
    });
    
    var data = JSON.parse(response.getContentText());
    var ads = data.data || [];
    
    var prices = [];
    for (var i = 0; i < Math.min(ads.length, 10); i++) {
      var price = parseFloat(ads[i].adv.price);
      if (price > 1 && price < 10000) {
        prices.push(price);
      }
    }
    
    if (prices.length === 0) return null;
    
    prices.sort(function(a, b) { return a - b; });
    var mid = Math.floor(prices.length / 2);
    return prices.length % 2 === 0
      ? (prices[mid - 1] + prices[mid]) / 2
      : prices[mid];
      
  } catch(e) {
    Logger.log("Binance fetch error: " + e.toString());
  }
  return null;
}

function fetchAndAppendRates() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(SHEET_NAME);
  
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.getRange(1, 1, 1, 7).setValues([[
      "fecha", "tasa_binance", "tasa_bcv",
      "dif_pct_paralelo", "dif_pct_oficial",
      "log_return_binance", "log_return_bcv"
    ]]);
  }
  
  var today = Utilities.formatDate(new Date(), "UTC", "yyyy-MM-dd");
  var binanceRate = fetchBinanceRate();
  var bcvRate = fetchBCVRate();
  
  if (!binanceRate && !bcvRate) {
    Logger.log("No rates fetched for " + today);
    return;
  }
  
  // Get last row to compute log returns
  var lastRow = sheet.getLastRow();
  var prevBinance = null, prevBCV = null;
  if (lastRow > 1) {
    var lastData = sheet.getRange(lastRow, 1, 1, 7).getValues()[0];
    prevBinance = lastData[1];
    prevBCV = lastData[2];
  }
  
  var difPct = (binanceRate && bcvRate) ? ((binanceRate - bcvRate) / bcvRate * 100) : null;
  var logRetBinance = (binanceRate && prevBinance && prevBinance > 0)
    ? Math.log(binanceRate / prevBinance) : null;
  var logRetBCV = (bcvRate && prevBCV && prevBCV > 0)
    ? Math.log(bcvRate / prevBCV) : null;
  
  sheet.appendRow([
    today,
    binanceRate || "",
    bcvRate || "",
    difPct ? difPct.toFixed(2) : "",
    "",  // dif_pct_oficial
    logRetBinance ? logRetBinance.toFixed(6) : "",
    logRetBCV ? logRetBCV.toFixed(6) : ""
  ]);
  
  Logger.log("Appended: " + today + " | BCV=" + bcvRate + " | Binance=" + binanceRate);
}

// Manual trigger for testing
function runNow() {
  fetchAndAppendRates();
}
