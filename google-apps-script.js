/**
 * Google Apps Script Web App for FootyArcade / Playmaker
 * 
 * Instructions:
 * 1. Open your Google Sheet (https://docs.google.com/spreadsheets/d/1ZNJ57i7kVUYrdW4q4S3lRe4NqYUM7-lL4RQtSzX0_8Q).
 * 2. Click "Extensions" -> "Apps Script".
 * 3. Replace all code in the Apps Script editor with this file's code and click "Save".
 * 4. IMPORTANT - AUTHORIZATION (One-Time Step):
 *    - In the toolbar at the top, select the function "authorizeScript" from the dropdown.
 *    - Click "Run" (▶).
 *    - A popup will appear: "Authorization Required" (נדרשת הרשאה).
 *    - Click "Review Permissions" -> Select your Google Account -> Click "Advanced" (מתקדם) -> Click "Go to (unsafe)" -> Click "Allow" (אישור).
 *    - This grants the required 'external_request' permission for UrlFetchApp.
 * 5. (Recommended) Go to Project Settings (⚙️) -> Script Properties -> Add "GROQ_API_KEY" with your Groq key.
 * 6. Click "Deploy" -> "Manage deployments" -> edit (pencil icon) -> select "New version" -> "Deploy".
 *    Make sure "Execute as" is "Me" and "Who has access" is "Anyone".
 * 7. (ONE-TIME REPAIR FOR TASK #17):
 *    - Select function "repairFeedbackSheet" from the Apps Script editor toolbar and click "Run" (▶).
 *    - OR simply open in your browser: <WEB_APP_URL>?action=repair_feedback
 *    - This will auto-migrate headers and unshift any previously corrupted feedback rows!
 */

/**
 * Run this function once from the Apps Script editor toolbar to grant UrlFetchApp permissions!
 */
function authorizeScript() {
  var testUrl = "https://httpbin.org/get";
  var res = UrlFetchApp.fetch(testUrl);
  Logger.log("UrlFetchApp authorized successfully! Response code: " + res.getResponseCode());
}

/**
 * Resolves feedback payload into an array matching the sheet's actual header names dynamically.
 */
function buildFeedbackRow(headers, payload, timestamp) {
  return headers.map(function(header) {
    var h = (header || '').toString().trim().toLowerCase();
    if (h.indexOf('time') !== -1 || h.indexOf('date') !== -1) {
      return timestamp;
    }
    if (h.indexOf('visitor') !== -1) {
      return payload.visitorId || '';
    }
    if (h.indexOf('session') !== -1) {
      return payload.sessionId || '';
    }
    if (h.indexOf('category') !== -1 || h.indexOf('type') !== -1) {
      return payload.category || '';
    }
    if (h.indexOf('message') !== -1 || h.indexOf('feedback') !== -1 || h.indexOf('comment') !== -1) {
      return payload.message || '';
    }
    if (h.indexOf('email') !== -1) {
      return payload.email || '';
    }
    if (h.indexOf('url') !== -1 || h.indexOf('page') !== -1) {
      return payload.url || '';
    }
    return '';
  });
}

/**
 * Resolves event payload into an array matching the sheet's actual header names dynamically.
 */
function buildEventsRow(headers, payload, timestamp) {
  return headers.map(function(header) {
    var h = (header || '').toString().trim().toLowerCase();
    if (h.indexOf('time') !== -1 || h.indexOf('date') !== -1) return timestamp;
    if (h.indexOf('event') !== -1) return payload.eventName || '';
    if (h.indexOf('game') !== -1) return payload.gameId || '';
    if (h.indexOf('puzzle') !== -1) return payload.puzzleNum !== undefined ? payload.puzzleNum : 0;
    if (h === 'score') return payload.score !== undefined ? payload.score : '';
    if (h.indexOf('max') !== -1) return payload.maxScore !== undefined ? payload.maxScore : '';
    if (h.indexOf('live') !== -1) return payload.lives !== undefined ? payload.lives : '';
    if (h === 'won') return payload.won !== undefined ? payload.won : '';
    if (h.indexOf('back') !== -1) return payload.isBackInTime !== undefined ? payload.isBackInTime : '';
    if (h.indexOf('detail') !== -1 || h.indexOf('extra') !== -1) return payload.extraDetails || '';
    if (h.indexOf('source') !== -1) return payload.urlSource || payload.source || '';
    if (h.indexOf('visitor') !== -1) return payload.visitorId || '';
    if (h.indexOf('session') !== -1) return payload.sessionId || '';
    if (h === 'url' || h.indexOf('page') !== -1) return payload.url || '';
    return '';
  });
}

