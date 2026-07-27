/**
 * Google Apps Script Web App Template for Playmaker
 * 
 * Instructions:
 * 1. Open Google Sheets (create a new or open an existing spreadsheet).
 * 2. Click "Extensions" -> "Apps Script".
 * 3. Delete any code in the editor and paste this code.
 * 4. Click "Deploy" -> "New deployment".
 * 5. Under "Select type", choose "Web app".
 * 6. Set "Execute as" to "Me".
 * 7. Set "Who has access" to "Anyone" (crucial for public POST requests).
 * 8. Click "Deploy", authorize the permissions, and copy the "Web app URL".
 * 9. Paste the URL into footy-ui.js under FEEDBACK_WEBHOOK_URL.
 */

function doPost(e) {
  try {
    // Parse incoming payload
    var payload = JSON.parse(e.postData.contents);
    var type = payload.type || 'feedback';
    
    var doc = SpreadsheetApp.getActiveSpreadsheet();
    var sheetName = type === 'feedback' ? 'Feedback' : 'Events';
    var sheet = doc.getSheetByName(sheetName);
    
    // Auto-create sheet and write headers if it does not exist
    if (!sheet) {
      sheet = doc.insertSheet(sheetName);
      if (type === 'feedback') {
        sheet.appendRow(['Timestamp', 'Category', 'Message', 'Email', 'URL']);
      } else {
        sheet.appendRow([
          'Timestamp', 
          'Event Name', 
          'Game ID', 
          'Puzzle Number', 
          'Score', 
          'Max Score', 
          'Lives Left', 
          'Won', 
          'Is Back In Time', 
          'Extra Details', 
          'URL'
        ]);
      }
      // Apply basic styling to headers
      sheet.getRange(1, 1, 1, sheet.getLastColumn())
        .setFontWeight('bold')
        .setBackground('#1c1b1b')
        .setFontColor('#ffffff');
    }
    
    var timestamp = new Date().toISOString();
    
    if (type === 'feedback') {
      sheet.appendRow([
        timestamp,
        payload.category || '',
        payload.message || '',
    const data = JSON.parse(e.postData.contents);
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    
    // Route by action/type
    if (data.type === "analytics") {
      logAnalytics(ss, data);
    } else if (data.type === "feedback") {
      logFeedback(ss, data);
    }
    
    return ContentService.createTextOutput(JSON.stringify({ status: "success" }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function logAnalytics(ss, data) {
  let sheet = ss.getSheetByName("Analytics");
  if (!sheet) {
    sheet = ss.insertSheet("Analytics");
    sheet.appendRow(["Timestamp", "Game ID", "Game Name", "Result", "Guesses Used", "User Agent"]);
  }
  sheet.appendRow([
    new Date(),
    data.gameId || "",
    data.gameName || "",
    data.result || "",
    data.guessesUsed || "",
    data.userAgent || ""
  ]);
}

function logFeedback(ss, data) {
  let sheet = ss.getSheetByName("Feedback");
  if (!sheet) {
    sheet = ss.insertSheet("Feedback");
    sheet.appendRow(["Timestamp", "Category", "Message", "User Agent"]);
  }
  sheet.appendRow([
    new Date(),
    data.category || "General",
    data.message || "",
    data.userAgent || ""
  ]);
}

function doGet(e) {
  return HtmlService.createHtmlOutput("<h3>Playmaker Analytics Webhook is active!</h3><p>Send a POST request with event or feedback data.</p>");
}
