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
 */

/**
 * Run this function once from the Apps Script editor toolbar to grant UrlFetchApp permissions!
 */
function authorizeScript() {
  var testUrl = "https://httpbin.org/get";
  var res = UrlFetchApp.fetch(testUrl);
  Logger.log("UrlFetchApp authorized successfully! Response code: " + res.getResponseCode());
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

    // ── 2. Guard for general feedback/events ─────────────────────
    // Only record events from the production domain, and never from template URLs
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
          'Session ID'
        ]);
      }
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
        payload.eventName || '',
        payload.gameId || '',
        payload.puzzleNum || 0,
        payload.score !== undefined ? payload.score : '',
        payload.maxScore !== undefined ? payload.maxScore : '',
        payload.lives !== undefined ? payload.lives : '',
        payload.won !== undefined ? payload.won : '',
        payload.isBackInTime !== undefined ? payload.isBackInTime : '',
        payload.extraDetails || '',
        payload.url || '',
        payload.visitorId || '',
        payload.sessionId || ''
      ]);
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
      "3. For 'player_chain': Check if " + guess + " legitimately satisfies the step constraint (e.g. was a teammate at the specified club, or has the required nationality/position). If factually true, set accepted=true.\n" +
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

    var modelsToTry = ["openai/gpt-oss-20b", "qwen/qwen3.8-27b", "groq/compound-mini"];
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

function doGet(e) {
  try {
    var params = e ? e.parameter : {};
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