/**
 * Ensures Feedback sheet headers include Visitor ID and Session ID without shifting data.
 */
function ensureFeedbackHeaders(sheet) {
  var lastCol = sheet.getLastColumn();
  if (lastCol === 0) {
    var defaultHeaders = [
      'Timestamp',
      'Category',
      'Message',
      'Email',
      'Visitor ID',
      'Session ID',
      'URL'
    ];
    sheet.appendRow(defaultHeaders);
    sheet.getRange(1, 1, 1, defaultHeaders.length)
      .setFontWeight('bold')
      .setBackground('#1c1b1b')
      .setFontColor('#ffffff');
    return defaultHeaders;
  }

  var headers = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  var norm = headers.map(function(h) { return (h || '').toString().trim().toLowerCase(); });
  var hasVisitorId = norm.some(function(h) { return h.indexOf('visitor') !== -1; });
  var hasSessionId = norm.some(function(h) { return h.indexOf('session') !== -1; });

  if (!hasVisitorId) {
    var nextCol = sheet.getLastColumn() + 1;
    sheet.getRange(1, nextCol).setValue('Visitor ID')
      .setFontWeight('bold')
      .setBackground('#1c1b1b')
      .setFontColor('#ffffff');
    headers.push('Visitor ID');
  }
  if (!hasSessionId) {
    var nextCol = sheet.getLastColumn() + 1;
    sheet.getRange(1, nextCol).setValue('Session ID')
      .setFontWeight('bold')
      .setBackground('#1c1b1b')
      .setFontColor('#ffffff');
    headers.push('Session ID');
  }

  return headers;
}

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput(JSON.stringify({ status: 'error', message: 'No payload provided' }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // Parse incoming payload
    var payload = JSON.parse(e.postData.contents);
    var type = payload.type || 'feedback';
    var url = (payload.url || '').toLowerCase();

    // ── 1. VAR Review Appeal Request ─────────────────────────────
    if (type === 'var_check') {
      return handleVarCheck(payload);
    }

    // ── 1b. Daily Puzzle Verification Cron Audit Report ─────────
    if (type === 'puzzle_audit') {
      return handlePuzzleAudit(payload);
    }

    // ── 2. Guard for general feedback/events ─────────────────────
    // Only record events from the production domain, and never from template URLs
    if (url && (url.indexOf('playmaker.best') === -1 || url.indexOf('/templates/') !== -1 || url.indexOf('_template.html') !== -1)) {
      return ContentService.createTextOutput(JSON.stringify({ status: 'ignored', reason: 'Non-production or template URL' }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var doc = SpreadsheetApp.getActiveSpreadsheet();
    var sheetName = type === 'feedback' ? 'Feedback' : 'Events';
    var sheet = doc.getSheetByName(sheetName);
    var timestamp = new Date().toISOString();

    if (type === 'feedback') {
      if (!sheet) {
        sheet = doc.insertSheet(sheetName);
      }
      var feedbackHeaders = ensureFeedbackHeaders(sheet);
      var feedbackRow = buildFeedbackRow(feedbackHeaders, payload, timestamp);
      sheet.appendRow(feedbackRow);
    } else {
      // Auto-create Events sheet and write headers if it does not exist
      if (!sheet) {
        sheet = doc.insertSheet(sheetName);
        var defaultEventsHeaders = [
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
          'URL',
          'Visitor ID',
          'Session ID',
          'URL Source'
        ];
        sheet.appendRow(defaultEventsHeaders);
        sheet.getRange(1, 1, 1, defaultEventsHeaders.length)
          .setFontWeight('bold')
          .setBackground('#1c1b1b')
          .setFontColor('#ffffff');
      } else {
        // Auto-migrate: check if column 14 header needs to be added for URL Source
        var lastCol = sheet.getLastColumn();
        if (lastCol === 13) {
          sheet.getRange(1, 14).setValue('URL Source')
            .setFontWeight('bold')
            .setBackground('#1c1b1b')
            .setFontColor('#ffffff');
        }
      }

      var eventHeaders = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
      var eventRow = buildEventsRow(eventHeaders, payload, timestamp);
      sheet.appendRow(eventRow);
    }

    return ContentService.createTextOutput(JSON.stringify({ status: 'success' }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: 'error', message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Handles real-time VAR checks using Groq Llama 3.3 70B
 */
function handleVarCheck(payload) {
  var timestamp = new Date().toISOString();
  var scriptProps = PropertiesService.getScriptProperties();
  var apiKey = scriptProps.getProperty('GROQ_API_KEY') || '';

  var gameId = payload.gameId || '';
  var puzzleNum = payload.puzzleNum || 0;
  var theme = payload.theme || '';
  var guess = payload.guess || '';
  var context = payload.context || '';
  var visitorId = payload.visitorId || '';
  var sessionId = payload.sessionId || '';
  var url = payload.url || '';

  var varResult = {
    accepted: false,
    reason: 'VAR check could not be completed.',
    stat: ''
  };

  try {
    var prompt = "You are the official Video Assistant Referee (VAR) for FootyArcade / Playmaker football trivia.\n" +
      "A player guessed '" + guess + "' and it was flagged incorrect. The player appealed for a VAR Review.\n\n" +
      "Game Type: " + gameId + "\n" +
      "Puzzle Theme / Target: " + theme + "\n" +
      "Player Guessed: " + guess + "\n" +
      "Extra Context / Criteria: " + context + "\n\n" +
      "VERIFICATION RULES:\n" +
      "1. For 'top_scorers': Check if " + guess + " legitimately belongs among the top goalscorers for the specified competition and season ('" + theme + "').\n" +
      "   - CRITICAL REQUIREMENT FOR GOALS: The 'goals' field MUST be strictly the goals scored ONLY in the exact competition and season specified in Puzzle Theme ('" + theme + "'). NEVER return domestic league or all-competition totals. (For example, in 'UEFA Champions League 2020/21', Lionel Messi scored 5 goals in the Champions League for Barcelona, NOT his 30 domestic La Liga goals. In UEFA Champions League, his goals are 5).\n" +
      "   - If their goals in '" + theme + "' equal or exceed the 10th-place cutoff mentioned in the context (or tie with the cutoff rank), set accepted=true and return their exact competition goal count in 'goals'.\n" +
      "   - If their goals in '" + theme + "' fall below the cutoff or they did not participate in that competition, set accepted=false.\n" +
      "2. For 'top_transfers': Check if " + guess + " legitimately transferred to/from the club or fits the nationality transfer criteria with a fee that meets or exceeds the 10th-place cutoff fee mentioned in the context (or ranks among the club's record transfers). For example, Klaas-Jan Huntelaar transferred from AC Milan to Schalke 04 in 2010 for ~€14M, which is higher than an €8.0M cutoff and MUST be accepted. If their transfer fee meets or exceeds the cutoff, set accepted=true.\n" +
      "3. For 'player_chain': The context specifies the required clubs (e.g. 'Must have played for Club A & Club B & Club C'). The guessed player (" + guess + ") MUST have played for ALL listed clubs during their senior professional career. If they played for only some of the clubs, or were merely international teammates with the target player, you MUST set accepted=false.\n" +
      "4. If the player clearly does NOT meet the criteria or did not play/score/transfer as claimed, set accepted=false.\n\n" +
      "Return ONLY a JSON object with this exact schema:\n" +
      "{\n" +
      '  "accepted": true or false,\n' +
      '  "reason": "Concise 1-sentence referee explanation (e.g. \'Klaas-Jan Huntelaar transferred to Schalke in 2010 for €14M, exceeding the cutoff.\')",\n' +
      '  "stat": "Short stat label (e.g. \'€14.0M Transfer\' or \'17 Goals\')",\n' +
      '  "fee_amount": 14000000,\n' +
      '  "year": "2010",\n' +
      '  "from_club": "AC Milan",\n' +
      '  "goals": 6,\n' +
      '  "club": "Real Madrid"\n' +
      "}";

    var modelsToTry = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "qwen/qwen3.6-27b", "meta-llama/llama-prompt-guard-2-22m", "groq/compound-mini"];
    var success = false;
    var lastError = "";

    for (var m = 0; m < modelsToTry.length; m++) {
      var currentModel = modelsToTry[m];
      var groqPayload = {
        model: currentModel,
        messages: [
          { role: "system", content: "You are an official football referee VAR official. Return ONLY valid JSON with keys: accepted, reason, stat, fee_amount, year, from_club, goals, club." },
          { role: "user", content: prompt }
        ],
        response_format: { type: "json_object" },
        temperature: 0.1
      };

      var response = UrlFetchApp.fetch("https://api.groq.com/openai/v1/chat/completions", {
        method: "post",
        contentType: "application/json",
        headers: { "Authorization": "Bearer " + apiKey },
        payload: JSON.stringify(groqPayload),
        muteHttpExceptions: true
      });

      var resCode = response.getResponseCode();
      var resText = response.getContentText();

      if (resCode === 200) {
        var resJson = JSON.parse(resText);
        var rawContent = resJson.choices && resJson.choices[0] && resJson.choices[0].message ? resJson.choices[0].message.content : '{}';
        var parsed = JSON.parse(rawContent);
        varResult.accepted = parsed.accepted === true;
        varResult.reason = varResult.accepted ? (parsed.reason || 'Goal awarded after VAR review!') : 'The VAR challenge failed and the decision stands.';
        varResult.stat = parsed.stat || '';
        varResult.fee_amount = parsed.fee_amount || 0;
        varResult.year = parsed.year || '';
        varResult.from_club = parsed.from_club || '';
        varResult.goals = parsed.goals || 0;
        varResult.club = parsed.club || '';
        success = true;
        break;
      } else {
        lastError = "Model " + currentModel + " returned " + resCode + ": " + resText;
        console.warn(lastError);
      }
    }

    if (!success) {
      varResult.reason = 'VAR review service error: ' + lastError;
      varResult.isError = true;
    }

  } catch (apiErr) {
    varResult.reason = 'VAR evaluation exception: ' + apiErr.toString();
    varResult.isError = true;
  }

  // Log to "VAR Reviews" tab in Google Sheet
  try {
    var doc = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = doc.getSheetByName('VAR Reviews');
    if (!sheet) {
      sheet = doc.insertSheet('VAR Reviews');
      sheet.appendRow([
        'Timestamp',
        'Visitor ID',
        'Session ID',
        'Game ID',
        'Puzzle Number',
        'Theme',
        'Guessed Player',
        'Decision',
        'Reason',
        'Stat',
        'URL'
      ]);
      sheet.getRange(1, 1, 1, sheet.getLastColumn())
        .setFontWeight('bold')
        .setBackground('#1c1b1b')
        .setFontColor('#39ff14');
    }

    sheet.appendRow([
      timestamp,
      visitorId,
      sessionId,
      gameId,
      puzzleNum,
      theme,
      guess,
      varResult.accepted ? 'ACCEPTED (OVERRULED)' : 'REJECTED (STANDS)',
      varResult.reason,
      varResult.stat,
      url
    ]);

    // If accepted, record in "Puzzle Overrides" for global synchronization across all players
    if (varResult.accepted && !varResult.isError) {
      try {
        var overridesSheet = doc.getSheetByName('Puzzle Overrides');
        if (!overridesSheet) {
          overridesSheet = doc.insertSheet('Puzzle Overrides');
          overridesSheet.appendRow([
            'Timestamp',
            'Game ID',
            'Puzzle Number',
            'Player Name',
            'Stat',
            'Fee Amount',
            'Year',
            'From Club',
            'To Club',
            'Goals',
            'Reason'
          ]);
          overridesSheet.getRange(1, 1, 1, overridesSheet.getLastColumn())
            .setFontWeight('bold')
            .setBackground('#1c1b1b')
            .setFontColor('#39ff14');
        }

        var existingRows = overridesSheet.getDataRange().getValues();
        var alreadySaved = false;
        for (var r = 1; r < existingRows.length; r++) {
          if (existingRows[r][1] === gameId &&
            parseInt(existingRows[r][2], 10) === parseInt(puzzleNum, 10) &&
            existingRows[r][3].toString().toLowerCase() === guess.toLowerCase()) {
            alreadySaved = true;
            break;
          }
        }

        if (!alreadySaved) {
          overridesSheet.appendRow([
            timestamp,
            gameId,
            puzzleNum,
            guess,
            varResult.stat || '',
            varResult.fee_amount || 0,
            varResult.year || '',
            varResult.from_club || '',
            varResult.club || theme || '',
            varResult.goals || 0,
            varResult.reason || ''
          ]);
        }
      } catch (ovErr) {
        console.error('Failed to log puzzle override:', ovErr);
      }
    }
  } catch (sheetErr) {
    // Non-blocking if sheet logging fails
    console.error('Sheet logging error:', sheetErr);
  }

  return ContentService.createTextOutput(JSON.stringify({
    status: 'success',
    accepted: varResult.accepted,
    reason: varResult.reason,
    stat: varResult.stat,
    fee_amount: varResult.fee_amount,
    year: varResult.year,
    from_club: varResult.from_club,
    goals: varResult.goals,
    club: varResult.club,
    isError: varResult.isError === true
  })).setMimeType(ContentService.MimeType.JSON);
}

/**
 * Handles daily puzzle verification cron audit reports
 */
function handlePuzzleAudit(payload) {
  var doc = SpreadsheetApp.getActiveSpreadsheet();
  var sheetName = 'Puzzle Audits';
  var sheet = doc.getSheetByName(sheetName);

  if (!sheet) {
    sheet = doc.insertSheet(sheetName);
    sheet.appendRow([
      'Timestamp',
      'Target Date',
      'Puzzle Number',
      'Status',
      'Games Audited',
      'Issues Detected',
      'Auto-Fixes Applied',
      'Execution Time (s)',
      'Details / Summary'
    ]);
    sheet.getRange(1, 1, 1, 9)
      .setFontWeight('bold')
      .setBackground('#1c1b1b')
      .setFontColor('#00f0ff');
  }

  var timestamp = new Date().toISOString();
  var targetDate = payload.targetDate || '';
  var puzzleNum = payload.puzzleNum || 0;
  var status = payload.status || 'UNKNOWN';
  var gamesAudited = payload.gamesAudited || '';
  var issuesCount = payload.issuesCount !== undefined ? payload.issuesCount : 0;
  var fixesCount = payload.fixesCount !== undefined ? payload.fixesCount : 0;
  var execTime = payload.execTimeSec !== undefined ? payload.execTimeSec : '';
  var summary = typeof payload.summary === 'object' ? JSON.stringify(payload.summary) : (payload.summary || '');

  sheet.appendRow([
    timestamp,
    targetDate,
    puzzleNum,
    status,
    gamesAudited,
    issuesCount,
    fixesCount,
    execTime,
    summary
  ]);

  // Also log flagged discrepancies / suggestions into 'Puzzle Review' tab for easy human approval
  var flaggedReviews = payload.flaggedReviews || [];
  if (flaggedReviews && flaggedReviews.length > 0) {
    try {
      var reviewSheetName = 'Puzzle Review';
      var reviewSheet = doc.getSheetByName(reviewSheetName);
      if (!reviewSheet) {
        reviewSheet = doc.insertSheet(reviewSheetName);
        reviewSheet.appendRow([
          'Timestamp',
          'Target Date',
          'Game ID',
          'Puzzle #',
          'Field / Player',
          'Current Value',
          'Suggested / Correct',
          'Reason / Note',
          'Status (Action)',
          'Applied Date'
        ]);
        reviewSheet.getRange(1, 1, 1, 10)
          .setFontWeight('bold')
          .setBackground('#1c1b1b')
          .setFontColor('#ffd700');
        reviewSheet.setFrozenRows(1);
      }

      // Add each flagged item with a Pending dropdown
      for (var f = 0; f < flaggedReviews.length; f++) {
        var item = flaggedReviews[f];
        var newRow = reviewSheet.getLastRow() + 1;
        reviewSheet.appendRow([
          timestamp,
          targetDate,
          item.game_id || '',
          item.puzzle_num || '',
          item.field || '',
          item.current || '',
          item.correct || '',
          item.reason || '',
          'Pending',
          ''
        ]);

        // Build interactive dropdown in Column I: Pending, Approved, Rejected
        var rule = SpreadsheetApp.newDataValidation()
          .requireValueInList(['Pending', 'Approved', 'Rejected'], true)
          .setAllowInvalid(false)
          .build();
        reviewSheet.getRange(newRow, 9).setDataValidation(rule).setFontWeight('bold').setFontColor('#ffaa00');
      }
    } catch (revErr) {
      console.error('Failed to log to Puzzle Review sheet:', revErr);
    }
  }

  return ContentService.createTextOutput(JSON.stringify({
    status: 'success',
    message: 'Puzzle audit logged successfully'
  })).setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  try {
    var params = e ? e.parameter : {};

    // ── 0. Repair Feedback Sheet Historical Data ─────────────────
    if (params && params.action === 'repair_feedback') {
      var repairResult = repairFeedbackSheet();
      return ContentService.createTextOutput(JSON.stringify(repairResult))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // ── 1. Get Approved Reviews for Auto-Applying Fixes ──────────
    if (params && params.action === 'get_approved_reviews') {
      var doc = SpreadsheetApp.getActiveSpreadsheet();
      var reviewSheet = doc.getSheetByName('Puzzle Review');
      var approved = [];

      if (reviewSheet) {
        var data = reviewSheet.getDataRange().getValues();
        for (var i = 1; i < data.length; i++) {
          var row = data[i];
          var status = (row[8] || '').toString().trim();
          var appliedDate = row[9];

          // Return rows marked 'Approved' that have not yet been marked applied
          if (status === 'Approved' && !appliedDate) {
            approved.push({
              rowIndex: i + 1, // 1-indexed for sheet
              targetDate: row[1],
              gameId: row[2],
              puzzleNum: parseInt(row[3], 10),
              field: row[4],
              current: row[5],
              correct: row[6],
              reason: row[7]
            });
          }
        }
      }

      return ContentService.createTextOutput(JSON.stringify({
        status: 'success',
        approved: approved
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // ── 2. Get Global Overrides for Runtime App ──────────────────
    if (params && params.action === 'get_overrides') {
      var targetGameId = params.gameId || '';
      var targetPuzzleNum = parseInt(params.puzzleNum || '0', 10);

      var doc = SpreadsheetApp.getActiveSpreadsheet();
      var sheet = doc.getSheetByName('Puzzle Overrides');
      var overrides = [];

      if (sheet) {
        var data = sheet.getDataRange().getValues();
        for (var i = 1; i < data.length; i++) {
          var row = data[i];
          var rowGameId = row[1];
          var rowPuzzleNum = parseInt(row[2], 10);

          if ((!targetGameId || rowGameId === targetGameId) && (!targetPuzzleNum || rowPuzzleNum === targetPuzzleNum)) {
            overrides.push({
              gameId: rowGameId,
              puzzleNum: rowPuzzleNum,
              player_name: row[3],
              stat: row[4],
              fee_amount: row[5],
              year: row[6],
              from_club: row[7],
              to_club: row[8],
              goals: row[9],
              reason: row[10]
            });
          }
        }
      }

      return ContentService.createTextOutput(JSON.stringify({
        status: 'success',
        overrides: overrides
      })).setMimeType(ContentService.MimeType.JSON);
    }
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: 'error', message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  return HtmlService.createHtmlOutput("<h3>FootyArcade Analytics & VAR Webhook is active!</h3><p>Send a POST request with event, feedback, or VAR review data.</p>");
}

/**
 * Repairs historical corrupted rows in the 'Feedback' sheet where UUIDs were shifted into Category/Message.
 * Can be run from the Apps Script editor or triggered via doGet(?action=repair_feedback).
 */
function repairFeedbackSheet() {
  try {
    var doc = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = doc.getSheetByName('Feedback');
    if (!sheet) {
      return { status: 'error', message: "No 'Feedback' sheet found" };
    }

    // Ensure headers exist and have Visitor ID & Session ID
    var headers = ensureFeedbackHeaders(sheet);
    var numCols = headers.length;
    var lastRow = sheet.getLastRow();
    if (lastRow <= 1) {
      return { status: 'success', message: 'No data rows to repair', repairedRows: 0, totalRows: 0 };
    }

    var colMap = {};
    for (var i = 0; i < headers.length; i++) {
      var hl = (headers[i] || '').toString().trim().toLowerCase();
      if (hl.indexOf('time') !== -1 || hl.indexOf('date') !== -1) {
        colMap['timestamp'] = i;
      } else if (hl.indexOf('visitor') !== -1) {
        colMap['visitorId'] = i;
      } else if (hl.indexOf('session') !== -1) {
        colMap['sessionId'] = i;
      } else if (hl.indexOf('category') !== -1 || hl.indexOf('type') !== -1) {
        colMap['category'] = i;
      } else if (hl.indexOf('message') !== -1 || hl.indexOf('feedback') !== -1 || hl.indexOf('comment') !== -1) {
        colMap['message'] = i;
      } else if (hl.indexOf('email') !== -1) {
        colMap['email'] = i;
      } else if (hl.indexOf('url') !== -1 || hl.indexOf('page') !== -1) {
        colMap['url'] = i;
      }
    }

    var catIdx = colMap['category'] !== undefined ? colMap['category'] : 1;
    var uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    
    // Read all data rows
    var dataRange = sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn());
    var rows = dataRange.getValues();
    var repairedCount = 0;

    for (var r = 0; r < rows.length; r++) {
      var row = rows[r];
      var valInCat = (row[catIdx] || '').toString().trim();

      // Check if category column has a UUID (corrupted by shifted visitorId)
      if (uuidRegex.test(valInCat)) {
        // Row was previously inserted as: [timestamp, visitorId, sessionId, category, message, email, url]
        var origTs = row[0];
        var trueVisitorId = row[1] || '';
        var trueSessionId = row[2] || '';
        var trueCategory = row[3] || '';
        var trueMessage = row[4] || '';
        var trueEmail = row[5] || '';
        var trueUrl = row[6] || '';

        var correctedRow = new Array(numCols).fill('');
        if (colMap['timestamp'] !== undefined) correctedRow[colMap['timestamp']] = origTs;
        if (colMap['visitorId'] !== undefined) correctedRow[colMap['visitorId']] = trueVisitorId;
        if (colMap['sessionId'] !== undefined) correctedRow[colMap['sessionId']] = trueSessionId;
        if (colMap['category'] !== undefined) correctedRow[colMap['category']] = trueCategory;
        if (colMap['message'] !== undefined) correctedRow[colMap['message']] = trueMessage;
        if (colMap['email'] !== undefined) correctedRow[colMap['email']] = trueEmail;
        if (colMap['url'] !== undefined) correctedRow[colMap['url']] = trueUrl;

        // Update row in sheet (row index is r + 2 because 1-indexed and header is row 1)
        sheet.getRange(r + 2, 1, 1, numCols).setValues([correctedRow]);
        repairedCount++;
      }
    }

    var result = {
      status: 'success',
      message: 'Feedback sheet processed successfully',
      repairedRows: repairedCount,
      totalRows: rows.length
    };
    Logger.log(JSON.stringify(result));
    return result;
  } catch (err) {
    Logger.log('Error repairing feedback sheet: ' + err.toString());
    return { status: 'error', message: err.toString() };
  }
}
