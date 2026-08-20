/**
 * Google Apps Script Web App for FootyArcade / Playmaker
 * 
 * Instructions:
 * 1. Open your Google Sheet.
 * 2. Click "Extensions" -> "Apps Script".
 * 3. Replace all code in the Apps Script editor with this code.
 * 4. Click "Deploy" -> "New deployment" (or "Manage deployments" -> edit -> new version).
 * 5. Set "Execute as" to "Me".
 * 6. Set "Who has access" to "Anyone".
 * 7. Click "Deploy".
 */

function doPost(e) {
  try {
    // Parse incoming payload
    var payload = JSON.parse(e.postData.contents);
    var type = payload.type || 'feedback';
    var url = (payload.url || '').toLowerCase();

    // Guard: Only record events from the production domain, and never from template URLs
    if (url && (url.indexOf('playmaker.best') === -1 || url.indexOf('/templates/') !== -1 || url.indexOf('_template.html') !== -1)) {
      return ContentService.createTextOutput(JSON.stringify({ status: 'ignored', reason: 'Non-production or template URL' }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    var doc = SpreadsheetApp.getActiveSpreadsheet();
    var sheetName = type === 'feedback' ? 'Feedback' : 'Events';
    var sheet = doc.getSheetByName(sheetName);
    
    // Auto-create sheet and write headers if it does not exist
    if (!sheet) {
      sheet = doc.insertSheet(sheetName);
      if (type === 'feedback') {
        sheet.appendRow([
          'Timestamp', 
          'Visitor ID', 
          'Session ID', 
          'Category', 
          'Message', 
          'Email', 
          'URL'
        ]);
      } else {
        sheet.appendRow([
          'Timestamp', 
          'Visitor ID',
          'Session ID',
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
        payload.visitorId || '',
        payload.sessionId || '',
        payload.category || '',
        payload.message || '',
        payload.email || '',
        payload.url || ''
      ]);
    } else {
      sheet.appendRow([
        timestamp,
        payload.visitorId || '',
        payload.sessionId || '',
        payload.eventName || '',
        payload.gameId || '',
        payload.puzzleNum || 0,
        payload.score !== undefined ? payload.score : '',
        payload.maxScore !== undefined ? payload.maxScore : '',
        payload.lives !== undefined ? payload.lives : '',
        payload.won !== undefined ? payload.won : '',
        payload.isBackInTime !== undefined ? payload.isBackInTime : '',
        payload.extraDetails || '',
        payload.url || ''
      ]);
    }
    
    return ContentService.createTextOutput(JSON.stringify({ status: 'success' }))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: 'error', message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return HtmlService.createHtmlOutput("<h3>FootyArcade Analytics Webhook is active!</h3><p>Send a POST request with event or feedback data.</p>");
}
