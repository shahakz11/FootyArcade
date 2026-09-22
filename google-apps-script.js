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
    if (h.indexOf('max') !== -1) return payload.maxScore !== undefined ? payload.maxScore : '';
    if (h === 'score') return payload.score !== undefined ? payload.score : '';
    if (h.indexOf('live') !== -1) return payload.lives !== undefined ? payload.lives : (payload.livesLeft !== undefined ? payload.livesLeft : '');
    if (h === 'won') return payload.won !== undefined ? payload.won : '';
    if (h.indexOf('correct') !== -1) return payload.isCorrect !== undefined ? payload.isCorrect : (payload.correct !== undefined ? payload.correct : '');
    if (h.indexOf('guess') !== -1) return payload.guess !== undefined ? payload.guess : '';
    if (h.indexOf('step') !== -1 || h.indexOf('slot') !== -1) return payload.step !== undefined ? payload.step : (payload.slot !== undefined ? payload.slot : '');
    if (h.indexOf('target') !== -1) return payload.target !== undefined ? payload.target : '';
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
 * Ensures Events sheet headers include all standard and extended event columns without shifting data.
 */
function ensureEventsHeaders(sheet) {
  var lastCol = sheet.getLastColumn();
  var defaultEventsHeaders = [
    'Timestamp',
    'Event Name',
    'Game ID',
    'Puzzle Number',
    'Score',
    'Max Score',
    'Lives Left',
    'Won',
    'Is Correct',
    'Guess',
    'Step',
    'Target',
    'Extra Details',
    'URL',
    'Visitor ID',
    'Session ID',
    'URL Source'
  ];

  if (lastCol === 0) {
    sheet.appendRow(defaultEventsHeaders);
    sheet.getRange(1, 1, 1, defaultEventsHeaders.length)
      .setFontWeight('bold')
      .setBackground('#1c1b1b')
      .setFontColor('#ffffff');
    return defaultEventsHeaders;
  }

  var headers = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  var norm = headers.map(function(h) { return (h || '').toString().trim().toLowerCase(); });

  var expectedCols = [
    { name: 'Is Correct', check: function(n) { return n.some(function(h) { return h.indexOf('correct') !== -1; }); } },
    { name: 'Guess', check: function(n) { return n.some(function(h) { return h.indexOf('guess') !== -1; }); } },
    { name: 'Step', check: function(n) { return n.some(function(h) { return h.indexOf('step') !== -1 || h.indexOf('slot') !== -1; }); } },
    { name: 'Target', check: function(n) { return n.some(function(h) { return h.indexOf('target') !== -1; }); } },
    { name: 'Visitor ID', check: function(n) { return n.some(function(h) { return h.indexOf('visitor') !== -1; }); } },
    { name: 'Session ID', check: function(n) { return n.some(function(h) { return h.indexOf('session') !== -1; }); } },
    { name: 'URL Source', check: function(n) { return n.some(function(h) { return h.indexOf('source') !== -1; }); } }
  ];

  for (var i = 0; i < expectedCols.length; i++) {
    if (!expectedCols[i].check(norm)) {
      var nextCol = sheet.getLastColumn() + 1;
      sheet.getRange(1, nextCol).setValue(expectedCols[i].name)
        .setFontWeight('bold')
        .setBackground('#1c1b1b')
        .setFontColor('#ffffff');
      headers.push(expectedCols[i].name);
      norm.push(expectedCols[i].name.toLowerCase());
    }
  }

  return headers;
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

/**
 * Ensures VAR Reviews sheet headers include all standard and debugging columns without shifting existing data.
 */
function ensureVarReviewsHeaders(sheet) {
  var lastCol = sheet.getLastColumn();
  var defaultVarHeaders = [
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
    'Fee Amount',
    'Year',
    'From Club',
    'To Club',
    'Goals',
    'Appearances',
    'Nationality',
    'Model Used',
    'Prompt Sent to AI',
    'Full AI Response (Raw JSON)',
    'Full Request Payload',
    'Error / Exception Details',
    'URL'
  ];

  if (lastCol === 0) {
    sheet.appendRow(defaultVarHeaders);
    sheet.getRange(1, 1, 1, defaultVarHeaders.length)
      .setFontWeight('bold')
      .setBackground('#1c1b1b')
      .setFontColor('#39ff14');
    return defaultVarHeaders;
  }

  var headers = sheet.getRange(1, 1, 1, lastCol).getValues()[0];
  var norm = headers.map(function(h) { return (h || '').toString().trim().toLowerCase(); });

  var expectedCols = [
    { name: 'Timestamp', check: function(n) { return n.some(function(h) { return h.indexOf('time') !== -1 || h.indexOf('date') !== -1; }); } },
    { name: 'Visitor ID', check: function(n) { return n.some(function(h) { return h.indexOf('visitor') !== -1; }); } },
    { name: 'Session ID', check: function(n) { return n.some(function(h) { return h.indexOf('session') !== -1; }); } },
    { name: 'Game ID', check: function(n) { return n.some(function(h) { return h.indexOf('game') !== -1; }); } },
    { name: 'Puzzle Number', check: function(n) { return n.some(function(h) { return h.indexOf('puzzle') !== -1; }); } },
    { name: 'Theme', check: function(n) { return n.some(function(h) { return h.indexOf('theme') !== -1; }); } },
    { name: 'Guessed Player', check: function(n) { return n.some(function(h) { return h.indexOf('guess') !== -1 || h.indexOf('player') !== -1; }); } },
    { name: 'Decision', check: function(n) { return n.some(function(h) { return h.indexOf('decision') !== -1 || h.indexOf('status') !== -1; }); } },
    { name: 'Reason', check: function(n) { return n.some(function(h) { return h.indexOf('reason') !== -1 || h.indexOf('explanation') !== -1; }); } },
    { name: 'Stat', check: function(n) { return n.some(function(h) { return h === 'stat' || (h.indexOf('stat') !== -1 && h.indexOf('status') === -1); }); } },
    { name: 'Fee Amount', check: function(n) { return n.some(function(h) { return h.indexOf('fee') !== -1; }); } },
    { name: 'Year', check: function(n) { return n.some(function(h) { return h === 'year'; }); } },
    { name: 'From Club', check: function(n) { return n.some(function(h) { return h.indexOf('from') !== -1; }); } },
    { name: 'To Club', check: function(n) { return n.some(function(h) { return h.indexOf('to') !== -1 && h.indexOf('visitor') === -1; }); } },
    { name: 'Goals', check: function(n) { return n.some(function(h) { return h.indexOf('goal') !== -1; }); } },
    { name: 'Appearances', check: function(n) { return n.some(function(h) { return h.indexOf('app') !== -1; }); } },
    { name: 'Nationality', check: function(n) { return n.some(function(h) { return h.indexOf('nation') !== -1; }); } },
    { name: 'Model Used', check: function(n) { return n.some(function(h) { return h.indexOf('model') !== -1; }); } },
    { name: 'Prompt Sent to AI', check: function(n) { return n.some(function(h) { return h.indexOf('prompt') !== -1; }); } },
    { name: 'Full AI Response (Raw JSON)', check: function(n) { return n.some(function(h) { return h.indexOf('response') !== -1 || h.indexOf('raw') !== -1; }); } },
    { name: 'Full Request Payload', check: function(n) { return n.some(function(h) { return h.indexOf('payload') !== -1 || h.indexOf('request') !== -1; }); } },
    { name: 'Error / Exception Details', check: function(n) { return n.some(function(h) { return h.indexOf('error') !== -1 || h.indexOf('exception') !== -1; }); } },
    { name: 'URL', check: function(n) { return n.some(function(h) { return h === 'url' || h.indexOf('page') !== -1; }); } }
  ];

  for (var i = 0; i < expectedCols.length; i++) {
    if (!expectedCols[i].check(norm)) {
      var nextCol = sheet.getLastColumn() + 1;
      sheet.getRange(1, nextCol).setValue(expectedCols[i].name)
        .setFontWeight('bold')
        .setBackground('#1c1b1b')
        .setFontColor('#39ff14');
      headers.push(expectedCols[i].name);
      norm.push(expectedCols[i].name.toLowerCase());
    }
  }

  return headers;
}

/**
 * Maps VAR review details dynamically to sheet headers.
 */
function buildVarReviewsRow(headers, data) {
  return headers.map(function(header) {
    var h = (header || '').toString().trim().toLowerCase();
    if (h.indexOf('time') !== -1 || h.indexOf('date') !== -1) return data.timestamp || '';
    if (h.indexOf('visitor') !== -1) return data.visitorId || '';
    if (h.indexOf('session') !== -1) return data.sessionId || '';
    if (h.indexOf('game') !== -1) return data.gameId || '';
    if (h.indexOf('puzzle') !== -1) return data.puzzleNum !== undefined ? data.puzzleNum : 0;
    if (h.indexOf('theme') !== -1) return data.theme || '';
    if (h.indexOf('guess') !== -1 || h.indexOf('player') !== -1) return data.guess || '';
    if (h.indexOf('decision') !== -1 || h.indexOf('status') !== -1) return data.decision || '';
    if (h.indexOf('reason') !== -1 || h.indexOf('explanation') !== -1) return data.reason || '';
    if (h === 'stat' || (h.indexOf('stat') !== -1 && h.indexOf('status') === -1)) return data.stat || '';
    if (h.indexOf('fee') !== -1) return data.fee_amount || 0;
    if (h === 'year') return data.year || '';
    if (h.indexOf('from') !== -1) return data.from_club || '';
    if (h.indexOf('to') !== -1 && h.indexOf('visitor') === -1) return data.to_club || '';
    if (h.indexOf('goal') !== -1) return data.goals || 0;
    if (h.indexOf('app') !== -1) return data.appearances || '';
    if (h.indexOf('nation') !== -1) return data.nationality || '';
    if (h.indexOf('model') !== -1) return data.modelUsed || '';
    if (h.indexOf('prompt') !== -1) return data.prompt || '';
    if (h.indexOf('response') !== -1 || h.indexOf('raw') !== -1) return data.rawResponse || '';
    if (h.indexOf('payload') !== -1 || h.indexOf('request') !== -1) return data.requestPayload || '';
    if (h.indexOf('error') !== -1 || h.indexOf('exception') !== -1) return data.errorDetails || '';
    if (h === 'url' || h.indexOf('page') !== -1) return data.url || '';
    return '';
  });
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
      if (!sheet) {
        sheet = doc.insertSheet(sheetName);
      }
      var eventHeaders = ensureEventsHeaders(sheet);
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
 * Handles real-time VAR checks using Groq high-accuracy models
 */
function handleVarCheck(payload) {
  var timestamp = new Date().toISOString();
  var scriptProps = PropertiesService.getScriptProperties();
  var geminiApiKey = scriptProps.getProperty('GEMINI_API_KEY') || '';
  var groqApiKey = scriptProps.getProperty('GROQ_API_KEY') || '';

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
    stat: '',
    fee_amount: 0,
    year: '',
    from_club: '',
    to_club: '',
    goals: 0,
    club: '',
    appearances: '',
    nationality: '',
    isError: false
  };

  var modelUsed = '';
  var rawResponse = '';
  var errorDetails = '';
  var prompt = '';

  if (!geminiApiKey && !groqApiKey) {
    varResult.reason = 'VAR review service error: Neither GEMINI_API_KEY nor GROQ_API_KEY is configured in Script Properties.';
    varResult.isError = true;
    errorDetails = 'Missing GEMINI_API_KEY and GROQ_API_KEY in Script Properties';
  } else {
    try {
      prompt = "You are the official Video Assistant Referee (VAR) for FootyArcade / Playmaker football trivia.\n" +
        "A player guessed '" + guess + "' and it was flagged incorrect. The player appealed for an official VAR Review.\n\n" +
        "APPEAL DETAILS:\n" +
        "- Game Type: " + gameId + "\n" +
        "- Puzzle Theme / Target: " + theme + "\n" +
        "- Guessed Player / Answer: " + guess + "\n" +
        "- Extra Context / Cutoff: " + context + "\n\n" +
        "STRICT FACT-CHECKING RULES (You must be strict, impartial, and skeptical):\n" +
        "1. DEFAULT TO REJECT (accepted=false): Most appeals are invalid guesses. Overturn the pitch ruling (accepted=true) ONLY if you can verify with 100% historical accuracy against official football databases (Transfermarkt, FIFA, UEFA) that the guess meets all requirements.\n" +
        "2. ZERO HALLUCINATION POLICY: NEVER invent fake transfers, imaginary clubs, unverified transfer fees, or fictitious player records. If the player never played for the club, is not of that nationality, or the transfer fee is below the cutoff, you MUST set accepted=false.\n" +
        "3. STRICT NUMERIC THRESHOLD ENFORCEMENT (Compare fees/goals mathematically):\n" +
        "   * For 'top_transfers': You MUST compare the official transfer fee mathematically against the cutoff fee provided in Extra Context. If the transfer fee is even €1 below the cutoff fee (for example, a fee of €17.5M when the cutoff is €23.0M), the transfer is NOT a top record signing and you MUST set accepted=false with a reason stating the fee is below the cutoff.\n" +
        "   * For 'top_scorers': You MUST compare the goals scored in that competition mathematically against the cutoff goals. If goals < cutoff, you MUST set accepted=false.\n\n" +
        "GAME SPECIFIC VERIFICATION CRITERIA:\n" +
        "- For 'top_transfers':\n" +
        "   * Mode Check: Determine if the theme is a Club (e.g. 'Real Madrid', 'Arsenal', 'Wolverhampton Wanderers') or a Nationality (e.g. 'Ivory Coast', 'Brazil', 'France').\n" +
        "   * If Club Mode: The puzzle is strictly for RECORD SIGNINGS / INCOMING ARRIVALS to that club. The guessed player (" + guess + ") MUST have completed a senior professional transfer TO that club (the target club MUST be the buying club / 'to_club') with an official fee meeting or exceeding the cutoff fee. If the incoming fee is below the cutoff (e.g. €17.5M < €23.0M cutoff), or if it is an outgoing sale/departure FROM the club, set accepted=false. Outgoing sales/departures FROM the club (where the target club was the selling club / 'from_club') are STRICTLY INVALID and MUST be rejected with accepted=false. Return exact 'from_club', 'to_club', 'year', and 'fee_amount'.\n" +
        "   * If Nationality Mode: The guessed player (" + guess + ") MUST be an official international representative of that country in senior football AND must have had a senior club-to-club transfer with an official fee meeting or exceeding the cutoff fee. If the fee is below the cutoff, set accepted=false. Return the exact selling club ('from_club'), buying club ('to_club'), 'year', 'fee_amount', and 'nationality'. If the player is NOT of that nationality or their record transfer fee is below the cutoff, set accepted=false.\n" +
        "- For 'top_scorers':\n" +
        "   * The guessed player (" + guess + ") MUST have scored goals in the EXACT competition and season specified in '" + theme + "'.\n" +
        "   * The 'goals' field MUST be strictly the goals scored ONLY in that competition and season (NEVER domestic league or all-competition totals). If their goals equal or exceed the 10th-place cutoff, set accepted=true, otherwise accepted=false.\n" +
        "- For 'player_chain':\n" +
        "   * The context specifies required clubs (e.g. 'Must have played for Club A & Club B & Club C'). The guessed player (" + guess + ") MUST have played senior professional matches for ALL listed clubs. If they missed even one club, set accepted=false.\n" +
        "- For 'passport_fc':\n" +
        "   * The theme is the Anchor Club and the context specifies the nationality. The guessed player (" + guess + ") MUST have represented that nationality internationally AND played for the anchor club in their senior career. If both true, set accepted=true, else false.\n" +
        "- For 'transfer_destination':\n" +
        "   * The guessed club (" + guess + ") must be a club the target player actually played for / signed for in their senior career.\n" +
        "- For 'club_connect':\n" +
        "   * The guessed club (" + guess + ") must be a club that ALL listed hint players played for during their senior careers.\n" +
        "- For 'anyone_but':\n" +
        "   * Must satisfy the criteria AND must NOT be the excluded player.\n\n" +
        "OUTPUT SCHEMA:\n" +
        "Return ONLY a valid JSON object matching this schema:\n" +
        "{\n" +
        '  "accepted": true,\n' +
        '  "reason": "1 concise factual sentence explaining the referee ruling and exact historical record",\n' +
        '  "stat": "Short stat label (e.g. \'€35.0M Transfer\' or \'8 Goals\')",\n' +
        '  "fee_amount": 35000000,\n' +
        '  "year": "2021",\n' +
        '  "from_club": "Selling Club Name",\n' +
        '  "to_club": "Buying Club Name",\n' +
        '  "goals": 0,\n' +
        '  "club": "Club Name",\n' +
        '  "appearances": "10",\n' +
        '  "nationality": "Country Name"\n' +
        "}";

      // Build Multi-Tier Waterfall Pipeline
      var waterfallSteps = [];

      if (geminiApiKey) {
        // Tier 1: Search Grounded Models (Live Web Grounding for breaking & recent transfers)
        waterfallSteps.push({ provider: 'gemini', model: 'gemini-2.5-flash', useSearch: true });
        waterfallSteps.push({ provider: 'gemini', model: 'gemini-2.5-flash-lite', useSearch: true });

        // Tier 2: High-Quota Gemini Direct Text Models (500 RPD) & Frontier Flash models
        waterfallSteps.push({ provider: 'gemini', model: 'gemini-3.5-flash-lite', useSearch: false });
        waterfallSteps.push({ provider: 'gemini', model: 'gemini-3.1-flash-lite', useSearch: false });
        waterfallSteps.push({ provider: 'gemini', model: 'gemini-3.7-flash', useSearch: false });
        waterfallSteps.push({ provider: 'gemini', model: 'gemini-3.6-flash', useSearch: false });
        waterfallSteps.push({ provider: 'gemini', model: 'gemini-3.5-flash', useSearch: false });
        waterfallSteps.push({ provider: 'gemini', model: 'gemini-2.5-flash', useSearch: false });
        waterfallSteps.push({ provider: 'gemini', model: 'gemini-2.5-flash-lite', useSearch: false });
        waterfallSteps.push({ provider: 'gemini', model: 'gemini-flash-latest', useSearch: false });
        waterfallSteps.push({ provider: 'gemini', model: 'gemma-4-31b-it', useSearch: false });
        waterfallSteps.push({ provider: 'gemini', model: 'gemma-4-26b-a4b-it', useSearch: false });
      }

      if (groqApiKey) {
        // Tier 3: Groq High-Speed LPU Failover
        waterfallSteps.push({ provider: 'groq', model: 'openai/gpt-oss-120b', useSearch: false });
        waterfallSteps.push({ provider: 'groq', model: 'qwen/qwen3.8-27b', useSearch: false });
        waterfallSteps.push({ provider: 'groq', model: 'meta-llama/llama-3.3-70b-versatile', useSearch: false });
        waterfallSteps.push({ provider: 'groq', model: 'openai/gpt-oss-20b', useSearch: false });
      }

      var success = false;
      var lastError = "";
      var startTime = new Date().getTime();

      for (var s = 0; s < waterfallSteps.length; s++) {
        // Guard against total Apps Script execution exceeding gateway limits (22s max)
        if (new Date().getTime() - startTime > 22000) {
          lastError = "VAR evaluation reached 22s deadline limit before completing waterfall.";
          break;
        }
        var step = waterfallSteps[s];
        try {
          if (step.provider === 'gemini') {
            var geminiUrl = "https://generativelanguage.googleapis.com/v1beta/models/" + step.model + ":generateContent?key=" + geminiApiKey;
            var geminiBody = {
              contents: [
                {
                  role: "user",
                  parts: [
                    { text: "SYSTEM: You are a strict, skeptical official football referee VAR fact-checker. Return ONLY valid JSON matching the requested schema.\n\n" + prompt }
                  ]
                }
              ],
              generationConfig: {
                temperature: 0.0
              }
            };

            if (step.useSearch) {
              geminiBody.tools = [{ googleSearch: {} }];
            } else {
              geminiBody.generationConfig.responseMimeType = "application/json";
            }

            var res = UrlFetchApp.fetch(geminiUrl, {
              method: "post",
              contentType: "application/json",
              payload: JSON.stringify(geminiBody),
              muteHttpExceptions: true
            });

            var code = res.getResponseCode();
            var text = res.getContentText();
            rawResponse = text;

            if (code === 200) {
              var resJson = JSON.parse(text);
              var candidate = resJson.candidates && resJson.candidates[0];
              var partText = '';
              if (candidate && candidate.content && candidate.content.parts) {
                for (var p = 0; p < candidate.content.parts.length; p++) {
                  if (candidate.content.parts[p].text) {
                    partText += candidate.content.parts[p].text;
                  }
                }
              }
              var parsed = parseVarJsonResponse(partText);
              if (parsed && typeof parsed.accepted === 'boolean') {
                modelUsed = step.model + (step.useSearch ? ' (Search Grounded)' : '');
                varResult.accepted = parsed.accepted === true;
                varResult.reason = parsed.reason || (varResult.accepted ? 'Appeal accepted after VAR review!' : 'The VAR challenge was rejected and the on-pitch ruling stands.');
                varResult.stat = parsed.stat || '';
                varResult.fee_amount = parsed.fee_amount || 0;
                varResult.year = parsed.year ? parsed.year.toString() : '';
                varResult.from_club = parsed.from_club || '';
                varResult.to_club = parsed.to_club || '';
                varResult.goals = parsed.goals || 0;
                varResult.club = parsed.club || '';
                varResult.appearances = parsed.appearances ? parsed.appearances.toString() : '';
                varResult.nationality = parsed.nationality || '';
                success = true;
                break;
              } else {
                lastError = "Gemini " + step.model + " (search=" + step.useSearch + ") 200 invalid JSON: " + partText.substring(0, 150);
                errorDetails = (errorDetails ? errorDetails + ' | ' : '') + lastError;
              }
            } else {
              lastError = "Gemini " + step.model + " (search=" + step.useSearch + ") HTTP " + code + ": " + text.substring(0, 150);
              errorDetails = (errorDetails ? errorDetails + ' | ' : '') + lastError;
            }

          } else if (step.provider === 'groq') {
            var groqPayload = {
              model: step.model,
              messages: [
                { role: "system", content: "You are a strict, skeptical official football referee VAR fact-checker. Return ONLY valid JSON with keys: accepted, reason, stat, fee_amount, year, from_club, to_club, goals, club, appearances, nationality." },
                { role: "user", content: prompt }
              ],
              response_format: { type: "json_object" },
              temperature: 0.0
            };

            var groqRes = UrlFetchApp.fetch("https://api.groq.com/openai/v1/chat/completions", {
              method: "post",
              contentType: "application/json",
              headers: { "Authorization": "Bearer " + groqApiKey },
              payload: JSON.stringify(groqPayload),
              muteHttpExceptions: true
            });

            var gCode = groqRes.getResponseCode();
            var gText = groqRes.getContentText();
            rawResponse = gText;

            if (gCode === 200) {
              var gJson = JSON.parse(gText);
              var rawContent = gJson.choices && gJson.choices[0] && gJson.choices[0].message ? gJson.choices[0].message.content : '{}';
              var parsedG = parseVarJsonResponse(rawContent);
              if (parsedG && typeof parsedG.accepted === 'boolean') {
                modelUsed = step.model;
                varResult.accepted = parsedG.accepted === true;
                varResult.reason = parsedG.reason || (varResult.accepted ? 'Appeal accepted after VAR review!' : 'The VAR challenge was rejected and the on-pitch ruling stands.');
                varResult.stat = parsedG.stat || '';
                varResult.fee_amount = parsedG.fee_amount || 0;
                varResult.year = parsedG.year ? parsedG.year.toString() : '';
                varResult.from_club = parsedG.from_club || '';
                varResult.to_club = parsedG.to_club || '';
                varResult.goals = parsedG.goals || 0;
                varResult.club = parsedG.club || '';
                varResult.appearances = parsedG.appearances ? parsedG.appearances.toString() : '';
                varResult.nationality = parsedG.nationality || '';
                success = true;
                break;
              } else {
                lastError = "Groq " + step.model + " 200 invalid JSON: " + rawContent.substring(0, 150);
                errorDetails = (errorDetails ? errorDetails + ' | ' : '') + lastError;
              }
            } else {
              lastError = "Groq " + step.model + " HTTP " + gCode + ": " + gText.substring(0, 150);
              errorDetails = (errorDetails ? errorDetails + ' | ' : '') + lastError;
            }
          }
        } catch (stepErr) {
          lastError = (step.provider + "/" + step.model) + " Exception: " + stepErr.toString();
          errorDetails = (errorDetails ? errorDetails + ' | ' : '') + lastError;
        }
      }

      if (!success) {
        varResult.reason = 'VAR review service error: All waterfall models failed. Last error: ' + lastError;
        varResult.isError = true;
      } else if (varResult.accepted && !varResult.isError) {
        // Deterministic Programmatic Threshold & Anti-Hallucination Guards
        if (gameId === 'top_transfers') {
          var cutoffFee = parseCutoffFeeFromContext(context);
          var actualFee = parseNumericFee(varResult.fee_amount, (varResult.stat || '') + ' ' + (varResult.reason || ''));
          if (cutoffFee > 0 && actualFee > 0 && actualFee < cutoffFee) {
            varResult.accepted = false;
            var feeM = (actualFee / 1000000).toFixed(1);
            var cutoffM = (cutoffFee / 1000000).toFixed(1);
            varResult.reason = "Transfer fee of €" + feeM + "M for " + guess + " is below the 10th-place cutoff fee of €" + cutoffM + "M.";
          }
        } else if (gameId === 'top_scorers') {
          var cutoffGoals = parseCutoffGoalsFromContext(context);
          var actualGoals = parseInt(varResult.goals, 10) || 0;
          if (!actualGoals && (varResult.stat || varResult.reason)) {
            var gMatch = ((varResult.stat || '') + ' ' + (varResult.reason || '')).match(/(\d+)\s*goals?/i);
            if (gMatch) actualGoals = parseInt(gMatch[1], 10);
          }
          if (cutoffGoals > 0 && actualGoals > 0 && actualGoals < cutoffGoals) {
            varResult.accepted = false;
            varResult.reason = guess + " scored " + actualGoals + " goals, which is below the 10th-place cutoff of " + cutoffGoals + " goals.";
          }
        }
      }

    } catch (apiErr) {
      varResult.reason = 'VAR evaluation exception: ' + apiErr.toString();
      varResult.isError = true;
      errorDetails = (errorDetails ? errorDetails + ' | ' : '') + apiErr.toString();
    }
  }

  // Log to "VAR Reviews" tab in Google Sheet
  try {
    var doc = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = doc.getSheetByName('VAR Reviews');
    if (!sheet) {
      sheet = doc.insertSheet('VAR Reviews');
    }

    var varHeaders = ensureVarReviewsHeaders(sheet);
    var varRow = buildVarReviewsRow(varHeaders, {
      timestamp: timestamp,
      visitorId: visitorId,
      sessionId: sessionId,
      gameId: gameId,
      puzzleNum: puzzleNum,
      theme: theme,
      guess: guess,
      decision: varResult.isError ? 'ERROR' : (varResult.accepted ? 'ACCEPTED (OVERRULED)' : 'REJECTED (STANDS)'),
      reason: varResult.reason,
      stat: varResult.stat,
      fee_amount: varResult.fee_amount,
      year: varResult.year,
      from_club: varResult.from_club,
      to_club: varResult.to_club,
      goals: varResult.goals,
      appearances: varResult.appearances,
      nationality: varResult.nationality,
      modelUsed: modelUsed,
      prompt: prompt,
      rawResponse: rawResponse,
      requestPayload: JSON.stringify(payload),
      errorDetails: errorDetails,
      url: url
    });

    sheet.appendRow(varRow);

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
            varResult.to_club || varResult.club || theme || '',
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
    to_club: varResult.to_club,
    goals: varResult.goals,
    club: varResult.club,
    appearances: varResult.appearances,
    nationality: varResult.nationality,
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

/**
 * Robust JSON parser for VAR model responses.
 * Handles markdown code fences, embedded reasoning text, and extracts pure JSON object.
 */
function parseVarJsonResponse(text) {
  if (!text || typeof text !== 'string') return null;
  var clean = text.trim();
  // Strip markdown code fences if present: ```json ... ``` or ``` ... ```
  clean = clean.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '').trim();
  try {
    return JSON.parse(clean);
  } catch (e1) {
    // Extract outermost JSON object substring {...}
    var firstOpen = clean.indexOf('{');
    var lastClose = clean.lastIndexOf('}');
    if (firstOpen !== -1 && lastClose !== -1 && lastClose > firstOpen) {
      var candidate = clean.substring(firstOpen, lastClose + 1);
      try {
        return JSON.parse(candidate);
      } catch (e2) {
        return null;
      }
    }
    return null;
  }
}

/**
 * Parses numeric transfer fee from number or string representation with units (e.g. 17500000, "€17.5M", "35m").
 */
function parseNumericFee(feeVal, textFallback) {
  if (typeof feeVal === 'number' && feeVal > 0) return feeVal;
  if (typeof feeVal === 'string' && feeVal.trim() !== '') {
    var str = feeVal.trim().toLowerCase();
    var m = str.match(/€?\s*([\d.]+)\s*(m(?:illion)?|k|b(?:illion)?)?/i);
    if (m) {
      var v = parseFloat(m[1]);
      var u = (m[2] || '').toLowerCase();
      if (u.startsWith('b')) v *= 1000000000;
      else if (u.startsWith('m') || v < 1000) v *= 1000000;
      else if (u.startsWith('k')) v *= 1000;
      return v;
    }
    var cleanNum = parseFloat(str.replace(/[^0-9.]/g, ''));
    if (!isNaN(cleanNum) && cleanNum > 0) {
      return cleanNum < 1000 ? cleanNum * 1000000 : cleanNum;
    }
  }
  if (textFallback && typeof textFallback === 'string') {
    var mText = textFallback.match(/€\s*([\d.]+)\s*(m(?:illion)?|k|b(?:illion)?)?/i);
    if (mText) {
      var vT = parseFloat(mText[1]);
      var uT = (mText[2] || '').toLowerCase();
      if (uT.startsWith('b')) vT *= 1000000000;
      else if (uT.startsWith('m') || vT < 1000) vT *= 1000000;
      else if (uT.startsWith('k')) vT *= 1000;
      return vT;
    }
  }
  return 0;
}

/**
 * Extracts 10th-place cutoff fee in euros from Extra Context string.
 */
function parseCutoffFeeFromContext(contextStr) {
  if (!contextStr || typeof contextStr !== 'string') return 0;
  var m = contextStr.match(/cutoff\s*(?:fee)?\s*(?:is)?\s*€?\s*([\d.]+)\s*(m(?:illion)?|k|b(?:illion)?)?/i);
  if (m) {
    var v = parseFloat(m[1]);
    var u = (m[2] || 'm').toLowerCase();
    if (u.startsWith('b')) v *= 1000000000;
    else if (u.startsWith('m') || v < 1000) v *= 1000000;
    else if (u.startsWith('k')) v *= 1000;
    return v;
  }
  return 0;
}

/**
 * Extracts 10th-place goals cutoff integer from Extra Context string.
 */
function parseCutoffGoalsFromContext(contextStr) {
  if (!contextStr || typeof contextStr !== 'string') return 0;
  var m = contextStr.match(/cutoff\s*(?:is)?\s*(\d+)\s*goals?/i);
  if (m) {
    return parseInt(m[1], 10);
  }
  return 0;
}

